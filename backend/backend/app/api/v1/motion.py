from collections import defaultdict
from statistics import fmean

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability_run import _load_points
from app.analytics.motion import Key, roll_up, with_carry, year_over_year
from app.api.v1.employability import _current_method as employability_method
from app.api.v1.indicators import _country_list
from app.core.config_files import MotionAxis, app_config, catalog, indicators
from app.core.database import get_session
from app.models import EmployabilityScore
from app.schemas.observatory import MotionAxisInfo, MotionGroup, MotionPage, MotionPoint

router = APIRouter(tags=["motion"])


def _source_digits(indicator_code: str, countries: list[str]) -> dict[str, int]:
    """Country -> digits of the groups the indicator's occupation series is published at.
    Countries without such a series (per-occupation tables) keep the full code."""
    out = {}
    for s in indicators().get(indicator_code).series:
        if s.occupation_isco_digits:
            for c in s.countries or countries:
                out.setdefault(c, s.occupation_isco_digits)
    return out


def _info(key: str, axis: MotionAxis) -> MotionAxisInfo:
    ind = indicators().get(axis.indicator) if axis.indicator else None
    unit = "percent" if axis.measure == "yoy" else ind.unit if ind else None
    return MotionAxisInfo(key=key, label=axis.label, short_label=axis.short_label, unit=unit,
                          scale=axis.scale, description=axis.description, reference=axis.reference,
                          domain=axis.domain)


def _employability(session: Session, countries: list[str], digits: int) -> dict[Key, float]:
    """Mean ISE of the group's scored occupations, per country and year."""
    method = employability_method(session)
    if method is None:
        return {}
    rows = session.execute(select(
        EmployabilityScore.country_iso3, EmployabilityScore.occupation_code,
        EmployabilityScore.year, EmployabilityScore.score,
    ).where(EmployabilityScore.methodology_id == method.methodology_id,
            EmployabilityScore.country_iso3.in_(countries),
            EmployabilityScore.score.is_not(None))).all()
    grouped: dict[Key, list[float]] = defaultdict(list)
    for country, occ, year, score in rows:
        grouped[(country, occ[:digits], year)].append(score)
    return {k: fmean(v) for k, v in grouped.items()}


@router.get("/occupation-groups/motion", response_model=MotionPage)
def occupation_groups_motion(
    y: str | None = Query(None, description="Variable del eje vertical (ver y_options)"),
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """One bubble per occupation group and country, per year: x and size from config
    (app.yaml -> motion), y chosen among y_options."""
    conf = app_config().motion
    y_key = y or conf.default_y
    if y_key not in conf.y:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            app_config().messages["unknown_motion_axis"].format(
                                axis=y_key, options=", ".join(conf.y)))
    countries = _country_list(country)
    y_axis = conf.y[y_key]
    axes = {"x": conf.x, "x_secondary": conf.x_secondary, "size": conf.size, "y": y_axis}
    codes = {a.indicator for a in axes.values() if a and a.indicator}
    excluded = {o.occupation_code for o in catalog().occupations if o.is_excluded}
    raw = _load_points(session, codes)
    by_indicator: dict[str, dict] = defaultdict(dict)
    for (ind, c, occ), pts in raw.items():
        if c in countries and occ not in excluded:
            by_indicator[ind][(c, occ)] = pts

    size_values = roll_up(by_indicator[conf.size.indicator],
                          _source_digits(conf.size.indicator, countries),
                          conf.group_digits, conf.size.aggregate)
    years = sorted({y for (_, _, y) in size_values if y >= conf.first_year})

    def values(axis: MotionAxis) -> dict[Key, float]:
        if axis.methodology:
            return _employability(session, countries, conf.group_digits)
        rolled = roll_up(by_indicator[axis.indicator], _source_digits(axis.indicator, countries),
                         conf.group_digits, axis.aggregate,
                         years if axis.applies_to_all_years else None)
        return year_over_year(rolled, axis.min_base) if axis.measure == "yoy" else rolled

    x_values = values(conf.x)
    x2_values = values(conf.x_secondary) if conf.x_secondary else {}
    y_values = values(y_axis)
    points = []
    for (c, g, yr), yv in sorted(y_values.items()):
        if yr not in years:
            continue
        xv = with_carry(x_values, (c, g, yr), conf.max_carry_years)
        sv = with_carry(size_values, (c, g, yr), conf.max_carry_years)
        if xv is None or sv is None:
            continue
        carried = {name: used for name, (_, used) in (("x", xv), ("size", sv)) if used != yr}
        x2 = with_carry(x2_values, (c, g, xv[1]), 0)  # same year as the x value shown
        points.append(MotionPoint(country_iso3=c, group_code=g, year=yr, x=xv[0],
                                  x_secondary=x2[0] if x2 else None, y=yv, size=sv[0],
                                  carried=carried))
    shown = {p.year for p in points}
    group_codes = sorted({p.group_code for p in points})
    return MotionPage(
        title=conf.title, description=conf.description, years=[y for y in years if y in shown], x=_info("x", conf.x),
        x_secondary=_info("x_secondary", conf.x_secondary) if conf.x_secondary else None,
        y=_info(y_key, y_axis), size=_info("size", conf.size),
        y_options=[_info(k, a) for k, a in conf.y.items()],
        groups=[MotionGroup(code=g, name=catalog().groups.get(g)) for g in group_codes],
        points=points, notes=conf.notes,
    )
