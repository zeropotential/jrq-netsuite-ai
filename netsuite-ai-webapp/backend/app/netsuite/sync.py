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
    NSCustomer,
    NSEmployee,
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
        # Batch insert for safety (PostgreSQL has 65535 param limit)
        batch_size = 2000
        total_synced = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            stmt = insert(NSAccount).values(batch)
            update_set = {"synced_at": text("now()")}
            for col in available_cols:
                if col != "id":  # Don't update the primary key
                    update_set[col] = getattr(stmt.excluded, col)
            if "ns_last_modified" in batch[0].keys() if batch else False:
                update_set["ns_last_modified"] = stmt.excluded.ns_last_modified
            
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_set
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} accounts (total: {total_synced})")
        
        db.commit()
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
                foreigntotal, foreignamountpaid, foreignamountunpaid,
                currency, exchangerate, memo
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
        
        # Upsert into PostgreSQL in batches (PostgreSQL has 65535 param limit)
        # With 17 columns, batch size of 3000 = 51000 params (safe margin)
        BATCH_SIZE = 3000
        total_synced = 0
        
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            stmt = insert(NSTransaction).values(batch)
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
                    "foreignamountpaid": stmt.excluded.foreignamountpaid,
                    "foreignamountunpaid": stmt.excluded.foreignamountunpaid,
                    "currency": stmt.excluded.currency,
                    "exchangerate": stmt.excluded.exchangerate,
                    "memo": stmt.excluded.memo,
                    "synced_at": text("now()"),
                }
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // BATCH_SIZE + 1}: {len(batch)} transactions (total: {total_synced})")
        
        db.commit()
        _complete_sync_log(db, sync_log, "success", rows_synced=len(records))
        logger.info(f"Synced {len(records)} transactions total")
        
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
                    # Keep 'class' as the key - it's the actual DB column name
                    record = {k: v for k, v in full_record.items() if k in pg_columns}
                    all_records.append(record)
        
        if not all_records:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "transactionline"}
        
        if "id" not in all_records[0].keys():
            raise ValueError("TransactionLine must have 'id' column")
        
        # Deduplicate records by id (keep last occurrence)
        # This prevents "ON CONFLICT DO UPDATE command cannot affect row a second time"
        seen_ids = {}
        for record in all_records:
            seen_ids[record["id"]] = record
        all_records = list(seen_ids.values())
        logger.info(f"Deduplicated to {len(all_records)} unique transaction lines")
        
        # Get the available columns from first record for dynamic upsert
        record_cols = set(all_records[0].keys()) - {"id"}  # Exclude id from update
        
        # Upsert into PostgreSQL - batch in chunks (PostgreSQL has 65535 param limit)
        insert_batch_size = 2000
        total_synced = 0
        
        for i in range(0, len(all_records), insert_batch_size):
            batch = all_records[i:i + insert_batch_size]
            
            stmt = insert(NSTransactionLine).values(batch)
            
            # Build dynamic update set based on available columns
            # Use actual DB column names (not Python attribute names)
            update_set = {"synced_at": text("now()")}
            for col in record_cols:
                # Access excluded columns by DB column name
                update_set[col] = stmt.excluded[col]
            
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


def sync_employees(db: Session, connection_id: str) -> dict[str, Any]:
    """
    Sync Employee table from NetSuite to PostgreSQL.
    
    Fetches all employees. Uses SELECT * for dynamic column mapping.
    """
    sync_log = _create_sync_log(db, connection_id, "employee")
    
    # Define which columns our PostgreSQL table has
    pg_columns = {
        "id", "entityid", "firstname", "lastname", "email",
        "isinactive", "department", "class", "location", "subsidiary",
        "supervisor", "title", "hiredate", "releasedate"
    }
    
    try:
        sql = "SELECT * FROM employee"
        
        logger.info("Syncing employees from NetSuite...")
        result = run_query(db, connection_id, sql, limit=50000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "employee"}
        
        col_lower = [c.lower() for c in columns]
        available_cols = set(col_lower) & pg_columns
        
        if "id" not in available_cols:
            raise ValueError("Employee table must have 'id' column")
        
        logger.info(f"Employee columns available: {available_cols}, NetSuite columns: {col_lower}")
        
        records = []
        for row in rows:
            full_record = dict(zip(col_lower, row))
            record = {k: v for k, v in full_record.items() if k in pg_columns}
            records.append(record)
        
        # Deduplicate by id
        seen_ids = {}
        for record in records:
            seen_ids[record["id"]] = record
        records = list(seen_ids.values())
        
        record_cols = set(records[0].keys()) - {"id"}
        
        # Batch insert for safety (PostgreSQL has 65535 param limit)
        batch_size = 2000
        total_synced = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            stmt = insert(NSEmployee).values(batch)
            update_set = {"synced_at": text("now()")}
            for col in record_cols:
                update_set[col] = stmt.excluded[col]
            
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_set
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} employees (total: {total_synced})")
        
        db.commit()
        _complete_sync_log(db, sync_log, "success", rows_synced=len(records))
        logger.info(f"Synced {len(records)} employees")
        
        return {"status": "success", "rows_synced": len(records), "table": "employee"}
        
    except JdbcError as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.error(f"Failed to sync employees: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "employee"}
    except Exception as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.exception(f"Unexpected error syncing employees: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "employee"}


def sync_customers(db: Session, connection_id: str) -> dict[str, Any]:
    """
    Sync Customer table from NetSuite to PostgreSQL.
    
    Fetches all customers. Uses SELECT * for dynamic column mapping.
    """
    sync_log = _create_sync_log(db, connection_id, "customer")
    
    # Define which columns our PostgreSQL table has
    pg_columns = {
        "id", "entityid", "companyname", "email", "phone",
        "isinactive", "category", "subsidiary", "salesrep",
        "balance", "creditlimit", "currency", "datecreated", "lastmodifieddate"
    }
    
    try:
        sql = "SELECT * FROM customer"
        
        logger.info("Syncing customers from NetSuite...")
        result = run_query(db, connection_id, sql, limit=100000)
        
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        if not rows:
            _complete_sync_log(db, sync_log, "success", rows_synced=0)
            return {"status": "success", "rows_synced": 0, "table": "customer"}
        
        col_lower = [c.lower() for c in columns]
        available_cols = set(col_lower) & pg_columns
        
        if "id" not in available_cols:
            raise ValueError("Customer table must have 'id' column")
        
        logger.info(f"Customer columns available: {available_cols}, NetSuite columns: {col_lower}")
        
        records = []
        for row in rows:
            full_record = dict(zip(col_lower, row))
            record = {k: v for k, v in full_record.items() if k in pg_columns}
            records.append(record)
        
        # Deduplicate by id
        seen_ids = {}
        for record in records:
            seen_ids[record["id"]] = record
        records = list(seen_ids.values())
        
        record_cols = set(records[0].keys()) - {"id"}
        
        # Batch insert for large datasets (PostgreSQL has 65535 param limit)
        batch_size = 2000
        total_synced = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            stmt = insert(NSCustomer).values(batch)
            update_set = {"synced_at": text("now()")}
            for col in record_cols:
                update_set[col] = stmt.excluded[col]
            
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_set
            )
            db.execute(stmt)
            total_synced += len(batch)
            logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} customers (total: {total_synced})")
        
        _complete_sync_log(db, sync_log, "success", rows_synced=total_synced)
        logger.info(f"Synced {total_synced} customers")
        
        return {"status": "success", "rows_synced": total_synced, "table": "customer"}
        
    except JdbcError as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.error(f"Failed to sync customers: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "customer"}
    except Exception as e:
        error_msg = str(e)
        _complete_sync_log(db, sync_log, "failed", error_message=error_msg)
        logger.exception(f"Unexpected error syncing customers: {error_msg}")
        return {"status": "error", "error": error_msg, "table": "customer"}


def sync_all(
    db: Session,
    connection_id: str,
    months_back: int = 3,
) -> dict[str, Any]:
    """
    Sync all tables from NetSuite to PostgreSQL.
    
    Order matters: accounts first, then employees, customers, transactions, then lines.
    """
    results = {}
    
    # Sync accounts (no date filter)
    results["account"] = sync_accounts(db, connection_id)
    
    # Sync employees (no date filter)
    results["employee"] = sync_employees(db, connection_id)
    
    # Sync customers (no date filter)
    results["customer"] = sync_customers(db, connection_id)
    
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
    
    # Get row counts from mirror tables (with error handling for missing tables)
    counts = {}
    table_models = [
        ("account", NSAccount),
        ("employee", NSEmployee),
        ("customer", NSCustomer),
        ("transaction", NSTransaction),
        ("transactionline", NSTransactionLine),
    ]
    for table_name, model in table_models:
        try:
            counts[table_name] = db.query(func.count(model.id)).scalar() or 0
        except Exception:
            counts[table_name] = 0  # Table might not exist yet
    
    return {
        "connection_id": connection_id,
        "sync_logs": result,
        "row_counts": counts,
    }
