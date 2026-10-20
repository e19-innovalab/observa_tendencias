from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config_files import app_config, catalog, education_requirements, indicators
from app.core.database import get_session
from app.models import EducationMismatchCell, Source
from app.schemas.observatory import (
    EducationMismatch,
    MismatchBand,
    MismatchCell,
    MismatchGroup,
    MismatchStatus,
    MismatchTotals,
    SourceRef,
)

router = APIRouter(prefix="/education-mismatch", tags=["education"])

STATUSES = ("matched", "over", "under")


def _mismatch_series():
    """(requirements file, source code, {measure: indicator code}) from indicators.yaml."""
    found = [(ind, s) for ind in indicators().indicators for s in ind.series if s.education_mismatch]
    if not found:
        return None, None, {}
    _, first = found[0]
    return first.education_mismatch.file, first.source, {
        s.education_mismatch.measure: ind.code for ind, s in found}


def _share(part: float, whole: float) -> float | None:
    return part / whole if whole else None


@router.get("", response_model=EducationMismatch)
def education_mismatch(
    country: str = Query(..., description="ISO3 (ARG, URY, CHL)"),
    year: int | None = Query(None, description="Año; por defecto, el último con datos"),
    session: Session = Depends(get_session),
):
    """Employed persons (thousands) by major occupation group and education band: the data behind
    the over/under-qualification indicators, with the rule and how the rates come out of it."""
    file, source_code, measures = _mismatch_series()
    country = country.upper()
    source = session.scalar(select(Source).where(Source.source_code == source_code)) \
        if source_code else None
    base = select(EducationMismatchCell).where(EducationMismatchCell.country_iso3 == country)
    if source:
        base = base.where(EducationMismatchCell.source_id == source.source_id)
    years = sorted(session.scalars(select(EducationMismatchCell.year).where(
        EducationMismatchCell.country_iso3 == country).distinct()).all())
    if not file or not years or (year is not None and year not in years):
        raise HTTPException(status.HTTP_404_NOT_FOUND, app_config().messages[
            "no_education_mismatch"].format(country=country))
    year = year or years[-1]
    cells = session.scalars(base.where(EducationMismatchCell.year == year)).all()

    req = education_requirements(file)
    needed = req.required_rank()
    top, bottom = max(needed.values()), min(needed.values())
    names = catalog().groups
    by_group: dict[str, list[EducationMismatchCell]] = {}
    for c in cells:
        by_group.setdefault(c.isco_group, []).append(c)
    order = list(req.requirements) + list(req.excluded_groups)
    groups, totals = [], dict.fromkeys((*STATUSES, "excluded"), 0.0)
    for code in sorted(by_group, key=lambda g: order.index(g) if g in order else len(order)):
        group_cells = by_group[code]
        sums = dict.fromkeys(STATUSES, 0.0)
        for c in group_cells:
            totals[c.status] += c.employed
            if c.status in sums:
                sums[c.status] += c.employed
        considered = sum(sums.values())
        required = req.requirements.get(code)
        groups.append(MismatchGroup(
            isco_group=code, name=names.get(code) or req.excluded_groups.get(code, code),
            required_band=required, excluded_reason=req.excluded_groups.get(code),
            cells=[MismatchCell(band=c.band, employed=c.employed, status=c.status)
                   for c in group_cells],
            total=sum(c.employed for c in group_cells),
            over_share=_share(sums["over"], considered)
            if required and needed[code] != top else None,
            under_share=_share(sums["under"], considered)
            if required and needed[code] != bottom else None,
        ))
    considered = sum(totals[s] for s in STATUSES)
    fetched = session.scalar(select(func.max(EducationMismatchCell.fetched_at)).where(
        EducationMismatchCell.country_iso3 == country))
    return EducationMismatch(
        country_iso3=country, year=year, years=years, unit="thousands_persons",
        source=SourceRef(code=source.source_code, name=source.name) if source else None,
        fetched_at=fetched, indicators=measures,
        bands=[MismatchBand(code=b.code, name=b.name) for b in (*req.bands, req.not_stated)],
        statuses=[MismatchStatus(status=k, label=v.label, description=v.description)
                  for k, v in req.status_info.items()],
        groups=groups,
        totals=MismatchTotals(matched=totals["matched"], over=totals["over"],
                              under=totals["under"], considered=considered,
                              excluded=totals["excluded"]),
        over_rate=_share(totals["over"], considered),
        under_rate=_share(totals["under"], considered),
        explanation=req.explanation,
        page_size=app_config().pagination.ranking_size,
    )
