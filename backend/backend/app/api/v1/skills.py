from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.analytics.recompute import params_digest
from app.analytics.skill_gaps_run import DEMAND_INDICATOR, load_crosswalk
from app.api.v1.indicators import _country_list
from app.core.config_files import analytics_params, app_config, catalog
from app.core.database import get_session
from app.core.search import text_match
from app.datasets.profiles import profiles
from app.models import (
    Graduate,
    IngestionRun,
    Methodology,
    Observation,
    OccupationSkill,
    Skill,
    SkillGap,
    SkillGroup,
    SkillGroupGap,
    Source,
)
from app.schemas.observatory import (
    GapDataThrough,
    MethodologyRef,
    OccupationItem,
    OccupationSkills,
    SkillDetail,
    SkillGapExtreme,
    SkillGapItem,
    SkillGapsPage,
    SkillGapsSummary,
    SkillGroupGapItem,
    SkillGroupGapsPage,
    SkillGroupItem,
    SkillItem,
    SkillOccupation,
    SkillOccupationUse,
    SkillSectorUse,
    SourceRef,
)

ESSENTIAL = "essential"
VIA_SHOWN = 3  # ESCO occupations named per CIUO group

router = APIRouter(tags=["skills"])
_pagination = app_config().pagination
# ESCO relations are not country-specific: they are read from one catalog country
REFERENCE_COUNTRY_INDEX = 0


def _reference_country() -> str:
    return catalog().countries[REFERENCE_COUNTRY_INDEX].iso3


def _skill_item(skill: Skill, weight: float | None = None, occupations: int | None = None):
    return SkillItem(skill_code=skill.skill_code, name=skill.name, skill_type=skill.skill_type,
                     skill_type_label=app_config().skills.types.get(skill.skill_type or ""),
                     esco_uri=skill.esco_uri, description=skill.description,
                     description_en=skill.description_en, description_origin=skill.description_origin,
                     group_code=skill.group_code, weight=weight, occupations=occupations)


def occupation_skills(session: Session, code: str, limit: int,
                      skill_type: str | None = None) -> tuple[int, list[SkillItem]]:
    stmt = (select(Skill, OccupationSkill.weight)
            .join(OccupationSkill, OccupationSkill.skill_code == Skill.skill_code)
            .where(OccupationSkill.occupation_code == code,
                   OccupationSkill.country_iso3 == _reference_country()))
    if skill_type:
        stmt = stmt.where(Skill.skill_type == skill_type)
    rows = session.execute(stmt.order_by(OccupationSkill.weight.desc(), Skill.name)).all()
    return len(rows), [_skill_item(s, float(w)) for s, w in rows[:limit]]


def _skills_source(session: Session) -> tuple[SourceRef | None, object]:
    row = session.execute(
        select(Source, func.max(IngestionRun.finished_at))
        .join(IngestionRun, IngestionRun.source_id == Source.source_id)
        .join(OccupationSkill, OccupationSkill.source_id == Source.source_id)
        .where(IngestionRun.status.in_(("success", "partial")))
        .group_by(Source.source_id)).first()
    if not row:
        return None, None
    return SourceRef(code=row[0].source_code, name=row[0].name), row[1]


@router.get("/occupations/{code}/skills", response_model=OccupationSkills)
def skills_of_occupation(
    code: str,
    skill_type: str | None = Query(None, description="knowledge | skill"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    session: Session = Depends(get_session),
):
    """Skills of an ISCO occupation (ESCO), most relevant first."""
    occ = catalog().occupation(code)
    if occ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_occupation"].format(code=code))
    total, items = occupation_skills(session, code, limit, skill_type)
    source, updated = _skills_source(session)
    return OccupationSkills(occupation_code=code, occupation_name=occ.name, total=total,
                            weight_note=app_config().skills.weight_note, source=source,
                            updated_at=updated, items=items)


@router.get("/skills", response_model=list[SkillItem])
def search_skills(
    q: str | None = Query(None, description="Palabras a buscar en el nombre (en cualquier orden, sin importar tildes)"),
    skill_type: str | None = Query(None, description="knowledge | skill"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    session: Session = Depends(get_session),
):
    """Skills, the most widely used first (number of ISCO occupations that list them)."""
    used = func.count(OccupationSkill.occupation_code)
    stmt = (select(Skill, used)
            .join(OccupationSkill, OccupationSkill.skill_code == Skill.skill_code)
            .where(OccupationSkill.country_iso3 == _reference_country())
            .group_by(Skill.skill_code))
    if q and (match := text_match(Skill.name, q)) is not None:
        stmt = stmt.where(match)
    if skill_type:
        stmt = stmt.where(Skill.skill_type == skill_type)
    rows = session.execute(stmt.order_by(used.desc(), Skill.name).limit(limit)).all()
    return [_skill_item(s, occupations=n) for s, n in rows]


GapView = Literal["top", "bottom", "all"]
GapSort = Literal["gap", "demand_growth", "supply_growth", "occupations"]
SORT_COLUMNS = {"gap": SkillGap.gap, "demand_growth": SkillGap.demand_growth,
                "supply_growth": SkillGap.supply_growth, "occupations": SkillGap.occupations}


@router.get("/skills/gaps", response_model=SkillGapsPage)
def skill_gaps(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    view: GapView = Query("top", description="top: mayores brechas · bottom: menores · all: todas"),
    sort_by: GapSort = "gap",
    order: Literal["asc", "desc"] | None = None,
    min_occupations: int | None = Query(None, ge=1, description="Default: config"),
    emerging: bool | None = Query(None, description="true: solo habilidades emergentes"),
    q: str | None = Query(None, description="Texto a buscar en el nombre de la habilidad"),
    sector: str | None = Query(None, description="Solo habilidades del sector: esenciales (ESCO) para alguna de sus ocupaciones"),
    relation: Literal["essential", "any"] | None = Query(None, description="Con sector: essential (default de config) o any (también las opcionales)"),
    occupation: str | None = Query(None, description="Solo habilidades de esa ocupación (CIUO)"),
    year: int | None = Query(None, description="Año de referencia (default: el último de cada país)"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Skill gaps: demand growth vs training growth (percentage points as fractions).
    occupation keeps the skills that occupation uses (ESCO relations); sector keeps the skills
    that are essential (ESCO) for at least one of the sector's occupations, or also optional with
    relation=any. Each item lists the sectors that use the skill and how.
    top/bottom rank skills with a full gap used by at least min_occupations occupations;
    all lists every skill (those without a gap last)."""
    conf = app_config()
    method = session.scalar(select(Methodology).where(
        Methodology.methodology_type == "skill_gap",
        Methodology.params_hash == params_digest("skill_gap")[2]))
    min_occ = min_occupations or conf.skills.gap_ranking_min_occupations
    order = order or ("asc" if view == "bottom" else "desc")
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    p = analytics_params("skill_gaps")
    reviewed = {c: bool(load_crosswalk(path).get("reviewed")) for c, path in p["crosswalks"].items()}
    empty = SkillGapsPage(view=view, sort_by=sort_by, order=order, min_occupations=min_occ,
                          total=0, full_total=0, year=None, limit=page_size, offset=offset,
                          crosswalk_reviewed=reviewed, items=[])
    if method is None:
        return empty
    conds, available_years = _year_conds(session, SkillGap, method.methodology_id,
                                         _country_list(country), year)
    if emerging is not None:
        conds.append(SkillGap.is_emerging.is_(emerging))
    stmt = select(SkillGap, Skill).join(Skill, Skill.skill_code == SkillGap.skill_code).where(*conds)
    reference = catalog().countries[REFERENCE_COUNTRY_INDEX].iso3
    if occupation:
        stmt = stmt.where(SkillGap.skill_code.in_(select(OccupationSkill.skill_code).where(
            OccupationSkill.country_iso3 == reference, OccupationSkill.occupation_code == occupation)))
    if sector:
        codes = [o.occupation_code for o in catalog().occupations if o.sector_code == sector]
        uses = select(OccupationSkill.skill_code).where(
            OccupationSkill.country_iso3 == reference, OccupationSkill.occupation_code.in_(codes))
        if (relation or conf.skills.sector_relation) != "any":
            uses = uses.where(OccupationSkill.relation == (relation or conf.skills.sector_relation))
        stmt = stmt.where(SkillGap.skill_code.in_(uses))
    if q:
        stmt = stmt.where(Skill.name.ilike(f"%{q}%"))
    if view != "all":
        stmt = stmt.where(SkillGap.data_sufficiency == "full", SkillGap.occupations >= min_occ)
    column = SORT_COLUMNS[sort_by]
    ordering = column.asc() if order == "asc" else column.desc()
    # rows without the sort value go last whatever the direction
    stmt = stmt.order_by(column.is_(None), ordering, Skill.name, SkillGap.country_iso3)
    rows = session.execute(stmt).all()
    full_total = sum(1 for g, _ in rows if g.data_sufficiency == "full")
    summary = _gaps_summary(session, stmt.where(SkillGap.data_sufficiency == "full")
                            if view == "all" else stmt, len(rows), full_total)
    data_type = "calculated"
    page = rows[offset:offset + page_size]
    sectors_of = _skill_sectors(session, [sk.skill_code for _, sk in page], reference)
    items = [SkillGapItem(
        skill=_skill_item(sk), country_iso3=g.country_iso3, year=g.year,
        demand_growth=g.demand_growth, supply_growth=g.supply_growth, gap=g.gap,
        is_emerging=g.is_emerging, data_sufficiency=g.data_sufficiency,
        data_sufficiency_label=conf.skills.sufficiency[g.data_sufficiency],
        demand_coverage=g.demand_coverage, supply_coverage=g.supply_coverage,
        occupations=g.occupations,
        top_occupations=[{**o, "name": catalog().occupation(o["occupation"]).name}
                         for o in g.details.get("top_occupations", [])],
        sectors=sectors_of.get(sk.skill_code, []),
        unstable_supply=_named(g.details.get("unstable_supply", [])),
        is_cross_sector=sum(u.relation == ESSENTIAL and u.sector_code is not None
                            for u in sectors_of.get(sk.skill_code, [])) > 1,
        data_type=data_type, data_type_label=conf.data_types[data_type],
        methodology=MethodologyRef(methodology_id=method.methodology_id,
                                   methodology_type=method.methodology_type,
                                   version=method.version, name=method.name),
    ) for g, sk in page]
    return SkillGapsPage(view=view, sort_by=sort_by, order=order, min_occupations=min_occ,
                         total=len(rows), full_total=full_total,
                         year=rows[0][0].year if rows else None, available_years=available_years,
                         data_through=_data_through(session, _country_list(country)),
                         limit=page_size, offset=offset,
                         crosswalk_reviewed=reviewed, summary=summary, items=items)


def _named(codes: list[str]) -> list[dict]:
    return [{"occupation": c, "name": catalog().occupation(c).name} for c in codes if catalog().occupation(c)]


def _year_conds(session: Session, model, method_id: int, countries: list[str],
                year: int | None) -> tuple[list, list[int]]:
    """Conditions for the chosen reference year (default: each country's latest year with gaps)
    and the years with gaps for those countries. Two small grouped queries, so the filter is a
    plain (country, year) match that uses the index."""
    base = [model.methodology_id == method_id, model.country_iso3.in_(countries)]
    per_country = session.execute(
        select(model.country_iso3, model.year).where(*base, model.gap.is_not(None))
        .group_by(model.country_iso3, model.year)).all()
    years = sorted({y for _, y in per_country})
    if year is not None:
        return [*base, model.year == year], years
    latest: dict[str, int] = {}
    for country, y in per_country:
        latest[country] = max(latest.get(country, y), y)
    if not latest:
        return [*base, model.year.is_(None)], years
    return [*base, tuple_(model.country_iso3, model.year).in_(list(latest.items()))], years


def _data_through(session: Session, countries: list[str]) -> list[GapDataThrough]:
    """Last year of employment by occupation (demand) and of graduates (supply) per country."""
    demand = dict(session.execute(
        select(Observation.country_iso3, func.max(Observation.period_start))
        .where(Observation.indicator_code == DEMAND_INDICATOR, Observation.occupation_code.is_not(None),
               Observation.data_type == "observed", Observation.country_iso3.in_(countries))
        .group_by(Observation.country_iso3)).all())
    supply = dict(session.execute(
        select(Graduate.country_iso3, func.max(Graduate.year))
        .where(Graduate.country_iso3.in_(countries)).group_by(Graduate.country_iso3)).all())
    supplements = analytics_params("skill_gaps").get("supply_supplements", {})
    out = []
    for c in countries:
        extra = supplements.get(c)
        years: list[int] = []
        if extra and extra.get("profile") in profiles():
            years = sorted(session.scalars(
                select(Graduate.year).join(Source, Source.source_id == Graduate.source_id)
                .where(Graduate.country_iso3 == c,
                       Source.source_code == profiles()[extra["profile"]].source,
                       Graduate.level == extra.get("combined_level")).distinct()).all())
        out.append(GapDataThrough(country_iso3=c, demand=demand[c].year if demand.get(c) else None,
                                  supply=supply.get(c), supplemented_years=years,
                                  supply_note=app_config().skills.supply_notes.get(c) if years else None))
    return out


def _skill_sectors(session: Session, skill_codes: list[str], country: str, by_group: bool = False
                   ) -> dict[str, list[SkillSectorUse]]:
    """Per skill (or per ESCO group with by_group), every occupation that uses it with its ESCO
    category, grouped by strategic sector (strongest relation first; occupations outside the
    strategic sectors go last). For a group, an occupation takes its strongest member skill."""
    if not skill_codes:
        return {}
    occs = {o.occupation_code: o for o in catalog().occupations}
    names = {s.sector_code: s.name for s in catalog().sectors}
    conf = app_config().skills
    labels = conf.relations
    order = {code: i for i, code in enumerate(labels)}  # essential before optional
    found: dict[str, dict[str | None, list[SkillOccupationUse]]] = defaultdict(lambda: defaultdict(list))
    key = Skill.group_code if by_group else OccupationSkill.skill_code
    strongest: dict[tuple[str, str], str] = {}
    vias: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)  # ESCO occupation -> rank
    stmt = (select(key, OccupationSkill.occupation_code, OccupationSkill.relation, OccupationSkill.via)
            .join(Skill, Skill.skill_code == OccupationSkill.skill_code)
            .where(OccupationSkill.country_iso3 == country, key.in_(skill_codes)))
    for code, occ, rel, via in session.execute(stmt):
        if rel in labels and order[rel] < order.get(strongest.get((code, occ), ""), len(order)):
            strongest[(code, occ)] = rel
        for v in via or []:
            r = order.get(v.get("relation"), len(order))
            vias[(code, occ)][v["name"]] = min(vias[(code, occ)].get(v["name"], r), r)
    for (code, occ), rel in strongest.items():
        o = occs.get(occ)
        if o:
            esco_names = sorted(vias[(code, occ)].items(), key=lambda kv: (kv[1], kv[0]))
            found[code][o.sector_code].append(SkillOccupationUse(
                occupation_code=occ, name=o.name, relation=rel, relation_label=labels[rel],
                via=[n.split("/")[0].strip() for n, _ in esco_names][:VIA_SHOWN]))
    out = {}
    for skill, sectors in found.items():
        uses = []
        for code, occupations in sectors.items():
            occupations.sort(key=lambda u: (order[u.relation], u.name))
            rel = occupations[0].relation
            uses.append(SkillSectorUse(sector_code=code, name=names.get(code, code) if code else conf.no_sector_label,
                                       relation=rel, relation_label=labels[rel], occupations=occupations))
        out[skill] = sorted(uses, key=lambda u: (u.sector_code is None, order[u.relation],
                                                 -len(u.occupations), u.name))
    return out


def _gaps_summary(session: Session, stmt, matching: int, full_total: int) -> SkillGapsSummary:
    full = [(g, sk) for g, sk in session.execute(stmt).all() if g.gap is not None]
    gaps = [g.gap for g, _ in full]

    def extreme(pair):
        g, sk = pair
        return SkillGapExtreme(skill_code=sk.skill_code, name=sk.name, country_iso3=g.country_iso3,
                               gap=g.gap)

    occupations = {o["occupation"] for g, _ in full for o in g.details.get("top_occupations", [])}
    return SkillGapsSummary(
        skills_with_gap=len(full), average_gap=sum(gaps) / len(gaps) if gaps else None,
        largest_shortage=extreme(max(full, key=lambda p: p[0].gap)) if full else None,
        largest_surplus=extreme(min(full, key=lambda p: p[0].gap)) if full else None,
        occupations=len(occupations), full_share=full_total / matching if matching else None)


@router.get("/skills/groups/gaps", response_model=SkillGroupGapsPage)
def skill_group_gaps(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    view: GapView = Query("top", description="top: mayores brechas · bottom: menores · all: todas"),
    sort_by: GapSort = "gap",
    order: Literal["asc", "desc"] | None = None,
    min_occupations: int | None = Query(None, ge=1, description="Default: config"),
    q: str | None = Query(None, description="Texto a buscar en el nombre del grupo"),
    sector: str | None = Query(None, description="Solo grupos con alguna habilidad esencial (o cualquiera con relation=any) para ocupaciones del sector"),
    relation: Literal["essential", "any"] | None = None,
    year: int | None = Query(None, description="Año de referencia (default: el último de cada país)"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Gaps per ESCO skill group (analytics.yaml -> skill_gaps.group_level): the same method as
    /skills/gaps over the occupations that use any skill of the group, each weighing as its
    strongest skill of the group. Joins ESCO's near-identical skills."""
    conf = app_config()
    method = session.scalar(select(Methodology).where(
        Methodology.methodology_type == "skill_gap",
        Methodology.params_hash == params_digest("skill_gap")[2]))
    min_occ = min_occupations or conf.skills.gap_ranking_min_occupations
    order = order or ("asc" if view == "bottom" else "desc")
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    p = analytics_params("skill_gaps")
    reviewed = {c: bool(load_crosswalk(path).get("reviewed")) for c, path in p["crosswalks"].items()}
    page = SkillGroupGapsPage(view=view, sort_by=sort_by, order=order, min_occupations=min_occ,
                              total=0, full_total=0, year=None, limit=page_size, offset=offset,
                              group_level=p["group_level"], crosswalk_reviewed=reviewed, items=[])
    if method is None:
        return page
    conds, page.available_years = _year_conds(session, SkillGroupGap, method.methodology_id,
                                              _country_list(country), year)
    page.data_through = _data_through(session, _country_list(country))
    stmt = (select(SkillGroupGap, SkillGroup)
            .join(SkillGroup, SkillGroup.group_code == SkillGroupGap.group_code).where(*conds))
    reference = catalog().countries[REFERENCE_COUNTRY_INDEX].iso3
    if sector:
        codes = [o.occupation_code for o in catalog().occupations if o.sector_code == sector]
        uses = (select(Skill.group_code).join(OccupationSkill, OccupationSkill.skill_code == Skill.skill_code)
                .where(OccupationSkill.country_iso3 == reference, OccupationSkill.occupation_code.in_(codes)))
        if (relation or conf.skills.sector_relation) != "any":
            uses = uses.where(OccupationSkill.relation == (relation or conf.skills.sector_relation))
        stmt = stmt.where(SkillGroupGap.group_code.in_(uses))
    if q:
        stmt = stmt.where(SkillGroup.name.ilike(f"%{q}%"))
    if view != "all":
        stmt = stmt.where(SkillGroupGap.data_sufficiency == "full", SkillGroupGap.occupations >= min_occ)
    column = getattr(SkillGroupGap, SORT_COLUMNS[sort_by].key)
    ordering = column.asc() if order == "asc" else column.desc()
    stmt = stmt.order_by(column.is_(None), ordering, SkillGroup.name, SkillGroupGap.country_iso3)
    rows = session.execute(stmt).all()
    chunk = rows[offset:offset + page_size]
    parents = {g.group_code: g.name for g in session.scalars(select(SkillGroup).where(
        SkillGroup.group_code.in_({grp.parent_code for _, grp in chunk if grp.parent_code}))).all()}
    member_codes = {sk for g, _ in chunk for sk in g.details.get("top_skills", [])}
    members = {sk.skill_code: sk for sk in session.scalars(
        select(Skill).where(Skill.skill_code.in_(member_codes))).all()}
    sectors_of = _skill_sectors(session, [grp.group_code for _, grp in chunk], reference, by_group=True)
    method_ref = MethodologyRef(methodology_id=method.methodology_id, methodology_type=method.methodology_type,
                                version=method.version, name=method.name)
    page.items = [SkillGroupGapItem(
        group=SkillGroupItem(group_code=grp.group_code, name=grp.name, description=grp.description,
                             description_en=grp.description_en, description_origin=grp.description_origin,
                             level=grp.level, parent=parents.get(grp.parent_code or "")),
        country_iso3=g.country_iso3, year=g.year, demand_growth=g.demand_growth,
        supply_growth=g.supply_growth, gap=g.gap, is_emerging=g.is_emerging,
        data_sufficiency=g.data_sufficiency, data_sufficiency_label=conf.skills.sufficiency[g.data_sufficiency],
        demand_coverage=g.demand_coverage, supply_coverage=g.supply_coverage, occupations=g.occupations,
        skills=g.skills,
        top_skills=[_skill_item(members[sk]) for sk in g.details.get("top_skills", []) if sk in members],
        top_occupations=[{**o, "name": catalog().occupation(o["occupation"]).name}
                         for o in g.details.get("top_occupations", [])],
        sectors=sectors_of.get(grp.group_code, []),
        unstable_supply=_named(g.details.get("unstable_supply", [])),
        is_cross_sector=sum(u.relation == ESSENTIAL and u.sector_code is not None
                            for u in sectors_of.get(grp.group_code, [])) > 1,
        methodology=method_ref,
    ) for g, grp in chunk]
    page.total = len(rows)
    page.full_total = sum(1 for g, _ in rows if g.data_sufficiency == "full")
    page.year = rows[0][0].year if rows else None
    return page


@router.get("/skills/{skill_code}", response_model=SkillDetail)
def skill_detail(
    skill_code: str,
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    session: Session = Depends(get_session),
):
    """A skill and the occupations that use it, highest weight first."""
    skill = session.get(Skill, skill_code)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_skill"].format(code=skill_code))
    rows = session.execute(
        select(OccupationSkill.occupation_code, OccupationSkill.weight)
        .where(OccupationSkill.skill_code == skill_code,
               OccupationSkill.country_iso3 == _reference_country())
        .order_by(OccupationSkill.weight.desc())).all()
    used_by = [SkillOccupation(occupation=OccupationItem.model_validate(
        catalog().occupation(code).model_dump()), weight=float(w)) for code, w in rows[:limit]]
    item = _skill_item(skill, occupations=len(rows))
    return SkillDetail(**item.model_dump(), used_by=used_by)
