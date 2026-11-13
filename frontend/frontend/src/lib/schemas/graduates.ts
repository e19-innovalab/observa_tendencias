import { z } from 'zod';

/* ---------- Graduados (vistas extendidas) ---------- */

export const GraduateInstitutionsSchema = z.object({
  pais: z.string(),
  nombre: z.string(),
  anios: z.array(z.number()),
  instituciones: z.array(
    z.object({
      institucion: z.string(),
      por_anio: z.record(z.string(), z.number()),
      total: z.number(),
    }),
  ),
  totales: z.record(z.string(), z.number()),
});

export const InstitutionListSchema = z.array(
  z.object({ pais: z.string(), institucion: z.string(), n_carreras: z.number() }),
);

export const InstitutionCareersSchema = z.object({
  institucion: z.string(),
  carreras: z.array(
    z.object({
      pais: z.string(),
      nombre: z.string(),
      por_anio: z.record(z.string(), z.number()),
      es_seguimiento: z.boolean(),
      sector: z.string().nullable(),
      tema: z.string().nullable(),
    }),
  ),
});

const optionalNumber = z.number().nullable().optional();

export const SectorKpisSchema = z.object({
  items: z.array(
    z.object({
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
    }),
  ),
  proyecciones: z.array(
    z.object({
      pais: z.string(),
      sector: z.string(),
      anio: z.number(),
      valor: z.number(),
      limite_inferior: optionalNumber,
      limite_superior: optionalNumber,
    }),
  ),
  nota: z.string(),
  genero_nota: z.string().default(''),
  cep_xxi: z
    .array(
      z.object({
        sector: z.string(),
        anio: z.number(),
        puestos: optionalNumber,
        meses: optionalNumber,
        pct_mujeres: optionalNumber,
        salario_ars: optionalNumber,
        salario_usd: optionalNumber,
        salario_usd_ppa: optionalNumber,
        indice_real: optionalNumber,
      }),
    )
    .default([]),
  cep_nota: z.string().default(''),
  cep_base: z.number().nullable().optional(),
  dolar_oficial: z.object({ nombre: z.string(), fecha: z.string(), valor: z.number() }).nullable().optional(),
});
export type SectorKpis = z.infer<typeof SectorKpisSchema>;

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
  items: z.array(
    z.object({
      pais: z.string(),
      nombre: z.string(),
      anio: z.number(),
      graduados: z.number(),
      tipo: z.enum(['observado', 'proyectado']),
      limite_inferior: z.number().nullable().optional(),
      limite_superior: z.number().nullable().optional(),
      es_seguimiento: z.boolean(),
    }),
  ),
});

export const GraduateTrendExtendedSchema = z.object({
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
export const GraduateTrendsExtendedSchema = z.object({
  items: z.array(GraduateTrendExtendedSchema),
  source: z.string(),
});
