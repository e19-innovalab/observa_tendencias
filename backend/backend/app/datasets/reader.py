"""Read an official file with its profile and check that it keeps the validated format.

The same reader serves automatic downloads and manual uploads. It never loads anything: it
returns canonical records plus a report (errors block the load, warnings do not).
"""
import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string

from app.connectors.base import CanonicalRecord
from app.core.config_files import app_config, catalog, indicators
from app.datasets.profiles import DatasetProfile, normalize_text
from app.normalization.periods import period_label, to_period_range

_MONTH_ABBR_YY = re.compile(r"^([a-z]{3})-(\d{2})$")


@dataclass
class Issue:
    message: str
    row: int | None = None
    column: str | None = None


@dataclass
class ReadReport:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    header_found: list[str] = field(default_factory=list)
    header_expected: list[str] | None = None
    records: list[CanonicalRecord] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)  # target "graduates": aggregated rows
    periods: list[str] = field(default_factory=list)
    provisional_periods: list[str] = field(default_factory=list)
    fingerprint: str = ""

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [vars(e) for e in self.errors],
            "warnings": [vars(w) for w in self.warnings],
            "header_found": self.header_found,
            "header_expected": self.header_expected,
            "records": len(self.records) or len(self.rows),
            "first_period": self.periods[0] if self.periods else None,
            "last_period": self.periods[-1] if self.periods else None,
            "periods": len(self.periods),
            "provisional_periods": self.provisional_periods,
            "fingerprint": self.fingerprint,
        }


def _msg(key: str, **kw) -> str:
    return app_config().datasets.messages[key].format(**kw)


def _iter_rows(path: Path, profile: DatasetProfile, report: ReadReport):
    """Rows as tuples, streamed (large row-per-record files are never loaded whole)."""
    fmt = profile.file.format
    if fmt == "auto":
        fmt = path.suffix.lower().lstrip(".")
    if fmt == "xlsx":
        wb = load_workbook(path, read_only=True, data_only=True)
        if profile.file.sheet and profile.file.sheet not in wb.sheetnames:
            report.errors.append(Issue(_msg("sheet_missing", sheet=profile.file.sheet,
                                            sheets=", ".join(wb.sheetnames))))
            return None
        ws = wb[profile.file.sheet] if profile.file.sheet else wb.worksheets[0]
        return ws.iter_rows(values_only=True)
    if fmt == "csv":
        text = path.read_bytes().decode(profile.file.csv_encoding)
        return (tuple(r) for r in csv.reader(io.StringIO(text), delimiter=profile.file.csv_delimiter))
    report.errors.append(Issue(_msg("unsupported_format", name=path.name)))
    return None


def _rows(path: Path, profile: DatasetProfile, report: ReadReport) -> list[tuple] | None:
    rows = _iter_rows(path, profile, report)
    return None if rows is None else list(rows)


def _parse_period(cell, profile: DatasetProfile) -> tuple[date, bool] | None:
    """(first day of the period, provisional?) or None if the cell is not a period."""
    conf = profile.period
    if "date" in conf.formats and isinstance(cell, datetime | date):
        d = cell.date() if isinstance(cell, datetime) else cell
        return d.replace(day=1), False
    if cell is None:
        return None
    text = normalize_text(cell)
    provisional = bool(conf.provisional_marker and text.endswith(conf.provisional_marker))
    if provisional:
        text = text[: -len(conf.provisional_marker)].strip()
    if "month_abbr_yy" in conf.formats:
        m = _MONTH_ABBR_YY.match(text)
        if m and m.group(1) in conf.month_abbr:
            return date(2000 + int(m.group(2)), conf.month_abbr[m.group(1)], 1), provisional
    return None


def _number(value, profile: DatasetProfile | None = None) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if profile and profile.file.thousands_separator:
        text = text.replace(profile.file.thousands_separator, "")
    if profile and profile.file.decimal_separator != ".":
        text = text.replace(profile.file.decimal_separator, ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _check_headers(found: list[str], expected: list[str], report: ReadReport) -> None:
    exp = [normalize_text(h) for h in expected]
    if found == exp:
        return
    report.errors.append(Issue(_msg("headers_changed")))
    for h in exp:
        if h not in found:
            report.errors.append(Issue(_msg("header_missing", column=h)))
    for h in found:
        if h not in exp:
            report.errors.append(Issue(_msg("header_unexpected", column=h)))
    if sorted(found) == sorted(exp):
        report.errors.append(Issue(_msg("header_order")))


def _read_wide(rows: list[tuple], profile: DatasetProfile, report: ReadReport) -> None:
    exp = profile.expected
    header = [normalize_text(c) for c in rows[profile.file.header_row - 1] if c not in (None, "")]
    report.header_found = header
    report.header_expected = exp.headers
    if exp.headers:
        _check_headers(header, exp.headers, report)
        if not report.ok:
            return
    raw_header = [normalize_text(c) if c not in (None, "") else None
                  for c in rows[profile.file.header_row - 1]]
    index = {h: i for i, h in enumerate(raw_header) if h}
    period_idx = index[normalize_text(profile.period.column)]
    targets = {index[normalize_text(name)]: (name, t) for name, t in profile.columns.items()}
    unit = indicators().get(profile.indicator).unit
    previous: date | None = None
    for offset, row in enumerate(rows[profile.file.first_data_row - 1:]):
        row_no = profile.file.first_data_row + offset
        parsed = _parse_period(row[period_idx] if period_idx < len(row) else None, profile)
        if parsed is None:
            if not report.periods:
                continue  # blank or note rows before the data starts
            break  # footnotes after the data
        start, provisional = parsed
        label = period_label(start, profile.frequency)
        if previous and start <= previous:
            report.errors.append(Issue(_msg("period_order", period=label), row=row_no))
        previous = start
        report.periods.append(label)
        if provisional:
            report.provisional_periods.append(label)
        for idx, (name, target) in targets.items():
            raw = row[idx] if idx < len(row) else None
            if raw in (None, "") and target.skip_empty:
                continue
            value = _number(raw, profile)
            if value is None:
                report.errors.append(Issue(_msg("not_numeric", value=raw), row=row_no, column=name))
                continue
            if (exp.value_min is not None and value < exp.value_min) or (
                    exp.value_max is not None and value > exp.value_max):
                report.errors.append(Issue(_msg("out_of_range", min=exp.value_min,
                                                max=exp.value_max, value=value),
                                           row=row_no, column=name))
                continue
            report.records.append(CanonicalRecord(
                indicator_code=profile.indicator, country_iso3=profile.country,
                sector_code=target.sector, occupation_code=target.occupation,
                period=label, frequency=profile.frequency, value=value, unit=unit,
            ))
    if not report.periods:
        report.errors.append(Issue(_msg("no_periods", column=profile.period.column)))
        return
    if exp.first_period and report.periods[0] != exp.first_period:
        report.errors.append(Issue(_msg("first_period", found=report.periods[0],
                                        expected=exp.first_period)))
    if exp.min_periods and len(report.periods) < exp.min_periods:
        report.errors.append(Issue(_msg("min_periods", found=len(report.periods),
                                        expected=exp.min_periods)))


def _read_long(rows: list[tuple], profile: DatasetProfile, report: ReadReport) -> None:
    conf, exp = profile.long_format, profile.expected
    header = [normalize_text(c) if c not in (None, "") else None
              for c in rows[profile.file.header_row - 1]]
    report.header_found = [h for h in header if h]
    report.header_expected = [conf.columns[k] for k in conf.required]
    index = {h: i for i, h in enumerate(header) if h}
    for key in conf.required:
        if normalize_text(conf.columns[key]) not in index:
            report.errors.append(Issue(_msg("header_missing", column=conf.columns[key])))
    if not report.ok:
        return
    col = {k: index.get(normalize_text(v)) for k, v in conf.columns.items()}
    known = {i.code: i for i in indicators().indicators}
    countries = {c.iso3 for c in catalog().countries}
    sectors = {s.sector_code for s in catalog().sectors}
    occupations = {o.occupation_code for o in catalog().occupations}
    periods = set()

    def cell(row, key):
        i = col.get(key)
        v = row[i] if i is not None and i < len(row) else None
        return None if v in (None, "") else v

    for offset, row in enumerate(rows[profile.file.first_data_row - 1:]):
        row_no = profile.file.first_data_row + offset
        if not any(v not in (None, "") for v in row):
            continue
        problems = []
        for key in conf.required:
            if cell(row, key) is None:
                problems.append(Issue(_msg("missing_value", column=conf.columns[key]), row_no,
                                      conf.columns[key]))
        if problems:
            report.errors.extend(problems)
            continue
        ind_code, country = str(cell(row, "indicator")).strip(), str(cell(row, "country")).strip().upper()
        freq, period = str(cell(row, "frequency")).strip().upper(), str(cell(row, "period")).strip()
        sector = cell(row, "sector")
        occupation = cell(row, "occupation")
        occupation = str(occupation).strip().zfill(4) if occupation is not None else None
        value = _number(cell(row, "value"))
        checks = [
            (ind_code not in known, "unknown_indicator", {"code": ind_code}, "indicator"),
            (country not in countries, "unknown_country", {"code": country}, "country"),
            (sector is not None and sector not in sectors, "unknown_sector", {"code": sector}, "sector"),
            (occupation is not None and occupation not in occupations, "unknown_occupation",
             {"code": occupation}, "occupation"),
            (freq not in ("A", "Q", "M"), "bad_frequency", {"value": freq}, "frequency"),
            (value is None, "not_numeric", {"value": cell(row, "value")}, "value"),
        ]
        for failed, key, kw, column in checks:
            if failed:
                problems.append(Issue(_msg(key, **kw), row_no, conf.columns[column]))
        if not problems:
            try:
                start, _ = to_period_range(period, freq)
            except ValueError:
                problems.append(Issue(_msg("bad_period", frequency=freq, value=period), row_no,
                                      conf.columns["period"]))
        if not problems and ((exp.value_min is not None and value < exp.value_min) or (
                exp.value_max is not None and value > exp.value_max)):
            problems.append(Issue(_msg("out_of_range", min=exp.value_min, max=exp.value_max,
                                       value=value), row_no, conf.columns["value"]))
        if problems:
            report.errors.extend(problems)
            continue
        label = period_label(start, freq)
        periods.add((start, label))
        report.records.append(CanonicalRecord(
            indicator_code=ind_code, country_iso3=country, sector_code=sector,
            occupation_code=occupation, period=label, frequency=freq, value=value,
            unit=known[ind_code].unit,
        ))
    report.periods = [label for _, label in sorted(periods)]


def _read_aggregate(rows, profile: DatasetProfile, report: ReadReport) -> None:
    """Row-per-record files (e.g. one row per program and year): add up value_column by the
    group columns and the year read from period_column."""
    conf, exp = profile.aggregate, profile.expected
    for _ in range(profile.file.header_row - 1):
        next(rows, None)
    header_row = next(rows, None) or ()
    header = [normalize_text(c) if c not in (None, "") else None for c in header_row]
    report.header_found = [h for h in header if h]
    report.header_expected = exp.headers
    if exp.headers:
        _check_headers(report.header_found, exp.headers, report)
        if not report.ok:
            return
    index = {h: i for i, h in enumerate(header) if h}
    period_idx = index[normalize_text(conf.period_column)]
    value_idx = index[normalize_text(conf.value_column)]
    group_idx = {k: index[normalize_text(v)] for k, v in conf.group_columns.items()}
    filters = {index[normalize_text(k)]: {normalize_text(x) for x in v}
               for k, v in conf.filters.items()}
    pattern = re.compile(conf.period_pattern)
    totals: dict[tuple, float] = {}
    years = set()
    skip = profile.file.first_data_row - profile.file.header_row - 1
    for offset, row in enumerate(rows):
        if offset < skip:
            continue
        row_no = profile.file.first_data_row + offset - skip
        if not row or all(v in (None, "") for v in row):
            continue
        if any(normalize_text(row[i]) not in allowed for i, allowed in filters.items()):
            continue
        m = pattern.match(str(row[period_idx] or "").strip())
        if not m:
            report.errors.append(Issue(_msg("bad_period", frequency="A", value=row[period_idx]),
                                       row=row_no, column=conf.period_column))
            if len(report.errors) > app_config().datasets.max_errors_reported:
                return
            continue
        raw = row[value_idx]
        value = 0.0 if raw in (None, "") else _number(raw, profile)
        if value is None:
            report.errors.append(Issue(_msg("not_numeric", value=raw), row=row_no,
                                       column=conf.value_column))
            continue
        year = int(m.group("year"))
        years.add(year)
        key = (year,) + tuple(row[i] for i in group_idx.values())
        totals[key] = totals.get(key, 0.0) + value
    names = list(group_idx)
    for key, value in totals.items():
        if (exp.value_min is not None and value < exp.value_min) or (
                exp.value_max is not None and value > exp.value_max):
            report.errors.append(Issue(_msg("out_of_range", min=exp.value_min,
                                            max=exp.value_max, value=value)))
            continue
        report.rows.append({"year": key[0], **dict(zip(names, key[1:])), "value": value})
    report.periods = [str(y) for y in sorted(years)]
    if not report.periods:
        report.errors.append(Issue(_msg("no_periods", column=conf.period_column)))
    elif exp.first_period and report.periods[0] != exp.first_period:
        report.errors.append(Issue(_msg("first_period", found=report.periods[0],
                                        expected=exp.first_period)))
    if exp.min_periods and len(report.periods) < exp.min_periods:
        report.errors.append(Issue(_msg("min_periods", found=len(report.periods),
                                        expected=exp.min_periods)))


def _read_outline(path: Path, profile: DatasetProfile, report: ReadReport) -> None:
    """Nested report sheets: item rows (not bold) are added up by name for each sheet's level;
    the year comes from the sheet title and the items must add up to the sheet total."""
    conf = profile.outline
    wb = load_workbook(path, data_only=True)  # not read-only: the reader needs cell styles
    sheets = {ws.title.strip(): ws for ws in wb.worksheets}
    name_col, value_col = column_index_from_string(conf.name_column), \
        column_index_from_string(conf.value_column)
    period_re, total_re, end_re = (re.compile(p, re.I) for p in (
        conf.period_pattern, conf.total_pattern, conf.end_pattern))
    missing = {normalize_text(v) for v in conf.missing_values}
    exp = profile.expected
    totals: dict[tuple, float] = {}
    names: dict[tuple, str] = {}
    years = set()
    for spec in conf.sheets:
        ws = sheets.get(spec.sheet)
        if ws is None:
            report.errors.append(Issue(_msg("sheet_missing", sheet=spec.sheet,
                                            sheets=", ".join(sheets))))
            continue
        title = " ".join(str(c.value) for row in ws.iter_rows(max_row=conf.title_rows)
                         for c in row if c.value is not None)
        m = period_re.search(title)
        if not m:
            report.errors.append(Issue(_msg("outline_no_period", sheet=spec.sheet)))
            continue
        year = int(m.group("year"))
        years.add(year)
        sheet_total, found, items = None, 0.0, 0
        for row in ws.iter_rows(min_row=conf.title_rows + 1):
            cell = row[name_col - 1] if len(row) >= name_col else None
            if cell is None or cell.value in (None, ""):
                continue
            name = str(cell.value).strip()
            value = row[value_col - 1].value if len(row) >= value_col else None
            if sheet_total is None:
                if total_re.search(name):
                    sheet_total = _number(value, profile)
                continue
            if end_re.search(name):
                break
            if cell.font.b or value in (None, ""):
                continue  # headings (institution, faculty, campus) and items without a value
            if isinstance(value, str) and normalize_text(value) in missing:
                continue
            number = _number(value, profile)
            if number is None:
                report.errors.append(Issue(_msg("not_numeric", value=value), row=cell.row,
                                           column=f"{spec.sheet}!{conf.value_column}"))
                continue
            key = (year, normalize_text(name), spec.level)
            names.setdefault(key, name)
            totals[key] = totals.get(key, 0.0) + number
            found += number
            items += 1
        if sheet_total is None:
            report.errors.append(Issue(_msg("outline_no_total", sheet=spec.sheet)))
            continue
        if not items:
            report.errors.append(Issue(_msg("outline_no_items", sheet=spec.sheet)))
            continue
        gap = abs(sheet_total - found) / sheet_total if sheet_total else 0.0
        if gap:
            issue = Issue(_msg("outline_total_gap", sheet=spec.sheet, found=fmt_number(found),
                               total=fmt_number(sheet_total), pct=round(gap * 100, 1)))
            (report.warnings if gap <= conf.max_total_gap else report.errors).append(issue)
    if len(years) > 1:
        report.errors.append(Issue(_msg("outline_periods_differ",
                                        years=", ".join(map(str, sorted(years))))))
    for key, value in totals.items():
        if (exp.value_min is not None and value < exp.value_min) or (
                exp.value_max is not None and value > exp.value_max):
            report.errors.append(Issue(_msg("out_of_range", min=exp.value_min,
                                            max=exp.value_max, value=value)))
            continue
        report.rows.append({"year": key[0], "career": names[key], "level": key[2],
                            "value": value})
    report.periods = [str(y) for y in sorted(years)]
    report.header_found = [s.sheet for s in conf.sheets]


def fmt_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def read_dataset(path: Path, profile: DatasetProfile) -> ReadReport:
    report = ReadReport()
    if profile.outline:
        _read_outline(path, profile, report)
        report.fingerprint = hashlib.sha256("|".join(report.header_found).encode()).hexdigest()[:16]
        report.errors = report.errors[:app_config().datasets.max_errors_reported]
        return report
    if profile.aggregate:
        rows = _iter_rows(path, profile, report)
        if rows is not None:
            _read_aggregate(iter(rows), profile, report)
        report.fingerprint = hashlib.sha256("|".join(
            [profile.file.sheet or "", *report.header_found]).encode()).hexdigest()[:16]
        report.errors = report.errors[:app_config().datasets.max_errors_reported]
        return report
    rows = _rows(path, profile, report)
    if rows is None:
        return report
    if len(rows) < profile.file.header_row:
        report.errors.append(Issue(_msg("no_periods", column=profile.file.header_row)))
        return report
    if profile.is_long:
        _read_long(rows, profile, report)
    else:
        _read_wide(rows, profile, report)
    report.fingerprint = hashlib.sha256("|".join(
        [profile.file.sheet or "", *report.header_found]).encode()).hexdigest()[:16]
    limit = app_config().datasets.max_errors_reported
    if len(report.errors) > limit:
        report.errors = report.errors[:limit]
    return report
