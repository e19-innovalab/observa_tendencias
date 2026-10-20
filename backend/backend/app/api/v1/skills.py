from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.recompute import params_digest
from app.analytics.skill_gaps_run import load_crosswalk
from app.api.v1.indicators import _country_list
from app.core.config_files import analytics_params, app_config, catalog
from app.core.database import get_session
from app.models import IngestionRun, Methodology, OccupationSkill, Skill, SkillGap, Source
from app.schemas.observatory import (
    MethodologyRef,
    OccupationItem,
    OccupationSkills,
    SkillDetail,
    SkillGapItem,
    SkillGapsPage,
    SkillItem,
    SkillOccupation,
    SourceRef,
)

router = APIRouter(tags=["skills"])
_pagination = app_config().pagination
# ESCO relations are not country-specific: they are read from one catalog country
REFERENCE_COUNTRY_INDEX = 0


def _reference_country() -> str:
    return catalog().countries[REFERENCE_COUNTRY_INDEX].iso3


def _skill_item(skill: Skill, weight: float | None = None, occupations: int | None = None):
    return SkillItem(skill_code=skill.skill_code, name=skill.name, skill_type=skill.skill_type,
                     skill_type_label=app_config().skills.types.get(skill.skill_type or ""),
                     esco_uri=skill.esco_uri, weight=weight, occupations=occupations)


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
    q: str | None = Query(None, description="Texto a buscar en el nombre"),
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
    if q:
        stmt = stmt.where(Skill.name.ilike(f"%{q}%"))
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
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Skill gaps: demand growth vs training growth (percentage points as fractions).
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
    conds = [SkillGap.methodology_id == method.methodology_id,
             SkillGap.country_iso3.in_(_country_list(country))]
    if emerging is not None:
        conds.append(SkillGap.is_emerging.is_(emerging))
    stmt = select(SkillGap, Skill).join(Skill, Skill.skill_code == SkillGap.skill_code).where(*conds)
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
    data_type = "calculated"
    items = [SkillGapItem(
        skill=_skill_item(sk), country_iso3=g.country_iso3, year=g.year,
        demand_growth=g.demand_growth, supply_growth=g.supply_growth, gap=g.gap,
        is_emerging=g.is_emerging, data_sufficiency=g.data_sufficiency,
        data_sufficiency_label=conf.skills.sufficiency[g.data_sufficiency],
        demand_coverage=g.demand_coverage, supply_coverage=g.supply_coverage,
        occupations=g.occupations,
        top_occupations=[{**o, "name": catalog().occupation(o["occupation"]).name}
                         for o in g.details.get("top_occupations", [])],
        data_type=data_type, data_type_label=conf.data_types[data_type],
        methodology=MethodologyRef(methodology_id=method.methodology_id,
                                   methodology_type=method.methodology_type,
                                   version=method.version, name=method.name),
    ) for g, sk in rows[offset:offset + page_size]]
    return SkillGapsPage(view=view, sort_by=sort_by, order=order, min_occupations=min_occ,
                         total=len(rows), full_total=full_total,
                         year=rows[0][0].year if rows else None, limit=page_size, offset=offset,
                         crosswalk_reviewed=reviewed, items=items)


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
