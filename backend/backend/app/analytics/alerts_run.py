"""Evaluate the alert rules after each update and record new alerts (plan 8.5 and 10).

Rules and thresholds come from config/analytics.yaml (section alerts); labels for messages from
config/app.yaml. Every alert has a dedupe_key (rule + series + period), so evaluating again with
the same data records nothing new.
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.alerts import significant_change, stale_source
from app.analytics.recompute_keys import observed_series_keys
from app.core.config_files import analytics_params, app_config, catalog, indicators, sources
from app.models import Alert, EmployabilityScore, IngestionRun, Methodology, Source, TrendResult
from app.normalization.periods import period_label, shift_period
from app.services.observations import query_points


def _in_scope(occupation: str | None, scope: str, featured: set[str]) -> bool:
    if occupation is None:
        return True
    return scope == "all" or (scope == "featured" and occupation in featured)


NOT_STATES = ("insufficient_data", "not_applicable")


def _changed(previous: str | None, current: str | None) -> bool:
    return bool(previous and current and previous != current
                and not set(NOT_STATES) & {previous, current})


class _Recorder:
    def __init__(self, session: Session):
        from app.analytics.recompute import ensure_methodology  # avoid an import cycle

        self.session = session
        self.keys = set(session.scalars(select(Alert.dedupe_key)).all())
        self.now = datetime.now(UTC)
        self.added = 0
        self.methodology_id = ensure_methodology(session, "alert").methodology_id

    def add(self, key: str, **fields) -> None:
        """Rules computed here point to the alert methodology; trend and index alerts keep the
        methodology of the result they compare."""
        if key in self.keys:
            return
        self.keys.add(key)
        fields.setdefault("methodology_id", self.methodology_id)
        self.session.add(Alert(dedupe_key=key, detected_at=self.now, **fields))
        self.added += 1


def _significant_changes(rec: _Recorder, codes, scope, featured) -> None:
    p = analytics_params("alerts")
    refs = {s.source_code: s.source_id for s in rec.session.scalars(select(Source)).all()}
    oldest_year = rec.now.year - p["max_age_years"]
    found_by_series: dict[tuple, tuple] = {}
    for ind_code, country, sector, occupation, freq in observed_series_keys(rec.session, codes):
        ind = indicators().get(ind_code)
        if ind is None or not _in_scope(occupation, scope, featured):
            continue
        points = [x for x in query_points(rec.session, ind, [country], sector, occupation,
                                          data_type="observed") if x.frequency == freq]
        if len(points) < 2 or points[-1].period_start.year < oldest_year:
            continue
        prev, last = points[-2], points[-1]
        if p["require_consecutive"] and shift_period(prev.period_start, freq, 1)[0] != last.period_start:
            continue
        found = significant_change([x.value for x in points], analytics_params("alerts", ind.alerts),
                                   absolute=ind.unit in p["absolute_units"])
        if found:
            found_by_series[(ind_code, country, sector, occupation, freq)] = (found, last)

    # occupations of the same ISCO group share the value: one alert per group, naming them
    groups: dict[tuple, list[str]] = {}
    for (ind_code, country, sector, occupation, freq), (found, last) in found_by_series.items():
        if occupation is not None:
            key = (ind_code, country, freq, last.period_start, found["previous_value"],
                   found["current_value"])
            groups.setdefault(key, []).append(occupation)
    for (ind_code, country, sector, occupation, freq), (found, last) in found_by_series.items():
        message = found["message"]
        if occupation is not None:
            members = groups[(ind_code, country, freq, last.period_start, found["previous_value"],
                              found["current_value"])]
            if occupation != min(members):
                continue
            if len(members) > 1:
                occ = catalog().occupation(occupation)
                group = occ.isco08_code[:_group_digits(ind_code, occupation, members)]
                message += p["messages"]["shared_group"].format(
                    group=group, occupations=", ".join(catalog().occupation(m).name
                                                       for m in sorted(members)))
        rec.add(
            f"significant_change|{ind_code}|{country}|{sector}|{occupation}|{freq}|{last.period_start}",
            alert_type="significant_change", severity=found["severity"], entity_type="indicator",
            indicator_code=ind_code, country_iso3=country, sector_code=sector,
            occupation_code=occupation, source_id=refs.get(last.source.code),
            period_label=last.period, previous_value=found["previous_value"],
            current_value=found["current_value"], message=message,
        )


def _group_digits(ind_code: str, occupation: str, members: list[str]) -> int:
    """Longest ISCO prefix shared by the occupations (the group the value comes from)."""
    codes = [catalog().occupation(m).isco08_code for m in members]
    digits = 4
    while digits > 1 and len({c[:digits] for c in codes}) > 1:
        digits -= 1
    return digits


def _trend_reversals(rec: _Recorder, codes, scope, featured) -> None:
    from app.analytics.recompute import params_digest  # avoid an import cycle

    p, labels = analytics_params("alerts"), app_config().trend_states
    for ind in indicators().indicators:
        if codes and ind.code not in codes:
            continue
        method = rec.session.scalar(select(Methodology).where(
            Methodology.methodology_type == "trend",
            Methodology.params_hash == params_digest("trend", ind.trend)[2]))
        if method is None:
            continue
        rows = rec.session.scalars(select(TrendResult).where(
            TrendResult.indicator_code == ind.code,
            TrendResult.methodology_id == method.methodology_id,
        ).order_by(TrendResult.window_end.desc())).all()
        history: dict[tuple, list[TrendResult]] = {}
        for t in rows:
            history.setdefault((t.country_iso3, t.sector_code, t.occupation_code, t.frequency),
                               []).append(t)
        oldest_year = rec.now.year - p["max_age_years"]
        changes = {}
        for (country, sector, occupation, freq), series in history.items():
            if len(series) < 2 or not _in_scope(occupation, scope, featured):
                continue
            cur, prev = series[0], series[1]
            if cur.window_end.year >= oldest_year and _changed(prev.trend_state, cur.trend_state):
                changes[(country, sector, occupation, freq)] = (cur, prev)
        # occupations of the same ISCO group share the series: one alert per group
        groups: dict[tuple, list[str]] = {}
        for (country, sector, occupation, freq), (cur, prev) in changes.items():
            if occupation is not None:
                groups.setdefault((country, freq, cur.window_end, cur.slope), []).append(occupation)
        for (country, sector, occupation, freq), (cur, prev) in changes.items():
            message = p["messages"]["trend_reversal"].format(
                previous=labels[prev.trend_state], current=labels[cur.trend_state])
            if occupation is not None:
                members = groups[(country, freq, cur.window_end, cur.slope)]
                if occupation != min(members):
                    continue
                if len(members) > 1:
                    group = catalog().occupation(occupation).isco08_code[
                        :_group_digits(ind.code, occupation, members)]
                    message += p["messages"]["shared_group"].format(
                        group=group, occupations=", ".join(
                            catalog().occupation(m).name for m in sorted(members)))
            rec.add(
                f"trend_reversal|{ind.code}|{country}|{sector}|{occupation}|{freq}|"
                f"{cur.window_end}|{method.methodology_id}",
                alert_type="trend_reversal", severity=p["severities"]["trend_reversal"],
                entity_type="indicator", indicator_code=ind.code, country_iso3=country,
                sector_code=sector, occupation_code=occupation, source_id=cur.source_id,
                period_label=period_label(cur.window_end, freq),
                previous_state=prev.trend_state, current_state=cur.trend_state,
                methodology_id=method.methodology_id, message=message,
            )


def _index_level_changes(rec: _Recorder, scope, featured) -> None:
    from app.analytics.recompute import params_digest  # avoid an import cycle

    if scope == "none":
        return
    p, labels = analytics_params("alerts"), app_config().employability.levels
    method = rec.session.scalar(select(Methodology).where(
        Methodology.methodology_type == "employability_index",
        Methodology.params_hash == params_digest("employability_index")[2]))
    if method is None:
        return
    years = sorted(set(rec.session.scalars(select(EmployabilityScore.year).where(
        EmployabilityScore.methodology_id == method.methodology_id)).all()))
    if len(years) < 2:
        return
    prev_year, cur_year = years[-2], years[-1]
    rows = rec.session.scalars(select(EmployabilityScore).where(
        EmployabilityScore.methodology_id == method.methodology_id,
        EmployabilityScore.year.in_([prev_year, cur_year]))).all()
    by_key = {(s.country_iso3, s.occupation_code, s.year): s for s in rows}
    for (country, occupation, year), cur in by_key.items():
        if year != cur_year or not _in_scope(occupation, scope, featured):
            continue
        prev = by_key.get((country, occupation, prev_year))
        if prev is None or not _changed(prev.level, cur.level):
            continue
        rec.add(
            f"index_level_change|{country}|{occupation}|{cur_year}|{method.methodology_id}",
            alert_type="index_level_change", severity=p["severities"]["index_level_change"],
            entity_type="employability", country_iso3=country, occupation_code=occupation,
            period_label=str(cur_year), previous_value=prev.score, current_value=cur.score,
            previous_state=prev.level, current_state=cur.level,
            methodology_id=method.methodology_id,
            message=p["messages"]["index_level_change"].format(
                previous=labels[prev.level], current=labels[cur.level]),
        )


def evaluate_stale_sources(session: Session) -> int:
    """Sources whose last successful update is older than their expected frequency allows."""
    rec = _Recorder(session)
    conf = sources()
    for source in session.scalars(select(Source)).all():
        sconf = conf.get(source.source_code)
        days = conf.frequency_days.get(source.expected_frequency or "")
        if not sconf or not sconf.connector or not days:
            continue
        last = session.scalar(select(IngestionRun.finished_at).where(
            IngestionRun.source_id == source.source_id,
            IngestionRun.status.in_(("success", "partial")),
        ).order_by(IngestionRun.finished_at.desc()))
        if last is None:
            continue
        last = last if last.tzinfo else last.replace(tzinfo=UTC)
        found = stale_source(last, days, now=rec.now)
        if found:
            rec.add(f"stale_source|{source.source_code}|{last.date()}",
                    alert_type="stale_source", severity=found["severity"], entity_type="source",
                    source_id=source.source_id, period_label=str(last.date()),
                    message=found["message"])
    return rec.added


def evaluate_alerts(session: Session, indicator_codes: list[str] | None = None) -> int:
    """Run every rule for the indicators that changed (all when None). Returns new alerts."""
    scope = analytics_params("alerts")["occupation_scope"]
    featured = {o.occupation_code for o in catalog().occupations if o.is_featured}
    rec = _Recorder(session)
    _significant_changes(rec, indicator_codes, scope, featured)
    _trend_reversals(rec, indicator_codes, scope, featured)
    _index_level_changes(rec, scope, featured)
    session.flush()
    return rec.added + evaluate_stale_sources(session)
