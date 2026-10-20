"""observations (single fact table with source, date and data type per value)

Revision ID: 0004
Revises: 0003
"""
from alembic import op

from app.models import Observation

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Observation.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Observation.__table__.drop(op.get_bind(), checkfirst=True)
