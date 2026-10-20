"""Response schemas for catalog, indicators, observations and sources.

Traceability convention (plan 9): every value carries its source, the source's update date,
when we fetched it and whether it is observed, calculated or projected.
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CountryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    iso3: str
    name_es: str
    name_en: str


class SectorItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sector_code: str
    name: str
    isic_codes: list[str]


class OccupationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    occupation_code: str
    name: str
    name_en: str | None = None
    isco08_code: str
    sector_code: str | None = None
    is_featured: bool = False
    is_excluded: bool = False
    exclusion_reason: str | None = None


class SourceRef(BaseModel):
    code: str
    name: str


class IndicatorItem(BaseModel):
    code: str
    name: str
    unit: str
    domain: str
    domain_label: str
    higher_is_better: bool | None
    description: str | None
    sources: list[SourceRef]
    has_sector_breakdown: bool


class ObservationPoint(BaseModel):
    indicator_code: str
    country_iso3: str
    sector_code: str | None
    occupation_code: str | None
    period: str
    period_start: date
    period_end: date
    frequency: str
    value: float
    unit: str
    data_type: str
    data_type_label: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    source: SourceRef
    source_updated_at: date | None
    fetched_at: datetime
    methodology_id: int | None = None


class ObservationsPage(BaseModel):
    indicator: IndicatorItem
    total: int
    items: list[ObservationPoint]


class ComparePoint(BaseModel):
    country_iso3: str
    current: ObservationPoint | None
    previous: ObservationPoint | None
    change: float | None
    change_kind: str


class CompareResult(BaseModel):
    indicator: IndicatorItem
    sector_code: str | None
    items: list[ComparePoint]


class HighlightCard(BaseModel):
    indicator: IndicatorItem
    country_iso3: str
    current: ObservationPoint | None
    previous: ObservationPoint | None
    change: float | None
    change_kind: str


class DashboardSummary(BaseModel):
    country_iso3: str
    highlights: list[HighlightCard]


class RunItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    records_fetched: int
    records_normalized: int
    error_message: str | None
    triggered_by: str


class RevisionItem(BaseModel):
    """A source value that a later load changed (revised) or removed; old_value is what was
    published before."""
    model_config = ConfigDict(from_attributes=True)
    revision_id: int
    dataset: str  # observations | graduates | education_mismatch_cells
    record_key: dict
    change: str  # revised | removed
    old_value: float | None
    new_value: float | None
    old_run_id: int | None
    run_id: int | None
    revised_at: datetime


class SourceItem(BaseModel):
    code: str
    name: str
    kind: str
    base_url: str | None
    expected_frequency: str | None
    has_connector: bool
    status: str
    last_success_at: datetime | None
    last_run: RunItem | None


class MethodologyRef(BaseModel):
    methodology_id: int
    methodology_type: str
    version: str
    name: str | None


class MethodologyItem(MethodologyRef):
    model_config = ConfigDict(from_attributes=True)
    params: dict
    description_md: str | None
    created_at: datetime
    is_current: bool


class TrendItem(BaseModel):
    indicator: IndicatorItem
    country_iso3: str
    sector_code: str | None
    occupation_code: str | None
    window_mode: str  # latest: stored latest window | range: requested years
    window_start: str | None
    window_end: str | None
    n_points: int
    slope: float | None
    pct_change: float | None
    trend_state: str
    trend_state_label: str
    assessment: str | None
    assessment_label: str | None
    previous_trend_state: str | None
    data_type: str
    data_type_label: str
    source: SourceRef
    computed_at: datetime
    methodology: MethodologyRef | None


class ProjectionSeries(BaseModel):
    country_iso3: str
    observed: list[ObservationPoint]
    projected: list[ObservationPoint]
    methodology: MethodologyRef | None


class ProjectionResult(BaseModel):
    indicator: IndicatorItem
    sector_code: str | None
    occupation_code: str | None
    items: list[ProjectionSeries]


class EmployabilityComponent(BaseModel):
    dimension: str
    label: str
    weight: float
    raw: float | None
    normalized: float | None
    contribution: float | None
    indicator: str | None
    unit: str | None
    measure: str
    detail: dict
    available: bool


class EmployabilityItem(BaseModel):
    occupation: OccupationItem
    sector_name: str | None
    country_iso3: str
    year: int
    score: float | None
    level: str
    level_label: str
    coverage_ratio: float
    components: list[EmployabilityComponent]
    data_type: str
    data_type_label: str
    computed_at: datetime
    methodology: MethodologyRef
    group_code: str  # ISCO group used to cap rankings
    group_hidden: int | None = None  # rankings: rows of the same group left out


class DimensionRange(BaseModel):
    """What a dimension measures and the range it takes in the comparison cohort that year
    (all countries and occupations: the values that map to 0 and 100 when scaling)."""
    dimension: str
    label: str
    weight: float
    higher_is_better: bool
    definition: str | None
    unit: str | None
    possible_range: str | None
    observed_min: float | None
    observed_max: float | None
    with_data: int
    total: int
    has_source: bool  # False while analytics.yaml has no indicator for it
    source_status: str | None  # why it has no source (app.yaml)
    effective_weight: float  # weight once the dimensions without a source are left out


class EmployabilityPage(BaseModel):
    year: int | None
    available_years: list[int]
    view: str  # top | bottom | all
    sort_by: str  # score or a dimension
    order: str  # asc | desc
    total: int  # rows matching the filters (scored or not)
    scored_total: int
    limit: int
    offset: int
    dimension_ranges: list[DimensionRange]
    no_source_note: str | None  # how the index is computed while a dimension has no source
    items: list[EmployabilityItem]


class EmployabilityHistoryPoint(BaseModel):
    year: int
    score: float | None
    level: str
    level_label: str
    coverage_ratio: float


class EmployabilityHistory(BaseModel):
    occupation_code: str
    country_iso3: str
    points: list[EmployabilityHistoryPoint]
    methodology: MethodologyRef | None


class OccupationGroup(BaseModel):
    indicator: str
    source: str
    countries: list[str]
    group_code: str
    isco_digits: int
    shared_with: list[str]


class OccupationProfile(BaseModel):
    occupation: OccupationItem
    sector_name: str | None
    groups: list[OccupationGroup]
    employability: list[EmployabilityItem]
    latest: list[ObservationPoint]
    top_skills: list["SkillItem"] = []
    hierarchy: list["IscoLevel"] = []


class CodeName(BaseModel):
    code: str
    name: str


class AlertItem(BaseModel):
    alert_id: int
    alert_type: str
    alert_type_label: str
    severity: str
    severity_label: str
    entity_type: str
    indicator: CodeName | None
    country_iso3: str | None
    sector: CodeName | None
    occupation: CodeName | None
    source: SourceRef | None
    period: str | None
    previous_value: float | None
    current_value: float | None
    unit: str | None
    previous_state: str | None
    current_state: str | None
    message: str
    methodology_id: int | None
    detected_at: datetime
    is_read: bool


class AlertsPage(BaseModel):
    total: int
    unread: int
    by_severity: dict[str, int]
    limit: int
    offset: int
    items: list[AlertItem]


class AlertRule(BaseModel):
    alert_type: str
    label: str
    definition: str | None
    params: dict
    severity_rule: str
    active: bool


class AlertSeverity(BaseModel):
    code: str
    label: str
    definition: str | None


class AlertOverride(BaseModel):
    indicator: CodeName
    params: dict


class AlertRules(BaseModel):
    methodology: MethodologyItem | None
    rules: list[AlertRule]
    severities: list[AlertSeverity]
    overrides: list[AlertOverride]


class AlertReadUpdate(BaseModel):
    is_read: bool = True


class DatasetProfileItem(BaseModel):
    dataset_code: str
    title: str
    source: str
    landing_page: str | None
    automatic: bool
    requires_declared_source: bool
    file_format: str
    sheet: str | None
    expected_headers: list[str] | None
    template_columns: dict[str, str] | None
    required_columns: list[str] | None
    mapped_columns: dict[str, dict] | None


class DatasetFileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dataset_id: int
    profile_code: str
    origin: str
    file_name: str
    url: str | None
    release: str | None
    sha256: str
    size_bytes: int
    status: str
    records: int
    declared_source_name: str | None
    declared_source_url: str | None
    reference_date: date | None
    run_id: int | None
    replaces_dataset_id: int | None
    created_at: datetime
    loaded_at: datetime | None
    report: dict


class DatasetUploadResult(DatasetFileItem):
    preview: list[dict]


class SkillItem(BaseModel):
    skill_code: str
    name: str
    skill_type: str | None
    skill_type_label: str | None
    esco_uri: str | None
    weight: float | None = None
    occupations: int | None = None


class OccupationSkills(BaseModel):
    occupation_code: str
    occupation_name: str
    total: int
    weight_note: str
    source: SourceRef | None
    updated_at: datetime | None
    items: list[SkillItem]


class SkillOccupation(BaseModel):
    occupation: OccupationItem
    weight: float


class SkillDetail(SkillItem):
    used_by: list[SkillOccupation]



class SkillGapItem(BaseModel):
    skill: SkillItem
    country_iso3: str
    year: int
    demand_growth: float | None
    supply_growth: float | None
    gap: float | None
    is_emerging: bool
    data_sufficiency: str
    data_sufficiency_label: str
    demand_coverage: float
    supply_coverage: float
    occupations: int
    top_occupations: list[dict]
    data_type: str
    data_type_label: str
    methodology: MethodologyRef


class SkillGapsPage(BaseModel):
    view: str
    sort_by: str
    order: str
    min_occupations: int
    total: int
    full_total: int
    year: int | None
    limit: int
    offset: int
    crosswalk_reviewed: dict[str, bool]
    items: list[SkillGapItem]


class IscoLevel(BaseModel):
    level: int
    level_label: str
    code: str
    name: str | None


class CrosswalkOccupation(BaseModel):
    occupation_code: str
    name: str
    share: float  # share of the career's graduates assigned to this occupation
    hierarchy: list[IscoLevel]


class CrosswalkCareer(BaseModel):
    career: str
    level: str
    field_area: str | None
    field_subarea: str | None
    graduates: float | None
    graduates_year: int | None
    graduates_growth: float | None
    is_generic: bool
    occupations: list[CrosswalkOccupation]


class CrosswalkReview(BaseModel):
    country_iso3: str
    reviewed: bool
    file: str
    levels: list[str]
    source: SourceRef | None
    careers: int
    mapped: int
    generic: int
    graduates_mapped_share: float | None
    items: list[CrosswalkCareer]


# OccupationProfile refers to classes defined after it
OccupationProfile.model_rebuild()


class MismatchBand(BaseModel):
    code: str
    name: str


class MismatchStatus(BaseModel):
    status: str  # matched | over | under | excluded
    label: str
    description: str


class MismatchCell(BaseModel):
    band: str
    employed: float
    status: str  # matched | over | under | excluded


class MismatchGroup(BaseModel):
    isco_group: str
    name: str
    required_band: str | None  # None: left out of the rates (excluded_reason)
    excluded_reason: str | None = None
    cells: list[MismatchCell]
    total: float
    over_share: float | None  # None when the group cannot be over-qualified
    under_share: float | None


class MismatchTotals(BaseModel):
    matched: float
    over: float
    under: float
    considered: float  # matched + over + under: the denominator of the rates
    excluded: float


class EducationMismatch(BaseModel):
    country_iso3: str
    year: int
    years: list[int]
    unit: str
    source: SourceRef | None
    fetched_at: datetime | None
    indicators: dict[str, str]  # measure (over, under) -> indicator code
    bands: list[MismatchBand]  # lowest to highest, then "not stated"
    statuses: list[MismatchStatus]  # meaning of the cell colors (legend)
    groups: list[MismatchGroup]
    totals: MismatchTotals
    over_rate: float | None
    under_rate: float | None
    explanation: list[str]
    page_size: int  # rows per page in tables (app.yaml -> pagination.ranking_size)
