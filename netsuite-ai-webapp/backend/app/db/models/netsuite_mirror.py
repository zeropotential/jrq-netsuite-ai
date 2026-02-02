"""
PostgreSQL mirror tables for NetSuite data.

These tables store a local copy of NetSuite data for fast querying.
Data is synced periodically from NetSuite via JDBC.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NSAccount(Base):
    """Mirror of NetSuite Account table."""
    __tablename__ = "ns_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # NetSuite internal ID
    
    # Core fields
    acctnumber: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fullname: Mapped[str | None] = mapped_column(String(500), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Classification
    accttype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    specialaccttype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Status
    isinactive: Mapped[str | None] = mapped_column(String(1), nullable=True)  # T/F
    issummary: Mapped[str | None] = mapped_column(String(1), nullable=True)  # T/F
    
    # Hierarchy
    parent: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Currency
    currency: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Sync metadata
    ns_last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_ns_account_acctnumber", "acctnumber"),
        Index("ix_ns_account_name", "name"),
        Index("ix_ns_account_type", "type"),
    )


class NSTransaction(Base):
    """Mirror of NetSuite Transaction table."""
    __tablename__ = "ns_transaction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # NetSuite internal ID
    
    # Core fields
    tranid: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Document number
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CustInvc, SalesOrd, etc.
    trandate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    posting: Mapped[str | None] = mapped_column(String(1), nullable=True)  # T/F
    
    # Entity (customer/vendor)
    entity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Dates
    duedate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closedate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    createddate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lastmodifieddate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Amounts (header level if available)
    foreigntotal: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Currency
    currency: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    exchangerate: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # References
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_ns_transaction_tranid", "tranid"),
        Index("ix_ns_transaction_type", "type"),
        Index("ix_ns_transaction_trandate", "trandate"),
        Index("ix_ns_transaction_status", "status"),
        Index("ix_ns_transaction_posting", "posting"),
        Index("ix_ns_transaction_entity", "entity"),
        Index("ix_ns_transaction_createddate", "createddate"),
    )


class NSTransactionLine(Base):
    """Mirror of NetSuite TransactionLine table."""
    __tablename__ = "ns_transactionline"

    # Composite primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Line unique ID
    transaction: Mapped[int] = mapped_column(BigInteger, ForeignKey("ns_transaction.id"), nullable=False)
    
    # Line identification
    linesequencenumber: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Item
    item: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Amounts
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    netamount: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreignamount: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Quantities
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Account
    account: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Classification
    department: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    class_: Mapped[int | None] = mapped_column("class", BigInteger, nullable=True)
    location: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Memo
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_ns_transactionline_transaction", "transaction"),
        Index("ix_ns_transactionline_item", "item"),
        Index("ix_ns_transactionline_account", "account"),
    )


class NSSyncLog(Base):
    """Track sync operations."""
    __tablename__ = "ns_sync_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("netsuite_jdbc_connections.id"), nullable=False)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")  # running, success, failed
    rows_synced: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("ix_ns_sync_log_connection_id", "connection_id"),
        Index("ix_ns_sync_log_table_name", "table_name"),
        Index("ix_ns_sync_log_started_at", "started_at"),
    )


class NSEmployee(Base):
    """Mirror of NetSuite Employee table."""
    __tablename__ = "ns_employee"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # NetSuite internal ID
    
    # Core fields
    entityid: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Employee ID/code
    firstname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Status
    isinactive: Mapped[str | None] = mapped_column(String(1), nullable=True)  # T/F
    
    # Classification
    department: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    class_: Mapped[int | None] = mapped_column("class", BigInteger, nullable=True)
    location: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    subsidiary: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    supervisor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Job info
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hiredate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    releasedate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_ns_employee_entityid", "entityid"),
        Index("ix_ns_employee_email", "email"),
        Index("ix_ns_employee_department", "department"),
        Index("ix_ns_employee_isinactive", "isinactive"),
    )


class NSCustomer(Base):
    """Mirror of NetSuite Customer table."""
    __tablename__ = "ns_customer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # NetSuite internal ID
    
    # Core fields
    entityid: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Customer ID/code
    companyname: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Status
    isinactive: Mapped[str | None] = mapped_column(String(1), nullable=True)  # T/F
    
    # Classification
    category: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    subsidiary: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    salesrep: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Financials
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    creditlimit: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Dates
    datecreated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lastmodifieddate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_ns_customer_entityid", "entityid"),
        Index("ix_ns_customer_companyname", "companyname"),
        Index("ix_ns_customer_email", "email"),
        Index("ix_ns_customer_isinactive", "isinactive"),
        Index("ix_ns_customer_subsidiary", "subsidiary"),
    )
