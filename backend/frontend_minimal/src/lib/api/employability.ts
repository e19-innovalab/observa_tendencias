import {
  EmployabilityPageSchema,
  OccupationProfileSchema,
  OccupationSkillsSchema,
  SectorsPageSchema,
} from '../schemas/employability';
import { apiGet } from './client';

export const getSectorSummaries = (params: { country?: string; year?: string }) =>
  apiGet('/employability/sectors', SectorsPageSchema, params, 300);

export const getEmployability = (params: {
  country?: string; sector?: string; occupation?: string; year?: string; q?: string; featured?: boolean;
  view?: string; sort_by?: string; order?: string; limit?: number; offset?: number;
}) => apiGet('/employability', EmployabilityPageSchema, params, 300);

export const getOccupationProfile = (code: string) =>
  apiGet(`/occupations/${encodeURIComponent(code)}`, OccupationProfileSchema, {}, 300);

export const getOccupationSkills = (code: string, limit = 500) =>
  apiGet(`/occupations/${encodeURIComponent(code)}/skills`, OccupationSkillsSchema, { limit }, 3600);
