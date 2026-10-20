"""methodologies and trend_results

Revision ID: 0005
Revises: 0004
"""
from alembic import op

from app.models import Methodology, TrendResult

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Methodology.__table__.create(bind, checkfirst=True)
    TrendResult.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    TrendResult.__table__.drop(bind, checkfirst=True)
    Methodology.__table__.drop(bind, checkfirst=True)
