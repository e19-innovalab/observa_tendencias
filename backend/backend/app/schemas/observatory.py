"""Response schemas for catalog, indicators, observations and sources.

Traceability convention (plan 9): every value carries its source, the source's update date,
when we fetched it and whether it is observed, calculated or projected.
"""
from datetime import date, datetime
from typing import Literal

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


class DisplayValue(BaseModel):
    """Value shown first for a dimension (e.g. salary in USD); the index uses `raw`."""
    indicator: str
    label: str
    unit: str
    value: float
    period: str
    note: str | None = None


class EmployabilityTexts(BaseModel):
    """Wording for the ISE screens, from app.yaml (employability): hover notes for the terms
    (normalized, contribution), how each unit is written and the label/note of display values."""
    terms: dict[str, str]
    unit_formats: dict[str, str]
    display: dict[str, dict[str, str | None]]


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
    display: DisplayValue | None = None


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


class MoctezumaComponent(BaseModel):
    dimension: str
    label: str
    side: str  # pace | readiness
    weight: float  # relative within the side
    raw: float | None
    normalized: float | None
    indicator: str
    scope: str  # occupation | country
    measure: str
    detail: dict
    available: bool


class MoctezumaItem(BaseModel):
    occupation: OccupationItem
    sector_name: str | None
    country_iso3: str
    year: int
    score: float | None
    level: str
    level_label: str
    pace: float | None
    readiness: float | None
    gap: float | None  # pace − readiness
    pace_coverage: float
    readiness_coverage: float
    components: list[MoctezumaComponent]
    data_type: str
    data_type_label: str
    computed_at: datetime
    methodology: MethodologyRef


class MoctezumaDimension(BaseModel):
    """What a dimension measures and how it enters its side."""
    dimension: str
    label: str
    weight: float  # relative within the side
    higher_is_more: bool
    indicator: str
    scope: str  # occupation | country
    definition: str | None
    unit: str | None
    possible_range: str | None


class MoctezumaSide(BaseModel):
    side: str  # pace | readiness
    label: str
    definition: str | None
    weight: float  # side weight in the indicator
    dimensions: list[MoctezumaDimension]


class MoctezumaRange(BaseModel):
    """Raw values that map to 0 and 100 in the comparison cohort that year."""
    observed_min: float | None
    observed_max: float | None
    with_data: int


class MoctezumaPage(BaseModel):
    year: int | None
    available_years: list[int]
    view: str  # top | bottom | all
    side_labels: dict[str, str]
    level_labels: dict[str, str] = {}
    sides: list[MoctezumaSide]  # definitions of Ritmo del cambio and Capacidad de respuesta
    dimension_ranges: dict[str, MoctezumaRange] = {}
    total: int
    scored_total: int
    limit: int
    offset: int
    items: list[MoctezumaItem]


class MoctezumaCountryPoint(BaseModel):
    """Country value for a year: simple mean over its occupations with a score."""
    year: int
    score: float
    pace: float
    readiness: float
    level: str
    level_label: str
    scored: int  # occupations averaged
    total: int  # occupations of the country in the cohort


class MoctezumaCountry(BaseModel):
    country_iso3: str
    points: list[MoctezumaCountryPoint]
    methodology: MethodologyRef | None


class MoctezumaHistoryPoint(BaseModel):
    year: int
    score: float | None
    level: str
    level_label: str
    pace: float | None
    readiness: float | None


class MoctezumaHistory(BaseModel):
    occupation_code: str
    country_iso3: str
    points: list[MoctezumaHistoryPoint]
    methodology: MethodologyRef | None


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


class SectorTopOccupation(BaseModel):
    occupation_code: str
    name: str
    country_iso3: str
    score: float


class SectorSummary(BaseModel):
    """Employability of a strategic sector: averages over its scored occupation x country rows."""
    sector_code: str
    name: str
    occupations: int  # catalog occupations in the sector
    scored: int  # occupation x country rows with a score
    average_score: float | None
    previous_average: float | None  # same sector, previous reference year
    change: float | None
    level: str | None
    level_label: str | None
    top_occupation: SectorTopOccupation | None
    salary_ppp_average: float | None
    salary_usd_average: float | None = None  # same rows, display_values.salary_ppp indicator
    automation_average: float | None
    dimensions: dict[str, float | None]  # average scaled (0-100) value of each dimension


class SectorsPage(BaseModel):
    year: int | None
    available_years: list[int]
    countries: list[str]
    regional_average: float | None  # all scored rows of the five sectors
    dimension_ranges: list[DimensionRange]  # weights, effective weights, what each measures
    no_source_note: str | None
    items: list[SectorSummary]
    texts: EmployabilityTexts | None = None


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
    texts: EmployabilityTexts | None = None


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
    has_template: bool = False  # GET /datasets/profiles/{code}/template
    example_files: list[str] = []  # GET /datasets/profiles/{code}/examples/{name}


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
    description: str | None = None  # definition in Spanish
    description_en: str | None = None  # ESCO's English original
    description_origin: str | None = None  # esco | translation (config/reference/esco_traducciones_es.yaml)
    group_code: str | None = None  # ESCO hierarchy group (analytics.yaml -> skill_gaps.group_level)
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



class SkillOccupationUse(BaseModel):
    occupation_code: str
    name: str
    relation: str  # ESCO category for this CIUO group: essential | optional
    relation_label: str
    via: list[str] = []  # the group's ESCO occupations that use it (why it shows up here)


class SkillSectorUse(BaseModel):
    sector_code: str | None  # None: occupations outside the strategic sectors
    name: str
    relation: str  # strongest ESCO relation among the sector's occupations: essential | optional
    relation_label: str
    occupations: list[SkillOccupationUse]  # every occupation of the sector that uses it, essential first


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
    sectors: list[SkillSectorUse] = []  # sectors whose occupations use it (essential first), then the rest
    is_cross_sector: bool = False  # essential in two or more sectors
    unstable_supply: list[dict] = []  # occupations left out of supply: unstable graduates series
    data_type: str
    data_type_label: str
    methodology: MethodologyRef


class SkillGapExtreme(BaseModel):
    skill_code: str
    name: str
    country_iso3: str
    gap: float


class SkillGapsSummary(BaseModel):
    """Over the skills with a full gap that match the filters (gaps as fractions: 0.05 = 5 pp)."""
    skills_with_gap: int
    average_gap: float | None
    largest_shortage: SkillGapExtreme | None  # highest gap: demand grows faster than training
    largest_surplus: SkillGapExtreme | None  # lowest gap: training grows faster than demand
    occupations: int  # distinct occupations using those skills
    full_share: float | None  # skills with a full gap / all matching skills


class GapDataThrough(BaseModel):
    """Last year with data on each side of the gap, per country: the gaps cannot go further."""
    country_iso3: str
    demand: int | None  # employment by occupation
    supply: int | None  # graduates
    # years whose graduates come from a supplementary source, and its note
    supplemented_years: list[int] = []
    supply_note: str | None = None


class SkillGapsPage(BaseModel):
    view: str
    sort_by: str
    order: str
    min_occupations: int
    total: int
    full_total: int
    year: int | None
    available_years: list[int] = []
    data_through: list[GapDataThrough] = []
    limit: int
    offset: int
    crosswalk_reviewed: dict[str, bool]
    summary: SkillGapsSummary | None = None
    items: list[SkillGapItem]


class SkillGroupItem(BaseModel):
    group_code: str
    name: str
    description: str | None  # Spanish
    description_en: str | None  # ESCO's English original
    description_origin: str | None  # esco | translation | None (still English)
    level: int
    parent: str | None  # name of the broader group


class SkillGroupGapItem(BaseModel):
    group: SkillGroupItem
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
    skills: int  # ESCO skills of the group used by the occupations
    top_skills: list[SkillItem]
    top_occupations: list[dict]
    sectors: list[SkillSectorUse] = []
    is_cross_sector: bool = False
    unstable_supply: list[dict] = []  # occupations left out of supply: unstable graduates series
    methodology: MethodologyRef


class SkillGroupGapsPage(BaseModel):
    view: str
    sort_by: str
    order: str
    min_occupations: int
    total: int
    full_total: int
    year: int | None
    available_years: list[int] = []
    data_through: list[GapDataThrough] = []
    limit: int
    offset: int
    group_level: int
    crosswalk_reviewed: dict[str, bool]
    items: list[SkillGroupGapItem]


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
    cine_f: str | None = None  # CINE-F 2013 detailed field, when the crosswalk goes through it
    cine_f_name: str | None = None
    technical: bool | None = None  # uses the field's "tecnico" occupations
    occupations: list[CrosswalkOccupation]


class CrosswalkReview(BaseModel):
    country_iso3: str
    reviewed: bool
    file: str
    levels: list[str]
    via: str | None = None  # shared CINE-F -> CIUO table, when used
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


class MotionAxisInfo(BaseModel):
    key: str
    label: str
    short_label: str | None = None
    unit: str | None = None
    scale: Literal["linear", "log"] = "linear"
    description: str | None = None
    reference: float | None = None
    domain: tuple[float, float] | None = None


class MotionGroup(BaseModel):
    code: str
    name: str | None = None


class MotionPoint(BaseModel):
    country_iso3: str
    group_code: str
    year: int
    x: float
    x_secondary: float | None = None
    y: float
    size: float
    # x/size taken from an earlier year (at most max_carry_years older): {"x": 2024}
    carried: dict[str, int] = {}


class MotionPage(BaseModel):
    title: str
    description: str | None = None
    years: list[int]
    x: MotionAxisInfo
    x_secondary: MotionAxisInfo | None = None
    y: MotionAxisInfo
    size: MotionAxisInfo
    y_options: list[MotionAxisInfo]
    groups: list[MotionGroup]
    points: list[MotionPoint]
    notes: list[str] = []


class LuditaPath(BaseModel):
    """A quadrant of exposure and vitality, named after a historical case."""
    path: str  # weaver | teller | other_causes | out_of_reach
    label: str
    short: str
    description: str


class LuditaItem(BaseModel):
    occupation: OccupationItem
    sector_name: str | None
    country_iso3: str
    year: int
    score: float | None
    level: str
    level_label: str
    path: str | None
    path_label: str | None
    exposure: float | None
    vitality: float | None
    exposure_coverage: float
    vitality_coverage: float
    components: list[MoctezumaComponent]
    data_type: str
    data_type_label: str
    computed_at: datetime
    methodology: MethodologyRef


class LuditaPage(BaseModel):
    year: int | None
    available_years: list[int]
    view: str  # top | bottom | all
    side_labels: dict[str, str]
    level_labels: dict[str, str] = {}
    sides: list[MoctezumaSide]
    paths: list[LuditaPath]
    path_rules: dict[str, float]  # exposed_from, retreat_below
    dimension_ranges: dict[str, MoctezumaRange] = {}
    total: int
    scored_total: int
    limit: int
    offset: int
    items: list[LuditaItem]


class LuditaCountryPoint(BaseModel):
    """Country value for a year: simple mean over its occupations with a score, and how many
    occupations follow each path."""
    year: int
    score: float
    exposure: float
    vitality: float
    level: str
    level_label: str
    scored: int
    total: int
    paths: dict[str, int]


class LuditaCountry(BaseModel):
    country_iso3: str
    points: list[LuditaCountryPoint]
    methodology: MethodologyRef | None


class LuditaCasePoint(BaseModel):
    year: int
    years_since: int  # year - arrival_year
    value: float  # thousands of workers
    index: float  # base_year = 100
    approx: bool = False
    note: str | None = None


class LuditaSource(BaseModel):
    label: str
    detail: str | None = None
    url: str


class LuditaCase(BaseModel):
    key: str
    label: str
    technology: str
    arrival_year: int
    arrival_note: str
    base_year: int
    path: str | None
    source_short: str | None = None
    country_iso3: str | None = None  # today's curves: one per catalog country
    points: list[LuditaCasePoint]
    sources: list[LuditaSource] = []


class LuditaHistory(BaseModel):
    zoom_years: int  # years after the arrival shown in "Los primeros años"
    cases: list[LuditaCase]  # historical cases
    today: list[LuditaCase]  # today's occupations, same scale


class MoctezumaHistoricalPoint(BaseModel):
    year: int
    population: float
    pace: float
    readiness: float  # population / population of base_year x 100
    score: float


class MoctezumaAlternativePoint(BaseModel):
    """The same calculation with a lower population estimate, to show the sensitivity."""
    label: str
    base_year: int
    base_population: float
    year: int
    population: float
    readiness: float
    score: float


class MoctezumaEvent(BaseModel):
    year: int
    label: str
    detail: str


class MoctezumaReference(BaseModel):
    region: str
    contact_year: int
    pace_full_from: int
    pace_note: str
    population_unit: str
    base_year: int
    points: list[MoctezumaHistoricalPoint]
    example_year: int
    alternative: MoctezumaAlternativePoint
    sources: dict[str, list[LuditaSource]]  # series | debate
    side_history: dict[str, str]
    example_occupation: str | None
    events: list[MoctezumaEvent] = []
    point_notes: dict[int, str] = {}  # what happened up to each population figure
    point_labels: dict[int, str] = {}  # short label next to a figure on the time chart


class RedQueenDimension(BaseModel):
    dimension: str
    label: str
    weight: float
    source_code: str
    source_name: str | None
    source_url: str | None
    definition: str | None
    unit: str | None
    possible_range: str | None


class RedQueenComponent(BaseModel):
    """One source: the two versions compared and what changed between them."""
    dimension: str
    label: str
    available: bool
    normalized: float | None
    from_version: str | None = None
    to_version: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    years: float | None = None
    n_from: int | None = None
    n_to: int | None = None
    added_count: int | None = None
    removed_count: int | None = None
    renamed_count: int | None = None
    new_per_year: float | None = None
    turnover: float | None = None  # between the two versions
    annual: float | None = None
    half_life: float | None = None
    added: list[str] = []
    removed: list[str] = []


class RedQueenItem(BaseModel):
    occupation: OccupationItem
    sector_name: str | None
    year: int
    score: float | None
    level: str
    level_label: str
    turnover: float | None
    half_life: float | None
    half_life_capped: bool
    coverage: float
    components: list[RedQueenComponent]
    methodology: MethodologyRef


class RedQueenPage(BaseModel):
    year: int | None
    available_years: list[int]
    view: str
    level_labels: dict[str, str]
    dimensions: list[RedQueenDimension]
    half_life_cap: float
    examples_shown: int  # added/removed items shown before expanding the list
    career: str | None = None  # filter applied: occupations this career leads to
    total: int
    scored_total: int
    limit: int
    offset: int
    items: list[RedQueenItem]


class CareerOption(BaseModel):
    """A career of a country's career -> occupation crosswalk, for the career filter."""
    career: str
    occupations: int  # catalog occupations it leads to (any level)


class RedQueenYear(BaseModel):
    """Median over the occupations with a score that year."""
    year: int
    scored: int
    median_new_per_year: dict[str, float]  # per dimension
    median_turnover: float | None
    median_half_life: float | None


class SisyphusItem(BaseModel):
    """One ISCO-08 major group in a country and year."""
    country_iso3: str
    group_code: str
    group_name: str | None
    year: int
    score: float | None
    level: str
    level_label: str
    stone: float | None
    reward: float | None
    quadrant: str | None
    quadrant_label: str | None
    overeducation: float | None  # %
    earnings_ratio: float | None  # group earnings / tertiary-educated earnings
    earnings_ppp: float | None
    earnings_usd: float | None
    tertiary_ppp: float | None
    components: list[MoctezumaComponent]


class GroupExample(BaseModel):
    occupation_code: str
    name: str
    is_featured: bool


class GroupInfo(BaseModel):
    """What an ISCO-08 major group includes (ILO definition) and some of its occupations."""
    code: str
    name: str | None
    definition: str | None
    occupations: int  # catalog occupations in the group
    examples: list[GroupExample]


class SisyphusPage(BaseModel):
    year: int | None
    available_years: list[int]
    level_labels: dict[str, str]
    side_labels: dict[str, str]
    sides: list[MoctezumaSide]
    quadrants: list[LuditaPath]
    quadrant_rules: dict[str, float]  # overeducated_from, paid_below
    excluded_groups: list[str]  # groups that cannot be overeducated
    groups: list[GroupInfo] = []
    groups_source: dict[str, str] = {}  # label, url of the definitions
    items: list[SisyphusItem]
    methodology: MethodologyRef | None


class SisyphusCountryPoint(BaseModel):
    year: int
    score: float | None  # simple mean over the country's groups with a score
    graduates_below_share: float | None  # tertiary educated working in a group that does not require it
    premium: float | None  # tertiary / secondary earnings - 1 (USD PPA)
    tertiary_ppp: float | None
    tertiary_usd: float | None
    secondary_ppp: float | None
    secondary_usd: float | None


class SisyphusCountry(BaseModel):
    country_iso3: str
    points: list[SisyphusCountryPoint]


class GapPoint(BaseModel):
    year: int
    youth: float  # %
    total: float  # %
    ratio: float  # youth / total


class GapCountry(BaseModel):
    country_iso3: str
    points: list[GapPoint]
    latest: GapPoint | None
    headline: str | None


class GenerationalGap(BaseModel):
    title: str
    description: str
    youth: IndicatorItem
    total: IndicatorItem
    source: str | None  # source name of the two series
    countries: list[GapCountry]
