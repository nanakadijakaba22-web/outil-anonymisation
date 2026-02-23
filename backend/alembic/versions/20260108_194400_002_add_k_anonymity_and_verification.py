"""Phase 1: Add k-anonymity and post-anonymization verification

Revision ID: 002
Revises: 001
Create Date: 2026-01-08 19:44:00.000000

Changes:
- Add k_anonymity_value and k_anonymity_violations columns to risk_assessments
- Create verification_logs table for post-anonymization verification results
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add k-anonymity columns to risk_assessments
    op.add_column('risk_assessments', sa.Column('k_anonymity_value', sa.Integer(), nullable=True))
    op.add_column('risk_assessments', sa.Column('k_anonymity_violations', sa.Float(), nullable=True))

    # Create verification_logs table
    op.create_table(
        'verification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('direct_ids_found', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('k_value', sa.Integer(), nullable=True),
        sa.Column('k_violations_percentage', sa.Float(), nullable=True),
        sa.Column('overall_risk_score', sa.Float(), nullable=False),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['anonymization_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_logs_dataset_id'), 'verification_logs', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_verification_logs_job_id'), 'verification_logs', ['job_id'], unique=False)


def downgrade() -> None:
    # Drop verification_logs table
    op.drop_index(op.f('ix_verification_logs_job_id'), table_name='verification_logs')
    op.drop_index(op.f('ix_verification_logs_dataset_id'), table_name='verification_logs')
    op.drop_table('verification_logs')

    # Remove k-anonymity columns from risk_assessments
    op.drop_column('risk_assessments', 'k_anonymity_violations')
    op.drop_column('risk_assessments', 'k_anonymity_value')
