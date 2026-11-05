import { z } from 'zod';
import {
  GraduateInstitutionsSchema,
  GraduateProjectionSchema,
  GraduateSeriesSchema,
  GraduateTotalsSchema,
  GraduatesByYearSchema,
  GraduateTrendsSchema,
  InstitutionCareersSchema,
  InstitutionListSchema,
  OccupationOptionSchema,
  SectorKpisSchema,
  SkillGapsPageSchema,
  SkillGroupGapsPageSchema,
} from '../schemas/skills';
import { apiGet } from './client';

export const getSkillGaps = (params: {
  country?: string; sector?: string; relation?: string; occupation?: string; view?: string; q?: string; year?: string; limit?: number; offset?: number;
}) => apiGet('/skills/gaps', SkillGapsPageSchema, params, 300);

export const getSkillGroupGaps = (params: {
  country?: string; sector?: string; relation?: string; view?: string; q?: string; year?: string; limit?: number; offset?: number;
}) => apiGet('/skills/groups/gaps', SkillGroupGapsPageSchema, params, 300);

export const getOccupations = (sector?: string) =>
  apiGet('/occupations', z.array(OccupationOptionSchema), { sector }, 3600);

export const getGraduateSeries = (pais: string, nombre: string) =>
  apiGet('/graduates/series', GraduateSeriesSchema, { pais, nombre }, 3600);
export const getGraduateInstitutions = (pais: string, nombre: string) =>
  apiGet('/graduates/institutions', GraduateInstitutionsSchema, { pais, nombre }, 3600);
export const getInstitutionList = () => apiGet('/graduates/institutions/list', InstitutionListSchema, {}, 3600);
export const getInstitutionCareers = (institucion: string) =>
  apiGet('/graduates/institutions/careers', InstitutionCareersSchema, { institucion }, 3600);
export const getSectorKpis = () => apiGet('/analytics/sectores', SectorKpisSchema, {}, 3600);
export const getGraduateTotals = (params: { sector?: string; tema?: string }) =>
  apiGet('/graduates/totals', GraduateTotalsSchema, params, 3600);
export const getGraduatesByYear = (year?: string) => apiGet('/graduates/by-year', GraduatesByYearSchema, { year }, 3600);
export const getGraduateTrends = () => apiGet('/graduates/trends', GraduateTrendsSchema, {}, 3600);
export const getGraduateProjections = () => apiGet('/graduates/projections', z.array(GraduateProjectionSchema), {}, 3600);
