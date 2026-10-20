"""alerts

Revision ID: 0008
Revises: 0007
"""
from alembic import op

from app.models import Alert

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Alert.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Alert.__table__.drop(op.get_bind(), checkfirst=True)
