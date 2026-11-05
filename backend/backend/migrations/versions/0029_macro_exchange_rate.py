"""factores_macro_ppa.tipo_cambio: official exchange rate, to show salaries in USD next to USD PPA

Revision ID: 0029
Revises: 0028
"""
import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has it: an earlier migration creates the table from the
    # current model
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("factores_macro_ppa")}
    if "tipo_cambio" not in columns:
        op.add_column("factores_macro_ppa", sa.Column("tipo_cambio", sa.Float()))


def downgrade() -> None:
    op.drop_column("factores_macro_ppa", "tipo_cambio")
