"""graduates: graduates per year by generic career and level (official files)

Revision ID: 0011
Revises: 0010
"""
from alembic import op

from app.models import Graduate

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Graduate.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Graduate.__table__.drop(op.get_bind(), checkfirst=True)
