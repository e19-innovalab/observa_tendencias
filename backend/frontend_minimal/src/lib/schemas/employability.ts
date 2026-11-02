import { z } from 'zod';

/** Qué mide cada dimensión del ISE, su peso y su rango en el grupo comparado. */
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
export type DimensionRange = z.infer<typeof DimensionRangeSchema>;

export const SectorSummarySchema = z.object({
  sector_code: z.string(),
  name: z.string(),
  occupations: z.number(),
  scored: z.number(),
  average_score: z.number().nullable(),
  previous_average: z.number().nullable(),
  change: z.number().nullable(),
  level: z.string().nullable(),
  level_label: z.string().nullable(),
  top_occupation: z
    .object({ occupation_code: z.string(), name: z.string(), country_iso3: z.string(), score: z.number() })
    .nullable(),
  salary_ppp_average: z.number().nullable(),
  salary_usd_average: z.number().nullable().optional(),
  automation_average: z.number().nullable(),
  dimensions: z.record(z.string(), z.number().nullable()),
});
export type SectorSummary = z.infer<typeof SectorSummarySchema>;

/** Textos de las pantallas del ISE (app.yaml → employability). */
export const EmployabilityTextsSchema = z.object({
  terms: z.record(z.string(), z.string()),
  unit_formats: z.record(z.string(), z.string()),
  display: z.record(z.string(), z.object({ label: z.string().nullable().optional(), note: z.string().nullable().optional() })),
});

export const SectorsPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  countries: z.array(z.string()),
  regional_average: z.number().nullable(),
  dimension_ranges: z.array(DimensionRangeSchema),
  no_source_note: z.string().nullable(),
  items: z.array(SectorSummarySchema),
  texts: EmployabilityTextsSchema.nullable().optional(),
});

const OccupationRefSchema = z.object({
  occupation_code: z.string(),
  name: z.string(),
  name_en: z.string().nullable().optional(),
  isco08_code: z.string(),
  sector_code: z.string().nullable().optional(),
  is_featured: z.boolean().optional(),
  is_excluded: z.boolean().optional(),
});

export const ComponentSchema = z.object({
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
  /** Valor que se muestra primero (p. ej. salario en USD); el índice usa raw. */
  display: z
    .object({ indicator: z.string(), label: z.string(), unit: z.string(), value: z.number(), period: z.string(), note: z.string().nullable() })
    .nullable()
    .optional(),
});
export type Component = z.infer<typeof ComponentSchema>;

export const EmployabilityItemSchema = z.object({
  occupation: OccupationRefSchema,
  sector_name: z.string().nullable(),
  country_iso3: z.string(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  coverage_ratio: z.number(),
  components: z.array(ComponentSchema),
});
export type EmployabilityItem = z.infer<typeof EmployabilityItemSchema>;

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
  no_source_note: z.string().nullable(),
  items: z.array(EmployabilityItemSchema),
});

export const SkillRefSchema = z.object({
  skill_code: z.string(),
  name: z.string(),
  skill_type: z.string().nullable().optional(),
  skill_type_label: z.string().nullable().optional(),
  esco_uri: z.string().nullable().optional(),
  weight: z.number().nullable().optional(),
});

export const OccupationProfileSchema = z.object({
  occupation: OccupationRefSchema,
  sector_name: z.string().nullable(),
  groups: z.array(
    z.object({
      indicator: z.string(),
      source: z.string(),
      countries: z.array(z.string()),
      group_code: z.string(),
      isco_digits: z.number(),
      shared_with: z.array(z.string()),
    }),
  ),
  employability: z.array(EmployabilityItemSchema),
  top_skills: z.array(SkillRefSchema),
  hierarchy: z.array(z.object({ level: z.number(), level_label: z.string(), code: z.string(), name: z.string().nullable() })),
  texts: EmployabilityTextsSchema.nullable().optional(),
});

export const OccupationSkillsSchema = z.object({
  occupation_code: z.string(),
  occupation_name: z.string(),
  total: z.number(),
  weight_note: z.string(),
  source: z.object({ code: z.string(), name: z.string() }).nullable(),
  updated_at: z.string().nullable(),
  items: z.array(SkillRefSchema),
});

export type EmployabilityTexts = z.infer<typeof EmployabilityTextsSchema>;
