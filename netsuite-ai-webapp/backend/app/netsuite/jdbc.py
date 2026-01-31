import uuid
from typing import Any

import jaydebeapi
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crypto.envelope import EncryptedSecret, decrypt_secret
from app.db.models.netsuite import NetSuiteJdbcConnection
from app.db.models.secret import Secret


class JdbcError(RuntimeError):
    pass


def _get_connection(db: Session, connection_id: str) -> NetSuiteJdbcConnection:
    try:
        conn_uuid = uuid.UUID(connection_id)
    except ValueError as exc:
        raise JdbcError("Invalid connection_id") from exc

    conn = db.get(NetSuiteJdbcConnection, conn_uuid)
    if not conn:
        raise JdbcError("JDBC connection not found")
    return conn


def _get_password(db: Session, conn: NetSuiteJdbcConnection) -> str:
    secret = db.get(Secret, conn.password_secret_id)
    if not secret:
        raise JdbcError("JDBC password secret not found")

    enc = EncryptedSecret(
        key_id=secret.key_id,
        aad=secret.aad,
        wrapped_dek=secret.wrapped_dek,
        wrapped_dek_nonce=secret.wrapped_dek_nonce,
        data_nonce=secret.data_nonce,
        ciphertext=secret.ciphertext,
    )
    return decrypt_secret(enc=enc, kek_b64=settings.app_kek_b64).decode()


def _build_jdbc_url(conn: NetSuiteJdbcConnection) -> str:
    return (
        f"jdbc:ns://{conn.host}:{conn.port};"
        f"accountId={conn.account_id};"
        f"roleId={conn.role_id}"
    )


def _connect(conn: NetSuiteJdbcConnection, password: str):
    if not settings.netsuite_jdbc_jar:
        raise JdbcError("NETSUITE_JDBC_JAR is not configured")

    return jaydebeapi.connect(
        settings.netsuite_jdbc_driver,
        _build_jdbc_url(conn),
        [conn.username, password],
        jars=[settings.netsuite_jdbc_jar],
    )


def test_connection(db: Session, connection_id: str) -> dict[str, Any]:
    conn = _get_connection(db, connection_id)
    password = _get_password(db, conn)

    jdbc_conn = _connect(conn, password)
    try:
        cursor = jdbc_conn.cursor()
        try:
            cursor.execute("SELECT 1")
            value = cursor.fetchone()
            return {"status": "ok", "result": value[0] if value else None}
        finally:
            cursor.close()
    finally:
        jdbc_conn.close()


def run_query(db: Session, connection_id: str, sql: str, limit: int | None = None) -> dict[str, Any]:
    conn = _get_connection(db, connection_id)
    password = _get_password(db, conn)

    jdbc_conn = _connect(conn, password)
    try:
        cursor = jdbc_conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchmany(limit or settings.netsuite_jdbc_row_limit)
            columns = [col[0] for col in (cursor.description or [])]
            return {"columns": columns, "rows": rows}
        finally:
            cursor.close()
    finally:
        jdbc_conn.close()
