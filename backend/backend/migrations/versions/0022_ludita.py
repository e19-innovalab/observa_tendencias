"""Ludita indicator: exposure to generative AI vs vitality (employment and training) per occupation

Revision ID: 0022
Revises: 0021
"""
from alembic import op

from app.models import LuditaScore

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    LuditaScore.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    LuditaScore.__table__.drop(op.get_bind(), checkfirst=True)
