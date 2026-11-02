from statistics import median

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.recompute import params_digest
from app.analytics.skill_gaps_run import crosswalk_codes, crosswalk_levels, load_crosswalk
from app.api.v1.employability import View, _occupation, _ref, _sector_name
from app.core.config_files import analytics_params, app_config, catalog, sources
from app.core.database import get_session
from app.models import Methodology, RedQueenScore
from app.schemas.observatory import (
    CareerOption,
    OccupationItem,
    RedQueenComponent,
    RedQueenDimension,
    RedQueenItem,
    RedQueenPage,
    RedQueenYear,
)

router = APIRouter(tags=["red_queen"])
_pagination = app_config().pagination
INSUFFICIENT = "insufficient_data"


def _current_method(session: Session) -> Methodology | None:
    """Scores shown are those of the parameter set currently in config/analytics.yaml."""
    digest = params_digest("red_queen_index")[2]
    return session.scalar(select(Methodology).where(
        Methodology.methodology_type == "red_queen_index", Methodology.params_hash == digest))


def _crosswalk(country: str) -> dict:
    path = analytics_params("skill_gaps")["crosswalks"].get(country.upper())
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, app_config().messages[
            "no_crosswalk"].format(country=country.upper()))
    return load_crosswalk(path)


def career_occupations(country: str, career: str) -> set[str]:
    """Occupations a career leads to in a country's crosswalk (the same one the skill gaps
    use), at any of its levels."""
    cw = _crosswalk(country)
    entry = cw["careers"].get(career)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, app_config().messages[
            "unknown_career"].format(career=career, country=country.upper()))
    return {c for level in crosswalk_levels(cw) for c in crosswalk_codes(entry, level)}


def _dimensions() -> list[RedQueenDimension]:
    labels = app_config().red_queen
    out = []
    for dim, c in analytics_params("red_queen")["dimensions"].items():
        src = sources().get(c["source"])
        info = labels.dimension_info.get(dim)
        out.append(RedQueenDimension(
            dimension=dim, label=labels.dimensions.get(dim, dim), weight=c["weight"],
            source_code=c["source"], source_name=src.name if src else None,
            source_url=src.base_url if src else None,
            definition=info.definition if info else None, unit=info.unit if info else None,
            possible_range=info.possible_range if info else None))
    return out


def _item(s: RedQueenScore, method: Methodology) -> RedQueenItem:
    labels = app_config().red_queen
    occ = _occupation(s.occupation_code)
    cap = analytics_params("red_queen")["half_life_cap"]
    components = [RedQueenComponent(
        dimension=dim, label=labels.dimensions.get(dim, dim), available=c.get("available", False),
        normalized=c.get("normalized"),
        **{k: c.get(k) for k in ("from_version", "to_version", "from_date", "to_date", "years",
                                 "n_from", "n_to", "added_count", "removed_count",
                                 "renamed_count", "new_per_year", "turnover", "annual",
                                 "half_life")},
        added=c.get("added", []), removed=c.get("removed", []),
    ) for dim in analytics_params("red_queen")["dimensions"]  # config order
        if (c := s.components.get(dim)) is not None]
    return RedQueenItem(
        occupation=OccupationItem.model_validate(occ.model_dump()), sector_name=_sector_name(occ),
        year=s.year, score=s.score, level=s.level, level_label=labels.levels[s.level],
        turnover=s.turnover, half_life=s.half_life,
        half_life_capped=s.half_life is not None and s.half_life >= cap, coverage=s.coverage,
        components=components, methodology=_ref(method))


@router.get("/red-queen", response_model=RedQueenPage)
def red_queen(
    occupation: str | None = None,
    sector: str | None = None,
    country: str | None = Query(None, description="ISO3 del país de la carrera (con career)"),
    career: str | None = Query(None, description="Carrera: solo las ocupaciones a las que lleva"),
    featured: bool | None = Query(None, description="true: solo las ocupaciones destacadas"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    view: View = Query("top", description="top: cambio más rápido · bottom: más lento · all: todas"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit,
                              description="Default: ranking_size para top/bottom, default_limit para all"),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Reina Roja indicator per occupation: new technologies and skills per year in O*NET and
    ESCO, with what entered and left between the versions compared."""
    method = _current_method(session)
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    p = analytics_params("red_queen")
    base = dict(view=view, level_labels=app_config().red_queen.levels, dimensions=_dimensions(),
                half_life_cap=p["half_life_cap"], examples_shown=p["examples"], limit=page_size,
                offset=offset)
    if method is None:
        return RedQueenPage(year=None, available_years=[], total=0, scored_total=0, items=[], **base)
    years = sorted(set(session.scalars(select(RedQueenScore.year).where(
        RedQueenScore.methodology_id == method.methodology_id,
        RedQueenScore.score.is_not(None))).all()))
    year = year or (years[-1] if years else None)
    from_career = career_occupations(country, career) if country and career else None
    codes = [o.occupation_code for o in catalog().occupations
             if (from_career is None or o.occupation_code in from_career)
             and (not sector or o.sector_code == sector)
             and (featured is None or o.is_featured == featured)
             and (not occupation or o.occupation_code == occupation)]
    rows = session.scalars(select(RedQueenScore).where(
        RedQueenScore.methodology_id == method.methodology_id, RedQueenScore.year == year,
        RedQueenScore.occupation_code.in_(codes))).all()
    scored = sorted((s for s in rows if s.score is not None),
                    key=lambda s: (s.score, s.occupation_code), reverse=view != "bottom")
    ordered = scored if view != "all" else scored + sorted(
        (s for s in rows if s.score is None), key=lambda s: s.occupation_code)
    return RedQueenPage(year=year, available_years=years, career=career if from_career else None,
                        total=len(rows), scored_total=len(scored),
                        items=[_item(s, method) for s in ordered[offset:offset + page_size]],
                        **base)


@router.get("/red-queen/years", response_model=list[RedQueenYear])
def red_queen_years(session: Session = Depends(get_session)):
    """Per year, the median over the occupations with a score: new items per year by source,
    annual turnover and half-life."""
    method = _current_method(session)
    if method is None:
        return []
    rows = session.scalars(select(RedQueenScore).where(
        RedQueenScore.methodology_id == method.methodology_id,
        RedQueenScore.score.is_not(None))).all()
    by_year: dict[int, list[RedQueenScore]] = {}
    for s in rows:
        by_year.setdefault(s.year, []).append(s)
    dims = analytics_params("red_queen")["dimensions"]
    out = []
    for year in sorted(by_year):
        scores = by_year[year]
        per_dim = {}
        for d in dims:
            values = [c["new_per_year"] for s in scores if (c := s.components.get(d)) and c.get("available")]
            if values:
                per_dim[d] = median(values)
        out.append(RedQueenYear(
            year=year, scored=len(scores), median_new_per_year=per_dim,
            median_turnover=median(s.turnover for s in scores),
            median_half_life=median(s.half_life for s in scores)))
    return out


@router.get("/red-queen/careers", response_model=list[CareerOption])
def red_queen_careers(country: str = Query(..., description="ISO3")):
    """Careers of a country's crosswalk that lead to at least one occupation, by name."""
    cw = _crosswalk(country)
    out = []
    for career in cw["careers"]:
        n = len(career_occupations(country, career))
        if n:
            out.append(CareerOption(career=career, occupations=n))
    return sorted(out, key=lambda c: c.career.casefold())
