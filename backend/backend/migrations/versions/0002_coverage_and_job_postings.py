"""coverage_report and job_postings

Revision ID: 0002
Revises: 0001
"""
from alembic import op

from app.models import CoverageReport, JobPosting

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    CoverageReport.__table__.create(bind, checkfirst=True)
    JobPosting.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    JobPosting.__table__.drop(bind, checkfirst=True)
    CoverageReport.__table__.drop(bind, checkfirst=True)
