from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.recompute import METHODOLOGY_SECTIONS, current_digests, params_digest
from app.analytics.trends import classify_trend
from app.api.v1.indicators import _country_list, _indicator
from app.core.config_files import app_config, indicators
from app.core.database import get_session
from app.models import Methodology, TrendResult
from app.normalization.periods import period_label
from app.schemas.observatory import (
    MethodologyItem,
    MethodologyRef,
    ProjectionResult,
    ProjectionSeries,
    TrendItem,
)
from app.services.observations import indicator_item, query_points, source_refs

router = APIRouter(tags=["trends"])
TrendState = Literal["growing", "stable", "declining", "insufficient_data"]


def _assessment(state: str, higher_is_better: bool | None) -> str | None:
    if state == "insufficient_data":
        return None
    if state == "stable" or higher_is_better is None:
        return "neutral"
    return "favorable" if (state == "growing") == higher_is_better else "unfavorable"


def _ref(m: Methodology) -> MethodologyRef:
    return MethodologyRef(methodology_id=m.methodology_id, methodology_type=m.methodology_type,
                          version=m.version, name=m.name)


def _validate_range(from_year: int | None, to_year: int | None) -> None:
    if from_year and to_year and from_year > to_year:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            app_config().messages["invalid_year_range"])


def _trend_item(ind, country, sector, occupation, frequency, window_start, window_end, n_points,
                slope, pct_change, state, previous_state, source, computed_at, method,
                window_mode, refs) -> TrendItem:
    conf = app_config()
    assessment = _assessment(state, ind.higher_is_better)
    return TrendItem(
        indicator=indicator_item(ind, refs), country_iso3=country, sector_code=sector,
        occupation_code=occupation, window_mode=window_mode,
        window_start=period_label(window_start, frequency) if window_start else None,
        window_end=period_label(window_end, frequency) if window_end else None,
        n_points=n_points, slope=slope, pct_change=pct_change,
        trend_state=state, trend_state_label=conf.trend_states[state],
        assessment=assessment, assessment_label=conf.assessments[assessment] if assessment else None,
        previous_trend_state=previous_state,
        data_type="calculated", data_type_label=conf.data_types["calculated"],
        source=source, computed_at=computed_at, methodology=_ref(method) if method else None,
    )


def _stored_trends(session, codes, countries, sector, occupation, refs) -> list[TrendItem]:
    """Latest stored window per series (computed after each ingestion), plus the previous state."""
    stmt = select(TrendResult).where(
        TrendResult.indicator_code.in_(codes),
        TrendResult.country_iso3.in_(countries),
        TrendResult.sector_code == sector if sector else TrendResult.sector_code.is_(None),
        TrendResult.occupation_code == occupation if occupation
        else TrendResult.occupation_code.is_(None),
    ).order_by(TrendResult.window_end.desc(), TrendResult.computed_at.desc())
    methods = {m.methodology_id: m for m in session.scalars(select(Methodology)).all()}
    history: dict[tuple, list[TrendResult]] = {}
    for t in session.scalars(stmt).all():
        key = (t.indicator_code, t.country_iso3, t.sector_code, t.occupation_code, t.frequency)
        history.setdefault(key, []).append(t)
    out = []
    for rows in history.values():
        t = rows[0]
        out.append(_trend_item(
            indicators().get(t.indicator_code), t.country_iso3, t.sector_code, t.occupation_code,
            t.frequency, t.window_start, t.window_end, t.n_points, t.slope, t.pct_change,
            t.trend_state, rows[1].trend_state if len(rows) > 1 else None, refs[t.source_id],
            t.computed_at, methods.get(t.methodology_id), "latest", refs,
        ))
    return out


def _range_trends(session, codes, countries, sector, occupation, from_year, to_year,
                  refs) -> list[TrendItem]:
    """Trend over every observed point in the requested years (Período filter). Computed per
    request with the same methodology; window_points does not apply."""
    now = datetime.now(UTC)
    out = []
    for code in codes:
        ind = indicators().get(code)
        _, params, digest = params_digest("trend", ind.trend)
        method = session.scalar(select(Methodology).where(
            Methodology.methodology_type == "trend", Methodology.params_hash == digest))
        for country in countries:
            points = query_points(session, ind, [country], sector, occupation, from_year, to_year,
                                  data_type="observed")
            if not points:
                continue
            result = classify_trend([p.value for p in points], params)
            last = points[-1]
            out.append(_trend_item(
                ind, country, sector, occupation, last.frequency, points[0].period_start,
                last.period_start, len(points), result["slope"], result["pct_change"],
                result["trend_state"], None, last.source, now, method, "range", refs,
            ))
    return out


@router.get("/trends", response_model=list[TrendItem])
def trends(
    indicator: str | None = None,
    domain: str | None = None,
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    from_year: int | None = Query(None, description="Inicio del período (incluido)"),
    to_year: int | None = Query(None, description="Fin del período (incluido)"),
    state: TrendState | None = None,
    session: Session = Depends(get_session),
):
    """Trend state per series. Without a period: the latest stored window and the previous
    state (to spot reversals). With from_year/to_year: computed over that range."""
    _validate_range(from_year, to_year)
    codes = [_indicator(indicator).code] if indicator else [
        i.code for i in indicators().indicators if domain is None or i.domain == domain
    ]
    countries = _country_list(country)
    refs = source_refs(session)
    if from_year or to_year:
        out = _range_trends(session, codes, countries, sector, occupation, from_year, to_year, refs)
    else:
        out = _stored_trends(session, codes, countries, sector, occupation, refs)
    out = [t for t in out if state is None or t.trend_state == state]
    out.sort(key=lambda i: (i.indicator.code, i.country_iso3))
    return out


@router.get("/projections", response_model=ProjectionResult)
def projections(
    indicator: str,
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    from_year: int | None = Query(None, description="Primer año observado a mostrar"),
    to_year: int | None = Query(None, description="Último año observado a mostrar"),
    session: Session = Depends(get_session),
):
    """Observed series plus indicative projected points (Tendencia actual vs Proyección).

    The period filters the observed part only: projections always start after the latest
    observed value, since that is the history they were fitted on.
    """
    _validate_range(from_year, to_year)
    ind = _indicator(indicator)
    methods = {m.methodology_id: m for m in session.scalars(select(Methodology)).all()}
    items = []
    for iso3 in _country_list(country):
        observed = query_points(session, ind, [iso3], sector, occupation, from_year, to_year,
                                data_type="observed")
        projected = query_points(session, ind, [iso3], sector, occupation, data_type="projected")
        method = methods.get(projected[0].methodology_id) if projected else None
        items.append(ProjectionSeries(country_iso3=iso3, observed=observed, projected=projected,
                                      methodology=_ref(method) if method else None))
    return ProjectionResult(indicator=indicator_item(ind, source_refs(session)),
                            sector_code=sector, occupation_code=occupation, items=items)


@router.get("/methodologies/{methodology_type}", response_model=list[MethodologyItem])
def methodologies(methodology_type: str, session: Session = Depends(get_session)):
    """Every parameter set used for a calculation type; is_current marks the one in config."""
    if methodology_type not in METHODOLOGY_SECTIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, app_config().messages[
            "unknown_methodology"].format(code=methodology_type))
    current = current_digests(methodology_type)
    rows = session.scalars(
        select(Methodology).where(Methodology.methodology_type == methodology_type)
        .order_by(Methodology.created_at.desc())
    ).all()
    return [MethodologyItem(**_ref(m).model_dump(), params=m.params,
                            description_md=m.description_md, created_at=m.created_at,
                            is_current=m.params_hash in current) for m in rows]
