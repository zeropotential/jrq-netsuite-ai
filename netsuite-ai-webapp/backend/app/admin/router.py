from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crypto.envelope import encrypt_secret
from app.db.models.netsuite import NetSuiteJdbcConnection
from app.db.models.secret import Secret
from app.db.session import get_db
from app.netsuite.jdbc import JdbcError, test_connection
from app.netsuite.schema_discovery import (
    discover_schema,
    clear_schema_cache,
    get_cached_schema,
    schema_to_llm_context,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class JdbcConnectionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    account_id: str = Field(..., min_length=2, max_length=64)
    role_id: str = Field(..., min_length=1, max_length=32)
    host: str = Field(..., min_length=3, max_length=255)
    port: int = Field(1708, ge=1, le=65535)
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class JdbcConnectionOut(BaseModel):
    id: str
    name: str
    account_id: str
    role_id: str
    host: str
    port: int
    username: str


@router.post("/jdbc-connections", response_model=JdbcConnectionOut)
def create_jdbc_connection(payload: JdbcConnectionCreate, db: Session = Depends(get_db)) -> JdbcConnectionOut:
    if not settings.app_kek_b64:
        raise HTTPException(status_code=400, detail="APP_KEK_B64 is not configured")

    aad = f"netsuite-jdbc:{payload.name}".encode()
    encrypted = encrypt_secret(
        plaintext=payload.password.encode(),
        kek_b64=settings.app_kek_b64,
        key_id=settings.app_key_id,
        aad=aad,
    )

    secret = Secret(
        purpose="netsuite_jdbc_password",
        key_id=encrypted.key_id,
        aad=encrypted.aad,
        wrapped_dek=encrypted.wrapped_dek,
        wrapped_dek_nonce=encrypted.wrapped_dek_nonce,
        data_nonce=encrypted.data_nonce,
        ciphertext=encrypted.ciphertext,
    )
    db.add(secret)
    db.flush()

    conn = NetSuiteJdbcConnection(
        name=payload.name,
        account_id=payload.account_id,
        role_id=payload.role_id,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password_secret_id=secret.id,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return JdbcConnectionOut(
        id=str(conn.id),
        name=conn.name,
        account_id=conn.account_id,
        role_id=conn.role_id,
        host=conn.host,
        port=conn.port,
        username=conn.username,
    )


@router.post("/jdbc-connections/{connection_id}/test")
def test_jdbc_connection(connection_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return test_connection(db, connection_id)
    except JdbcError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class SchemaDiscoveryRequest(BaseModel):
    force_refresh: bool = False
    table_filter: list[str] | None = None
    transaction_tables_only: bool = True  # Default to just transaction tables for speed
    quick_mode: bool = False  # Just check if tables exist, don't fetch all columns


# Default tables to fetch (transaction-focused for common queries)
# NOTE: These are the actual NetSuite table names (case-sensitive)
DEFAULT_TRANSACTION_TABLES = [
    "transaction",
    "transactionline", 
    "account",
    "customer",
]


class SchemaDiscoveryResponse(BaseModel):
    table_count: int
    tables: list[str]
    cached: bool
    llm_context_preview: str


class SchemaTestResponse(BaseModel):
    status: str
    oa_tables_accessible: bool
    sample_tables: list[str]
    error: str | None = None


@router.get("/jdbc-connections/{connection_id}/schema-test", response_model=SchemaTestResponse)
def test_schema_access(
    connection_id: str,
    db: Session = Depends(get_db)
) -> SchemaTestResponse:
    """
    Quick test to verify OA_TABLES is accessible.
    Much faster than full discovery - just fetches a few table names.
    """
    from app.netsuite.jdbc import run_query
    
    try:
        # Just fetch first 10 table names - quick sanity check
        # Note: NetSuite uses TOP N syntax (not ROWNUM or FETCH FIRST)
        result = run_query(
            db, 
            connection_id, 
            "SELECT TOP 10 TABLE_NAME FROM OA_TABLES",
            limit=10
        )
        rows = result.get("rows", [])
        tables = [row[0] for row in rows if row]
        
        return SchemaTestResponse(
            status="ok",
            oa_tables_accessible=True,
            sample_tables=tables
        )
    except JdbcError as exc:
        return SchemaTestResponse(
            status="error",
            oa_tables_accessible=False,
            sample_tables=[],
            error=str(exc)
        )
    except Exception as exc:
        return SchemaTestResponse(
            status="error",
            oa_tables_accessible=False,
            sample_tables=[],
            error=f"Unexpected error: {exc}"
        )


@router.post("/jdbc-connections/{connection_id}/discover-schema", response_model=SchemaDiscoveryResponse)
def discover_database_schema(
    connection_id: str,
    payload: SchemaDiscoveryRequest | None = None,
    db: Session = Depends(get_db)
) -> SchemaDiscoveryResponse:
    """
    Discover and cache the database schema from OA_TABLES and OA_COLUMNS.
    This schema will be used by the LLM for SQL generation.
    
    By default, only fetches transaction-related tables for faster loading.
    Set transaction_tables_only=false to fetch all tables (may be slow).
    """
    payload = payload or SchemaDiscoveryRequest()
    
    try:
        # Check if we already have cached schema
        was_cached = get_cached_schema(connection_id) is not None
        
        # Determine which tables to fetch
        table_filter = payload.table_filter
        if table_filter is None and payload.transaction_tables_only:
            table_filter = DEFAULT_TRANSACTION_TABLES
        
        # Discover schema
        tables = discover_schema(
            db,
            connection_id,
            force_refresh=payload.force_refresh,
            table_filter=table_filter
        )
        
        # Generate LLM context preview (truncated)
        llm_context = schema_to_llm_context(tables, max_tables=10)
        preview = llm_context[:2000] + "..." if len(llm_context) > 2000 else llm_context
        
        return SchemaDiscoveryResponse(
            table_count=len(tables),
            tables=sorted(tables.keys())[:100],  # First 100 table names
            cached=was_cached and not payload.force_refresh,
            llm_context_preview=preview
        )
    except JdbcError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema discovery failed: {exc}") from exc


class SchemaCacheStatusResponse(BaseModel):
    cached: bool
    table_count: int
    tables: list[str]
    cache_age_seconds: float | None
    expires_in_seconds: float | None


class ColumnDetail(BaseModel):
    name: str
    data_type: str
    nullable: bool


class TableDetail(BaseModel):
    name: str
    columns: list[ColumnDetail]


class SchemaCacheDetailResponse(BaseModel):
    cached: bool
    table_count: int
    tables: list[TableDetail]
    cache_age_seconds: float | None


@router.get("/jdbc-connections/{connection_id}/schema-cache/detail", response_model=SchemaCacheDetailResponse)
def get_schema_cache_detail(connection_id: str) -> SchemaCacheDetailResponse:
    """
    Get full detail of cached schema including all column names and types.
    Use this to see exactly what columns are available for SQL generation.
    """
    import time
    from app.netsuite.schema_discovery import _schema_cache, _cache_lock
    
    cached = get_cached_schema(connection_id)
    
    if cached is None:
        return SchemaCacheDetailResponse(
            cached=False,
            table_count=0,
            tables=[],
            cache_age_seconds=None
        )
    
    with _cache_lock:
        cache_entry = _schema_cache.get(connection_id)
        age = time.time() - cache_entry.fetched_at if cache_entry else None
    
    # Build detailed table list
    table_details = []
    for table_name, table_info in sorted(cached.items()):
        columns = [
            ColumnDetail(
                name=col.name,
                data_type=col.data_type,
                nullable=col.nullable
            )
            for col in sorted(table_info.columns.values(), key=lambda c: c.name)
        ]
        table_details.append(TableDetail(name=table_name, columns=columns))
    
    return SchemaCacheDetailResponse(
        cached=True,
        table_count=len(cached),
        tables=table_details,
        cache_age_seconds=round(age, 1) if age is not None else None
    )


@router.get("/jdbc-connections/{connection_id}/schema-cache", response_model=SchemaCacheStatusResponse)
def get_schema_cache_status(connection_id: str) -> SchemaCacheStatusResponse:
    """
    Check if schema is cached for a connection.
    
    Returns cache status including:
    - cached: whether schema exists in cache
    - table_count: number of tables cached
    - tables: list of cached table names
    - cache_age_seconds: how old the cache is
    - expires_in_seconds: when cache will expire (TTL is 1 hour)
    """
    import time
    from app.netsuite.schema_discovery import SCHEMA_CACHE_TTL, _schema_cache, _cache_lock
    
    cached = get_cached_schema(connection_id)
    
    if cached is None:
        return SchemaCacheStatusResponse(
            cached=False,
            table_count=0,
            tables=[],
            cache_age_seconds=None,
            expires_in_seconds=None
        )
    
    with _cache_lock:
        cache_entry = _schema_cache.get(connection_id)
        if cache_entry:
            age = time.time() - cache_entry.fetched_at
            expires_in = max(0, SCHEMA_CACHE_TTL - age)
        else:
            age = None
            expires_in = None
    
    return SchemaCacheStatusResponse(
        cached=True,
        table_count=len(cached),
        tables=sorted(cached.keys())[:100],
        cache_age_seconds=round(age, 1) if age is not None else None,
        expires_in_seconds=round(expires_in, 1) if expires_in is not None else None
    )


@router.delete("/jdbc-connections/{connection_id}/schema-cache")
def clear_connection_schema_cache(connection_id: str) -> dict:
    """Clear the cached schema for a specific connection."""
    clear_schema_cache(connection_id)
    return {"status": "ok", "message": f"Schema cache cleared for connection {connection_id}"}


@router.delete("/schema-cache")
def clear_all_schema_cache() -> dict:
    """Clear all cached schemas."""
    clear_schema_cache()
    return {"status": "ok", "message": "All schema caches cleared"}


# ============================================================================
# NetSuite Data Sync Endpoints (PostgreSQL Mirror)
# ============================================================================

class SyncRequest(BaseModel):
    months_back: int = Field(default=3, ge=1, le=24, description="Number of months of data to sync")
    tables: list[str] | None = Field(default=None, description="Specific tables to sync (account, transaction, transactionline). If None, syncs all.")


class SyncResponse(BaseModel):
    status: str
    tables: dict | None = None
    total_rows: int | None = None
    error: str | None = None


@router.post("/jdbc-connections/{connection_id}/sync", response_model=SyncResponse)
def sync_netsuite_data(
    connection_id: str,
    payload: SyncRequest | None = None,
    db: Session = Depends(get_db),
) -> SyncResponse:
    """
    Sync NetSuite data to local PostgreSQL tables.
    
    This pulls data from NetSuite via JDBC and stores it in local mirror tables
    for fast querying. Only syncs transactions created in the last N months.
    
    Tables synced:
    - account: All accounts
    - transaction: Transactions created in last N months
    - transactionline: Lines for those transactions
    """
    from app.netsuite.sync import sync_all, sync_accounts, sync_transactions, sync_transaction_lines
    
    payload = payload or SyncRequest()
    
    try:
        if payload.tables:
            # Sync specific tables
            results = {}
            for table in payload.tables:
                if table == "account":
                    results["account"] = sync_accounts(db, connection_id)
                elif table == "transaction":
                    results["transaction"] = sync_transactions(db, connection_id, payload.months_back)
                elif table == "transactionline":
                    results["transactionline"] = sync_transaction_lines(db, connection_id, payload.months_back)
                else:
                    return SyncResponse(status="error", error=f"Unknown table: {table}")
            
            db.commit()
            all_success = all(r.get("status") == "success" for r in results.values())
            return SyncResponse(
                status="success" if all_success else "partial",
                tables=results,
                total_rows=sum(r.get("rows_synced", 0) for r in results.values()),
            )
        else:
            # Sync all tables
            result = sync_all(db, connection_id, payload.months_back)
            db.commit()
            return SyncResponse(**result)
            
    except Exception as e:
        db.rollback()
        return SyncResponse(status="error", error=str(e))


class SyncStatusResponse(BaseModel):
    connection_id: str
    sync_logs: dict
    row_counts: dict


@router.get("/jdbc-connections/{connection_id}/sync/status", response_model=SyncStatusResponse)
def get_sync_status(
    connection_id: str,
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """
    Get the sync status and row counts for the PostgreSQL mirror tables.
    """
    from app.netsuite.sync import get_sync_status as _get_sync_status
    
    result = _get_sync_status(db, connection_id)
    return SyncStatusResponse(**result)
