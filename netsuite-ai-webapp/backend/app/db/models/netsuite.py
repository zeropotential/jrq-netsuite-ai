import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NetSuiteJdbcConnection(Base):
    __tablename__ = "netsuite_jdbc_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role_id: Mapped[str] = mapped_column(String(32), nullable=False)

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=1708)

    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_secret_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("secrets.id"), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
