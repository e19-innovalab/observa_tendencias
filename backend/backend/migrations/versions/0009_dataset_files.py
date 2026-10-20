"""dataset_files: every downloaded or uploaded official file with its validation report

Revision ID: 0009
Revises: 0008
"""
from alembic import op

from app.models import DatasetFile

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    DatasetFile.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    DatasetFile.__table__.drop(op.get_bind(), checkfirst=True)
