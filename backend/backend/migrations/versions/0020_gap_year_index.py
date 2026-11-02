"""Index skill gaps by methodology, country and year (gaps are kept for several years)

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_skill_gaps_method_country_year", "skill_gaps",
                    ["methodology_id", "country_iso3", "year"])
    op.create_index("ix_skill_group_gaps_method_country_year", "skill_group_gaps",
                    ["methodology_id", "country_iso3", "year"])


def downgrade() -> None:
    op.drop_index("ix_skill_group_gaps_method_country_year", "skill_group_gaps")
    op.drop_index("ix_skill_gaps_method_country_year", "skill_gaps")
