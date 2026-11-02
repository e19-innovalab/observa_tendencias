"""skills and skill_groups: English original and origin of the Spanish description

Revision ID: 0019
Revises: 0018
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("skills", "skill_groups"):
        op.add_column(table, sa.Column("description_en", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("description_origin", sa.Text(), nullable=True))


def downgrade() -> None:
    for table in ("skills", "skill_groups"):
        op.drop_column(table, "description_origin")
        op.drop_column(table, "description_en")
