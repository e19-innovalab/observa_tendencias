"""tipo_cambio_diario: official daily dollar; hecho_salario.salario_usd: wages converted month by month

Revision ID: 0031
Revises: 0030
"""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has them: an earlier migration creates the tables from
    # the current models
    inspector = sa.inspect(op.get_bind())
    if "tipo_cambio_diario" not in inspector.get_table_names():
        op.create_table(
            "tipo_cambio_diario",
            sa.Column("moneda", sa.String(3), primary_key=True),
            sa.Column("fecha", sa.Date(), primary_key=True),
            sa.Column("valor", sa.Float(), nullable=False),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.source_id")),
        )
    if "salario_usd" not in {c["name"] for c in inspector.get_columns("hecho_salario")}:
        op.add_column("hecho_salario", sa.Column("salario_usd", sa.Float()))


def downgrade() -> None:
    op.drop_column("hecho_salario", "salario_usd")
    op.drop_table("tipo_cambio_diario")
