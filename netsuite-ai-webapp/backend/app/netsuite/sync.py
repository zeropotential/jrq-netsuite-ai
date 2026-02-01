"""
NetSuite to PostgreSQL sync service.

Pulls data from NetSuite via JDBC and stores in local PostgreSQL tables.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
import uuid

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models.netsuite_mirror import (
    NSAccount,
    NSSyncLog,
    NSTransaction,
    NSTransactionLine,
)
from app.netsuite.jdbc import JdbcError, run_query

logger = logging.getLogger(__name__)


def _create_sync_log(db: Session, connection_id: str, table_name: str) -> NSSyncLog:
    """Create a sync log entry."""
    sync_log = NSSyncLog(
        connection_id=uuid.UUID(connection_id),
        table_name=table_name,
        status="running",
    )
    db.add(sync_log)
    db.flush()
    return sync_log


def _complete_sync_log(
    db: Session,
    sync_log: NSSyncLog,
    status: str,
    rows_synced: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update sync log with completion status."""
    sync_log.status = status
    sync_log.completed_at = datetime.utcnow()
    sync_log.rows_synced = rows_synced
    sync_log.error_message = error_message
    db.flush()


def sync_accounts(db: Session, connection_id: str) -> dict[str, Any]:
    """
    Sync Account table from NetSuite to PostgreSQL.
    
    Fetches all accounts (typically not many).
    Uses SELECT * to get whatever columns exist and maps dynamically.
    """
    sync_log = _create_sync_log(db, connection_id, "account")
    
    # Define which columns our PostgreSQL table has
    pg_columns = {
        "id", "acctnumber", "name", "fullname", "type", "accttype",
        "specialaccttype", "isinactive", "issummary", "parent", "currency"
    }
    
    try:
        # Query NetSuite for accounts - use SELECT * to get all available columns
        sql = "SELECT * FROM account"
        
        logger.info("Syncing accounts from NetSuite...")
        result = run_query(db, connection_id, sql, limit=10000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "account"}
        
        # Map columns dynamically - only include columns that exist in both
        col_lower = [c.lower() for c in columns]
        available_cols = set(col_lower) & pg_columns
        
        if "id" not in available_cols:
            raise ValueError("Account table must have 'id' column")
        
        logger.info(f"Account columns available: {available_cols}, NetSuite columns: {col_lower}")
        
        # Prepare records with only columns that exist in our PG table
        records = []
        for row in rows:
            full_record = dict(zip(col_lower, row))
            # Only include columns that exist in our PG table
            record = {k: v for k, v in full_record.items() if k in pg_columns}
            # Handle lastmodifieddate -> ns_last_modified mapping if present
            if "lastmodifieddate" in full_record:
                record["ns_last_modified"] = full_record["lastmodifieddate"]
            records.append(record)
        
        # Build dynamic upsert - only update columns that exist
        stmt = insert(NSAccount).values(records)
        update_set = {"synced_at": text("now()")}
        for col in available_cols:
            if col != "id":  # Don't update the primary key
                update_set[col] = getattr(stmt.excluded, col)
        if "ns_last_modified" in [r.keys() for r in records][0] if records else False:
            update_set["ns_last_modified"] = stmt.excluded.ns_last_modified
        
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=update_set
        )
        db.execute(stmt)
        
        _complete_sync_log(db, sync_log, "success", rows_synced=len(records))
        logger.info(f"Synced {len(records)} accounts")
        
        return {"status": "success", "rows_synced": len(records), "table": "account"}
        
    except JdbcError as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.error(f"Failed to sync accounts: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "account"}
    except Exception as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.exception(f"Unexpected error syncing accounts: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "account"}


def sync_transactions(
    db: Session,
    connection_id: str,
    months_back: int = 3,
) -> dict[str, Any]:
    """
    Sync Transaction table from NetSuite to PostgreSQL.
    
    Only fetches transactions created in the last N months.
    """
    sync_log = _create_sync_log(db, connection_id, "transaction")
    
    try:
        # Calculate date range (last N months)
        cutoff_date = datetime.utcnow() - timedelta(days=months_back * 30)
        date_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Query NetSuite for transactions
        sql = f"""
            SELECT 
                id, tranid, type, trandate, status, posting, entity,
                duedate, closedate, createddate, lastmodifieddate,
                foreigntotal, currency, exchangerate, memo
            FROM transaction
            WHERE createddate >= TO_DATE('{date_str}', 'YYYY-MM-DD')
        """
        
        logger.info(f"Syncing transactions from NetSuite (created since {date_str})...")
        result = run_query(db, connection_id, sql, limit=100000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "transaction"}
        
        # Prepare data for upsert
        col_lower = [c.lower() for c in columns]
        records = []
        for row in rows:
            record = dict(zip(col_lower, row))
            records.append(record)
        
        # Upsert into PostgreSQL
        stmt = insert(NSTransaction).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "tranid": stmt.excluded.tranid,
                "type": stmt.excluded.type,
                "trandate": stmt.excluded.trandate,
                "status": stmt.excluded.status,
                "posting": stmt.excluded.posting,
                "entity": stmt.excluded.entity,
                "duedate": stmt.excluded.duedate,
                "closedate": stmt.excluded.closedate,
                "createddate": stmt.excluded.createddate,
                "lastmodifieddate": stmt.excluded.lastmodifieddate,
                "foreigntotal": stmt.excluded.foreigntotal,
                "currency": stmt.excluded.currency,
                "exchangerate": stmt.excluded.exchangerate,
                "memo": stmt.excluded.memo,
                "synced_at": text("now()"),
            }
        )
        db.execute(stmt)
        
        _complete_sync_log(db, sync_log, "success", rows_synced=len(records))
        logger.info(f"Synced {len(records)} transactions")
        
        return {"status": "success", "rows_synced": len(records), "table": "transaction"}
        
    except JdbcError as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.error(f"Failed to sync transactions: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "transaction"}
    except Exception as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.exception(f"Unexpected error syncing transactions: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "transaction"}


def sync_transaction_lines(
    db: Session,
    connection_id: str,
    months_back: int = 3,
) -> dict[str, Any]:
    """
    Sync TransactionLine table from NetSuite to PostgreSQL.
    
    Only fetches lines for transactions created in the last N months.
    """
    sync_log = _create_sync_log(db, connection_id, "transactionline")
    
    # Define which columns our PostgreSQL table has
    pg_columns = {
        "id", "transaction", "linesequencenumber", "item",
        "amount", "netamount", "foreignamount", "quantity",
        "account", "department", "class", "location", "memo"
    }
    
    try:
        # Calculate date range (last N months)
        cutoff_date = datetime.utcnow() - timedelta(days=months_back * 30)
        date_str = cutoff_date.strftime("%Y-%m-%d")
        
        # First, get transaction IDs from the date range
        trans_sql = f"""
            SELECT id FROM transaction
            WHERE createddate >= TO_DATE('{date_str}', 'YYYY-MM-DD')
        """
        
        logger.info(f"Getting transaction IDs since {date_str}...")
        trans_result = run_query(db, connection_id, trans_sql, limit=100000)
        trans_ids = [row[0] for row in trans_result.get("rows", [])]
        
        if not trans_ids:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "transactionline"}
        
        logger.info(f"Found {len(trans_ids)} transactions, fetching lines...")
        
        # Query transaction lines for those transactions - batch if too many
        all_records = []
        batch_size = 1000  # IDs per query
        
        for i in range(0, len(trans_ids), batch_size):
            batch_ids = trans_ids[i:i + batch_size]
            ids_str = ", ".join(str(tid) for tid in batch_ids)
            
            # Use SELECT * to get all available columns
            sql = f"""
                SELECT * FROM transactionline
                WHERE transaction IN ({ids_str})
            """
            
            result = run_query(db, connection_id, sql, limit=500000)
            rows = result.get("rows", [])
            columns = result.get("columns", [])
            
            if rows:
                col_lower = [c.lower() for c in columns]
                available_cols = set(col_lower) & pg_columns
                
                logger.info(f"TransactionLine columns available: {available_cols}, NetSuite columns: {col_lower}")
                
                for row in rows:
                    full_record = dict(zip(col_lower, row))
                    # Only include columns that exist in our PG table
                    record = {k: v for k, v in full_record.items() if k in pg_columns}
                    # Rename 'class' to 'class_' for SQLAlchemy (class is reserved)
                    if "class" in record:
                        record["class_"] = record.pop("class")
                    all_records.append(record)
        
        if not all_records:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "transactionline"}
        
        if "id" not in (set(all_records[0].keys()) | {"class_"} - {"class"}):
            raise ValueError("TransactionLine must have 'id' column")
        
        # Get the available columns from first record for dynamic upsert
        record_cols = set(all_records[0].keys()) - {"id"}  # Exclude id from update
        
        # Upsert into PostgreSQL - batch in chunks
        insert_batch_size = 5000
        total_synced = 0
        
        for i in range(0, len(all_records), insert_batch_size):
            batch = all_records[i:i + insert_batch_size]
            
            stmt = insert(NSTransactionLine).values(batch)
            
            # Build dynamic update set based on available columns
            update_set = {"synced_at": text("now()")}
            for col in record_cols:
                if col == "class_":
                    update_set["class_"] = stmt.excluded.class_
                else:
                    update_set[col] = getattr(stmt.excluded, col)
            
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_set
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // insert_batch_size + 1}: {len(batch)} lines (total: {total_synced})")
        
        _complete_sync_log(db, sync_log, "success", rows_synced=total_synced)
        logger.info(f"Synced {total_synced} transaction lines")
        
        return {"status": "success", "rows_synced": total_synced, "table": "transactionline"}
        
    except JdbcError as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.error(f"Failed to sync transaction lines: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "transactionline"}
    except Exception as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.exception(f"Unexpected error syncing transaction lines: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "transactionline"}


def sync_all(
    db: Session,
    connection_id: str,
    months_back: int = 3,
) -> dict[str, Any]:
    """
    Sync all tables from NetSuite to PostgreSQL.
    
    Order matters: accounts first, then transactions, then lines.
    """
    results = {}
    
    # Sync accounts (no date filter)
    results["account"] = sync_accounts(db, connection_id)
    
    # Sync transactions (date filter)
    results["transaction"] = sync_transactions(db, connection_id, months_back)
    
    # Sync transaction lines (date filter via join)
    results["transactionline"] = sync_transaction_lines(db, connection_id, months_back)
    
    # Overall status
    all_success = all(r.get("status") == "success" for r in results.values())
    
    return {
        "status": "success" if all_success else "partial",
        "tables": results,
        "total_rows": sum(r.get("rows_synced", 0) for r in results.values()),
    }


def get_sync_status(db: Session, connection_id: str) -> dict[str, Any]:
    """Get the latest sync status for each table."""
    from sqlalchemy import func
    
    # Get latest sync for each table
    subq = (
        db.query(
            NSSyncLog.table_name,
            func.max(NSSyncLog.started_at).label("latest"),
        )
        .filter(NSSyncLog.connection_id == connection_id)
        .group_by(NSSyncLog.table_name)
        .subquery()
    )
    
    logs = (
        db.query(NSSyncLog)
        .join(
            subq,
            (NSSyncLog.table_name == subq.c.table_name) &
            (NSSyncLog.started_at == subq.c.latest)
        )
        .filter(NSSyncLog.connection_id == connection_id)
        .all()
    )
    
    result = {}
    for log in logs:
        result[log.table_name] = {
            "status": log.status,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "rows_synced": log.rows_synced,
            "error_message": log.error_message,
        }
    
    # Get row counts from mirror tables
    counts = {
        "account": db.query(func.count(NSAccount.id)).scalar() or 0,
        "transaction": db.query(func.count(NSTransaction.id)).scalar() or 0,
        "transactionline": db.query(func.count(NSTransactionLine.id)).scalar() or 0,
    }
    
    return {
        "connection_id": connection_id,
        "sync_logs": result,
        "row_counts": counts,
    }
