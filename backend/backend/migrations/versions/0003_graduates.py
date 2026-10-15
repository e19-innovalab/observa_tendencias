"""graduate_trends and graduate_projections

Revision ID: 0003
Revises: 0002
"""
from alembic import op

from app.models import GraduateProjection, GraduateTrend

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    GraduateTrend.__table__.create(bind, checkfirst=True)
    GraduateProjection.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    GraduateProjection.__table__.drop(bind, checkfirst=True)
    GraduateTrend.__table__.drop(bind, checkfirst=True)
