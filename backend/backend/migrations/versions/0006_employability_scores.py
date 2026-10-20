"""employability_scores

Revision ID: 0006
Revises: 0005
"""
from alembic import op

from app.models import EmployabilityScore

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    EmployabilityScore.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    EmployabilityScore.__table__.drop(op.get_bind(), checkfirst=True)
