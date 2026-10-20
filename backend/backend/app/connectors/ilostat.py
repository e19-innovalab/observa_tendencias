"""ILOSTAT SDMX REST API (CSV, no authentication).

GET {base_url}/data/{agency},{dataflow},{version}/{key}?startPeriod=
Sector series carry the ISIC section in `sector_dimension`; rows are mapped to catalog sectors
through sectors[].ilostat_eco in config/catalog.yaml. Occupation series carry an ISCO-08 group
in `occupation_dimension`; every catalog occupation whose isco08_code starts with the group's
digits gets that value (ILOSTAT does not publish 4-digit occupations).
Education-mismatch series (employment by occupation and education) are turned into the share of
workers whose education is above or below the one their major group requires
(config/reference/isco_education_requirements.yaml), nationally and per major group.
"""
import csv
import io
from collections import defaultdict
from statistics import fmean

from app.connectors.base import BaseConnector, CanonicalRecord, SeriesSpec
from app.connectors.http import get_with_retry, make_client
from app.core.config_files import (
    EducationMismatchSeries,
    EducationRequirementsConf,
    catalog,
    education_requirements,
)

VALUE_COLUMN = "OBS_VALUE"
COUNTRY_COLUMN = "REF_AREA"
PERIOD_COLUMN = "TIME_PERIOD"
STATUS_COLUMN = "OBS_STATUS"


def _sectors_by_code() -> dict[str, list[str]]:
    """ILOSTAT economic-activity code -> catalog sector codes (one code can feed several)."""
    out: dict[str, list[str]] = defaultdict(list)
    for sector in catalog().sectors:
        for code in sector.ilostat_eco:
            out[code].append(sector.sector_code)
    return out


def _occupations_by_code(prefix: str, digits: int) -> dict[str, list[str]]:
    """ILOSTAT occupation-group code -> catalog occupation codes in that ISCO-08 group."""
    out: dict[str, list[str]] = defaultdict(list)
    for occ in catalog().occupations:
        out[f"{prefix}{occ.isco08_code[:digits]}"].append(occ.occupation_code)
    return out


def education_cells(rows: list[dict], req: EducationRequirementsConf
                    ) -> dict[tuple[str, str, str, str], tuple[str, float]]:
    """{(country, period, ISCO group, band): (status, employed)}: employment by major group and
    education band, from each country's last break in series onward. status is matched, over or
    under against the band the group requires, or excluded (excluded groups, education not stated).
    Totals, aggregates and occupation groups of other classifications are not cells."""
    rank, needed = req.rank_by_edu_code(), req.required_rank()
    band_of = {code: band.code for band in req.bands for code in band.edu_codes}
    band_of.update({code: req.not_stated.code for code in req.not_stated.edu_codes})
    prefix, occ_col, edu_col = req.occupation_code_prefix, req.occupation_dimension, \
        req.education_dimension
    last_break: dict[str, int] = {}
    if req.break_status:
        for r in rows:
            if r.get(STATUS_COLUMN) == req.break_status:
                year = int(r[PERIOD_COLUMN][:4])
                last_break[r[COUNTRY_COLUMN]] = max(year, last_break.get(r[COUNTRY_COLUMN], year))
    cells: dict[tuple[str, str, str, str], tuple[str, float]] = {}
    for r in rows:
        occ, edu = r[occ_col], r[edu_col]
        group = occ[len(prefix):] if occ.startswith(prefix) else None
        if (group not in needed and group not in req.excluded_groups) or edu not in band_of:
            continue
        if int(r[PERIOD_COLUMN][:4]) < last_break.get(r[COUNTRY_COLUMN], 0):
            continue
        if group in needed and edu in rank:
            diff = rank[edu] - needed[group]
            status = "matched" if diff == 0 else "over" if diff > 0 else "under"
        else:
            status = "excluded"
        key = (r[COUNTRY_COLUMN], r[PERIOD_COLUMN], group, band_of[edu])
        previous = cells.get(key, (status, 0.0))[1]
        cells[key] = (status, previous + float(r[VALUE_COLUMN]))
    return cells


def education_mismatch(rows: list[dict], conf: EducationMismatchSeries
                       ) -> list[tuple[str, str, str | None, float]]:
    """(country, period, ISCO group or None for the national rate, percent of workers over- or
    under-qualified), computed from education_cells without the excluded ones."""
    req = education_requirements(conf.file)
    needed = req.required_rank()
    by_group: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    national: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (country, period, group, _), (status, employed) in education_cells(rows, req).items():
        if status == "excluded":
            continue
        by_group[(country, period, group)][status] += employed
        national[(country, period)][status] += employed
    pick = conf.measure
    # a group requiring the top band cannot be over-qualified (nor the bottom one under-qualified):
    # its 0 % is not a result, so it is not stored
    impossible = max(needed.values()) if pick == "over" else min(needed.values())
    out = [(country, period, group, 100 * c[pick] / sum(c.values()))
           for (country, period, group), c in by_group.items()
           if sum(c.values()) and needed[group] != impossible]
    out += [(country, period, None, 100 * c[pick] / sum(c.values()))
            for (country, period), c in national.items() if sum(c.values())]
    return out


class IlostatConnector(BaseConnector):
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        o = self.options
        countries = o["country_separator"].join(self.countries)
        payloads = []
        async with make_client() as client:
            for indicator, series in specs:
                flow = f"{o['agency']},{series.dataflow},{o['dataflow_version']}"
                series_countries = o["country_separator"].join(series.countries) \
                    if series.countries else countries
                key = series.key.format(countries=series_countries)
                url = f"{self.source.base_url}/data/{flow}/{key}"
                response = await get_with_retry(
                    client, url,
                    params={"startPeriod": since_year or o["start_year"]},
                    headers={"Accept": o["accept"]},
                )
                payloads.append({"indicator": indicator, "series": series, "csv": response.text})
        return payloads

    def education_cells(self, raw_payload: dict) -> list[dict]:
        series = raw_payload["series"]
        if not series.education_mismatch:
            return []
        allowed = set(series.countries or self.countries)
        rows = [r for r in csv.DictReader(io.StringIO(raw_payload["csv"]))
                if r.get(VALUE_COLUMN) not in (None, "") and r.get(COUNTRY_COLUMN) in allowed]
        cells = education_cells(rows, education_requirements(series.education_mismatch.file))
        return [{"country_iso3": c, "year": int(p[:4]), "isco_group": g, "band": b,
                 "status": status, "employed": employed}
                for (c, p, g, b), (status, employed) in cells.items()]

    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        indicator, series = raw_payload["indicator"], raw_payload["series"]
        allowed = set(series.countries or self.countries)
        rows = [
            r for r in csv.DictReader(io.StringIO(raw_payload["csv"]))
            if r.get(VALUE_COLUMN) not in (None, "") and r.get(COUNTRY_COLUMN) in allowed
        ]

        def record(country: str, period: str, value: float, sector: str | None = None,
                   occupation: str | None = None):
            return CanonicalRecord(
                indicator_code=indicator.code, country_iso3=country, sector_code=sector,
                occupation_code=occupation, period=period, frequency=series.frequency,
                value=value, unit=indicator.unit,
            )

        if series.education_mismatch:
            req = education_requirements(series.education_mismatch.file)
            groups = _occupations_by_code("", req.occupation_isco_digits)
            return [
                record(country, period, value, occupation=occ)
                for country, period, group, value in education_mismatch(rows, series.education_mismatch)
                for occ in ([None] if group is None else groups.get(group, []))
            ]

        if series.occupation_dimension:
            groups = _occupations_by_code(series.occupation_code_prefix,
                                          series.occupation_isco_digits)
            return [
                record(r[COUNTRY_COLUMN], r[PERIOD_COLUMN], float(r[VALUE_COLUMN]), occupation=occ)
                for r in rows for occ in groups.get(r[series.occupation_dimension], [])
            ]

        if not series.sector_dimension:
            return [record(r[COUNTRY_COLUMN], r[PERIOD_COLUMN], float(r[VALUE_COLUMN])) for r in rows]

        records = []
        by_code = _sectors_by_code()
        # (country, period, sector) -> {ilostat code: value}
        parts: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
        for r in rows:
            code, value = r[series.sector_dimension], float(r[VALUE_COLUMN])
            if code == series.total_code:
                records.append(record(r[COUNTRY_COLUMN], r[PERIOD_COLUMN], value))
            for sector in by_code.get(code, []):
                parts[(r[COUNTRY_COLUMN], r[PERIOD_COLUMN], sector)][code] = value

        required = {s.sector_code: set(s.ilostat_eco) for s in catalog().sectors}
        aggregate = sum if series.sector_aggregation == "sum" else fmean
        for (country, period, sector), values in parts.items():
            if set(values) != required[sector]:
                continue  # a partial sum or mean would misrepresent the sector
            records.append(record(country, period, float(aggregate(values.values())), sector))
        return records
