"""Add employee and customer mirror tables

Revision ID: 20260202_0001
Revises: 20260202_0001_netsuite_mirror
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260202_0002"
down_revision = "20260202_0001_netsuite_mirror"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ns_employee table
    op.create_table(
        "ns_employee",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("entityid", sa.String(255), nullable=True),
        sa.Column("firstname", sa.String(255), nullable=True),
        sa.Column("lastname", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("isinactive", sa.String(1), nullable=True),
        sa.Column("department", sa.BigInteger(), nullable=True),
        sa.Column("class", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.BigInteger(), nullable=True),
        sa.Column("subsidiary", sa.BigInteger(), nullable=True),
        sa.Column("supervisor", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("hiredate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("releasedate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ns_employee_entityid", "ns_employee", ["entityid"])
    op.create_index("ix_ns_employee_email", "ns_employee", ["email"])
    op.create_index("ix_ns_employee_department", "ns_employee", ["department"])
    op.create_index("ix_ns_employee_isinactive", "ns_employee", ["isinactive"])

    # Create ns_customer table
    op.create_table(
        "ns_customer",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("entityid", sa.String(255), nullable=True),
        sa.Column("companyname", sa.String(500), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("isinactive", sa.String(1), nullable=True),
        sa.Column("category", sa.BigInteger(), nullable=True),
        sa.Column("subsidiary", sa.BigInteger(), nullable=True),
        sa.Column("salesrep", sa.BigInteger(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("creditlimit", sa.Float(), nullable=True),
        sa.Column("currency", sa.BigInteger(), nullable=True),
        sa.Column("datecreated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lastmodifieddate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ns_customer_entityid", "ns_customer", ["entityid"])
    op.create_index("ix_ns_customer_companyname", "ns_customer", ["companyname"])
    op.create_index("ix_ns_customer_email", "ns_customer", ["email"])
    op.create_index("ix_ns_customer_isinactive", "ns_customer", ["isinactive"])
    op.create_index("ix_ns_customer_subsidiary", "ns_customer", ["subsidiary"])


def downgrade() -> None:
    op.drop_table("ns_customer")
    op.drop_table("ns_employee")
