"""ESCO skill hierarchy: skill descriptions and groups, and gaps per skill group

Revision ID: 0017
Revises: 0016
"""
import sqlalchemy as sa
from alembic import op

from app.models import SkillGroup, SkillGroupGap

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("group_code", sa.Text(), nullable=True))
    SkillGroup.__table__.create(op.get_bind(), checkfirst=True)
    SkillGroupGap.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    SkillGroupGap.__table__.drop(op.get_bind(), checkfirst=True)
    SkillGroup.__table__.drop(op.get_bind(), checkfirst=True)
    op.drop_column("skills", "group_code")
    op.drop_column("skills", "description")
