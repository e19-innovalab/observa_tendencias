"""coverage_report and job_postings

coverage_report is written out here because its model no longer exists (removed in 0026).

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

from app.models import JobPosting

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
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
    JobPosting.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    JobPosting.__table__.drop(bind, checkfirst=True)
    op.drop_table("coverage_report")
