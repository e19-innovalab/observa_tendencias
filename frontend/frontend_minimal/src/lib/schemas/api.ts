/**
 * Esquemas Zod de la API de Observa Tendencias (FastAPI, prefijo /api/v1).
 * Generado a mano a partir de openapi.json (API v0.1.0).
 * Cubre: catálogos, indicadores, observaciones, compare, dashboard, tendencias,
 * proyecciones, metodologías y alertas. Pendientes: employability, jobs, skills,
 * graduates, education-mismatch, datasets y sources.
 */
import { z } from 'zod';

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
/* ---------- Reglas de alertas (/alerts/rules) ---------- */
export const AlertRulesSchema = z.object({
  rules: z.array(
    z.object({
      alert_type: z.string(),
      label: z.string(),
      definition: z.string().nullable(),
      params: z.record(z.string(), z.unknown()),
      severity_rule: z.string(),
      active: z.boolean(),
    }),
  ),
  severities: z.array(z.object({ code: z.string(), label: z.string(), definition: z.string().nullable() })),
});
export type AlertRules = z.infer<typeof AlertRulesSchema>;
