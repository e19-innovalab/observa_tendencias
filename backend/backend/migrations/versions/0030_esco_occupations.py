"""esco_occupations: the ESCO occupations of each ISCO group, with their official address

Revision ID: 0030
Revises: 0029
"""
import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has it: an earlier migration creates the tables from the
    # current models
    if "esco_occupations" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "esco_occupations",
        sa.Column("occupation_code", sa.String(), sa.ForeignKey("occupations.occupation_code"), primary_key=True),
        sa.Column("esco_uri", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.source_id")),
    )


def downgrade() -> None:
    op.drop_table("esco_occupations")
