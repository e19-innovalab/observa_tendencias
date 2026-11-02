from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class AssistantLog(Base):
    """One question to the assistant and what happened. Kept forever (never edited): it is the
    record of what was answered, with which data, and what it cost; also used for daily limits.
    status: ok | unverified (numbers not found in the data) | blocked | refused | error |
    cancelled (the person stopped it)."""

    __tablename__ = "assistant_logs"
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), index=True, nullable=True)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONType, default=dict)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list] = mapped_column(JSONType, default=list)  # [{tool, args, ok}]
    unverified_numbers: Mapped[list] = mapped_column(JSONType, default=list)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
