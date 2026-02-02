"""Add learning and memory tables

Revision ID: 20260202_0001
Revises: 20260131_0001
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260202_0001'
down_revision = '20260131_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Query Memory - stores successful queries for few-shot learning
    op.create_table(
        'query_memory',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('query_mode', sa.String(20), server_default='postgres'),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('feedback_score', sa.Float(), server_default='0.0'),
        sa.Column('use_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_query_memory_question', 'query_memory', ['question'], unique=False)
    op.create_index('ix_query_memory_active_score', 'query_memory', ['is_active', 'feedback_score'], unique=False)

    # User Feedback - tracks user feedback on responses
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('query_memory_id', sa.Integer(), sa.ForeignKey('query_memory.id'), nullable=True),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('sql_generated', sa.Text(), nullable=True),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('feedback_comment', sa.Text(), nullable=True),
        sa.Column('corrected_sql', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_feedback_type_created', 'user_feedback', ['feedback_type', 'created_at'], unique=False)

    # Learning Errors - tracks mistakes to avoid repeating
    op.create_table(
        'learning_errors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('bad_sql', sa.Text(), nullable=False),
        sa.Column('error_type', sa.String(100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correct_sql', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_occurred_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_learning_errors_active', 'learning_errors', ['is_active', 'occurrence_count'], unique=False)


def downgrade() -> None:
    op.drop_table('learning_errors')
    op.drop_table('user_feedback')
    op.drop_table('query_memory')
