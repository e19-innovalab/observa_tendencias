"""occupation_skills.relation: ESCO category (essential / optional) per CIUO group

Revision ID: 0016
Revises: 0015
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("occupation_skills", sa.Column("relation", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("occupation_skills", "relation")
