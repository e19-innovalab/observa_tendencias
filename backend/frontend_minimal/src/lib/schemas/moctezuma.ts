import { z } from 'zod';
import { MethodologyRefSchema, OccupationSchema } from './api';

/** Qué mide cada dimensión del Indicador Moctezuma y cómo entra en su lado. */
export const MoctezumaDimensionSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  weight: z.number(),
  higher_is_more: z.boolean(),
  indicator: z.string(),
  scope: z.string(), // occupation | country
  definition: z.string().nullable(),
  unit: z.string().nullable(),
  possible_range: z.string().nullable(),
});

/** Ritmo del cambio (pace) y Capacidad de respuesta (readiness). */
export const MoctezumaSideSchema = z.object({
  side: z.string(),
  label: z.string(),
  definition: z.string().nullable(),
  weight: z.number(),
  dimensions: z.array(MoctezumaDimensionSchema),
});
export type MoctezumaSide = z.infer<typeof MoctezumaSideSchema>;

export const MoctezumaComponentSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  side: z.string(),
  weight: z.number(),
  raw: z.number().nullable(),
  normalized: z.number().nullable(),
  indicator: z.string(),
  scope: z.string(),
  measure: z.string(),
  detail: z.record(z.string(), z.unknown()),
  available: z.boolean(),
});

export const MoctezumaItemSchema = z.object({
  occupation: OccupationSchema,
  sector_name: z.string().nullable(),
  country_iso3: z.string(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  pace: z.number().nullable(),
  readiness: z.number().nullable(),
  gap: z.number().nullable(),
  pace_coverage: z.number(),
  readiness_coverage: z.number(),
  components: z.array(MoctezumaComponentSchema),
  methodology: MethodologyRefSchema,
});
export type MoctezumaItem = z.infer<typeof MoctezumaItemSchema>;

export const MoctezumaRangeSchema = z.object({
  observed_min: z.number().nullable(),
  observed_max: z.number().nullable(),
  with_data: z.number(),
});

export const MoctezumaPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  view: z.string(),
  side_labels: z.record(z.string(), z.string()),
  level_labels: z.record(z.string(), z.string()),
  sides: z.array(MoctezumaSideSchema),
  dimension_ranges: z.record(z.string(), MoctezumaRangeSchema),
  total: z.number(),
  scored_total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(MoctezumaItemSchema),
});
export type MoctezumaPage = z.infer<typeof MoctezumaPageSchema>;

/** Valor del país por año: promedio simple de sus ocupaciones con indicador. */
export const MoctezumaCountrySchema = z.object({
  country_iso3: z.string(),
  points: z.array(
    z.object({
      year: z.number(),
      score: z.number(),
      pace: z.number(),
      readiness: z.number(),
      level: z.string(),
      level_label: z.string(),
      scored: z.number(),
      total: z.number(),
    }),
  ),
  methodology: MethodologyRefSchema.nullable(),
});
export type MoctezumaCountry = z.infer<typeof MoctezumaCountrySchema>;

const ReferenceSourceSchema = z.object({ label: z.string(), detail: z.string().nullable(), url: z.string() });
export type ReferenceSource = z.infer<typeof ReferenceSourceSchema>;

/** Versión histórica ilustrativa (centro de México, 1518–1605) calculada en el backend con la fórmula vigente. */
export const MoctezumaReferenceSchema = z.object({
  region: z.string(),
  contact_year: z.number(),
  pace_full_from: z.number(),
  pace_note: z.string(),
  population_unit: z.string(),
  base_year: z.number(),
  points: z.array(z.object({ year: z.number(), population: z.number(), pace: z.number(), readiness: z.number(), score: z.number() })),
  example_year: z.number(),
  alternative: z.object({
    label: z.string(),
    base_year: z.number(),
    base_population: z.number(),
    year: z.number(),
    population: z.number(),
    readiness: z.number(),
    score: z.number(),
  }),
  sources: z.record(z.string(), z.array(ReferenceSourceSchema)),
  side_history: z.record(z.string(), z.string()),
  example_occupation: z.string().nullable(),
  events: z.array(z.object({ year: z.number(), label: z.string(), detail: z.string() })).default([]),
  point_notes: z.record(z.string(), z.string()).default({}), // año -> qué pasó hasta esa cifra
  point_labels: z.record(z.string(), z.string()).default({}), // año -> etiqueta corta en el gráfico
});
export type MoctezumaReference = z.infer<typeof MoctezumaReferenceSchema>;
