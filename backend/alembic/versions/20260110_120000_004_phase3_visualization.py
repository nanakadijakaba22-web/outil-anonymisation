"""Phase 3: Enhanced data visualization

Revision ID: 004
Revises: 003
Create Date: 2026-01-10 12:00:00.000000

Changes:
1. Add visualization_data JSON column to risk_assessments table
   - Stores compact statistical summaries for frontend charts
   - Includes: overview, distributions, correlations, outliers
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply Phase 3 changes."""

    # Add visualization_data column to risk_assessments
    op.add_column(
        'risk_assessments',
        sa.Column('visualization_data', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Rollback Phase 3 changes."""

    # Remove visualization_data column
    op.drop_column('risk_assessments', 'visualization_data')
