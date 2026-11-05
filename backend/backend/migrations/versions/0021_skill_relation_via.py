"""occupation_skills.via: the ESCO occupations of the CIUO group that use the skill

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("occupation_skills", sa.Column("via", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("occupation_skills", "via")
