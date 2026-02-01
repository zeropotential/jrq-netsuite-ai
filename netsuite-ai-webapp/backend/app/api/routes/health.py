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
