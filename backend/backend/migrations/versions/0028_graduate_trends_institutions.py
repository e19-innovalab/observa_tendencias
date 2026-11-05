"""graduate_trends.n_instituciones and institucion_principal: who grants each career

Revision ID: 0028
Revises: 0027
"""
import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has them: an earlier migration creates the table from the
    # current model
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("graduate_trends")}
    if "n_instituciones" not in columns:
        op.add_column("graduate_trends", sa.Column("n_instituciones", sa.Integer()))
    if "institucion_principal" not in columns:
        op.add_column("graduate_trends", sa.Column("institucion_principal", sa.Text()))


def downgrade() -> None:
    op.drop_column("graduate_trends", "institucion_principal")
    op.drop_column("graduate_trends", "n_instituciones")
