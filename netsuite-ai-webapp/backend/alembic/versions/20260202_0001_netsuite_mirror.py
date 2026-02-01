"""Add NetSuite mirror tables

Revision ID: 20260202_0001
Revises: 20260131_0001
Create Date: 2026-02-02

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260202_0001"
down_revision = "20260131_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Account mirror table
    op.create_table(
        "ns_account",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("acctnumber", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("fullname", sa.String(500), nullable=True),
        sa.Column("type", sa.String(64), nullable=True),
        sa.Column("accttype", sa.String(64), nullable=True),
        sa.Column("specialaccttype", sa.String(64), nullable=True),
        sa.Column("isinactive", sa.String(1), nullable=True),
        sa.Column("issummary", sa.String(1), nullable=True),
        sa.Column("parent", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.BigInteger(), nullable=True),
        sa.Column("ns_last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ns_account_acctnumber", "ns_account", ["acctnumber"])
    op.create_index("ix_ns_account_name", "ns_account", ["name"])
    op.create_index("ix_ns_account_type", "ns_account", ["type"])

    # Transaction mirror table
    op.create_table(
        "ns_transaction",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("tranid", sa.String(255), nullable=True),
        sa.Column("type", sa.String(64), nullable=True),
        sa.Column("trandate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(64), nullable=True),
        sa.Column("posting", sa.String(1), nullable=True),
        sa.Column("entity", sa.BigInteger(), nullable=True),
        sa.Column("duedate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closedate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createddate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lastmodifieddate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("foreigntotal", sa.Float(), nullable=True),
        sa.Column("currency", sa.BigInteger(), nullable=True),
        sa.Column("exchangerate", sa.Float(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ns_transaction_tranid", "ns_transaction", ["tranid"])
    op.create_index("ix_ns_transaction_type", "ns_transaction", ["type"])
    op.create_index("ix_ns_transaction_trandate", "ns_transaction", ["trandate"])
    op.create_index("ix_ns_transaction_status", "ns_transaction", ["status"])
    op.create_index("ix_ns_transaction_posting", "ns_transaction", ["posting"])
    op.create_index("ix_ns_transaction_entity", "ns_transaction", ["entity"])
    op.create_index("ix_ns_transaction_createddate", "ns_transaction", ["createddate"])

    # TransactionLine mirror table
    op.create_table(
        "ns_transactionline",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("transaction", sa.BigInteger(), sa.ForeignKey("ns_transaction.id"), nullable=False),
        sa.Column("linesequencenumber", sa.BigInteger(), nullable=True),
        sa.Column("item", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("netamount", sa.Float(), nullable=True),
        sa.Column("foreignamount", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("account", sa.BigInteger(), nullable=True),
        sa.Column("department", sa.BigInteger(), nullable=True),
        sa.Column("class", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.BigInteger(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ns_transactionline_transaction", "ns_transactionline", ["transaction"])
    op.create_index("ix_ns_transactionline_item", "ns_transactionline", ["item"])
    op.create_index("ix_ns_transactionline_account", "ns_transactionline", ["account"])

    # Sync log table
    op.create_table(
        "ns_sync_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("netsuite_jdbc_connections.id"), nullable=False),
        sa.Column("table_name", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rows_synced", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_ns_sync_log_connection_id", "ns_sync_log", ["connection_id"])
    op.create_index("ix_ns_sync_log_table_name", "ns_sync_log", ["table_name"])
    op.create_index("ix_ns_sync_log_started_at", "ns_sync_log", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_ns_sync_log_started_at", table_name="ns_sync_log")
    op.drop_index("ix_ns_sync_log_table_name", table_name="ns_sync_log")
    op.drop_index("ix_ns_sync_log_connection_id", table_name="ns_sync_log")
    op.drop_table("ns_sync_log")

    op.drop_index("ix_ns_transactionline_account", table_name="ns_transactionline")
    op.drop_index("ix_ns_transactionline_item", table_name="ns_transactionline")
    op.drop_index("ix_ns_transactionline_transaction", table_name="ns_transactionline")
    op.drop_table("ns_transactionline")

    op.drop_index("ix_ns_transaction_createddate", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_entity", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_posting", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_status", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_trandate", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_type", table_name="ns_transaction")
    op.drop_index("ix_ns_transaction_tranid", table_name="ns_transaction")
    op.drop_table("ns_transaction")

    op.drop_index("ix_ns_account_type", table_name="ns_account")
    op.drop_index("ix_ns_account_name", table_name="ns_account")
    op.drop_index("ix_ns_account_acctnumber", table_name="ns_account")
    op.drop_table("ns_account")
