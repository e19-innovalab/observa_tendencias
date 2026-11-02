"""ESCO: skills of every ISCO-08 unit group in the catalog (European Commission, public API).

For each ISCO group: GET /resource/concept?uri=.../isco/C{code} lists its ESCO occupations;
GET /resource/occupation?uri=... gives each one's essential and optional skills. A skill's weight
for the group is the mean, over the group's ESCO occupations, of its relation weight
(config/sources.yaml -> esco.options.relation_weights), and its category the strongest relation
found in any of them (esco.options.relation_categories: essential beats optional). Stored in
skills and occupation_skills, replacing what ESCO loaded before.
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.http import get_with_retry, ssl_context
from app.core.config_files import SourceConf, catalog, sources
from app.models import OccupationSkill, Skill, Source
from app.skills.esco_hierarchy import run_esco_hierarchy

ISCO_URI = "http://data.europa.eu/esco/isco/C{code}"


@dataclass
class EscoSkill:
    uri: str
    name: str
    skill_type: str | None


def _skill_type(href: str | None) -> str | None:
    marker = "/skill-type/"
    return href.split(marker, 1)[1] if href and marker in href else None


class EscoError(Exception):
    pass


async def _group_skills(client: httpx.AsyncClient, conf: SourceConf, code: str,
                        sem: asyncio.Semaphore, failed: list[str], version: str | None = None
                        ) -> tuple[str, int, dict[str, tuple[EscoSkill, float, str, list]], int]:
    """(ISCO code, ESCO occupations read, {skill uri: (skill, weight, category, via)},
    occupations listed). via: the group's ESCO occupations that use the skill and how.
    version: an ESCO version (e.g. v1.0.9); None is the current one."""
    o, base = conf.options, conf.base_url
    selected = {"selectedVersion": version} if version else {}
    async with sem:
        group = (await get_with_retry(client, f"{base}/resource/concept", params={
            "uri": ISCO_URI.format(code=code), "language": o["language"], **selected})).json()
        occs = group.get("_links", {}).get("narrowerOccupation", [])
        responses = []
        for occ in occs:
            try:
                responses.append(await get_with_retry(client, f"{base}/resource/occupation",
                                                      params={"uri": occ["uri"],
                                                              "language": o["language"],
                                                              **selected}))
            except httpx.HTTPStatusError:
                failed.append(f"{code}:{occ['uri'].rsplit('/', 1)[-1]}")
    totals: dict[str, float] = defaultdict(float)
    found: dict[str, EscoSkill] = {}
    categories = list(o["relation_categories"].items())  # strongest first
    rank = {relation: i for i, (relation, _) in enumerate(categories)}
    strongest: dict[str, int] = {}
    via: dict[str, dict[str, int]] = defaultdict(dict)  # skill uri -> ESCO occupation -> relation rank
    for response in responses:
        body = response.json()
        links = body.get("_links", {})
        occupation = body.get("title") or body.get("uri", "").rsplit("/", 1)[-1]
        best: dict[str, float] = {}
        for relation, weight in o["relation_weights"].items():
            for s in links.get(relation, []):
                found[s["uri"]] = EscoSkill(s["uri"], s.get("title") or s["uri"],
                                            _skill_type(s.get("skillType")))
                best[s["uri"]] = max(best.get(s["uri"], 0.0), weight)
                r = rank.get(relation, len(rank))
                strongest[s["uri"]] = min(strongest.get(s["uri"], len(rank)), r)
                via[s["uri"]][occupation] = min(via[s["uri"]].get(occupation, len(rank)), r)
        for uri, weight in best.items():
            totals[uri] += weight
    n = len(responses)

    def category(r: int) -> str | None:
        return categories[r][1] if r < len(categories) else None

    group = {uri: (found[uri], totals[uri] / n, category(strongest[uri]),
                   [{"name": name, "relation": category(r)}
                    for name, r in sorted(via[uri].items(), key=lambda kv: (kv[1], kv[0]))])
             for uri in totals} if n else {}
    return code, n, group, len(occs)


async def fetch_all(conf: SourceConf, codes: list[str], failed: list[str],
                    version: str | None = None) -> list[tuple]:
    sem = asyncio.Semaphore(conf.options["concurrency"])
    headers = {"User-Agent": sources().http.user_agent}
    async with httpx.AsyncClient(timeout=sources().http.timeout_seconds, headers=headers,
                                 follow_redirects=True, verify=ssl_context()) as client:
        return await asyncio.gather(*[_group_skills(client, conf, c, sem, failed, version)
                                      for c in codes])


def skill_code(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def run_esco_source(session: Session, source_code: str) -> tuple[int, int, list[str]]:
    """Fetch and store skills for every catalog occupation. Returns (groups with ESCO data,
    occupation-skill rows stored, ESCO occupations skipped because the API kept failing)."""
    conf = sources().get(source_code)
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    occupations = [o.occupation_code for o in catalog().occupations if not o.is_excluded]
    failed: list[str] = []
    results = asyncio.run(fetch_all(conf, occupations, failed))
    listed = sum(r[3] for r in results)
    if listed and len(failed) / listed > conf.options["max_failed_share"]:
        raise EscoError(f"{len(failed)} de {listed} ocupaciones ESCO fallaron: {', '.join(failed[:5])}")
    min_weight = conf.options["min_weight"]

    skills: dict[str, EscoSkill] = {}
    pairs: list[tuple[str, str, float, str | None, list]] = []
    for code, n_occ, group, _ in results:
        for uri, (skill, weight, category, via) in group.items():
            if weight > min_weight:
                skills[uri] = skill
                pairs.append((code, skill_code(uri), round(weight, 4), category, via))

    existing = {s.skill_code: s for s in session.scalars(select(Skill)).all()}
    for uri, s in skills.items():
        row = existing.get(skill_code(uri))
        if row is None:
            session.add(Skill(skill_code=skill_code(uri), name=s.name, skill_type=s.skill_type,
                              esco_uri=uri))
        else:
            row.name, row.skill_type, row.esco_uri = s.name, s.skill_type, uri
    session.flush()
    # ESCO is not country-specific: the same relations are stored for every catalog country
    session.execute(delete(OccupationSkill).where(OccupationSkill.source_id == source.source_id))
    countries = [c.iso3 for c in catalog().countries]
    session.add_all([
        OccupationSkill(occupation_code=occ, skill_code=sk, country_iso3=country, weight=w,
                        relation=category, via=via, source_id=source.source_id)
        for occ, sk, w, category, via in pairs for country in countries
    ])
    session.flush()
    run_esco_hierarchy(session, source_code)  # definitions and groups of the skills just stored
    return sum(1 for _, n, _g, _l in results if n), len(pairs), failed
