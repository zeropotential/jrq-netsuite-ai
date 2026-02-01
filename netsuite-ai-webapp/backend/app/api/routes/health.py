import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI, AuthenticationError, APIConnectionError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.netsuite import NetSuiteJdbcConnection
from app.db.session import db_can_connect, get_db
from app.netsuite.jdbc import JdbcError, test_connection

router = APIRouter(tags=["health"])


class ConnectionHealthRequest(BaseModel):
    connection_id: str = Field(..., min_length=1)


class JdbcConnectionInfo(BaseModel):
    status: str  # "connected" | "error" | "unknown"
    name: str | None = None
    account_id: str | None = None
    host: str | None = None
    role_id: str | None = None
    error: str | None = None


class OpenAiConnectionInfo(BaseModel):
    status: str  # "connected" | "error" | "unknown"
    model: str | None = None
    error: str | None = None


class ConnectionHealthResponse(BaseModel):
    jdbc: JdbcConnectionInfo
    openai: OpenAiConnectionInfo


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict:
    return {"status": "ok", "db": db_can_connect()}


@router.post("/api/connections/health", response_model=ConnectionHealthResponse)
def check_connections_health(
    payload: ConnectionHealthRequest,
    db: Session = Depends(get_db),
    x_openai_api_key: str | None = Header(None),
) -> ConnectionHealthResponse:
    """
    Check health of both JDBC (NetSuite) and OpenAI connections.
    Returns connection info (without credentials) and status.
    """
    # Check JDBC connection
    jdbc_info = _check_jdbc_health(db, payload.connection_id)
    
    # Check OpenAI connection
    openai_info = _check_openai_health(x_openai_api_key)
    
    return ConnectionHealthResponse(jdbc=jdbc_info, openai=openai_info)


def _check_jdbc_health(db: Session, connection_id: str) -> JdbcConnectionInfo:
    """Check JDBC connection health and return info (without credentials)."""
    try:
        conn_uuid = uuid.UUID(connection_id)
    except ValueError:
        return JdbcConnectionInfo(
            status="error",
            error="Invalid connection ID format (must be UUID)"
        )

    conn = db.get(NetSuiteJdbcConnection, conn_uuid)
    if not conn:
        return JdbcConnectionInfo(
            status="error",
            error="Connection not found"
        )

    # Try to test the actual connection
    try:
        result = test_connection(db, connection_id)
        return JdbcConnectionInfo(
            status="connected",
            name=conn.name,
            account_id=conn.account_id,
            host=conn.host,
            role_id=conn.role_id,
        )
    except JdbcError as e:
        return JdbcConnectionInfo(
            status="error",
            name=conn.name,
            account_id=conn.account_id,
            host=conn.host,
            role_id=conn.role_id,
            error=str(e)
        )
    except Exception as e:
        return JdbcConnectionInfo(
            status="error",
            name=conn.name,
            account_id=conn.account_id,
            host=conn.host,
            role_id=conn.role_id,
            error=f"Unexpected error: {str(e)}"
        )


def _check_openai_health(api_key: str | None) -> OpenAiConnectionInfo:
    """Check OpenAI API connectivity (without revealing the key)."""
    key = api_key or settings.openai_api_key
    if not key:
        return OpenAiConnectionInfo(
            status="error",
            error="No API key provided"
        )

    try:
        client = OpenAI(api_key=key)
        # Make a minimal API call to verify connectivity
        # Using models.list() is lightweight and doesn't cost tokens
        models = client.models.list()
        return OpenAiConnectionInfo(
            status="connected",
            model=settings.openai_model,
        )
    except AuthenticationError as e:
        return OpenAiConnectionInfo(
            status="error",
            error="Invalid API key"
        )
    except APIConnectionError as e:
        return OpenAiConnectionInfo(
            status="error",
            error="Cannot connect to OpenAI API"
        )
    except Exception as e:
        return OpenAiConnectionInfo(
            status="error",
            error=f"Connection error: {str(e)[:100]}"
        )


class SchemaInfoResponse(BaseModel):
    markdown_schema_loaded: bool
    markdown_schema_tables: list[str]
    markdown_schema_size: int
    csv_schema_loaded: bool
    csv_schema_tables: int


@router.get("/api/schema/info", response_model=SchemaInfoResponse)
def get_schema_info() -> SchemaInfoResponse:
    """
    Get info about loaded schema references (no JDBC required).
    This shows what schema the LLM will use for SQL generation.
    """
    from app.llm.sql_generator import _load_markdown_schema, _load_allowed_schema
    
    # Check markdown schema
    md_schema = _load_markdown_schema()
    md_loaded = md_schema is not None
    md_size = len(md_schema) if md_schema else 0
    
    # Extract table names from markdown (look for "# TableName" or "## TableName")
    md_tables = []
    if md_schema:
        import re
        # Match headers like "# Transactions" or "## Transaction_lines"
        matches = re.findall(r'^#+ ([A-Z][A-Za-z_]+)\s*$', md_schema, re.MULTILINE)
        md_tables = list(set(matches))
    
    # Check CSV schema
    csv_schema = _load_allowed_schema()
    csv_loaded = csv_schema is not None
    csv_tables = 0
    if csv_schema:
        csv_tables = csv_schema.count("\n- ")  # Count table entries
    
    return SchemaInfoResponse(
        markdown_schema_loaded=md_loaded,
        markdown_schema_tables=sorted(md_tables),
        markdown_schema_size=md_size,
        csv_schema_loaded=csv_loaded,
        csv_schema_tables=csv_tables
    )
