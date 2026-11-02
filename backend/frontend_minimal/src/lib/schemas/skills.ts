import { z } from 'zod';

const SkillSchema = z.object({
  skill_code: z.string(),
  name: z.string(),
  skill_type: z.string().nullable().optional(),
  skill_type_label: z.string().nullable().optional(),
  esco_uri: z.string().nullable().optional(),
  description: z.string().nullable().optional(), // definición en español
  description_en: z.string().nullable().optional(), // original de ESCO en inglés
  description_origin: z.string().nullable().optional(), // esco | translation
  group_code: z.string().nullable().optional(),
});

const SectorUseSchema = z.object({
  sector_code: z.string().nullable(), // null: ocupaciones fuera de los sectores estratégicos
  name: z.string(),
  relation: z.string(),
  relation_label: z.string(),
  occupations: z.array(z.object({ occupation_code: z.string(), name: z.string(), relation: z.string(), relation_label: z.string(), via: z.array(z.string()).default([]) })),
});
export type SectorUse = z.infer<typeof SectorUseSchema>;

export const SkillGapItemSchema = z.object({
  skill: SkillSchema,
  country_iso3: z.string(),
  year: z.number(),
  demand_growth: z.number().nullable(),
  supply_growth: z.number().nullable(),
  gap: z.number().nullable(),
  is_emerging: z.boolean(),
  data_sufficiency: z.string(),
  data_sufficiency_label: z.string(),
  occupations: z.number(),
  top_occupations: z.array(z.object({ occupation: z.string(), name: z.string() }).loose()),
  /** Sectores cuyas ocupaciones usan la habilidad y cómo (categoría ESCO), esenciales primero. */
  sectors: z.array(SectorUseSchema).default([]),
  is_cross_sector: z.boolean().default(false),
  unstable_supply: z.array(z.object({ occupation: z.string(), name: z.string() })).default([]),
});
export type SkillGapItem = z.infer<typeof SkillGapItemSchema>;

const ExtremeSchema = z.object({ skill_code: z.string(), name: z.string(), country_iso3: z.string(), gap: z.number() });

export const SkillGapsPageSchema = z.object({
  view: z.string(),
  total: z.number(),
  full_total: z.number(),
  year: z.number().nullable(),
  available_years: z.array(z.number()).default([]),
  data_through: z
    .array(
      z.object({
        country_iso3: z.string(),
        demand: z.number().nullable(),
        supply: z.number().nullable(),
        supplemented_years: z.array(z.number()).default([]), // titulados de una fuente complementaria
        supply_note: z.string().nullable().default(null),
      }),
    )
    .default([]),
  limit: z.number(),
  offset: z.number(),
  min_occupations: z.number(),
  crosswalk_reviewed: z.record(z.string(), z.boolean()),
  summary: z
    .object({
      skills_with_gap: z.number(),
      average_gap: z.number().nullable(),
      largest_shortage: ExtremeSchema.nullable(),
      largest_surplus: ExtremeSchema.nullable(),
      occupations: z.number(),
      full_share: z.number().nullable(),
    })
    .nullable(),
  items: z.array(SkillGapItemSchema),
});

/** Brechas por grupo de habilidades de ESCO (/skills/groups/gaps). */
export const SkillGroupGapsPageSchema = z.object({
  total: z.number(),
  full_total: z.number(),
  year: z.number().nullable(),
  available_years: z.array(z.number()).default([]),
  data_through: z
    .array(
      z.object({
        country_iso3: z.string(),
        demand: z.number().nullable(),
        supply: z.number().nullable(),
        supplemented_years: z.array(z.number()).default([]), // titulados de una fuente complementaria
        supply_note: z.string().nullable().default(null),
      }),
    )
    .default([]),
  group_level: z.number(),
  crosswalk_reviewed: z.record(z.string(), z.boolean()),
  items: z.array(
    z.object({
      group: z.object({
        group_code: z.string(),
        name: z.string(),
        description: z.string().nullable(),
        description_en: z.string().nullable(),
        description_origin: z.string().nullable(), // esco | translation | null (sigue en inglés)
        level: z.number(),
        parent: z.string().nullable(),
      }),
      country_iso3: z.string(),
      year: z.number(),
      demand_growth: z.number().nullable(),
      supply_growth: z.number().nullable(),
      gap: z.number().nullable(),
      is_emerging: z.boolean(),
      data_sufficiency: z.string(),
      occupations: z.number(),
      skills: z.number(),
      top_skills: z.array(SkillSchema),
      top_occupations: z.array(z.object({ occupation: z.string(), name: z.string() }).loose()),
      sectors: z.array(SectorUseSchema).default([]),
      is_cross_sector: z.boolean().default(false),
      unstable_supply: z.array(z.object({ occupation: z.string(), name: z.string() })).default([]),
    }),
  ),
});

export const OccupationOptionSchema = z.object({ occupation_code: z.string(), name: z.string() }).loose();

export const GraduateTrendSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anio_desde: z.number(),
  anio_hasta: z.number(),
  ventana_anios: z.number(),
  graduados_inicio_ventana: z.number(),
  graduados_ultimo: z.number(),
  variacion_ventana_pct: z.number().nullable(),
  tendencia: z.string(),
  proyeccion: z.string(),
});
export const GraduateTrendsSchema = z.object({ items: z.array(GraduateTrendSchema), source: z.string() });
export const GraduateProjectionSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anio: z.number(),
  graduados_proyectado: z.number(),
  limite_inferior: z.number(),
  limite_superior: z.number(),
});
