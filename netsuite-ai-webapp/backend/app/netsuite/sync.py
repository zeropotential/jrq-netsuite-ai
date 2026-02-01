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
    """
    sync_log = _create_sync_log(db, connection_id, "account")
    
    try:
        # Query NetSuite for accounts
        sql = """
            SELECT 
                id, acctnumber, name, fullname, type, accttype, 
                specialaccttype, isinactive, issummary, parent, currency,
                lastmodifieddate
            FROM account
        """
        
        logger.info("Syncing accounts from NetSuite...")
        result = run_query(db, connection_id, sql, limit=10000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "account"}
        
        # Prepare data for upsert
        col_lower = [c.lower() for c in columns]
        records = []
        for row in rows:
            record = dict(zip(col_lower, row))
            # Map lastmodifieddate to ns_last_modified
            record["ns_last_modified"] = record.pop("lastmodifieddate", None)
            records.append(record)
        
        # Upsert into PostgreSQL (insert or update on conflict)
        stmt = insert(NSAccount).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "acctnumber": stmt.excluded.acctnumber,
                "name": stmt.excluded.name,
                "fullname": stmt.excluded.fullname,
                "type": stmt.excluded.type,
                "accttype": stmt.excluded.accttype,
                "specialaccttype": stmt.excluded.specialaccttype,
                "isinactive": stmt.excluded.isinactive,
                "issummary": stmt.excluded.issummary,
                "parent": stmt.excluded.parent,
                "currency": stmt.excluded.currency,
                "ns_last_modified": stmt.excluded.ns_last_modified,
                "synced_at": text("now()"),
            }
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
    
    try:
        # Calculate date range (last N months)
        cutoff_date = datetime.utcnow() - timedelta(days=months_back * 30)
        date_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Query NetSuite for transaction lines (join with transaction for date filter)
        sql = f"""
            SELECT 
                TL.id, TL.transaction, TL.linesequencenumber, TL.item,
                TL.amount, TL.netamount, TL.foreignamount, TL.quantity,
                TL.account, TL.department, TL.class, TL.location, TL.memo
            FROM transactionline TL
            INNER JOIN transaction T ON TL.transaction = T.id
            WHERE T.createddate >= TO_DATE('{date_str}', 'YYYY-MM-DD')
        """
        
        logger.info(f"Syncing transaction lines from NetSuite (for transactions created since {date_str})...")
        result = run_query(db, connection_id, sql, limit=500000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "transactionline"}
        
        # Prepare data for upsert
        col_lower = [c.lower() for c in columns]
        records = []
        for row in rows:
            record = dict(zip(col_lower, row))
            # Rename 'class' to 'class_' for SQLAlchemy (class is reserved)
            if "class" in record:
                record["class_"] = record.pop("class")
            records.append(record)
        
        # Upsert into PostgreSQL - batch in chunks to avoid memory issues
        batch_size = 5000
        total_synced = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            stmt = insert(NSTransactionLine).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "transaction": stmt.excluded.transaction,
                    "linesequencenumber": stmt.excluded.linesequencenumber,
                    "item": stmt.excluded.item,
                    "amount": stmt.excluded.amount,
                    "netamount": stmt.excluded.netamount,
                    "foreignamount": stmt.excluded.foreignamount,
                    "quantity": stmt.excluded.quantity,
                    "account": stmt.excluded.account,
                    "department": stmt.excluded.department,
                    "class": stmt.excluded.class_,
                    "location": stmt.excluded.location,
                    "memo": stmt.excluded.memo,
                    "synced_at": text("now()"),
                }
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} lines (total: {total_synced})")
        
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
