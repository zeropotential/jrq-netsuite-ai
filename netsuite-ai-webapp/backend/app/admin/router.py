from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crypto.envelope import encrypt_secret
from app.db.models.netsuite import NetSuiteJdbcConnection
from app.db.models.secret import Secret
from app.db.session import get_db
from app.netsuite.jdbc import JdbcError, test_connection

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
