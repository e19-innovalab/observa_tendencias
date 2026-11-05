"""graduate_trends.es_seguimiento (tracked careers); coverage_report removed

coverage_report came from a team CSV that no official download refreshes, and nothing read it.

Revision ID: 0026
Revises: 0025
"""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has the column: an earlier migration creates the table
    # from the current model
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("graduate_trends")}
    if "es_seguimiento" not in columns:
        op.add_column("graduate_trends", sa.Column("es_seguimiento", sa.Boolean(), nullable=False,
                                                   server_default=sa.false()))
    op.drop_table("coverage_report")


def downgrade() -> None:
    op.create_table(
        "coverage_report",
        sa.Column("pais", sa.String(3), primary_key=True),
        sa.Column("sector", sa.Text(), primary_key=True),
        sa.Column("n_anios_observados", sa.Integer(), nullable=False),
        sa.Column("anio_min", sa.Integer()),
        sa.Column("anio_max", sa.Integer()),
        sa.Column("elegible_proyeccion", sa.Boolean(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
    )
    op.drop_column("graduate_trends", "es_seguimiento")
