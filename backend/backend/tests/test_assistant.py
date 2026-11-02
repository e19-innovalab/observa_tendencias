"""Assistant: tools run against the real API in-process; the model is replaced by scripted fakes."""
import asyncio
from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.recompute import recompute
from app.assistant import numbers, providers, service
from app.assistant.providers import LocalProvider, ProviderError, Reply
from app.core.config import settings
from app.core.config_files import app_config, catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import AssistantLog, Base, Country, Occupation, Source, User
from app.services.users import create_user
from seeds.load import catalog_rows
from tests.conftest import sqlite_tables

PASSWORD = "clave-segura-123"
FETCHED = datetime(2026, 10, 17, tzinfo=UTC)
CONF = app_config().assistant


def _obs(source_id, indicator, occupation, year, value, unit):
    return dict(indicator_code=indicator, country_iso3="ARG", sector_code=None,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=source_id, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    monkeypatch.setattr(settings, "admin_api_key", "")
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en) for c in catalog().countries])
        s.add_all([Occupation(**row) for row in catalog_rows()[Occupation][0]])  # for buscar_ocupacion
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"),
                   Source(source_id=2, source_code="ilo_genai_exposure", name="OIT", source_kind="dataset")])
        rows = []
        for occ, growth, salary, risk in (("2512", 1.10, 2500, 0.53), ("2221", 1.00, 2000, 0.25),
                                          ("5120", 1.02, 1200, 0.18)):
            rows += [_obs(1, "employment", occ, y, 100 * growth ** i, "thousands_persons")
                     for i, y in enumerate(range(2022, 2026))]
            rows.append(_obs(1, "mean_monthly_earnings_ppp", occ, 2025, salary, "ppp_usd_month"))
            rows.append(_obs(2, "genai_exposure", occ, 2025, risk, "index_0_1"))
        rows.append(_obs(1, "mean_monthly_earnings_usd", "2512", 2025, 1300, "usd_month"))
        upsert_observations(s, rows)
        s.commit()
        recompute(s)
        create_user(s, "viewer@obs.org", "Vera Consulta", PASSWORD, "viewer")
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield engine
    app.dependency_overrides.clear()


@pytest.fixture
def client(engine):
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": "viewer@obs.org", "password": PASSWORD})
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


class Scripted:
    """Fake model: calls the given tools in order, then answers with a fixed text."""

    name, model = "fake", "fake-model"

    def __init__(self, calls, answer, refused=False):
        self.calls, self.text, self.refused = calls, answer, refused
        self.runs, self.messages = [], None

    async def answer(self, system, messages, call_tool):
        self.messages = messages
        for name, args in self.calls:
            self.runs.append(await call_tool(name, args))
        return Reply(self.text, self.refused, input_tokens=120, output_tokens=30)


def _use(monkeypatch, fake, scripted=False):
    """The model answers (scripted answers off unless asked, so the model path is tested)."""
    monkeypatch.setattr(service, "get_provider", lambda conf: fake)
    monkeypatch.setattr(CONF.scripted, "enabled", scripted)
    return fake


def _ask(client, question, **body):
    r = client.post("/api/v1/assistant/ask", json={"question": question, **body})
    assert r.status_code == 200, r.text
    return r.json()


def test_answer_from_tools_with_links_and_log(client, engine, monkeypatch):
    fake = _use(monkeypatch, Scripted(
        [("buscar_ocupacion", {"q": "software"}), ("ficha_ocupacion", {"code": "2512"})],
        "En Argentina (2025) el salario medio fue USD 1.300 por mes (USD PPA 2.500)."))
    r = client.post("/api/v1/assistant/ask", json={"question": "¿Cuánto gana un desarrollador en Argentina?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok" and body["verified"] and body["warning"] is None
    assert all(run.ok for run in fake.runs)
    assert any(o["occupation_code"] == "2512" for o in fake.runs[0].data)
    assert body["links"] == [{"label": "Ficha de la ocupación", "href": "/ocupaciones/2512"}]
    assert [t["tool"] for t in body["tool_calls"]] == ["buscar_ocupacion", "ficha_ocupacion"]
    assert body["remaining_today"] == CONF.limits.questions_per_user_per_day - 1
    with Session(engine) as s:
        log = s.scalars(select(AssistantLog)).one()
        assert log.log_id == body["log_id"] and log.status == "ok" and log.model == "fake-model"
        assert log.input_tokens == 120 and log.tool_calls[1] == {"tool": "ficha_ocupacion", "args": {"code": "2512"}, "ok": True}


def test_numbers_not_in_the_data_warn_or_block(client, monkeypatch):
    monkeypatch.setattr(CONF.numbers_check, "on_unverified", "warn")
    _use(monkeypatch, Scripted([("ficha_ocupacion", {"code": "2512"})], "El salario fue USD 4.321 por mes."))
    body = client.post("/api/v1/assistant/ask", json={"question": "salario 2512"}).json()
    assert body["status"] == "unverified" and not body["verified"]
    assert body["unverified_numbers"] == ["4.321"] and "4.321" in body["warning"]
    assert body["answer"].startswith("El salario fue")

    monkeypatch.setattr(CONF.numbers_check, "on_unverified", "block")
    body = client.post("/api/v1/assistant/ask", json={"question": "salario 2512"}).json()
    assert body["status"] == "blocked" and body["answer"] == CONF.messages["blocked"]


def test_context_and_history_reach_the_model(client, monkeypatch):
    fake = _use(monkeypatch, Scripted([], "Sin números."))
    client.post("/api/v1/assistant/ask", json={
        "question": "¿Y en Chile?",
        "context": {"page": "/ocupaciones/2221", "country": "ARG", "occupation": "2221"},
        "history": [{"role": "assistant", "content": "hola"},  # dropped: must start with the user
                    {"role": "user", "content": "¿Cómo le va a enfermería?"},
                    {"role": "assistant", "content": "Bien en Argentina."}]})
    msgs = fake.messages
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[-1]["content"].startswith("¿Y en Chile?") and "ocupación (CIUO): 2221" in msgs[-1]["content"]


def test_login_validation_and_daily_limits(engine, client, monkeypatch):
    _use(monkeypatch, Scripted([], "Listo."))
    anon = TestClient(app)
    assert anon.post("/api/v1/assistant/ask", json={"question": "hola"}).status_code == 401
    assert anon.get("/api/v1/assistant").json()["remaining_today"] is None
    assert client.post("/api/v1/assistant/ask", json={"question": "  "}).status_code == 422
    assert client.post("/api/v1/assistant/ask", json={"question": "x" * (CONF.max_question_chars + 1)}).status_code == 422

    monkeypatch.setattr(CONF.limits, "questions_per_user_per_day", 1)
    assert client.post("/api/v1/assistant/ask", json={"question": "hola"}).status_code == 200
    r = client.post("/api/v1/assistant/ask", json={"question": "otra"})
    assert r.status_code == 429 and r.json()["detail"] == CONF.messages["user_limit"].format(limit=1)
    status = client.get("/api/v1/assistant").json()
    assert status["remaining_today"] == 0 and status["texts"]["title"] == CONF.texts["title"]

    # at the limit, scripted answers still work (they are free)
    monkeypatch.setattr(CONF.scripted, "enabled", True)
    assert _ask(client, "¿Cómo se calcula el ISE?")["source"] == "script"

    monkeypatch.setattr(CONF, "enabled", False)
    assert client.post("/api/v1/assistant/ask", json={"question": "hola"}).status_code == 503


def test_tool_errors_go_back_to_the_model(client, monkeypatch):
    fake = _use(monkeypatch, Scripted([("no_existe", {}), ("ficha_ocupacion", {}),
                                       ("ficha_ocupacion", {"code": "9999"}),
                                       ("ranking_ocupaciones", {"country": "arg", "view": "top", "extra": 1})],
                                      "Listo."))
    body = client.post("/api/v1/assistant/ask", json={"question": "probar con 9999"}).json()
    unknown, missing, not_found, ranking = fake.runs
    assert not unknown.ok and "desconocida" in unknown.result
    assert not missing.ok and "code" in missing.result
    assert not not_found.ok and not_found.result.startswith("Error 404")
    assert ranking.ok and ranking.args == {"country": "ARG", "view": "top"}  # unknown params dropped
    assert body["links"] == [{"label": "Ranking de ocupaciones", "href": "/ocupaciones?country=ARG"}]


def test_codes_must_come_from_the_search_or_the_person(client, monkeypatch):
    """A code the model made up is rejected; after the search returns it, it is accepted."""
    fake = _use(monkeypatch, Scripted([("ficha_ocupacion", {"code": "2512"}),
                                       ("buscar_ocupacion", {"q": "software"}),
                                       ("ficha_ocupacion", {"code": "2512"}),
                                       ("habilidades_ocupacion", {"code": "2221"})],  # from the context
                                      "Listo."))
    client.post("/api/v1/assistant/ask", json={"question": "¿Cuánto gana un programador?",
                                               "context": {"occupation": "2221"}})
    guessed, search, profile, skills = fake.runs
    assert not guessed.ok and guessed.result == CONF.messages["unknown_code"].format(value="2512")
    assert search.ok and profile.ok and skills.ok


def test_stopped_question_cancels_the_model_and_does_not_count(engine, monkeypatch):
    """The person pressed stop (the request closed): the model's work is cancelled, the question is
    logged as cancelled and does not count toward the daily limit."""
    state = {"cancelled": False}

    class Slow:
        name, model = "fake", "fake-model"

        async def answer(self, *a):
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                state["cancelled"] = True
                raise

    async def gone():
        return True

    monkeypatch.setattr(service, "get_provider", lambda conf: Slow())
    monkeypatch.setattr(service, "DISCONNECT_POLL", 0.01)
    with Session(engine) as s:
        user = s.scalars(select(User)).one()
        with pytest.raises(HTTPException) as e:
            asyncio.run(service.ask(s, user, service.AskRequest(question="algo"), None, gone))
        assert e.value.status_code == service.CANCELLED and state["cancelled"]
        assert s.scalars(select(AssistantLog.status)).all() == ["cancelled"]
        assert service.remaining_today(s, user.user_id) == CONF.limits.questions_per_user_per_day


def test_scripted_salary_from_a_local_name(client, engine, monkeypatch):
    """No model: "dev" is a local name of 2512; numbers come from the data, with the link."""
    fake = _use(monkeypatch, Scripted([], "no debería usarse"), scripted=True)
    body = _ask(client, "¿Cuánto gana un dev en Argentina?")
    assert body["source"] == "script" and body["status"] == "ok" and fake.messages is None
    assert "«dev»" in body["answer"] and "USD 1.300 por mes (USD PPA 2.500) en 2025" in body["answer"]
    assert "Uruguay" not in body["answer"]  # only the country asked
    assert body["links"] == [{"label": "Ficha de la ocupación", "href": "/ocupaciones/2512"}]
    assert body["remaining_today"] == CONF.limits.questions_per_user_per_day  # scripted: does not count
    with Session(engine) as s:
        log = s.scalars(select(AssistantLog)).one()
        assert log.provider == "script" and log.model == CONF.scripted.model_label and log.answer == body["answer"]


def test_scripted_options_then_choice(client, monkeypatch):
    """Several occupations match: buttons; the choice answers without asking again."""
    _use(monkeypatch, Scripted([], "no"), scripted=True)
    body = _ask(client, "¿Cómo le va a un programador?")  # local name: 2512, also 2514
    assert [o["occupation"] for o in body["options"]] == ["2512", "2514"]  # exact local name, not "programador web"
    body = _ask(client, "¿Cómo le va a un programador?", choice={"occupation": "2512"})
    assert body["options"] == [] and "Argentina:" in body["answer"] and "datos insuficientes" in body["answer"]


def test_scripted_rankings_sectors_methodology_and_follow_up(client, monkeypatch):
    _use(monkeypatch, Scripted([], "no"), scripted=True)
    ask_country = _ask(client, "mejores ocupaciones")
    assert ask_country["answer"] == CONF.scripted.templates["ask_country"]
    assert {o["country"] for o in ask_country["options"]} == {c.iso3 for c in catalog().countries}
    ranking = _ask(client, "mejores ocupaciones", choice={"country": "ARG"})
    assert ranking["answer"].splitlines()[1].startswith("1. ") and ranking["links"][0]["href"] == "/ocupaciones?country=ARG"
    assert _ask(client, "¿Qué sector tiene mejor ISE en Argentina?")["tool_calls"][0]["tool"] == "sectores"
    method = _ask(client, "¿Cómo se calcula el ISE?")
    assert "35 %" in method["answer"] and method["source"] == "script"
    follow = _ask(client, "¿Y en Argentina?", context={"occupation": "2221", "page": "/ocupaciones/2221"})
    assert follow["source"] == "script" and "Argentina:" in follow["answer"]


def test_unknown_questions_go_to_the_model(client, monkeypatch):
    fake = _use(monkeypatch, Scripted([], "No tengo ese dato."), scripted=True)
    body = _ask(client, "¿Quién ganó el mundial de fútbol?")
    assert body["source"] == "model" and fake.messages and body["answer"] == "No tengo ese dato."


def test_blocked_without_links_suggests_other_words(client, monkeypatch):
    _use(monkeypatch, Scripted([], "Gana USD 4.321."))
    body = _ask(client, "algo")
    assert body["status"] == "blocked" and body["answer"] == CONF.messages["blocked_no_links"]


def test_refusal_and_provider_errors(client, engine, monkeypatch):
    _use(monkeypatch, Scripted([], "", refused=True))
    body = client.post("/api/v1/assistant/ask", json={"question": "algo"}).json()
    assert body["status"] == "refused" and body["answer"] == CONF.messages["refused"]

    class Down:
        name, model = "fake", "fake-model"

        async def answer(self, *a):
            raise ProviderError("connection refused")

    _use(monkeypatch, Down())
    r = client.post("/api/v1/assistant/ask", json={"question": "algo"})
    assert r.status_code == 503 and r.json()["detail"] == CONF.messages["provider_unavailable"]
    with Session(engine) as s:
        assert s.scalars(select(AssistantLog.status).order_by(AssistantLog.log_id)).all() == ["refused", "error"]
    assert client.get("/api/v1/assistant").json()["remaining_today"] == CONF.limits.questions_per_user_per_day - 1


def test_local_provider_loop_and_final_round(monkeypatch):
    """OpenAI-compatible loop: tool calls go back as tool messages; at the cap, tools are off."""
    monkeypatch.setattr(CONF, "max_tool_calls", 2)
    sent = []
    script = [
        {"choices": [{"message": {"content": "", "tool_calls": [
            {"id": "a", "function": {"name": "ficha_ocupacion", "arguments": '{"code": "2512"}'}},
            {"id": "b", "function": {"name": "ficha_ocupacion", "arguments": "no es json"}},
            {"id": "c", "function": {"name": "ficha_ocupacion", "arguments": '{"code": "2221"}'}}]}}],
         "usage": {"prompt_tokens": 50, "completion_tokens": 10}},
        {"choices": [{"message": {"content": "Respuesta final."}}], "usage": {"prompt_tokens": 80, "completion_tokens": 5}},
    ]

    async def post(self, client, body):
        sent.append(body)
        return script[len(sent) - 1]

    monkeypatch.setattr(LocalProvider, "_post", post)
    called = []

    async def call_tool(name, args):
        called.append(args)
        return providers.ToolRun(name, args, True, '{"ok":1}')

    reply = asyncio.run(LocalProvider(CONF, CONF.providers["local"]).answer("sys", [{"role": "user", "content": "q"}], call_tool))
    assert reply.text == "Respuesta final." and (reply.input_tokens, reply.output_tokens) == (130, 15)
    assert called == [{"code": "2512"}]  # the bad JSON counts as a call; the third is over the cap
    tool_msgs = [m for m in sent[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b", "c"]
    assert tool_msgs[1]["content"] == "Los argumentos no son JSON válido."
    assert sent[0]["tool_choice"] == "auto" and sent[1]["tool_choice"] == "none"
    assert sent[1]["messages"][-1] == {"role": "user", "content": CONF.final_round_note}


def test_anthropic_provider_needs_a_key(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    with pytest.raises(ProviderError):
        asyncio.run(providers.AnthropicProvider(CONF, CONF.providers["anthropic"]).answer("s", [], None))


def test_number_readings_and_check():
    assert numbers.readings("1.068") == {1.068, 1068.0}
    assert numbers.readings("1.068,27") == numbers.readings("1,068.27") == {1068.27}
    check = CONF.numbers_check
    values = {1068.273, 64.52, 0.62}
    text = "USD 1.068 en 2025; ISE 64,5; 3 países; 62 %; 9.999"
    assert numbers.unverified(text, values, check) == ["9.999"]
    assert numbers.unverified("vale 77", values, check, also_allowed="¿y 77?") == []


def test_occupation_search_finds_local_names(client):
    """/occupations?q= (also the header search) knows local names: "remisero" is 8322."""
    codes = [o["occupation_code"] for o in client.get("/api/v1/occupations", params={"q": "remisero"}).json()]
    assert codes == ["8322"]
    both = {o["occupation_code"] for o in client.get("/api/v1/occupations", params={"q": "colectivero"}).json()}
    assert both == {"8331", "8322"}  # bus driver in Argentina, shared taxi in Chile


def test_provider_can_be_set_per_environment(monkeypatch):
    from app.core import config_files

    monkeypatch.setattr(settings, "assistant_provider", "anthropic")
    config_files.app_config.cache_clear()
    try:
        assert config_files.app_config().assistant.provider == "anthropic"
        # in the cloud: provider local pointed to a hosted OpenAI-compatible API
        monkeypatch.setattr(settings, "assistant_provider", "local")
        monkeypatch.setattr(settings, "assistant_base_url", "https://api.example.com/v1")
        monkeypatch.setattr(settings, "assistant_model", "modelo-hospedado")
        config_files.app_config.cache_clear()
        local = config_files.app_config().assistant.providers["local"]
        assert (local.base_url, local.model) == ("https://api.example.com/v1", "modelo-hospedado")
    finally:
        for name in ("assistant_provider", "assistant_base_url", "assistant_model"):
            monkeypatch.setattr(settings, name, "")
        config_files.app_config.cache_clear()
