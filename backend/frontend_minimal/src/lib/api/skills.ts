import { z } from 'zod';
import {
  GraduateProjectionSchema,
  GraduateTrendsSchema,
  OccupationOptionSchema,
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

export const getGraduateTrends = () => apiGet('/graduates/trends', GraduateTrendsSchema, {}, 3600);
export const getGraduateProjections = () => apiGet('/graduates/projections', z.array(GraduateProjectionSchema), {}, 3600);
