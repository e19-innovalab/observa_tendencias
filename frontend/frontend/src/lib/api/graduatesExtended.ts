import { z } from 'zod';
import { GraduateProjectionItemSchema, GraduateTrendsSchema } from '../schemas/api';
import {
  GraduateInstitutionsSchema,
  GraduateSeriesSchema,
  GraduateTotalsSchema,
  GraduatesByYearSchema,
  GraduateTrendsExtendedSchema,
  InstitutionCareersSchema,
  InstitutionListSchema,
  SectorKpisSchema,
} from '../schemas/graduates';
import { apiGet } from './client';

export { getGraduateProjections, getGraduateTrends } from './graduates';

export const getGraduateSeries = (pais: string, nombre: string) =>
  apiGet('/graduates/series', GraduateSeriesSchema, { pais, nombre }, 3600);

export const getGraduateInstitutions = (pais: string, nombre: string) =>
  apiGet('/graduates/institutions', GraduateInstitutionsSchema, { pais, nombre }, 3600);

export const getInstitutionList = () =>
  apiGet('/graduates/institutions/list', InstitutionListSchema, {}, 3600);

export const getInstitutionCareers = (institucion: string) =>
  apiGet('/graduates/institutions/careers', InstitutionCareersSchema, { institucion }, 3600);

export const getSectorKpis = () => apiGet('/analytics/sectores', SectorKpisSchema, {}, 3600);

export const getGraduateTotals = (params: { sector?: string; tema?: string } = {}) =>
  apiGet('/graduates/totals', GraduateTotalsSchema, params, 3600);

export const getGraduatesByYear = (year?: string) =>
  apiGet('/graduates/by-year', GraduatesByYearSchema, { year }, 3600);

export const getGraduateTrendsExtended = (params: { countries?: string[]; tendencia?: string } = {}) =>
  apiGet(
    '/graduates/trends',
    GraduateTrendsExtendedSchema,
    { country: params.countries, tendencia: params.tendencia },
    3600,
  );

export const getProjectionsRaw = () =>
  apiGet('/graduates/projections', z.array(GraduateProjectionItemSchema), {}, 3600);

export { GraduateTrendsSchema };
