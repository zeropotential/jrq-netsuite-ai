"""Add transaction amount columns

Revision ID: 20260202_0004
Revises: 20260202_0003
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260202_0004'
down_revision = '20260202_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add foreignamountpaid column to ns_transaction
    op.add_column(
        'ns_transaction',
        sa.Column('foreignamountpaid', sa.Float(), nullable=True)
    )
    
    # Add foreignamountunpaid column to ns_transaction
    op.add_column(
        'ns_transaction',
        sa.Column('foreignamountunpaid', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ns_transaction', 'foreignamountunpaid')
    op.drop_column('ns_transaction', 'foreignamountpaid')
