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
  es_seguimiento: z.boolean().default(false),
  sector: z.string().nullable().default(null),
  tema: z.string().nullable().default(null),
  n_instituciones: z.number().nullable().default(null),
  institucion_principal: z.string().nullable().default(null),
});
export const GraduateInstitutionsSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anios: z.array(z.number()),
  instituciones: z.array(z.object({
    institucion: z.string(),
    por_anio: z.record(z.string(), z.number()),
    total: z.number(),
  })),
  totales: z.record(z.string(), z.number()),
});
export const InstitutionListSchema = z.array(z.object({
  pais: z.string(),
  institucion: z.string(),
  n_carreras: z.number(),
}));
export const InstitutionCareersSchema = z.object({
  institucion: z.string(),
  carreras: z.array(z.object({
    pais: z.string(),
    nombre: z.string(),
    por_anio: z.record(z.string(), z.number()),
    es_seguimiento: z.boolean(),
    sector: z.string().nullable(),
    tema: z.string().nullable(),
  })),
});
const optionalNumber = z.number().nullable().optional();
export const SectorKpisSchema = z.object({
  items: z.array(z.object({
    pais: z.string(),
    sector: z.string(),
    anio: z.number(),
    graduados: optionalNumber,
    densidad: optionalNumber,
    ocupados: optionalNumber,
    pct_mujeres_ocupadas: optionalNumber,
    pct_mujeres_graduadas: optionalNumber,
    graduados_con_sexo: optionalNumber,
    f: optionalNumber,
    m: optionalNumber,
    nb: optionalNumber,
    pct_varones_graduados: optionalNumber,
    pct_nb_graduados: optionalNumber,
    brecha_graduados_pct: optionalNumber,
    diagnostico_paridad: z.string().nullable().optional(),
    brecha_empleo_pct: optionalNumber,
    diagnostico_empleo: z.string().nullable().optional(),
    salario_total: optionalNumber,
    salario_mujeres: optionalNumber,
    salario_varones: optionalNumber,
    brecha_salarial_pct: optionalNumber,
  })),
  proyecciones: z.array(z.object({
    pais: z.string(),
    sector: z.string(),
    anio: z.number(),
    valor: z.number(),
    limite_inferior: optionalNumber,
    limite_superior: optionalNumber,
  })),
  nota: z.string(),
  genero_nota: z.string().default(''),
  cep_xxi: z.array(z.object({
    sector: z.string(),
    anio: z.number(),
    puestos: optionalNumber,
    meses: optionalNumber,
    pct_mujeres: optionalNumber,
    salario_ars: optionalNumber,
    salario_usd: optionalNumber,
    salario_usd_ppa: optionalNumber,
    indice_real: optionalNumber,
  })).default([]),
  cep_nota: z.string().default(''),
  cep_base: z.number().nullable().optional(),
  dolar_oficial: z.object({ nombre: z.string(), fecha: z.string(), valor: z.number() }).nullable().optional(),
});
export const GraduateTotalsSchema = z.object({
  anios: z.array(z.number()),
  paises: z.array(z.object({ pais: z.string(), por_anio: z.record(z.string(), z.number()) })),
});
export const GraduateSeriesSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  puntos: z.array(z.object({ anio: z.number(), graduados: z.number() })),
});
export const GraduatesByYearSchema = z.object({
  anio: z.number().nullable(),
  anios_observados: z.array(z.number()),
  anios_proyectados: z.array(z.number()),
  items: z.array(z.object({
    pais: z.string(),
    nombre: z.string(),
    anio: z.number(),
    graduados: z.number(),
    tipo: z.enum(['observado', 'proyectado']),
    limite_inferior: z.number().nullable().optional(),
    limite_superior: z.number().nullable().optional(),
    es_seguimiento: z.boolean(),
  })),
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
