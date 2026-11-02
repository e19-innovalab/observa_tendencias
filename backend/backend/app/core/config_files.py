"""Typed access to backend/config/*.yaml. Files are validated on first read and cached."""
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

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
    # ISCO group prefixes -> sector, for occupations that are not featured (longest prefix wins)
    sectors_file: str | None = None


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
    group_definitions: dict[str, str] = {}  # what each major group includes (ILO)
    group_definitions_source: dict[str, str] = {}  # label, url

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
    # Values the indicator can take ([min, max], null = unbounded): projections are clipped to it.
    value_range: tuple[float | None, float | None] | None = None
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


class DisplayValueConf(BaseModel):
    indicator: str
    label: str
    note: str | None = None


class EmployabilityLabels(BaseModel):
    levels: dict[str, str]
    dimensions: dict[str, str]
    dimension_info: dict[str, DimensionInfo] = {}
    display_values: dict[str, DisplayValueConf] = {}
    terms: dict[str, str] = {}
    unit_formats: dict[str, str] = {}
    no_source_note: str | None = None
    ranking: RankingConf


class MoctezumaLabels(BaseModel):
    levels: dict[str, str]
    sides: dict[str, str]
    dimensions: dict[str, str]
    side_info: dict[str, str] = {}
    dimension_info: dict[str, DimensionInfo] = {}
    history_file: str | None = None
    example_occupation: str | None = None
    side_history: dict[str, str] = {}


class RedQueenLabels(BaseModel):
    levels: dict[str, str]
    dimensions: dict[str, str]
    dimension_info: dict[str, DimensionInfo] = {}


class SisyphusLabels(MoctezumaLabels):
    quadrants: dict[str, "PathInfo"]


class PathInfo(BaseModel):
    label: str
    short: str
    description: str


class LuditaToday(BaseModel):
    label: str
    technology: str
    arrival_year: int
    arrival_note: str
    indicator: str
    group_digits: int
    groups: list[str]
    source_short: str


class LuditaHistoryConf(BaseModel):
    file: str
    zoom_years: int
    today: LuditaToday


class LuditaLabels(MoctezumaLabels):
    paths: dict[str, PathInfo]
    history: LuditaHistoryConf


class GenerationalGapConf(BaseModel):
    title: str
    youth_indicator: str
    total_indicator: str
    description: str
    headline: str


class MotionAxis(BaseModel):
    label: str
    short_label: str | None = None  # selector of the vertical axis
    indicator: str | None = None
    methodology: str | None = None
    aggregate: Literal["sum", "mean"] = "mean"
    measure: Literal["level", "yoy"] = "level"
    applies_to_all_years: bool = False
    scale: Literal["linear", "log"] = "linear"
    description: str | None = None
    reference: float | None = None
    domain: tuple[float, float] | None = None
    min_base: float = 0


class MotionConf(BaseModel):
    title: str
    description: str | None = None
    group_digits: int
    first_year: int
    max_carry_years: int
    x: MotionAxis
    x_secondary: MotionAxis | None = None
    size: MotionAxis
    default_y: str
    y: dict[str, MotionAxis]
    notes: list[str] = []


class AlertLabels(BaseModel):
    types: dict[str, str]
    severities: dict[str, str]
    type_info: dict[str, str] = {}
    severity_info: dict[str, str] = {}


class DatasetTemplateConf(BaseModel):
    file_name: str
    sheets: dict[str, str]
    instructions: list[str]
    examples_title: str
    examples: list[dict[str, Any]]
    headers: dict[str, str]


class DatasetsConf(BaseModel):
    raw_dir: Path
    uploads_dir: Path
    max_upload_bytes: int
    max_errors_reported: int
    preview_rows: int
    max_rows: int
    max_unzipped_bytes: int
    group_rows_shown: int
    group_values_shown: int
    group_titles: dict[str, str]
    group_hints: dict[str, str]
    overlap_examples: int
    template: DatasetTemplateConf
    example_files: dict[str, dict[str, str]] = {}
    messages: dict[str, str]

    def path(self, relative: Path) -> Path:
        return (BACKEND_DIR / relative).resolve()


class SkillsConf(BaseModel):
    types: dict[str, str]
    profile_top: int
    weight_note: str
    gap_ranking_min_occupations: int
    sector_relation: str
    relations: dict[str, str]
    no_sector_label: str
    supply_notes: dict[str, str] = {}
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
    applicants_cap: int
    competition_min_postings: int


class RoleConf(BaseModel):
    label: str
    permissions: list[str]


class AuthConf(BaseModel):
    token_ttl_hours: float
    password_min_length: int
    default_role: str
    roles: dict[str, RoleConf]
    statuses: dict[str, str]
    messages: dict[str, str]


class AssistantProviderConf(BaseModel):
    model: str
    max_tokens: int
    timeout_seconds: float
    base_url: str | None = None  # local: OpenAI-compatible server
    temperature: float | None = None  # local only
    effort: str | None = None  # anthropic only
    fallbacks: str | None = None  # anthropic only; "default" or empty


class AssistantToolParam(BaseModel):
    type: str
    description: str = ""
    required: bool = False
    enum: list[str] | None = None
    # Only values already known in the conversation are accepted (see AssistantTool.provides).
    must_be_known: bool = False


class AssistantToolLink(BaseModel):
    path: str
    label: str
    query: list[str] = []


class AssistantTool(BaseModel):
    name: str
    description: str
    path: str
    params: dict[str, AssistantToolParam] = {}
    fixed: dict[str, str | int | bool] = {}
    link: AssistantToolLink | None = None
    # Key in this tool's results whose values become known codes (e.g. occupation_code).
    provides: str | None = None


class AssistantLimits(BaseModel):
    questions_per_user_per_day: int
    questions_per_day: int


class NumbersCheckConf(BaseModel):
    enabled: bool
    tolerance: float
    ignore_up_to: float
    year_range: tuple[int, int]
    on_unverified: Literal["warn", "block"]


class ScriptedConf(BaseModel):
    enabled: bool
    intent_words: dict[str, list[str]]
    stopwords: list[str]
    country_words: dict[str, list[str]]
    max_options: int
    ranking_size: int
    skills_size: int
    decimals: int
    model_label: str
    templates: dict[str, str]


class AssistantConf(BaseModel):
    enabled: bool
    permission: str
    provider: str
    providers: dict[str, AssistantProviderConf]
    max_tool_calls: int
    max_question_chars: int
    history_turns: int
    limits: AssistantLimits
    tool_result_max_items: int
    tool_result_max_chars: int
    tool_result_drop_keys: list[str] = []
    numbers_check: NumbersCheckConf
    system_prompt: str
    context_template: str
    context_fields: dict[str, str]
    # Known codes also come from the question, the history and the context: words of this shape.
    known_code_pattern: str
    final_round_note: str
    tools: list[AssistantTool]
    messages: dict[str, str]
    texts: dict[str, str]
    examples: list[str] = []
    scripted: ScriptedConf


class SearchConf(BaseModel):
    aliases_file: str


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
    moctezuma: MoctezumaLabels
    ludita: LuditaLabels
    red_queen: RedQueenLabels
    sisyphus: SisyphusLabels
    motion: MotionConf
    generational_gap: GenerationalGapConf
    alerts: AlertLabels
    skills: SkillsConf
    assessments: dict[str, str]
    dashboard: DashboardConf
    source_status: dict[str, str]
    notices: dict[str, str]
    jobs_view: JobsView
    auth: AuthConf
    search: SearchConf
    assistant: AssistantConf
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


def _sector_by_prefix(code: str, prefixes: dict[str, str]) -> str | None:
    """Sector of the longest prefix of the ISCO code listed in the sectors file."""
    for length in range(len(code), 0, -1):
        if code[:length] in prefixes:
            return prefixes[code[:length]]
    return None


@lru_cache
def catalog() -> CatalogConf:
    """Countries, sectors and the occupation universe (ISCO-08 unit groups), with the featured
    occupations' display name and sector applied."""
    conf = CatalogConf.model_validate(_read("catalog"))
    with (settings.config_dir / conf.occupation_universe.file).open(encoding="utf-8") as f:
        universe = yaml.safe_load(f)["occupations"]
    if conf.occupation_universe.groups_file:
        with (settings.config_dir / conf.occupation_universe.groups_file).open(encoding="utf-8") as f:
            groups_file = yaml.safe_load(f)
            conf.groups = {str(k): v for k, v in groups_file["groups"].items()}
            conf.group_definitions = {str(k): v for k, v in (groups_file.get("definitions") or {}).items()}
            conf.group_definitions_source = groups_file.get("definitions_source") or {}
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
    sector_prefixes: dict[str, str] = {}
    if conf.occupation_universe.sectors_file:
        with (settings.config_dir / conf.occupation_universe.sectors_file).open(encoding="utf-8") as f:
            sector_prefixes = {str(k): v for k, v in yaml.safe_load(f)["prefixes"].items()}
        unknown_sectors = set(sector_prefixes.values()) - sectors
        if unknown_sectors:
            raise ValueError(f"sectors_file uses unknown sectors: {sorted(unknown_sectors)}")
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
            name_en=names.get("name_en"),
            sector_code=f.sector_code if f else _sector_by_prefix(code, sector_prefixes),
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


# --- reference/ludita_history.yaml ------------------------------------------------
class HistoryPoint(BaseModel):
    year: int
    value: float
    approx: bool = False
    note: str | None = None


class HistorySource(BaseModel):
    label: str
    detail: str | None = None
    url: str


class HistoryCase(BaseModel):
    label: str
    technology: str
    arrival_year: int
    arrival_note: str
    base_year: int
    path: str
    source_short: str
    series: list[HistoryPoint]
    sources: list[HistorySource]

    @field_validator("series", mode="before")
    @classmethod
    def _rows(cls, rows):
        """[year, value] or [year, value, {approx, note}]."""
        return [r if isinstance(r, dict) else {"year": r[0], "value": r[1], **(r[2] if len(r) > 2 else {})}
                for r in rows]


@lru_cache
def ludita_history(file: str) -> dict[str, HistoryCase]:
    with (settings.config_dir / file).open(encoding="utf-8") as f:
        cases = yaml.safe_load(f)["cases"]
    return {k: HistoryCase.model_validate(v) for k, v in cases.items()}


class MoctezumaPace(BaseModel):
    before: float
    full: float
    full_from: int
    note: str


class MoctezumaAlternative(BaseModel):
    label: str
    base: tuple[int, float]
    compare: tuple[int, float]


class HistoryEvent(BaseModel):
    year: int
    label: str
    detail: str


class MoctezumaHistoryConf(BaseModel):
    region: str
    contact_year: int
    pace: MoctezumaPace
    population_unit: str
    base_year: int
    population: list[tuple[int, float]]
    example_year: int
    alternative: MoctezumaAlternative
    sources: dict[str, list[HistorySource]]  # series | debate
    events: list[HistoryEvent] = []
    point_notes: dict[int, str] = {}
    point_labels: dict[int, str] = {}
    event_sources: list[HistorySource] = []


@lru_cache
def moctezuma_history(file: str) -> MoctezumaHistoryConf:
    with (settings.config_dir / file).open(encoding="utf-8") as f:
        return MoctezumaHistoryConf.model_validate(yaml.safe_load(f))


class OccupationAlias(BaseModel):
    term: str
    code: str
    countries: list[str] = []
    also: list[str] = []
    note: str | None = None


@lru_cache
def occupation_aliases() -> list[OccupationAlias]:
    """Local names of occupations (app.yaml -> search.aliases_file)."""
    with (settings.config_dir / app_config().search.aliases_file).open(encoding="utf-8") as f:
        return [OccupationAlias.model_validate(e) for e in yaml.safe_load(f)["entries"]]


@lru_cache
def app_config() -> AppConf:
    conf = AppConf.model_validate(_read("app"))
    # per environment (.env): e.g. in the cloud there is no Ollama, so provider local points to a
    # hosted OpenAI-compatible API
    a = conf.assistant
    if settings.assistant_provider:
        a.provider = settings.assistant_provider
    active = a.providers.get(a.provider)
    if active and settings.assistant_base_url:
        active.base_url = settings.assistant_base_url
    if active and settings.assistant_model:
        active.model = settings.assistant_model
    return conf


@lru_cache
def analytics() -> dict[str, dict]:
    """Methodology parameters by section (employability, trends, ...). Free-form per method."""
    return _read("analytics")


def analytics_params(section: str, overrides: dict | None = None) -> dict:
    return {**analytics()[section], **(overrides or {})}
