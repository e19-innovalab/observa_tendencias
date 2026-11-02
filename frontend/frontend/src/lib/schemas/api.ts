/**
 * Esquemas Zod de la API de Observa Tendencias (FastAPI, prefijo /api/v1).
 * Generado a mano a partir de openapi.json (API v0.1.0).
 * Cubre: catálogos, indicadores, observaciones, compare, dashboard, tendencias,
 * proyecciones, metodologías, alertas, empleabilidad, ocupaciones, habilidades,
 * graduados y cobertura.
 */
import { z } from 'zod';

/* ---------- Cobertura ---------- */
export const CoverageItemSchema = z.object({
  pais: z.string(),
  sector: z.string(),
  n_anios_observados: z.number(),
  anio_min: z.number().nullable(),
  anio_max: z.number().nullable(),
  elegible_proyeccion: z.boolean(),
  estado: z.string(),
});

/* ---------- Comunes ---------- */
export const SourceRefSchema = z.object({ code: z.string(), name: z.string() });

export const MethodologyRefSchema = z.object({
  methodology_id: z.number(),
  methodology_type: z.string(),
  version: z.string(),
  name: z.string().nullable(),
});

export const DataTypeSchema = z.enum(['observed', 'calculated', 'projected']);

/* ---------- Catálogos (alimentan los filtros) ---------- */
export const CountrySchema = z.object({
  iso3: z.string(), // 'ARG' | 'URY' | 'CHL'
  name_es: z.string(),
  name_en: z.string(),
});

export const SectorSchema = z.object({
  sector_code: z.string(),
  name: z.string(),
  isic_codes: z.array(z.string()),
});

export const OccupationSchema = z.object({
  occupation_code: z.string(),
  name: z.string(),
  name_en: z.string().nullable().optional(),
  isco08_code: z.string(),
  sector_code: z.string().nullable().optional(),
  is_featured: z.boolean().optional(),
  is_excluded: z.boolean().optional(),
  exclusion_reason: z.string().nullable().optional(),
});

/* ---------- Indicadores (el sidebar se agrupa por domain_label) ---------- */
export const IndicatorSchema = z.object({
  code: z.string(),
  name: z.string(),
  unit: z.string(),
  domain: z.string(), // 'labor' | 'economic' | 'education'
  domain_label: z.string(),
  higher_is_better: z.boolean().nullable(),
  description: z.string().nullable(),
  sources: z.array(SourceRefSchema),
  has_sector_breakdown: z.boolean(), // habilita o no el filtro Sector
});

/* ---------- Observaciones ---------- */
export const ObservationPointSchema = z.object({
  indicator_code: z.string(),
  country_iso3: z.string(),
  sector_code: z.string().nullable(),
  occupation_code: z.string().nullable(),
  period: z.string(),
  period_start: z.string(),
  period_end: z.string(),
  frequency: z.string(), // 'A' | 'Q' | 'M'
  value: z.number(),
  unit: z.string(),
  data_type: z.string(),
  data_type_label: z.string(),
  lower_bound: z.number().nullable().optional(), // solo proyecciones
  upper_bound: z.number().nullable().optional(),
  source: SourceRefSchema,
  source_updated_at: z.string().nullable(),
  fetched_at: z.string(),
  methodology_id: z.number().nullable().optional(),
});

export const ObservationsPageSchema = z.object({
  indicator: IndicatorSchema,
  total: z.number(),
  items: z.array(ObservationPointSchema),
});

/* ---------- Compare y dashboard (KPIs con variación) ---------- */
export const ComparePointSchema = z.object({
  country_iso3: z.string(),
  current: ObservationPointSchema.nullable(),
  previous: ObservationPointSchema.nullable(),
  change: z.number().nullable(),
  change_kind: z.string(), // 'absolute' | 'relative'
});

export const CompareResultSchema = z.object({
  indicator: IndicatorSchema,
  sector_code: z.string().nullable(),
  items: z.array(ComparePointSchema),
});

export const HighlightCardSchema = z.object({
  indicator: IndicatorSchema,
  country_iso3: z.string(),
  current: ObservationPointSchema.nullable(),
  previous: ObservationPointSchema.nullable(),
  change: z.number().nullable(),
  change_kind: z.string(),
});

export const DashboardSummarySchema = z.object({
  country_iso3: z.string(),
  highlights: z.array(HighlightCardSchema),
});

/* ---------- Tendencias y proyecciones ---------- */
export const TrendItemSchema = z.object({
  indicator: IndicatorSchema,
  country_iso3: z.string(),
  sector_code: z.string().nullable(),
  occupation_code: z.string().nullable(),
  window_mode: z.string(),
  window_start: z.string().nullable(),
  window_end: z.string().nullable(),
  n_points: z.number(),
  slope: z.number().nullable(),
  pct_change: z.number().nullable(),
  trend_state: z.string(), // growing | stable | declining | insufficient_data
  trend_state_label: z.string(),
  assessment: z.string().nullable(),
  assessment_label: z.string().nullable(),
  previous_trend_state: z.string().nullable(),
  data_type: z.string(),
  data_type_label: z.string(),
  source: SourceRefSchema,
  computed_at: z.string(),
  methodology: MethodologyRefSchema.nullable(),
});

export const ProjectionSeriesSchema = z.object({
  country_iso3: z.string(),
  observed: z.array(ObservationPointSchema),
  projected: z.array(ObservationPointSchema), // con lower_bound / upper_bound
  methodology: MethodologyRefSchema.nullable(),
});

export const ProjectionResultSchema = z.object({
  indicator: IndicatorSchema,
  sector_code: z.string().nullable(),
  occupation_code: z.string().nullable(),
  items: z.array(ProjectionSeriesSchema),
});

/* ---------- Metodologías ("Ver metodología") ---------- */
export const MethodologyItemSchema = z.object({
  methodology_id: z.number(),
  methodology_type: z.string(),
  version: z.string(),
  name: z.string().nullable(),
  params: z.record(z.string(), z.unknown()),
  description_md: z.string().nullable(), // markdown listo para renderizar
  created_at: z.string(),
  is_current: z.boolean(),
});

/* ---------- Alertas (campana) ---------- */
const CodeNameSchema = z.object({ code: z.string(), name: z.string() });

export const AlertItemSchema = z.object({
  alert_id: z.number(),
  alert_type: z.string(),
  alert_type_label: z.string(),
  severity: z.string(),
  severity_label: z.string(),
  entity_type: z.string(),
  indicator: CodeNameSchema.nullable(),
  country_iso3: z.string().nullable(),
  sector: CodeNameSchema.nullable(),
  occupation: CodeNameSchema.nullable(),
  source: SourceRefSchema.nullable(),
  period: z.string().nullable(),
  previous_value: z.number().nullable(),
  current_value: z.number().nullable(),
  unit: z.string().nullable(),
  previous_state: z.string().nullable(),
  current_state: z.string().nullable(),
  message: z.string(),
  methodology_id: z.number().nullable(),
  detected_at: z.string(),
  is_read: z.boolean(),
});

export const AlertsPageSchema = z.object({
  total: z.number(),
  unread: z.number(), // contador de la campana
  by_severity: z.record(z.string(), z.number()),
  limit: z.number(),
  offset: z.number(),
  items: z.array(AlertItemSchema),
});

/* ---------- Empleabilidad (ISE) ---------- */
export const EmployabilityComponentSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  weight: z.number(),
  raw: z.number().nullable(),
  normalized: z.number().nullable(),
  contribution: z.number().nullable(),
  indicator: z.string().nullable(),
  unit: z.string().nullable(),
  measure: z.string(),
  detail: z.record(z.string(), z.unknown()),
  available: z.boolean(),
});

export const EmployabilityItemSchema = z.object({
  occupation: OccupationSchema,
  sector_name: z.string().nullable(),
  country_iso3: z.string(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  coverage_ratio: z.number(),
  components: z.array(EmployabilityComponentSchema),
  data_type: z.string(),
  data_type_label: z.string(),
  computed_at: z.string(),
  methodology: MethodologyRefSchema,
  group_code: z.string(),
  group_hidden: z.number().nullable().optional(),
});

export const DimensionRangeSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  weight: z.number(),
  higher_is_better: z.boolean(),
  definition: z.string().nullable(),
  unit: z.string().nullable(),
  possible_range: z.string().nullable(),
  observed_min: z.number().nullable(),
  observed_max: z.number().nullable(),
  with_data: z.number(),
  total: z.number(),
  has_source: z.boolean(),
  source_status: z.string().nullable(),
  effective_weight: z.number(),
});

export const EmployabilityPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  view: z.string(),
  sort_by: z.string(),
  order: z.string(),
  total: z.number(),
  scored_total: z.number(),
  limit: z.number(),
  offset: z.number(),
  dimension_ranges: z.array(DimensionRangeSchema),
  no_source_note: z.string().nullable().optional(),
  items: z.array(EmployabilityItemSchema),
});

export const EmployabilityHistoryPointSchema = z.object({
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  coverage_ratio: z.number(),
});

export const EmployabilityHistorySchema = z.object({
  occupation_code: z.string(),
  country_iso3: z.string(),
  points: z.array(EmployabilityHistoryPointSchema),
  methodology: MethodologyRefSchema.nullable(),
});

/* ---------- Ocupaciones: perfil y habilidades ---------- */
export const SkillItemSchema = z.object({
  skill_code: z.string(),
  name: z.string(),
  skill_type: z.string().nullable(),
  skill_type_label: z.string().nullable(),
  esco_uri: z.string().nullable(),
  weight: z.number().nullable().optional(),
  occupations: z.number().nullable().optional(),
});

export const IscoLevelSchema = z.object({
  level: z.number(),
  level_label: z.string(),
  code: z.string(),
  name: z.string().nullable(),
});

export const OccupationGroupSchema = z.object({
  indicator: z.string(),
  source: z.string(),
  countries: z.array(z.string()),
  group_code: z.string(),
  isco_digits: z.number(),
  shared_with: z.array(z.string()),
});

export const OccupationProfileSchema = z.object({
  occupation: OccupationSchema,
  sector_name: z.string().nullable(),
  groups: z.array(OccupationGroupSchema),
  employability: z.array(EmployabilityItemSchema),
  latest: z.array(ObservationPointSchema),
  top_skills: z.array(SkillItemSchema),
  hierarchy: z.array(IscoLevelSchema),
});

export const OccupationSkillsSchema = z.object({
  occupation_code: z.string(),
  occupation_name: z.string(),
  total: z.number(),
  weight_note: z.string(),
  source: SourceRefSchema.nullable(),
  updated_at: z.string().nullable(),
  items: z.array(SkillItemSchema),
});

export const SkillOccupationSchema = z.object({
  occupation: OccupationSchema,
  weight: z.number(),
});

export const SkillDetailSchema = SkillItemSchema.extend({
  used_by: z.array(SkillOccupationSchema),
});

/* ---------- Brechas de habilidades ---------- */
export const SkillGapItemSchema = z.object({
  skill: SkillItemSchema,
  country_iso3: z.string(),
  year: z.number(),
  demand_growth: z.number().nullable(),
  supply_growth: z.number().nullable(),
  gap: z.number().nullable(),
  is_emerging: z.boolean(),
  data_sufficiency: z.string(),
  data_sufficiency_label: z.string(),
  demand_coverage: z.number(),
  supply_coverage: z.number(),
  occupations: z.number(),
  top_occupations: z.array(z.record(z.string(), z.unknown())),
  data_type: z.string(),
  data_type_label: z.string(),
  methodology: MethodologyRefSchema,
});

export const SkillGapsPageSchema = z.object({
  view: z.string(),
  sort_by: z.string(),
  order: z.string(),
  min_occupations: z.number(),
  total: z.number(),
  full_total: z.number(),
  year: z.number().nullable(),
  limit: z.number(),
  offset: z.number(),
  crosswalk_reviewed: z.record(z.string(), z.boolean()),
  items: z.array(SkillGapItemSchema),
});

/* ---------- Graduados ---------- */
export const GraduateTrendItemSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anio_desde: z.number(),
  anio_hasta: z.number(),
  n_anios_serie: z.number(),
  ventana_anios: z.number(),
  graduados_inicio_ventana: z.number(),
  graduados_ultimo: z.number(),
  variacion_ventana_pct: z.number().nullable(),
  tendencia: z.string(),
  tiene_huecos: z.boolean(),
  proyeccion: z.string(),
});

export const GraduateTrendsSchema = z.object({
  items: z.array(GraduateTrendItemSchema),
  source: z.string(),
});

export const GraduateProjectionItemSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anio: z.number(),
  graduados_proyectado: z.number(),
  limite_inferior: z.number(),
  limite_superior: z.number(),
});

/* ---------- Tipos inferidos ---------- */
export type Country = z.infer<typeof CountrySchema>;
export type Sector = z.infer<typeof SectorSchema>;
export type Occupation = z.infer<typeof OccupationSchema>;
export type Indicator = z.infer<typeof IndicatorSchema>;
export type ObservationPoint = z.infer<typeof ObservationPointSchema>;
export type ObservationsPage = z.infer<typeof ObservationsPageSchema>;
export type ComparePoint = z.infer<typeof ComparePointSchema>;
export type CompareResult = z.infer<typeof CompareResultSchema>;
export type HighlightCard = z.infer<typeof HighlightCardSchema>;
export type DashboardSummary = z.infer<typeof DashboardSummarySchema>;
export type TrendItem = z.infer<typeof TrendItemSchema>;
export type ProjectionResult = z.infer<typeof ProjectionResultSchema>;
export type MethodologyItem = z.infer<typeof MethodologyItemSchema>;
export type AlertItem = z.infer<typeof AlertItemSchema>;
export type AlertsPage = z.infer<typeof AlertsPageSchema>;
export type CoverageItem = z.infer<typeof CoverageItemSchema>;
export type EmployabilityComponent = z.infer<typeof EmployabilityComponentSchema>;
export type EmployabilityItem = z.infer<typeof EmployabilityItemSchema>;
export type DimensionRange = z.infer<typeof DimensionRangeSchema>;
export type EmployabilityPage = z.infer<typeof EmployabilityPageSchema>;
export type EmployabilityHistory = z.infer<typeof EmployabilityHistorySchema>;
export type OccupationProfile = z.infer<typeof OccupationProfileSchema>;
export type SkillItem = z.infer<typeof SkillItemSchema>;
export type OccupationSkills = z.infer<typeof OccupationSkillsSchema>;
export type SkillGapItem = z.infer<typeof SkillGapItemSchema>;
export type SkillGapsPage = z.infer<typeof SkillGapsPageSchema>;
export type GraduateTrendItem = z.infer<typeof GraduateTrendItemSchema>;
export type GraduateProjectionItem = z.infer<typeof GraduateProjectionItemSchema>;