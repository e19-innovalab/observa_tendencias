import { z } from 'zod';
import { MethodologyRefSchema, OccupationSchema } from './api';

export const RedQueenDimensionSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  weight: z.number(),
  source_code: z.string(),
  source_name: z.string().nullable(),
  source_url: z.string().nullable(),
  definition: z.string().nullable(),
  unit: z.string().nullable(),
  possible_range: z.string().nullable(),
});
export type RedQueenDimension = z.infer<typeof RedQueenDimensionSchema>;

/** Una fuente: las dos versiones comparadas y qué cambió entre ellas. */
export const RedQueenComponentSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  available: z.boolean(),
  normalized: z.number().nullable(),
  from_version: z.string().nullable(),
  to_version: z.string().nullable(),
  from_date: z.string().nullable(),
  to_date: z.string().nullable(),
  years: z.number().nullable(),
  n_from: z.number().nullable(),
  n_to: z.number().nullable(),
  added_count: z.number().nullable(),
  removed_count: z.number().nullable(),
  renamed_count: z.number().nullable(),
  new_per_year: z.number().nullable(),
  turnover: z.number().nullable(),
  annual: z.number().nullable(),
  half_life: z.number().nullable(),
  added: z.array(z.string()),
  removed: z.array(z.string()),
});
export type RedQueenComponent = z.infer<typeof RedQueenComponentSchema>;

export const RedQueenItemSchema = z.object({
  occupation: OccupationSchema,
  sector_name: z.string().nullable(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  turnover: z.number().nullable(),
  half_life: z.number().nullable(),
  half_life_capped: z.boolean(),
  coverage: z.number(),
  components: z.array(RedQueenComponentSchema),
  methodology: MethodologyRefSchema,
});
export type RedQueenItem = z.infer<typeof RedQueenItemSchema>;

export const RedQueenPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  view: z.string(),
  level_labels: z.record(z.string(), z.string()),
  dimensions: z.array(RedQueenDimensionSchema),
  half_life_cap: z.number(),
  examples_shown: z.number(),
  career: z.string().nullish(), // filtro aplicado (opcional: respuestas cacheadas de antes no lo traen)
  total: z.number(),
  scored_total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(RedQueenItemSchema),
});
export type RedQueenPage = z.infer<typeof RedQueenPageSchema>;

/** Mediana de las ocupaciones con puntaje en cada año. */
export const RedQueenYearSchema = z.object({
  year: z.number(),
  scored: z.number(),
  median_new_per_year: z.record(z.string(), z.number()),
  median_turnover: z.number().nullable(),
  median_half_life: z.number().nullable(),
});
export type RedQueenYear = z.infer<typeof RedQueenYearSchema>;

/** Parámetros vigentes de la metodología (analytics.yaml -> red_queen). */
export const RedQueenParamsSchema = z.object({
  dimensions: z.record(z.string(), z.object({ source: z.string(), weight: z.number(), min_items: z.number() })),
  window_years: z.number(),
  min_years: z.number(),
  max_age_years: z.number(),
  rename_min_chars: z.number(),
  half_life_cap: z.number(),
  levels: z.object({ low: z.number(), high: z.number() }),
  scale_max: z.number(),
});
export type RedQueenParams = z.infer<typeof RedQueenParamsSchema>;

export const CareerOptionSchema = z.object({ career: z.string(), occupations: z.number() });
