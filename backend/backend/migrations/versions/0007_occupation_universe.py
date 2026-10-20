"""occupations: whole ISCO-08 universe (name_en, is_featured, optional sector)

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("occupations")}


def upgrade() -> None:
    cols = _columns()
    if "name_en" not in cols:
        op.add_column("occupations", sa.Column("name_en", sa.Text(), nullable=True))
    if "is_featured" not in cols:
        op.add_column("occupations", sa.Column("is_featured", sa.Boolean(), nullable=False,
                                               server_default=sa.false()))
    op.alter_column("occupations", "sector_code", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("occupations", "sector_code", existing_type=sa.Text(), nullable=False)
    op.drop_column("occupations", "is_featured")
    op.drop_column("occupations", "name_en")
