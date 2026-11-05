from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Observatory account. role: a key of app.yaml -> auth.roles; countries: ISO3 codes the user
    works on (empty = the whole region); sector_code: sector of interest (None = all)."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('active', 'suspended')", name="ck_users_status"),)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    sector_code: Mapped[str | None] = mapped_column(ForeignKey("sectors.sector_code"), nullable=True)
    countries: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    status: Mapped[str] = mapped_column(Text, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
