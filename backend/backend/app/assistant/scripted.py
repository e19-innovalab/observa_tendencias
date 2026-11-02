"""Scripted answers: frequent questions answered from templates with the API's data, no model.

Reads the question type from words (app.yaml -> assistant.scripted.intent_words), the occupation
from a CIUO code, a local name or the search, and the country from its name or the page. Data come
from the same tools the model uses (so links and the log are the same); numbers are copied from
the data, never generated. Returns None when the question does not fit a template: then the model
answers.
"""
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.assistant.tools import ToolRun
from app.core.config_files import ScriptedConf, app_config, catalog
from app.core.search import alias_matches, matches
from app.schemas.assistant import AskRequest

CallTool = Callable[[str, dict], Awaitable[ToolRun]]
_FOLD = str.maketrans("áàäéèëíìïóòöúùüñç", "aaaeeeiiiooouuunc")
CODE = re.compile(r"^\d{4}$")


@dataclass
class Scripted:
    text: str
    options: list[dict] = field(default_factory=list)  # [{label, occupation?, country?}]


def words(text: str) -> list[str]:
    return re.sub(r"[^\w]+", " ", text.lower().translate(_FOLD)).split()


def fmt(value: float, decimals: int) -> str:
    """Spanish number: 1.630,5."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


class Reader:
    """What the question asks: intents, countries, CIUO codes and the words left for the occupation."""

    def __init__(self, conf: ScriptedConf, question: str):
        self.conf = conf
        ws = words(question)
        padded = f" {' '.join(ws)} "
        consumed: set[str] = set(conf.stopwords)
        self.intents: set[str] = set()
        for intent, phrases in conf.intent_words.items():
            for phrase in phrases:
                if f" {' '.join(words(phrase))} " in padded:
                    self.intents.add(intent)
                    consumed |= set(words(phrase))
        by_word = {w: iso for iso, names in conf.country_words.items() for w in names}
        for c in catalog().countries:
            by_word[c.iso3.lower()] = c.iso3
            for w in words(c.name_es):
                by_word.setdefault(w, c.iso3)
        self.countries = list(dict.fromkeys(by_word[w] for w in ws if w in by_word))
        consumed |= {w for w in ws if w in by_word}
        self.codes = [w for w in ws if CODE.match(w)]
        self.rest = [w for w in ws if w not in consumed and not CODE.match(w)]


async def answer(conf: ScriptedConf, req: AskRequest, question: str, call: CallTool,
                 known: set[str]) -> Scripted | None:
    r = Reader(conf, question)
    choice, ctx, t = req.choice, req.context, conf.templates
    countries = [choice.country] if choice and choice.country else r.countries
    ranking = "ranking_top" in r.intents or "ranking_bottom" in r.intents

    if "methodology" in r.intents:
        return await _methodology(conf, call)
    if "sectors" in r.intents or (ranking and not r.rest and not r.codes):
        country = countries[0] if countries else (ctx.country if ctx and ctx.country else None)
        if not country:
            return Scripted(t["ask_country"], [{"label": c.name_es, "country": c.iso3} for c in catalog().countries])
        if "sectors" in r.intents:
            return await _sectors(conf, call, country, by_salary="salary" in r.intents)
        return await _ranking(conf, call, country, "bottom" if "ranking_bottom" in r.intents else "top")

    # which occupation: the one chosen, a code, a name in the question, or the page's
    alias_note = None
    if choice and choice.occupation:
        code = choice.occupation
    elif r.codes:
        code = r.codes[0]
    elif r.rest:
        query = " ".join(r.rest)
        found = await call("buscar_ocupacion", {"q": query})
        items = [o for o in (found.data or []) if not o.get("is_excluded")] if found.ok else []
        # a name or local name equal to what was written decides ("dev" is 2512, not every "Developers")
        exact_alias = {c for term, c in alias_matches(query) if words(term) == words(query)}
        exact = [o for o in items if words(o["name"]) == words(query) or o["occupation_code"] in exact_alias]
        items = exact or items
        if not items or len(items) > conf.max_options:
            return None  # unknown or too vague: the model tries
        if len(items) > 1:
            return Scripted(t["ask_occupation"].format(query=query),
                            [{"label": t["option_occupation"].format(code=o["occupation_code"], name=o["name"]),
                              "occupation": o["occupation_code"]} for o in items])
        code = items[0]["occupation_code"]
        # say which local name led there, unless the official name already says it
        if not matches(items[0]["name"], query):
            alias_note = next((term for term, c in alias_matches(query) if c == code), None)
    elif ctx and ctx.occupation and (r.intents or countries):
        code = ctx.occupation  # "¿cuánto gana?" or "¿y en Uruguay?" from an occupation's page
    else:
        return None
    known.add(code)
    if "skills" in r.intents:
        return await _skills(conf, call, code, alias_note)
    return await _occupation(conf, call, code, countries, "salary" in r.intents, alias_note)


def _country_names() -> dict[str, str]:
    return {c.iso3: c.name_es for c in catalog().countries}


def _header(t: dict, profile: dict, alias_note: str | None) -> tuple[str, list[str]]:
    occ = profile["occupation"]
    label = t["occupation"].format(name=occ["name"], code=occ["occupation_code"])
    lines = [t["alias_note"].format(term=alias_note, name=occ["name"], code=occ["occupation_code"])] if alias_note else []
    return label, lines


async def _occupation(conf: ScriptedConf, call: CallTool, code: str, countries: list[str],
                      salary: bool, alias_note: str | None) -> Scripted | None:
    run = await call("ficha_ocupacion", {"code": code})
    if not run.ok:
        return None
    t, d, p = conf.templates, conf.decimals, run.data
    names = _country_names()
    label, lines = _header(t, p, alias_note)
    by_country = {e["country_iso3"]: e for e in p.get("employability", [])}
    wanted = countries or list(names)
    if salary:
        lines.append(t["salary_title"].format(occupation=label))
        for iso in wanted:
            comp = next((c for c in by_country.get(iso, {}).get("components", []) if c["dimension"] == "salary_ppp"), None)
            if not comp or comp.get("raw") is None:
                lines.append(t["salary_missing"].format(country=names[iso]))
                continue
            year = (comp.get("detail") or {}).get("period") or by_country[iso]["year"]
            shown = comp.get("display")
            if shown and shown.get("value") is not None:
                lines.append(t["salary_line"].format(country=names[iso], usd=fmt(shown["value"], 0),
                                                     ppp=fmt(comp["raw"], 0), year=shown.get("period") or year))
            else:
                lines.append(t["salary_line_ppp"].format(country=names[iso], ppp=fmt(comp["raw"], 0), year=year))
        groups = {h["level"]: h for h in p.get("hierarchy", [])}
        for g in p.get("groups", []):
            covered = [iso for iso in g["countries"] if iso in wanted]
            if g["indicator"] == "mean_monthly_earnings_ppp" and g["isco_digits"] < 4 and covered:
                level = groups.get(g["isco_digits"], {})
                lines.append(t["salary_group_note"].format(group=level.get("code", code[: g["isco_digits"]]),
                                                           group_name=level.get("name", ""),
                                                           countries=", ".join(names[i] for i in covered)))
    else:
        lines.append(t["employability_title"].format(occupation=label))
        for iso in wanted:
            e = by_country.get(iso)
            if not e or e.get("score") is None:
                lines.append(t["employability_missing"].format(country=names[iso]))
            else:
                lines.append(t["employability_line"].format(country=names[iso], score=fmt(e["score"], d),
                                                            level=e["level_label"].lower(), year=e["year"]))
    return Scripted("\n".join(lines))


async def _skills(conf: ScriptedConf, call: CallTool, code: str, alias_note: str | None) -> Scripted | None:
    profile = await call("ficha_ocupacion", {"code": code})
    run = await call("habilidades_ocupacion", {"code": code})
    if not (run.ok and profile.ok):
        return None
    t = conf.templates
    label, lines = _header(t, profile.data, alias_note)
    items = sorted(run.data.get("items", []), key=lambda s: -(s.get("weight") or 0))[: conf.skills_size]
    if items:
        lines.append(t["skills"].format(occupation=label, items="; ".join(s["name"] for s in items)))
    else:
        lines.append(t["skills_missing"].format(occupation=label))
    return Scripted("\n".join(lines))


async def _ranking(conf: ScriptedConf, call: CallTool, country: str, view: str) -> Scripted | None:
    run = await call("ranking_ocupaciones", {"country": country, "view": view})
    if not run.ok:
        return None
    t, d = conf.templates, conf.decimals
    items = [i for i in run.data.get("items", []) if i.get("score") is not None][: conf.ranking_size]
    lines = [t[f"ranking_{view}"].format(country=_country_names()[country], year=run.data.get("year"))]
    lines += [t["ranking_line"].format(n=n, name=i["occupation"]["name"], score=fmt(i["score"], d))
              for n, i in enumerate(items, 1)]
    return Scripted("\n".join(lines))


async def _sectors(conf: ScriptedConf, call: CallTool, country: str, by_salary: bool) -> Scripted | None:
    run = await call("sectores", {"country": country})
    if not run.ok:
        return None
    t, d = conf.templates, conf.decimals
    key = "salary_usd_average" if by_salary else "average_score"
    items = sorted((i for i in run.data.get("items", []) if i.get(key) is not None), key=lambda i: -i[key])
    head = t["sectors_salary" if by_salary else "sectors_score"].format(country=_country_names()[country],
                                                                        year=run.data.get("year"))
    if by_salary:
        body = [t["sectors_salary_line"].format(n=n, name=i["name"], usd=fmt(i["salary_usd_average"], 0),
                                                ppp=fmt(i.get("salary_ppp_average") or 0, 0))
                for n, i in enumerate(items, 1)]
    else:
        body = [t["sectors_score_line"].format(n=n, name=i["name"], score=fmt(i["average_score"], d),
                                               level=(i.get("level_label") or "").lower())
                for n, i in enumerate(items, 1)]
    return Scripted("\n".join([head, *body]))


async def _methodology(conf: ScriptedConf, call: CallTool) -> Scripted | None:
    run = await call("metodologia", {"methodology_type": "employability_index"})
    if not run.ok or not run.data:
        return None
    current = next((m for m in run.data if m.get("is_current")), run.data[0])
    labels = app_config().employability.dimensions
    t = conf.templates
    parts = [t["methodology_part"].format(label=labels.get(dim, dim), weight=fmt(w * 100, 0))
             for dim, w in current["params"]["weights"].items()]
    return Scripted(t["methodology"].format(parts=", ".join(parts), version=current["version"]))

