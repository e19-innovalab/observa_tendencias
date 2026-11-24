"""users: Google sign-in (google_sub) and accounts without a password

Revision ID: 0032
Revises: 0031
"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a database built from zero already has it: an earlier migration creates the tables from the
    # current models
    if "google_sub" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}:
        op.add_column("users", sa.Column("google_sub", sa.Text(), nullable=True))
        op.create_unique_constraint("users_google_sub_key", "users", ["google_sub"])
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # accounts without a password cannot be kept: they need one before going back
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
    op.drop_constraint("users_google_sub_key", "users", type_="unique")
    op.drop_column("users", "google_sub")
