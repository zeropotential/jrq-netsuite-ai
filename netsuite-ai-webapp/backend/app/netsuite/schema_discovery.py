"""
Dynamic schema discovery for NetSuite SuiteAnalytics Connect.

Fetches table and column metadata from OA_TABLES and OA_COLUMNS system tables,
caches the results, and provides schema context for LLM SQL generation.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from sqlalchemy.orm import Session

from app.netsuite.jdbc import run_query, JdbcError

logger = logging.getLogger(__name__)

# Cache TTL in seconds (2 days)
SCHEMA_CACHE_TTL = 172800


@dataclass
class ColumnInfo:
    """Column metadata from OA_COLUMNS."""
    name: str
    data_type: str
    nullable: bool = True
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    description: str = ""


@dataclass
class TableInfo:
    """Table metadata from OA_TABLES with columns."""
    name: str
    table_type: str = ""
    description: str = ""
    columns: dict[str, ColumnInfo] = field(default_factory=dict)


@dataclass
class SchemaCache:
    """Cached schema data with timestamp."""
    tables: dict[str, TableInfo]
    fetched_at: float
    connection_id: str


# Global cache storage
_schema_cache: dict[str, SchemaCache] = {}
_cache_lock = Lock()


def _is_cache_valid(cache: SchemaCache | None) -> bool:
    """Check if cache is still valid based on TTL."""
    if cache is None:
        return False
    return (time.time() - cache.fetched_at) < SCHEMA_CACHE_TTL


def fetch_tables(db: Session, connection_id: str, table_filter: list[str] | None = None) -> list[dict[str, Any]]:
    """Fetch tables from OA_TABLES system table, optionally filtered by name."""
    logger.info("Fetching tables from OA_TABLES...")
    try:
        if table_filter:
            # Build IN clause with escaped table names
            safe_names = [f"'{name.replace(chr(39), chr(39)+chr(39))}'" for name in table_filter]
            in_clause = ", ".join(safe_names)
            sql = f"SELECT * FROM OA_TABLES WHERE TABLE_NAME IN ({in_clause})"
            logger.info(f"Querying OA_TABLES with filter: {table_filter}")
        else:
            sql = "SELECT * FROM OA_TABLES"
        
        result = run_query(db, connection_id, sql, limit=5000)
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        # Convert to list of dicts
        tables = []
        for row in rows:
            table_dict = dict(zip(columns, row))
            tables.append(table_dict)
        
        logger.info(f"Fetched {len(tables)} tables from OA_TABLES")
        return tables
    except JdbcError as e:
        logger.error(f"Failed to fetch OA_TABLES: {e}")
        raise


def fetch_columns_for_tables(db: Session, connection_id: str, table_names: list[str]) -> dict[str, list[dict[str, Any]]]:
    """
    Fetch columns for multiple tables.
    
    First tries a single IN clause query for efficiency.
    If that fails/times out, falls back to individual table queries.
    """
    if not table_names:
        return {}
    
    # Try batch query first (faster if it works)
    try:
        # Build IN clause with escaped table names
        safe_names = [f"'{name.replace(chr(39), chr(39)+chr(39))}'" for name in table_names]
        in_clause = ", ".join(safe_names)
        sql = f"SELECT * FROM OA_COLUMNS WHERE TABLE_NAME IN ({in_clause})"
        
        logger.info(f"Fetching columns for {len(table_names)} tables in batch query...")
        result = run_query(db, connection_id, sql, limit=10000)
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        # Group columns by table name
        table_columns: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            col_dict = dict(zip(columns, row))
            table_name = col_dict.get("TABLE_NAME", "")
            if table_name:
                table_columns.setdefault(table_name, []).append(col_dict)
        
        logger.info(f"Batch query returned columns for {len(table_columns)} tables")
        return table_columns
        
    except JdbcError as e:
        logger.warning(f"Batch column query failed: {e}. Trying individual tables...")
        
        # Fall back to individual table queries
        table_columns: dict[str, list[dict[str, Any]]] = {}
        for table_name in table_names:
            try:
                cols = fetch_columns_for_table(db, connection_id, table_name)
                if cols:
                    table_columns[table_name] = cols
                    logger.info(f"Fetched {len(cols)} columns for {table_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch columns for {table_name}: {e}")
                # Continue with other tables
        
        return table_columns


def fetch_columns_for_table(db: Session, connection_id: str, table_name: str) -> list[dict[str, Any]]:
    """Fetch columns for a specific table from OA_COLUMNS."""
    try:
        # Use parameterized-style query (escape single quotes in table name)
        safe_table_name = table_name.replace("'", "''")
        sql = f"SELECT * FROM OA_COLUMNS WHERE TABLE_NAME = '{safe_table_name}'"
        result = run_query(db, connection_id, sql, limit=1000)
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        
        # Convert to list of dicts
        col_list = []
        for row in rows:
            col_dict = dict(zip(columns, row))
            col_list.append(col_dict)
        
        return col_list
    except JdbcError as e:
        logger.warning(f"Failed to fetch columns for {table_name}: {e}")
        return []


def discover_schema(
    db: Session,
    connection_id: str,
    force_refresh: bool = False,
    table_filter: list[str] | None = None
) -> dict[str, TableInfo]:
    """
    Discover and cache the database schema.
    
    Args:
        db: Database session
        connection_id: JDBC connection ID
        force_refresh: Force cache refresh even if valid
        table_filter: Optional list of table names to fetch (for faster loading)
    
    Returns:
        Dictionary of table name -> TableInfo
    """
    global _schema_cache
    
    with _cache_lock:
        # Check cache first
        cache = _schema_cache.get(connection_id)
        if not force_refresh and _is_cache_valid(cache):
            # If we have a table_filter, check if ALL requested tables are already cached
            if table_filter:
                # Normalize table names for comparison (case-insensitive)
                cached_tables_lower = {t.lower() for t in cache.tables.keys()}
                requested_lower = {t.lower() for t in table_filter}
                missing_tables = requested_lower - cached_tables_lower
                
                if not missing_tables:
                    # All requested tables are already cached
                    logger.debug("All requested tables already cached for connection %s", connection_id)
                    return cache.tables
                else:
                    # Some tables are missing - continue to fetch them
                    logger.info(f"Cache hit but missing tables: {missing_tables}. Will fetch and merge.")
            else:
                # No filter - just return full cache
                logger.debug("Using cached schema for connection %s", connection_id)
                return cache.tables
    
    logger.info("Discovering schema for connection %s...", connection_id)
    start_time = time.time()
    
    # Build table info dictionary
    tables: dict[str, TableInfo] = {}
    
    # Get table names to process
    if table_filter:
        # Fetch only the filtered tables from OA_TABLES
        tables_data = fetch_tables(db, connection_id, table_filter=table_filter)
        table_names_to_process = [t.get("TABLE_NAME", "") for t in tables_data if t.get("TABLE_NAME")]
        logger.info(f"Using table filter: requested {len(table_filter)}, found {len(table_names_to_process)} tables in OA_TABLES")
    else:
        # Fetch all tables from OA_TABLES
        tables_data = fetch_tables(db, connection_id)
        table_names_to_process = [t.get("TABLE_NAME", "") for t in tables_data if t.get("TABLE_NAME")]
    
    if not table_names_to_process:
        logger.warning("No tables to process")
        return tables
    
    logger.info(f"Processing tables: {table_names_to_process[:10]}..." if len(table_names_to_process) > 10 else f"Processing tables: {table_names_to_process}")
    
    # Fetch ALL columns for ALL tables in a SINGLE query (much faster!)
    all_columns = fetch_columns_for_tables(db, connection_id, table_names_to_process)
    
    logger.info(f"Column query returned data for tables: {list(all_columns.keys())}")
    
    # Build TableInfo for each table
    for table_name in table_names_to_process:
        columns_data = all_columns.get(table_name, [])
        
        table_info = TableInfo(
            name=table_name,
            table_type="TABLE",
            description=""
        )
        
        for col_data in columns_data:
            col_name = col_data.get("COLUMN_NAME", "")
            if not col_name:
                continue
                
            col_info = ColumnInfo(
                name=col_name,
                data_type=col_data.get("TYPE_NAME", "UNKNOWN"),
                nullable=col_data.get("NULLABLE", 1) == 1,
                length=col_data.get("COLUMN_SIZE"),
                precision=col_data.get("DECIMAL_DIGITS"),
                scale=col_data.get("NUM_PREC_RADIX"),
                description=col_data.get("REMARKS", "") or ""
            )
            table_info.columns[col_name] = col_info
        
        if table_info.columns:  # Only add tables that have columns
            tables[table_name] = table_info
            logger.debug(f"Discovered table {table_name} with {len(table_info.columns)} columns")
    
    elapsed = time.time() - start_time
    logger.info(f"Schema discovery completed in {elapsed:.2f}s: {len(tables)} tables")
    
    # Only cache if we actually found tables (don't cache empty results)
    if tables:
        with _cache_lock:
            # ADDITIVE CACHING: Merge new tables with existing cached tables
            existing_cache = _schema_cache.get(connection_id)
            if existing_cache and not force_refresh:
                # Merge: existing tables + new tables (new tables overwrite if same name)
                merged_tables = dict(existing_cache.tables)  # Copy existing
                merged_tables.update(tables)  # Add/overwrite with new
                logger.info(f"Merging {len(tables)} new tables with {len(existing_cache.tables)} existing. Total: {len(merged_tables)}")
            else:
                merged_tables = tables
            
            _schema_cache[connection_id] = SchemaCache(
                tables=merged_tables,
                fetched_at=time.time(),
                connection_id=connection_id
            )
        logger.info(f"Cached {len(merged_tables)} total tables for connection {connection_id}")
    else:
        logger.warning(f"No tables discovered - NOT caching empty result for {connection_id}")
    
    # Return the full merged cache, not just the new tables
    with _cache_lock:
        final_cache = _schema_cache.get(connection_id)
        return final_cache.tables if final_cache else tables


def get_cached_schema(connection_id: str) -> dict[str, TableInfo] | None:
    """Get cached schema without refreshing."""
    with _cache_lock:
        cache = _schema_cache.get(connection_id)
        if cache and _is_cache_valid(cache):
            return cache.tables
    return None


def clear_schema_cache(connection_id: str | None = None) -> None:
    """Clear schema cache for a connection or all connections."""
    global _schema_cache
    with _cache_lock:
        if connection_id:
            _schema_cache.pop(connection_id, None)
        else:
            _schema_cache.clear()
    logger.info("Schema cache cleared")


def schema_to_llm_context(tables: dict[str, TableInfo], max_tables: int = 50) -> str:
    """
    Convert schema to a compact text format for LLM context.
    
    Args:
        tables: Dictionary of TableInfo objects
        max_tables: Maximum number of tables to include
    
    Returns:
        Formatted schema string for LLM consumption
    """
    lines = ["LIVE DATABASE SCHEMA (from OA_TABLES/OA_COLUMNS):"]
    lines.append("=" * 50)
    
    # Sort tables alphabetically and limit
    sorted_tables = sorted(tables.keys())[:max_tables]
    
    for table_name in sorted_tables:
        table = tables[table_name]
        lines.append(f"\nTABLE: {table.name}")
        if table.description:
            lines.append(f"  Description: {table.description}")
        
        if table.columns:
            lines.append("  Columns:")
            for col_name, col in sorted(table.columns.items()):
                nullable = "NULL" if col.nullable else "NOT NULL"
                type_info = col.data_type
                if col.length:
                    type_info += f"({col.length})"
                lines.append(f"    - {col_name}: {type_info} {nullable}")
    
    if len(tables) > max_tables:
        lines.append(f"\n... and {len(tables) - max_tables} more tables")
    
    return "\n".join(lines)


def get_transaction_tables_schema(db: Session, connection_id: str) -> str:
    """
    Get schema specifically for transaction-related tables.
    This is optimized for common transaction queries.
    """
    # Focus on key transaction tables
    transaction_tables = [
        "TRANSACTIONS",
        "TRANSACTION_LINES",
        "TRANSACTION_LINKS",
        "TRANSACTION_HISTORY",
        "TRANSACTION_ADDRESS",
        "ACCOUNTS",
        "ITEMS",
        "ENTITIES",
        "SUBSIDIARIES",
        "DEPARTMENTS",
        "CLASSES",
        "LOCATIONS"
    ]
    
    tables = discover_schema(db, connection_id, table_filter=transaction_tables)
    return schema_to_llm_context(tables)
