"""Moctezuma indicator: pace of technological change vs capacity to respond per occupation

Revision ID: 0018
Revises: 0017
"""
from alembic import op

from app.models import MoctezumaScore

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    MoctezumaScore.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    MoctezumaScore.__table__.drop(op.get_bind(), checkfirst=True)
