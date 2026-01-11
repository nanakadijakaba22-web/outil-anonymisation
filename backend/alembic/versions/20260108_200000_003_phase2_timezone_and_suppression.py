"""Phase 2: Timezone fixes and suppressed columns audit trail

Revision ID: 003
Revises: 002
Create Date: 2026-01-08 20:00:00.000000

Changes:
1. Convert all DateTime columns to timezone-aware (DateTime(timezone=True))
2. Create suppressed_columns table for audit trail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply Phase 2 changes."""

    # 1. Create suppressed_columns table for audit trail
    op.create_table(
        'suppressed_columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('column_name', sa.String(length=255), nullable=False),
        sa.Column('column_position', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('sensitivity_type', sa.String(length=50), nullable=True),
        sa.Column('sensitivity_category', sa.String(length=50), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('unique_count', sa.Integer(), nullable=True),
        sa.Column('null_count', sa.Integer(), nullable=True),
        sa.Column('sample_values', sa.JSON(), nullable=True),
        sa.Column('suppressed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['anonymization_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Alter all DateTime columns to be timezone-aware
    # Note: In PostgreSQL, altering timezone attribute requires recreating columns
    # For production, this should be done with careful data migration

    # datasets.upload_date
    op.execute("""
        ALTER TABLE datasets
        ALTER COLUMN upload_date TYPE TIMESTAMP WITH TIME ZONE
        USING upload_date AT TIME ZONE 'UTC'
    """)

    # anonymization_jobs.created_at
    op.execute("""
        ALTER TABLE anonymization_jobs
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC'
    """)

    # anonymization_jobs.completed_at
    op.execute("""
        ALTER TABLE anonymization_jobs
        ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
        USING completed_at AT TIME ZONE 'UTC'
    """)

    # transformation_logs.timestamp
    op.execute("""
        ALTER TABLE transformation_logs
        ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # verification_logs.verified_at
    op.execute("""
        ALTER TABLE verification_logs
        ALTER COLUMN verified_at TYPE TIMESTAMP WITH TIME ZONE
        USING verified_at AT TIME ZONE 'UTC'
    """)

    # risk_assessments.assessed_at
    op.execute("""
        ALTER TABLE risk_assessments
        ALTER COLUMN assessed_at TYPE TIMESTAMP WITH TIME ZONE
        USING assessed_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    """Rollback Phase 2 changes."""

    # 1. Drop suppressed_columns table
    op.drop_table('suppressed_columns')

    # 2. Revert DateTime columns to timezone-naive (not recommended in production)
    # datasets.upload_date
    op.execute("""
        ALTER TABLE datasets
        ALTER COLUMN upload_date TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

    # anonymization_jobs.created_at
    op.execute("""
        ALTER TABLE anonymization_jobs
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

    # anonymization_jobs.completed_at
    op.execute("""
        ALTER TABLE anonymization_jobs
        ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

    # transformation_logs.timestamp
    op.execute("""
        ALTER TABLE transformation_logs
        ALTER COLUMN timestamp TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

    # verification_logs.verified_at
    op.execute("""
        ALTER TABLE verification_logs
        ALTER COLUMN verified_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)

    # risk_assessments.assessed_at
    op.execute("""
        ALTER TABLE risk_assessments
        ALTER COLUMN assessed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)
