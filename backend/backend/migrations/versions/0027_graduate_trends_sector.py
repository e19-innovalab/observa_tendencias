"""graduate_trends.sector and tema: the sector of each career and the topic of tracked programs

Revision ID: 0027
Revises: 0026
"""
import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has them: an earlier migration creates the table from the
    # current model
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("graduate_trends")}
    for name in ("sector", "tema"):
        if name not in columns:
            op.add_column("graduate_trends", sa.Column(name, sa.Text()))


def downgrade() -> None:
    op.drop_column("graduate_trends", "tema")
    op.drop_column("graduate_trends", "sector")
