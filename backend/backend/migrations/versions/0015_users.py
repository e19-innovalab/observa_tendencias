"""users: observatory accounts with role, sector of interest and countries

Revision ID: 0015
Revises: 0014
"""
from alembic import op

from app.models import User

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    User.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    User.__table__.drop(op.get_bind(), checkfirst=True)
