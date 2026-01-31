import uuid

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    purpose: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)

    aad: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrapped_dek_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    data_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
