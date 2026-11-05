"""Reina Roja: skill profiles per source version and the indicator per occupation

Revision ID: 0023
Revises: 0022
"""
from alembic import op

from app.models import RedQueenScore, SkillProfile

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    SkillProfile.__table__.create(op.get_bind(), checkfirst=True)
    RedQueenScore.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    RedQueenScore.__table__.drop(op.get_bind(), checkfirst=True)
    SkillProfile.__table__.drop(op.get_bind(), checkfirst=True)
