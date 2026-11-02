import { z } from 'zod';
import { MethodologyRefSchema } from './api';
import { LuditaPathSchema } from './ludita';
import { MoctezumaComponentSchema, MoctezumaSideSchema } from './moctezuma';

/** Un gran grupo de ocupación en un país y año. */
export const SisyphusItemSchema = z.object({
  country_iso3: z.string(),
  group_code: z.string(),
  group_name: z.string().nullable(),
  year: z.number(),
  score: z.number().nullable(),
  level: z.string(),
  level_label: z.string(),
  stone: z.number().nullable(),
  reward: z.number().nullable(),
  quadrant: z.string().nullable(),
  quadrant_label: z.string().nullable(),
  overeducation: z.number().nullable(),
  earnings_ratio: z.number().nullable(),
  earnings_ppp: z.number().nullable(),
  earnings_usd: z.number().nullable(),
  tertiary_ppp: z.number().nullable(),
  components: z.array(MoctezumaComponentSchema),
});
export type SisyphusItem = z.infer<typeof SisyphusItemSchema>;

export const SisyphusPageSchema = z.object({
  year: z.number().nullable(),
  available_years: z.array(z.number()),
  level_labels: z.record(z.string(), z.string()),
  side_labels: z.record(z.string(), z.string()),
  sides: z.array(MoctezumaSideSchema),
  quadrants: z.array(LuditaPathSchema),
  quadrant_rules: z.record(z.string(), z.number()),
  excluded_groups: z.array(z.string()),
  // qué incluye cada gran grupo (OIT) y ocupaciones de ejemplo; opcionales por respuestas cacheadas de antes
  groups: z.array(z.object({
    code: z.string(),
    name: z.string().nullable(),
    definition: z.string().nullable(),
    occupations: z.number(),
    examples: z.array(z.object({ occupation_code: z.string(), name: z.string(), is_featured: z.boolean() })),
  })).default([]),
  groups_source: z.record(z.string(), z.string()).default({}),
  items: z.array(SisyphusItemSchema),
  methodology: MethodologyRefSchema.nullable(),
});
export type SisyphusPage = z.infer<typeof SisyphusPageSchema>;

export const SisyphusCountrySchema = z.object({
  country_iso3: z.string(),
  points: z.array(z.object({
    year: z.number(),
    score: z.number().nullable(),
    graduates_below_share: z.number().nullable(),
    premium: z.number().nullable(),
    tertiary_ppp: z.number().nullable(),
    tertiary_usd: z.number().nullable(),
    secondary_ppp: z.number().nullable(),
    secondary_usd: z.number().nullable(),
  })),
});
export type SisyphusCountry = z.infer<typeof SisyphusCountrySchema>;
