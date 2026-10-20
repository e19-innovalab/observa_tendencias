"""education_mismatch_cells: employed by major occupation group and education band (ILOSTAT)

Revision ID: 0013
Revises: 0012
"""
from alembic import op

from app.models import EducationMismatchCell

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    EducationMismatchCell.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    EducationMismatchCell.__table__.drop(op.get_bind(), checkfirst=True)
