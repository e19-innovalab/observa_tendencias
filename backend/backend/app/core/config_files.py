"""Typed access to backend/config/*.yaml. Files are validated on first read and cached."""
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from app.core.config import BACKEND_DIR, settings

Domain = Literal["labor", "economic", "education"]
Frequency = Literal["A", "Q", "M"]


# --- catalog.yaml -------------------------------------------------------------
class CountryConf(BaseModel):
    iso3: str
    name_es: str
    name_en: str


class SectorConf(BaseModel):
    sector_code: str
    name: str
    isic_codes: list[str]
    ilostat_eco: list[str] = []


class OccupationConf(BaseModel):
    """One ISCO-08 unit group. occupation_code is the ISCO-08 code."""
    occupation_code: str
    name: str
    name_en: str | None = None
    isco08_code: str
    sector_code: str | None = None
    is_featured: bool = False
    is_excluded: bool = False
    exclusion_reason: str | None = None


class ExcludedOccupationConf(BaseModel):
    isco08_code: str
    reason: str


class FeaturedOccupationConf(BaseModel):
    isco08_code: str
    name: str
    sector_code: str


class UniverseConf(BaseModel):
    file: str
    groups_file: str | None = None


class NameRuleConf(BaseModel):
    when_name_en_matches: str
    replace: str
    with_: str = Field(alias="with")

    def apply(self, name_es: str, name_en: str | None) -> str:
        if name_en and re.search(self.when_name_en_matches, name_en):
            return re.sub(self.replace, self.with_, name_es)
        return name_es


class GroupNameRuleConf(BaseModel):
    """Same as NameRuleConf for the hierarchy groups, which have no English title in the groups
    file: the groups it applies to are listed by code."""
    codes: list[str]
    replace: str
    with_: str = Field(alias="with")


class CatalogConf(BaseModel):
    countries: list[CountryConf]
    sectors: list[SectorConf]
    occupation_universe: UniverseConf
    occupation_name_rules: list[NameRuleConf] = []
    group_name_rules: list[GroupNameRuleConf] = []
    excluded_occupations: list[ExcludedOccupationConf] = []
    featured_occupations: list[FeaturedOccupationConf]
    occupations: list[OccupationConf] = []
    groups: dict[str, str] = {}

    def occupation(self, code: str) -> OccupationConf | None:
        return next((o for o in self.occupations if o.occupation_code == code), None)

    def hierarchy(self, code: str) -> list[tuple[str, str | None]]:
        """[(code, name)] from the major group down to the occupation, e.g. 2132 ->
        2, 21, 213, 2132."""
        occ = self.occupation(code)
        return [(code[:n], self.groups.get(code[:n])) for n in (1, 2, 3)] + [
            (code, occ.name if occ else None)]


# --- sources.yaml -------------------------------------------------------------
class HttpConf(BaseModel):
    timeout_seconds: float
    retries: int
    backoff_seconds: float
    user_agent: str
    extra_ca_files: list[str] = []


class SchedulerConf(BaseModel):
    timezone: str
    cron_by_frequency: dict[str, str]
    stale_check_cron: str
    misfire_grace_seconds: int


class SourceConf(BaseModel):
    source_code: str
    name: str
    kind: Literal["api", "dataset", "manual"]
    base_url: str | None = None
    expected_frequency: str | None = None
    connector: str | None = None
    schedule: str | None = None  # cron; overrides scheduler.cron_by_frequency
    series_fields: list[str] = []
    options: dict[str, Any] = {}


class SourcesConf(BaseModel):
    frequency_days: dict[str, float]
    http: HttpConf
    scheduler: SchedulerConf
    sources: list[SourceConf]

    def get(self, code: str) -> SourceConf | None:
        return next((s for s in self.sources if s.source_code == code), None)


# --- indicators.yaml ----------------------------------------------------------
class EducationMismatchSeries(BaseModel):
    """Over/under-qualification computed from employment by occupation and education."""
    file: str  # requirements file under config/ (EducationRequirementsConf)
    measure: Literal["over", "under"]


class SeriesConf(BaseModel):
    source: str
    frequency: Frequency
    id: str | None = None  # world_bank
    dataflow: str | None = None  # ilostat
    key: str | None = None
    sector_dimension: str | None = None
    total_code: str | None = None
    sector_aggregation: Literal["sum", "mean"] = "sum"
    collapse: Literal["quarter", "semester", "year"] | None = None  # datos_argentina
    collapse_aggregation: Literal["avg", "sum", "end_of_period", "min", "max"] | None = None
    transform: Literal["pct_change_year_ago"] | None = None
    scale: float = 1.0
    occupation_dimension: str | None = None  # ilostat occupation series
    occupation_code_prefix: str | None = None
    occupation_isco_digits: int | None = None
    file: str | None = None  # reference_table
    value_field: str | None = None
    profile: str | None = None  # dataset_download
    annualize: dict[str, Any] | None = None  # simel
    countries: list[str] | None = None  # any source: restrict the series to these countries
    education_mismatch: EducationMismatchSeries | None = None  # ilostat occupation x education


class IndicatorConf(BaseModel):
    code: str
    name: str
    unit: str
    domain: Domain
    higher_is_better: bool | None = None
    description: str | None = None
    trend: dict[str, Any] = {}
    alerts: dict[str, Any] = {}
    series: list[SeriesConf] = []


class IndicatorsConf(BaseModel):
    indicators: list[IndicatorConf]

    def series_for(self, source_code: str) -> list[tuple[IndicatorConf, SeriesConf]]:
        return [(i, s) for i in self.indicators for s in i.series if s.source == source_code]

    def get(self, code: str) -> IndicatorConf | None:
        return next((i for i in self.indicators if i.code == code), None)


# --- app.yaml -----------------------------------------------------------------
class PathsConf(BaseModel):
    processed_data: Path
    files: dict[str, str]
    csv_encoding: str

    def processed_file(self, name: str) -> Path:
        return (BACKEND_DIR / self.processed_data / self.files[name]).resolve()


class PaginationConf(BaseModel):
    default_limit: int
    max_limit: int
    observations_max_limit: int
    ranking_size: int


class CorsConf(BaseModel):
    allow_methods: list[str]
    allow_headers: list[str]


class HighlightConf(BaseModel):
    indicator: str
    change: Literal["absolute", "relative"]


class DashboardConf(BaseModel):
    highlights: list[HighlightConf]


class ComparisonConf(BaseModel):
    absolute_units: list[str]


class DevToolsConf(BaseModel):
    explorer: bool


class DimensionInfo(BaseModel):
    definition: str
    unit: str
    possible_range: str
    source_status: str | None = None  # why a dimension has no source yet


class RankingConf(BaseModel):
    max_per_group: int
    group_digits: int
    group_scope: Literal["all", "country"]


class EmployabilityLabels(BaseModel):
    levels: dict[str, str]
    dimensions: dict[str, str]
    dimension_info: dict[str, DimensionInfo] = {}
    no_source_note: str | None = None
    ranking: RankingConf


class AlertLabels(BaseModel):
    types: dict[str, str]
    severities: dict[str, str]
    type_info: dict[str, str] = {}
    severity_info: dict[str, str] = {}


class DatasetsConf(BaseModel):
    raw_dir: Path
    uploads_dir: Path
    max_upload_bytes: int
    max_errors_reported: int
    preview_rows: int
    messages: dict[str, str]

    def path(self, relative: Path) -> Path:
        return (BACKEND_DIR / relative).resolve()


class SkillsConf(BaseModel):
    types: dict[str, str]
    profile_top: int
    weight_note: str
    gap_ranking_min_occupations: int
    sufficiency: dict[str, str]


class JobsView(BaseModel):
    notice: str
    footnote: str
    source_label: str
    period_label: str
    sector_order: list[str]
    other_sector: str
    no_level: str
    page_size: int


class AppConf(BaseModel):
    app_name: str
    api_prefix: str
    version: str
    paths: PathsConf
    datasets: DatasetsConf
    dev_tools: DevToolsConf
    pagination: PaginationConf
    cors: CorsConf
    domains: dict[str, str]
    data_types: dict[str, str]
    comparison: ComparisonConf
    trend_states: dict[str, str]
    isco_levels: dict[int, str]
    employability: EmployabilityLabels
    alerts: AlertLabels
    skills: SkillsConf
    assessments: dict[str, str]
    dashboard: DashboardConf
    source_status: dict[str, str]
    notices: dict[str, str]
    jobs_view: JobsView
    messages: dict[str, str]


# --- reference/isco_education_requirements.yaml ---------------------------------
class EducationBand(BaseModel):
    code: str
    name: str
    edu_codes: list[str]


class StatusInfo(BaseModel):
    label: str
    description: str


class EducationRequirementsConf(BaseModel):
    occupation_dimension: str
    education_dimension: str
    occupation_code_prefix: str
    occupation_isco_digits: int
    bands: list[EducationBand]  # lowest to highest
    requirements: dict[str, str]  # ISCO group -> band code
    not_stated: EducationBand
    excluded_groups: dict[str, str] = {}  # ISCO group -> reason (shown, left out of the rates)
    break_status: str | None = None
    status_info: dict[str, StatusInfo] = {}  # matched | over | under | excluded
    explanation: list[str] = []

    @model_validator(mode="after")
    def _known_bands(self):
        unknown = set(self.requirements.values()) - {b.code for b in self.bands}
        if unknown:
            raise ValueError(f"requirements use unknown bands: {sorted(unknown)}")
        return self

    def rank_by_edu_code(self) -> dict[str, int]:
        return {code: i for i, band in enumerate(self.bands) for code in band.edu_codes}

    def required_rank(self) -> dict[str, int]:
        ranks = {b.code: i for i, b in enumerate(self.bands)}
        return {group: ranks[band] for group, band in self.requirements.items()}


# --- loaders ------------------------------------------------------------------
def _read(name: str, config_dir: Path | None = None) -> dict:
    path = (config_dir or settings.config_dir) / f"{name}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def catalog() -> CatalogConf:
    """Countries, sectors and the occupation universe (ISCO-08 unit groups), with the featured
    occupations' display name and sector applied."""
    conf = CatalogConf.model_validate(_read("catalog"))
    with (settings.config_dir / conf.occupation_universe.file).open(encoding="utf-8") as f:
        universe = yaml.safe_load(f)["occupations"]
    if conf.occupation_universe.groups_file:
        with (settings.config_dir / conf.occupation_universe.groups_file).open(encoding="utf-8") as f:
            conf.groups = {str(k): v for k, v in yaml.safe_load(f)["groups"].items()}
        for rule in conf.group_name_rules:
            for code in rule.codes:
                if code in conf.groups:
                    conf.groups[code] = re.sub(rule.replace, rule.with_, conf.groups[code])
    featured = {o.isco08_code: o for o in conf.featured_occupations}
    excluded = {o.isco08_code: o.reason for o in conf.excluded_occupations}
    unknown = (set(featured) | set(excluded)) - set(universe)
    if unknown:
        raise ValueError(f"featured or excluded occupations not in the universe: {sorted(unknown)}")
    if set(featured) & set(excluded):
        raise ValueError(f"occupations both featured and excluded: {sorted(set(featured) & set(excluded))}")
    sectors = {s.sector_code for s in conf.sectors}
    conf.occupations = []
    for code, names in sorted(universe.items()):
        f = featured.get(code)
        if f and f.sector_code not in sectors:
            raise ValueError(f"featured occupation {code}: unknown sector {f.sector_code}")
        name_es = names.get("name_es")
        if name_es:
            name_es = re.sub(r"\s+", " ", name_es).strip()
            for rule in conf.occupation_name_rules:
                name_es = rule.apply(name_es, names.get("name_en"))
        conf.occupations.append(OccupationConf(
            occupation_code=code, isco08_code=code,
            name=f.name if f else (name_es or names.get("name_en") or code),
            name_en=names.get("name_en"), sector_code=f.sector_code if f else None,
            is_featured=f is not None, is_excluded=code in excluded,
            exclusion_reason=excluded.get(code),
        ))
    return conf


@lru_cache
def sources() -> SourcesConf:
    return SourcesConf.model_validate(_read("sources"))


@lru_cache
def indicators() -> IndicatorsConf:
    conf = IndicatorsConf.model_validate(_read("indicators"))
    for ind in conf.indicators:
        for s in ind.series:
            source = sources().get(s.source)
            if source is None or not source.connector:
                raise ValueError(f"{ind.code}: source {s.source!r} has no connector in sources.yaml")
            missing = [f for f in source.series_fields if not getattr(s, f)]
            if missing:
                raise ValueError(f"{ind.code}: series of {s.source} needs {missing}")
    return conf


@lru_cache
def education_requirements(file: str) -> EducationRequirementsConf:
    with (settings.config_dir / file).open(encoding="utf-8") as f:
        return EducationRequirementsConf.model_validate(yaml.safe_load(f))


@lru_cache
def app_config() -> AppConf:
    return AppConf.model_validate(_read("app"))


@lru_cache
def analytics() -> dict[str, dict]:
    """Methodology parameters by section (employability, trends, ...). Free-form per method."""
    return _read("analytics")


def analytics_params(section: str, overrides: dict | None = None) -> dict:
    return {**analytics()[section], **(overrides or {})}
