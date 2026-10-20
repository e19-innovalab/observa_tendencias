"""data_revisions: previous values of source data changed or removed by a later load

Revision ID: 0014
Revises: 0013
"""
from alembic import op

from app.models import DataRevision

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    DataRevision.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    DataRevision.__table__.drop(op.get_bind(), checkfirst=True)
