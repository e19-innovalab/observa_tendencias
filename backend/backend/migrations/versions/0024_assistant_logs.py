"""assistant_logs: every question to the assistant, its answer, tools used and cost

Revision ID: 0024
Revises: 0023
"""
from alembic import op

from app.models import AssistantLog

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    AssistantLog.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    AssistantLog.__table__.drop(op.get_bind(), checkfirst=True)
