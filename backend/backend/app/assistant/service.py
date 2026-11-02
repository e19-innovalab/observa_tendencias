"""One question to the assistant: limits, the model's tool loop, the numbers check and the log."""
import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from datetime import time as dtime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant import numbers, scripted
from app.assistant.providers import ProviderError, get_provider
from app.assistant.tools import ToolRun, run_tool
from app.core.config_files import AssistantConf, app_config
from app.models import AssistantLog, User
from app.schemas.assistant import AnswerLink, AnswerOption, AskRequest, AskResponse, ToolCallItem


def _msg(key: str, **kw) -> str:
    return app_config().assistant.messages[key].format(**kw)


# while the model works, how often to check whether the person stopped the question (seconds)
DISCONNECT_POLL = 0.5
# provider recorded for scripted answers (templates, no model)
SCRIPT = "script"
# status for a question the person stopped (HTTP code nginx uses for "client closed request")
CANCELLED = 499


def _today_start() -> datetime:
    return datetime.combine(datetime.now(UTC).date(), dtime.min, tzinfo=UTC)


def asked_today(session: Session, user_id: int | None = None) -> int:
    """Questions the model answered today (UTC). Scripted answers (no model, no cost) and failed or
    stopped questions do not count."""
    stmt = (select(func.count()).select_from(AssistantLog)
            .where(AssistantLog.asked_at >= _today_start(), AssistantLog.provider != SCRIPT,
                   AssistantLog.status.not_in(["error", "cancelled"])))
    if user_id is not None:
        stmt = stmt.where(AssistantLog.user_id == user_id)
    return session.scalar(stmt) or 0


def remaining_today(session: Session, user_id: int) -> int:
    limit = app_config().assistant.limits.questions_per_user_per_day
    return max(limit - asked_today(session, user_id), 0)


def _check_request(session: Session, conf: AssistantConf, user: User, question: str) -> None:
    if not conf.enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _msg("disabled"))
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _msg("empty_question"))
    if len(question) > conf.max_question_chars:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _msg("too_long", max=conf.max_question_chars))


def _check_limits(session: Session, conf: AssistantConf, user: User) -> None:
    """Only before asking the model: scripted answers are free and always allowed."""
    if asked_today(session, user.user_id) >= conf.limits.questions_per_user_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            _msg("user_limit", limit=conf.limits.questions_per_user_per_day))
    if asked_today(session) >= conf.limits.questions_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, _msg("global_limit"))


def _messages(conf: AssistantConf, req: AskRequest, question: str) -> list[dict]:
    history = [{"role": t.role, "content": t.content} for t in req.history if t.content.strip()]
    history = history[-2 * conf.history_turns:] if conf.history_turns else []
    while history and history[0]["role"] != "user":  # the conversation must start with the user
        history.pop(0)
    content = question
    ctx = req.context.model_dump(exclude_none=True) if req.context else {}
    fields = [f"{conf.context_fields[k]}: {v}" for k, v in ctx.items() if k in conf.context_fields and str(v).strip()]
    if fields:
        content += "\n\n" + conf.context_template.format(fields=", ".join(fields))
    return [*history, {"role": "user", "content": content}]


async def _until_done_or_stopped(work: Awaitable, is_disconnected: Callable[[], Awaitable[bool]] | None):
    """Runs the model; if the person stops the question (the request is closed), cancels it, which
    also closes the connection to the model so it stops generating. None when stopped."""
    task = asyncio.ensure_future(work)
    if is_disconnected is None:
        return await task
    while True:
        done, _ = await asyncio.wait({task}, timeout=DISCONNECT_POLL)
        if done:
            return task.result()
        if await is_disconnected():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            return None


async def ask(session: Session, user: User, req: AskRequest, authorization: str | None,
              is_disconnected: Callable[[], Awaitable[bool]] | None = None) -> AskResponse:
    # tools call the API in-process (imported here because app.main imports this module)
    from app.main import app as api

    conf, prefix = app_config().assistant, app_config().api_prefix
    question = req.question.strip()
    _check_request(session, conf, user, question)
    log = AssistantLog(user_id=user.user_id, asked_at=datetime.now(UTC), question=question,
                       context=req.context.model_dump(exclude_none=True) if req.context else {},
                       provider=conf.provider, model="", status="error")
    runs: list[ToolRun] = []
    # codes the person wrote or is looking at; the search adds the ones it finds
    said = " ".join([question, *(t.content for t in req.history if t.role == "user"),
                     *(str(v) for v in log.context.values())])
    known = set(re.findall(conf.known_code_pattern, said))
    started = time.perf_counter()
    headers = {"Authorization": authorization} if authorization else {}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://assistant",
                                     headers=headers) as client:

            async def call_tool(name: str, args: dict) -> ToolRun:
                run = await run_tool(client, conf, prefix, name, args, known)
                runs.append(run)
                return run

            if conf.scripted.enabled:
                script = await scripted.answer(conf.scripted, req, question, call_tool, known)
                if script is not None:
                    log.provider, log.model, log.status, log.answer = SCRIPT, conf.scripted.model_label, "ok", script.text
                    _save(session, log, runs, started)
                    return _response(session, conf, log, runs, user, source=SCRIPT,
                                     options=[AnswerOption(**o) for o in script.options])
            _check_limits(session, conf, user)
            provider = get_provider(conf)
            log.model = provider.model
            reply = await _until_done_or_stopped(
                provider.answer(conf.system_prompt, _messages(conf, req, question), call_tool), is_disconnected)
    except ProviderError as e:
        log.error = str(e)
        _save(session, log, runs, started)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _msg("provider_unavailable")) from e

    if reply is None:
        log.status = "cancelled"
        _save(session, log, runs, started)
        raise HTTPException(CANCELLED, _msg("cancelled"))
    log.input_tokens, log.output_tokens = reply.input_tokens, reply.output_tokens
    answer, warning, bad = reply.text, None, []
    if reply.refused:
        log.status, answer = "refused", _msg("refused")
    elif not answer:
        log.status, answer = "ok", _msg("no_answer")
    else:
        check = conf.numbers_check
        if check.enabled:
            values: set[float] = set()
            for r in runs:
                if r.ok:
                    numbers.data_values(r.data, values)
            asked = " ".join([question, *(t.content for t in req.history)])
            bad = numbers.unverified(answer, values, check, also_allowed=asked)
        if bad and check.on_unverified == "block":
            log.status, answer = "blocked", _msg("blocked" if _links(conf, runs) else "blocked_no_links")
        elif bad:
            log.status, warning = "unverified", _msg("unverified_warning", numbers=", ".join(bad))
        else:
            log.status = "ok"
    log.answer, log.unverified_numbers = answer, bad
    _save(session, log, runs, started)
    return _response(session, conf, log, runs, user, source="model", warning=warning, bad=bad)


def _links(conf: AssistantConf, runs: list[ToolRun]) -> list[AnswerLink]:
    links, seen = [], set()
    tools = {t.name: t for t in conf.tools}
    for r in runs:
        if r.ok and r.link and r.link not in seen:
            seen.add(r.link)
            links.append(AnswerLink(label=tools[r.tool].link.label, href=r.link))
    return links


def _response(session: Session, conf: AssistantConf, log: AssistantLog, runs: list[ToolRun], user: User,
              source: str, warning: str | None = None, bad: list[str] | None = None,
              options: list[AnswerOption] | None = None) -> AskResponse:
    bad = bad or []
    return AskResponse(
        answer=log.answer or "", status=log.status, verified=not bad and log.status == "ok", warning=warning,
        unverified_numbers=bad, links=_links(conf, runs), options=options or [],
        tool_calls=[ToolCallItem(tool=r.tool, args=r.args, ok=r.ok) for r in runs],
        source=source, provider=log.provider, model=log.model, log_id=log.log_id,
        remaining_today=remaining_today(session, user.user_id))


def _save(session: Session, log: AssistantLog, runs: list[ToolRun], started: float) -> None:
    log.tool_calls = [{"tool": r.tool, "args": r.args, "ok": r.ok} for r in runs]
    log.duration_ms = int((time.perf_counter() - started) * 1000)
    session.add(log)
    session.commit()
