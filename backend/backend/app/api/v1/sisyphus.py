from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.recompute import params_digest
from app.analytics.sisyphus import SECTION, compute, country_view, not_applicable_groups
from app.api.v1.employability import _ref
from app.api.v1.indicators import _country_list
from app.api.v1.moctezuma import _sides
from app.core.config_files import analytics_params, app_config, catalog
from app.core.database import get_session
from app.models import Methodology
from app.schemas.observatory import (
    GroupExample,
    GroupInfo,
    LuditaPath,
    MoctezumaComponent,
    SisyphusCountry,
    SisyphusCountryPoint,
    SisyphusItem,
    SisyphusPage,
)

router = APIRouter(tags=["sisyphus"])


def _current_method(session: Session) -> Methodology | None:
    digest = params_digest("sisyphus_index")[2]
    return session.scalar(select(Methodology).where(
        Methodology.methodology_type == "sisyphus_index", Methodology.params_hash == digest))


def group_info(code: str, examples: int) -> GroupInfo:
    """Definition of a major group and some of its catalog occupations, featured ones first."""
    cat = catalog()
    occs = [o for o in cat.occupations if o.occupation_code.startswith(code) and not o.is_excluded]
    # one per sub-major group in turn (featured first in each), so the examples show the range
    by_sub: dict[str, list] = {}
    for o in sorted(occs, key=lambda o: (not o.is_featured, o.occupation_code)):
        by_sub.setdefault(o.occupation_code[:2], []).append(o)
    picked, queues = [], [list(v) for _, v in sorted(by_sub.items())]
    while len(picked) < examples and any(queues):
        for q in queues:
            if q and len(picked) < examples:
                picked.append(q.pop(0))
    return GroupInfo(code=code, name=cat.groups.get(code), definition=cat.group_definitions.get(code),
                     occupations=len(occs),
                     examples=[GroupExample(occupation_code=o.occupation_code, name=o.name,
                                            is_featured=o.is_featured) for o in picked])


def _item(r: dict) -> SisyphusItem:
    labels = app_config().sisyphus
    dims = analytics_params(SECTION)["dimensions"]
    components = [MoctezumaComponent(
        dimension=dim, label=labels.dimensions.get(dim, dim), side=c["side"], weight=c["weight"],
        raw=c["raw"], normalized=c["normalized"], indicator=dims[dim]["indicator"],
        scope=dims[dim]["scope"], measure=dims[dim]["measure"], detail=r["detail"].get(dim) or {},
        available=c["normalized"] is not None) for dim, c in r["components"].items()]
    push, counter = analytics_params(SECTION)["sides"]
    return SisyphusItem(
        country_iso3=r["country_iso3"], group_code=r["group_code"],
        group_name=catalog().groups.get(r["group_code"]), year=r["year"], score=r["score"],
        level=r["level"], level_label=labels.levels[r["level"]], stone=r[push], reward=r[counter],
        quadrant=r["quadrant"],
        quadrant_label=labels.quadrants[r["quadrant"]].label if r["quadrant"] else None,
        overeducation=r["raw"]["overeducation"], earnings_ratio=r["raw"]["earnings_vs_tertiary"],
        earnings_ppp=r["earnings_ppp"], earnings_usd=r["earnings_usd"],
        tertiary_ppp=r["tertiary_ppp"], components=components)


@router.get("/sisyphus", response_model=SisyphusPage)
def sisyphus(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    session: Session = Depends(get_session),
):
    """Sísifo indicator per major occupation group and country: overeducation against what the
    group pays relative to the tertiary educated. Most Sísifo first."""
    p = analytics_params(SECTION)
    labels = app_config().sisyphus
    by_year = compute(session)
    years = sorted(y for y, rows in by_year.items() if any(r["score"] is not None for r in rows))
    year = year or (years[-1] if years else None)
    countries = set(_country_list(country))
    rows = [r for r in by_year.get(year, []) if r["country_iso3"] in countries]
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), r["country_iso3"], r["group_code"]))
    method = _current_method(session)
    return SisyphusPage(
        year=year, available_years=years, level_labels=labels.levels, side_labels=labels.sides,
        sides=_sides(SECTION),
        quadrants=[LuditaPath(path=k, label=v.label, short=v.short, description=v.description)
                   for k, v in labels.quadrants.items()],
        quadrant_rules=p["quadrants"], excluded_groups=sorted(not_applicable_groups(p)),
        groups=[group_info(g, p["group_examples"])
                for g in sorted({r["group_code"] for r in rows})],
        groups_source=catalog().group_definitions_source,
        items=[_item(r) for r in rows], methodology=_ref(method) if method else None)


@router.get("/sisyphus/countries", response_model=list[SisyphusCountry])
def sisyphus_countries(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """Per country and year: mean index of its groups, share of the tertiary educated working
    below their level and the wage premium of tertiary education (with the earnings behind it)."""
    countries = _country_list(country)
    by_year = compute(session)
    view = country_view(session, countries)
    out = []
    for iso3 in countries:
        years = sorted(set(view.get(iso3, {})) | {y for y, rows in by_year.items()
                                                  if any(r["country_iso3"] == iso3 for r in rows)})
        points = []
        for y in years:
            scores = [r["score"] for r in by_year.get(y, [])
                      if r["country_iso3"] == iso3 and r["score"] is not None]
            v = view.get(iso3, {}).get(y, {})
            points.append(SisyphusCountryPoint(
                year=y, score=sum(scores) / len(scores) if scores else None,
                graduates_below_share=v.get("graduates_below_share"), premium=v.get("premium"),
                tertiary_ppp=v.get("tertiary_ppp"), tertiary_usd=v.get("tertiary_usd"),
                secondary_ppp=v.get("secondary_ppp"), secondary_usd=v.get("secondary_usd")))
        out.append(SisyphusCountry(country_iso3=iso3, points=points))
    return out
