from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.analytics.recompute import params_digest
from app.api.v1.indicators import _country_list
from app.core.config_files import analytics_params, app_config, catalog, indicators, sources
from app.core.database import get_session
from app.core.security import require_api_key
from app.models import Alert, Methodology
from app.schemas.observatory import (
    AlertItem,
    AlertOverride,
    AlertReadUpdate,
    AlertRule,
    AlertRules,
    AlertSeverity,
    AlertsPage,
    CodeName,
    MethodologyItem,
)
from app.services.observations import source_refs

router = APIRouter(prefix="/alerts", tags=["alerts"])
_pagination = app_config().pagination
Severity = Literal["high", "medium", "low"]


def _item(a: Alert, refs) -> AlertItem:
    conf = app_config()
    ind = indicators().get(a.indicator_code) if a.indicator_code else None
    occ = catalog().occupation(a.occupation_code) if a.occupation_code else None
    sector = next((s for s in catalog().sectors if s.sector_code == a.sector_code), None)
    state_labels = (conf.employability.levels if a.alert_type == "index_level_change"
                    else conf.trend_states)
    return AlertItem(
        alert_id=a.alert_id, alert_type=a.alert_type,
        alert_type_label=conf.alerts.types.get(a.alert_type, a.alert_type),
        severity=a.severity, severity_label=conf.alerts.severities.get(a.severity, a.severity),
        entity_type=a.entity_type,
        indicator=CodeName(code=ind.code, name=ind.name) if ind else None,
        country_iso3=a.country_iso3,
        sector=CodeName(code=sector.sector_code, name=sector.name) if sector else None,
        occupation=CodeName(code=occ.occupation_code, name=occ.name) if occ else None,
        source=refs.get(a.source_id) if a.source_id else None,
        period=a.period_label, previous_value=a.previous_value, current_value=a.current_value,
        unit=ind.unit if ind else None,
        previous_state=state_labels.get(a.previous_state) if a.previous_state else None,
        current_state=state_labels.get(a.current_state) if a.current_state else None,
        message=a.message, methodology_id=a.methodology_id, detected_at=a.detected_at,
        is_read=a.is_read,
    )


@router.get("", response_model=AlertsPage)
def list_alerts(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    severity: Severity | None = None,
    alert_type: str | None = None,
    indicator: str | None = None,
    sector: str | None = None,
    occupation: str | None = None,
    unread: bool | None = Query(None, description="true: solo las no leídas"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Alerts panel, newest and most severe first. `unread` is the count for the bell."""
    conds = []
    if country:
        conds.append(Alert.country_iso3.in_(_country_list(country)))
    if severity:
        conds.append(Alert.severity == severity)
    if alert_type:
        conds.append(Alert.alert_type == alert_type)
    if indicator:
        conds.append(Alert.indicator_code == indicator)
    if sector:
        conds.append(Alert.sector_code == sector)
    if occupation:
        conds.append(Alert.occupation_code == occupation)
    if unread is not None:
        conds.append(Alert.is_read.is_(not unread))
    severity_rank = {s: i for i, s in enumerate(app_config().alerts.severities)}
    rows = session.scalars(select(Alert).where(*conds)).all()
    rows.sort(key=lambda a: (-a.detected_at.timestamp(), severity_rank.get(a.severity, 99),
                             a.alert_type, a.alert_id))
    by_severity = dict(session.execute(
        select(Alert.severity, func.count()).where(*conds).group_by(Alert.severity)).all())
    unread_count = session.scalar(select(func.count()).select_from(Alert).where(
        *conds, Alert.is_read.is_(False)))
    refs = source_refs(session)
    return AlertsPage(total=len(rows), unread=unread_count, by_severity=by_severity, limit=limit,
                      offset=offset, items=[_item(a, refs) for a in rows[offset:offset + limit]])


@router.get("/rules", response_model=AlertRules)
def alert_rules(session: Session = Depends(get_session)):
    """What each alert type detects, with the thresholds currently in config/analytics.yaml."""
    conf, p = app_config(), analytics_params("alerts")
    sev = {rule: conf.alerts.severities[code] for rule, code in p["severities"].items()}
    method = session.scalar(select(Methodology).where(
        Methodology.methodology_type == "alert",
        Methodology.params_hash == params_digest("alert")[2]))
    rules = [
        AlertRule(
            alert_type="significant_change", label=conf.alerts.types["significant_change"],
            definition=conf.alerts.type_info.get("significant_change"),
            params={k: p[k] for k in ("change_pct", "min_base", "absolute_units",
                                      "absolute_change", "z_threshold", "z_min_points",
                                      "require_consecutive", "max_age_years",
                                      "occupation_scope")},
            severity_rule=f"{sev['significant_change_high']} si supera "
                          f"{p['high_severity_factor']} veces el umbral; si no, "
                          f"{sev['significant_change_default']}",
            active=True),
        AlertRule(
            alert_type="trend_reversal", label=conf.alerts.types["trend_reversal"],
            definition=conf.alerts.type_info.get("trend_reversal"),
            params={"max_age_years": p["max_age_years"], "occupation_scope": p["occupation_scope"],
                    "trend_methodology": "trend"},
            severity_rule=sev["trend_reversal"], active=True),
        AlertRule(
            alert_type="index_level_change", label=conf.alerts.types["index_level_change"],
            definition=conf.alerts.type_info.get("index_level_change"),
            params={"occupation_scope": p["occupation_scope"],
                    "levels": analytics_params("employability")["levels"]},
            severity_rule=sev["index_level_change"], active=p["occupation_scope"] != "none"),
        AlertRule(
            alert_type="stale_source", label=conf.alerts.types["stale_source"],
            definition=conf.alerts.type_info.get("stale_source"),
            params={"stale_factor": p["stale_factor"],
                    "frequency_days": sources().frequency_days},
            severity_rule=sev["stale_source"], active=True),
        AlertRule(
            alert_type="new_skill_gap", label=conf.alerts.types["new_skill_gap"],
            definition=conf.alerts.type_info.get("new_skill_gap"),
            params={"gap_threshold": p["gap_threshold"]},
            severity_rule=sev["new_skill_gap"], active=False),
    ]
    method_item = None
    if method:
        method_item = MethodologyItem(
            methodology_id=method.methodology_id, methodology_type=method.methodology_type,
            version=method.version, name=method.name, params=method.params,
            description_md=method.description_md, created_at=method.created_at,
            is_current=True)
    return AlertRules(
        methodology=method_item, rules=rules,
        severities=[AlertSeverity(code=code, label=label,
                                  definition=conf.alerts.severity_info.get(code))
                    for code, label in conf.alerts.severities.items()],
        overrides=[AlertOverride(indicator=CodeName(code=i.code, name=i.name), params=i.alerts)
                   for i in indicators().indicators if i.alerts],
    )


@router.patch("/{alert_id}", response_model=AlertItem, dependencies=[Depends(require_api_key)])
def mark_alert(alert_id: int, body: AlertReadUpdate, session: Session = Depends(get_session)):
    alert = session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_alert"].format(id=alert_id))
    alert.is_read = body.is_read
    session.commit()
    return _item(alert, source_refs(session))


@router.post("/read-all", dependencies=[Depends(require_api_key)])
def mark_all_read(session: Session = Depends(get_session)):
    result = session.execute(update(Alert).where(Alert.is_read.is_(False)).values(is_read=True))
    session.commit()
    return {"updated": result.rowcount}
