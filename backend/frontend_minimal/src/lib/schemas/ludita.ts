import { z } from 'zod';
import { MethodologyRefSchema, OccupationSchema } from './api';
import { MoctezumaComponentSchema, MoctezumaRangeSchema, MoctezumaSideSchema } from './moctezuma';

/** Camino (cuadrante de exposición y vitalidad), con el nombre de un caso histórico. */
export const LuditaPathSchema = z.object({
  path: z.string(), // weaver | teller | other_causes | out_of_reach
  label: z.string(),
  short: z.string(),
  description: z.string(),
});
export type LuditaPath = z.infer<typeof LuditaPathSchema>;

export const LuditaItemSchema = z.object({
  occupation: OccupationSchema,
  sector_name: z.string().nullable(),
  country_iso3: z.string(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  path: z.string().nullable(),
  path_label: z.string().nullable(),
  exposure: z.number().nullable(),
  vitality: z.number().nullable(),
  exposure_coverage: z.number(),
  vitality_coverage: z.number(),
  components: z.array(MoctezumaComponentSchema),
  methodology: MethodologyRefSchema,
});
export type LuditaItem = z.infer<typeof LuditaItemSchema>;

export const LuditaPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  view: z.string(),
  side_labels: z.record(z.string(), z.string()),
  level_labels: z.record(z.string(), z.string()),
  sides: z.array(MoctezumaSideSchema),
  paths: z.array(LuditaPathSchema),
  path_rules: z.record(z.string(), z.number()),
  dimension_ranges: z.record(z.string(), MoctezumaRangeSchema),
  total: z.number(),
  scored_total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(LuditaItemSchema),
});
export type LuditaPage = z.infer<typeof LuditaPageSchema>;

/** Valor del país por año (promedio simple) y cuántas ocupaciones siguen cada camino. */
export const LuditaCountrySchema = z.object({
  country_iso3: z.string(),
  points: z.array(z.object({
    year: z.number(),
    score: z.number(),
    exposure: z.number(),
    vitality: z.number(),
    level: z.string(),
    level_label: z.string(),
    scored: z.number(),
    total: z.number(),
    paths: z.record(z.string(), z.number()),
  })),
  methodology: MethodologyRefSchema.nullable(),
});
export type LuditaCountry = z.infer<typeof LuditaCountrySchema>;

/** Empleo de un caso (histórico o de hoy), con índice 100 en la llegada de su tecnología. */
export const LuditaCaseSchema = z.object({
  key: z.string(),
  label: z.string(),
  technology: z.string(),
  arrival_year: z.number(),
  arrival_note: z.string(),
  base_year: z.number(),
  path: z.string().nullable(),
  source_short: z.string().nullable(),
  country_iso3: z.string().nullable(),
  points: z.array(z.object({
    year: z.number(),
    years_since: z.number(),
    value: z.number(),
    index: z.number(),
    approx: z.boolean(),
    note: z.string().nullable(),
  })),
  sources: z.array(z.object({ label: z.string(), detail: z.string().nullable(), url: z.string() })),
});
export type LuditaCase = z.infer<typeof LuditaCaseSchema>;

export const LuditaHistorySchema = z.object({ zoom_years: z.number(), cases: z.array(LuditaCaseSchema), today: z.array(LuditaCaseSchema) });
export type LuditaHistory = z.infer<typeof LuditaHistorySchema>;
