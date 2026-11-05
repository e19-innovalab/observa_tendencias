"""Assistant: questions answered with the observatory's data (app.yaml -> assistant)."""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.assistant import service
from app.core.auth import current_user, optional_user, require_permission
from app.core.config_files import app_config
from app.core.database import get_session
from app.models import User
from app.schemas.assistant import AskRequest, AskResponse, AssistantStatus

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("", response_model=AssistantStatus)
def assistant_status(user: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    """Whether the assistant is on, which model answers, the texts for the screen and the questions
    left today for the logged-in user."""
    conf = app_config().assistant
    p = conf.providers.get(conf.provider)
    return AssistantStatus(
        enabled=conf.enabled, provider=conf.provider, model=p.model if p else "",
        questions_per_day=conf.limits.questions_per_user_per_day,
        remaining_today=service.remaining_today(session, user.user_id) if user else None,
        max_question_chars=conf.max_question_chars, history_turns=conf.history_turns, texts=conf.texts,
        examples=conf.examples)


@router.post("/ask", response_model=AskResponse,
             dependencies=[Depends(require_permission(app_config().assistant.permission))])
async def ask(body: AskRequest, request: Request,
              user: User = Depends(current_user),
              authorization: str | None = Header(default=None),
              session: Session = Depends(get_session)):
    """Answers one question. Send earlier turns in history (the server keeps no conversation) and
    what the user is looking at in context. Every question is logged and counts toward the limits.
    If the client closes the request (the person pressed stop), the model is stopped too and the
    question does not count."""
    return await service.ask(session, user, body, authorization, request.is_disconnected)
