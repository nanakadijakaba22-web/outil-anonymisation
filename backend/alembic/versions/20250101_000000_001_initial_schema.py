"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('column_count', sa.Integer(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('is_loi25_compliant', sa.Boolean(), nullable=True),
        sa.Column('is_anonymized', sa.Boolean(), nullable=True),
        sa.Column('parent_dataset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('encoding', sa.String(length=50), nullable=True),
        sa.Column('delimiter', sa.String(length=5), nullable=True),
        sa.ForeignKeyConstraint(['parent_dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasets_id'), 'datasets', ['id'], unique=False)

    # Create dataset_columns table
    op.create_table(
        'dataset_columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('sensitivity_type', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('null_count', sa.Integer(), nullable=True),
        sa.Column('unique_count', sa.Integer(), nullable=True),
        sa.Column('sample_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_columns_dataset_id'), 'dataset_columns', ['dataset_id'], unique=False)

    # Create anonymization_jobs table
    op.create_table(
        'anonymization_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('output_dataset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('rows_processed', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['output_dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anonymization_jobs_dataset_id'), 'anonymization_jobs', ['dataset_id'], unique=False)

    # Create transformation_logs table
    op.create_table(
        'transformation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('column_name', sa.String(length=255), nullable=False),
        sa.Column('technique', sa.String(length=50), nullable=False),
        sa.Column('params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('values_affected', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('sample_transformations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['anonymization_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transformation_logs_job_id'), 'transformation_logs', ['job_id'], unique=False)

    # Create risk_assessments table
    op.create_table(
        'risk_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessed_at', sa.DateTime(), nullable=False),
        sa.Column('individualization_score', sa.Float(), nullable=False),
        sa.Column('individualization_level', sa.String(length=20), nullable=False),
        sa.Column('correlation_score', sa.Float(), nullable=False),
        sa.Column('correlation_level', sa.String(length=20), nullable=False),
        sa.Column('inference_score', sa.Float(), nullable=False),
        sa.Column('inference_level', sa.String(length=20), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('overall_level', sa.String(length=20), nullable=False),
        sa.Column('is_loi25_compliant', sa.Boolean(), nullable=False),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_assessments_dataset_id'), 'risk_assessments', ['dataset_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_assessments_dataset_id'), table_name='risk_assessments')
    op.drop_table('risk_assessments')
    op.drop_index(op.f('ix_transformation_logs_job_id'), table_name='transformation_logs')
    op.drop_table('transformation_logs')
    op.drop_index(op.f('ix_anonymization_jobs_dataset_id'), table_name='anonymization_jobs')
    op.drop_table('anonymization_jobs')
    op.drop_index(op.f('ix_dataset_columns_dataset_id'), table_name='dataset_columns')
    op.drop_table('dataset_columns')
    op.drop_index(op.f('ix_datasets_id'), table_name='datasets')
    op.drop_table('datasets')
