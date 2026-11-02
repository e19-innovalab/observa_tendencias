import { z } from 'zod';
import { apiGet } from './client';

/** Ofertas de LinkedIn (recolección con Apify): no es una fuente oficial. */
export const JobsSummarySchema = z.object({
  total: z.number(),
  scraped_at: z.string().nullable(),
  por_provincia_sector: z.array(z.object({ provincia: z.string(), sector: z.string(), n: z.number() })),
  competencia: z
    .array(
      z.object({
        sector: z.string().nullable(), // null: todas las ofertas
        ofertas: z.number(),
        con_postulantes: z.number(),
        mediana_postulantes: z.number().nullable(),
        en_tope: z.number().nullable(),
      }),
    )
    .default([]),
  source: z.string(),
  view: z.object({
    notice: z.string(),
    footnote: z.string(),
    source_label: z.string(),
    period_label: z.string(),
    sector_order: z.array(z.string()),
    other_sector: z.string(),
    no_level: z.string(),
    page_size: z.number(),
    applicants_cap: z.number(),
    competition_min_postings: z.number(),
  }).loose(),
});
export type JobsSummary = z.infer<typeof JobsSummarySchema>;

export const JobsPageSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(
    z.object({
      id: z.string(),
      provincia: z.string(),
      sector: z.string(),
      titulo: z.string(),
      empresa: z.string().nullable(),
      fecha_publicacion: z.string().nullable(),
      nivel_experiencia: z.string().nullable(),
      tipo_empleo: z.string().nullable(),
      postulantes: z.number().nullable(),
      url: z.string(),
    }).loose(),
  ),
});

export const getJobsSummary = (country?: string) => apiGet('/jobs/summary', JobsSummarySchema, { country }, 300);
export const getJobs = (params: { country?: string; provincia?: string; sector?: string; q?: string; limit: number; offset: number }) =>
  apiGet('/jobs', JobsPageSchema, params, 300);
