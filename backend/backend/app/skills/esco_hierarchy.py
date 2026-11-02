"""ESCO skills hierarchy: each skill's definition and its group, and the groups' names.

GET /resource/skill?uris=... (several skills per request) gives each skill's description and its
broaderHierarchyConcept; GET /resource/concept?uris=... gives each group's title, description and
parent, walked up to the top. Skill groups follow ESCO codes (S skills, A attitudes, L languages,
T transversal: S2 > S2.2 > S2.2.1); knowledge groups follow CINE-F/ISCED-F fields (04 > 041 > 0412).
A skill's group is its hierarchy concept, rolled up to analytics.yaml -> skill_gaps.group_level.
Descriptions keep ESCO's English original; the Spanish shown is ESCO's own or, when ESCO has none,
the translation in sources.yaml -> esco.options.translations_file (description_origin says which).
"""
import asyncio
import re

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.http import get_with_retry, ssl_context
from app.core.config import settings
from app.core.config_files import analytics_params, sources
from app.models import Skill, SkillGroup

PARENT_LINKS = ("broaderConcept", "broaderHierarchyConcept")


def concept_code(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def concept_level(code: str) -> int:
    """S2.2.1 -> 3, S2 -> 1, S -> 0; CINE-F fields: 04 -> 1, 041 -> 2, 0412 -> 3."""
    if code.isdigit():
        return max(len(code) - 1, 1)
    m = re.match(r"^[A-Za-z]+(.*)$", code)
    rest = m.group(1) if m else ""
    return len(rest.split(".")) if rest else 0


ORIGIN_ESCO = "esco"
ORIGIN_TRANSLATION = "translation"


def _text(field: dict | None, language: str) -> str | None:
    """A multilingual ESCO field ({"es": {"literal": ...}} or {"es": "..."}) in one language."""
    value = (field or {}).get(language)
    if isinstance(value, dict):
        value = value.get("literal")
    return value.strip() if value else None


def load_translations(conf) -> dict[str, dict]:
    """{code: {"en": original, "es": translation}} for skills (by skill code) and groups."""
    path = settings.config_dir / conf.options["translations_file"]
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return {**(data.get("groups") or {}), **(data.get("skills") or {})}


def describe(field: dict | None, code: str, conf, translations: dict) -> tuple[str | None, str | None, str | None]:
    """(Spanish shown, English original, origin). A translation only applies while its English
    original still matches ESCO's text; if ESCO changed it, the description stays in English
    until the translation is updated."""
    o = conf.options
    shown, original = _text(field, o["display_language"]), _text(field, o["original_language"])
    if shown:
        return shown, original, ORIGIN_ESCO
    t = translations.get(code)
    if t and original and t.get(o["original_language"], "").strip() == original:
        return t[o["display_language"]].strip(), original, ORIGIN_TRANSLATION
    return original, original, None


async def _get_many(client, url: str, uris: list[str], conf, sem, failed: list[str]) -> dict:
    """One request for several records. ESCO answers 500 for the whole batch when one record is
    broken: split it in halves until the broken record is alone, and skip only that one."""
    try:
        async with sem:
            response = await get_with_retry(client, url, params=[("uris", u) for u in uris]
                                            + [("language", conf.options["language"])])
        return response.json().get("_embedded", {})
    except httpx.HTTPStatusError:
        if len(uris) == 1:
            failed.append(concept_code(uris[0]))
            return {}
        half = len(uris) // 2
        first = await _get_many(client, url, uris[:half], conf, sem, failed)
        return {**first, **await _get_many(client, url, uris[half:], conf, sem, failed)}


async def _fetch(client, url: str, uris: list[str], conf, sem, failed: list[str]) -> dict:
    size = conf.options["hierarchy_batch"]
    out: dict = {}
    for i in range(0, len(uris), size):
        out.update(await _get_many(client, url, uris[i:i + size], conf, sem, failed))
    return out


async def _fetch_all(conf, url: str, uris: list[str], failed: list[str]) -> dict:
    sem = asyncio.Semaphore(conf.options["concurrency"])
    headers = {"User-Agent": sources().http.user_agent}
    size = conf.options["hierarchy_batch"]
    chunks = [uris[i:i + size * 4] for i in range(0, len(uris), size * 4)]
    async with httpx.AsyncClient(timeout=sources().http.timeout_seconds, headers=headers,
                                 follow_redirects=True, verify=ssl_context()) as client:
        parts = await asyncio.gather(*[_fetch(client, url, c, conf, sem, failed) for c in chunks])
    return {k: v for part in parts for k, v in part.items()}


def run_esco_hierarchy(session: Session, source_code: str) -> tuple[int, int, list[str]]:
    """Store descriptions and groups for every skill in the database. Returns (skills with a
    group, groups stored, records ESCO could not return)."""
    failed: list[str] = []
    conf = sources().get(source_code)
    translations = load_translations(conf)
    group_level = analytics_params("skill_gaps")["group_level"]
    base = conf.base_url
    skills = session.scalars(select(Skill).where(Skill.esco_uri.is_not(None))).all()
    details = asyncio.run(_fetch_all(conf, f"{base}/resource/skill", [s.esco_uri for s in skills], failed))

    attached: dict[str, str] = {}  # skill uri -> hierarchy concept uri
    titles: dict[str, str] = {}  # concept uri -> title as the skill links it (fallback)
    for uri, d in details.items():
        links = d.get("_links", {})
        concepts = links.get("broaderHierarchyConcept", [])
        if concepts:
            attached[uri] = concepts[0]["uri"]
            titles.setdefault(concepts[0]["uri"], concepts[0].get("title") or concept_code(concepts[0]["uri"]))

    # walk the hierarchy up to the top, a level at a time
    concepts: dict[str, dict] = {}
    pending = set(attached.values())
    while pending:
        fetched = asyncio.run(_fetch_all(conf, f"{base}/resource/concept", sorted(pending), failed))
        concepts.update(fetched)
        pending = set()
        for d in fetched.values():
            for name in PARENT_LINKS:
                for parent in d.get("_links", {}).get(name, []):
                    if parent["uri"] not in concepts:
                        pending.add(parent["uri"])
        pending -= set(concepts)

    def parent_of(uri: str) -> str | None:
        links = concepts.get(uri, {}).get("_links", {})
        for name in PARENT_LINKS:
            if links.get(name):
                return links[name][0]["uri"]
        return None

    # a group ESCO could not return still gets a row, named as its skills link it
    for uri in set(attached.values()) - set(concepts):
        concepts[uri] = {"title": titles[uri], "_links": {}}
    existing = {g.group_code: g for g in session.scalars(select(SkillGroup)).all()}
    for uri, d in concepts.items():
        code = concept_code(uri)
        parent = parent_of(uri)
        shown, original, origin = describe(d.get("description"), code, conf, translations)
        values = dict(name=d.get("title") or _text(d.get("preferredLabel"), conf.options["display_language"]) or code,
                      description=shown, description_en=original, description_origin=origin,
                      level=concept_level(code), parent_code=concept_code(parent) if parent else None,
                      esco_uri=uri)
        if code in existing:
            for k, v in values.items():
                setattr(existing[code], k, v)
        else:
            session.add(SkillGroup(group_code=code, **values))
    session.flush()

    with_group = 0
    for skill in skills:
        d = details.get(skill.esco_uri)
        if d is None:
            continue
        skill.description, skill.description_en, skill.description_origin = describe(
            d.get("description"), skill.skill_code, conf, translations)
        uri = attached.get(skill.esco_uri)
        while uri and concept_level(concept_code(uri)) > group_level and parent_of(uri):
            uri = parent_of(uri)
        skill.group_code = concept_code(uri) if uri else None
        with_group += skill.group_code is not None
    return with_group, len(concepts), failed
