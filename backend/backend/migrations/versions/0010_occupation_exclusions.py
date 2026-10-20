"""occupations: is_excluded and exclusion_reason

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("occupations")}
    if "is_excluded" not in cols:
        op.add_column("occupations", sa.Column("is_excluded", sa.Boolean(), nullable=False,
                                               server_default=sa.false()))
    if "exclusion_reason" not in cols:
        op.add_column("occupations", sa.Column("exclusion_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("occupations", "exclusion_reason")
    op.drop_column("occupations", "is_excluded")
