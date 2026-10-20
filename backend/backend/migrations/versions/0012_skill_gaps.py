"""skill_gaps

Revision ID: 0012
Revises: 0011
"""
from alembic import op

from app.models import SkillGap

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    SkillGap.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    SkillGap.__table__.drop(op.get_bind(), checkfirst=True)
