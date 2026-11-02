import { z } from 'zod';
import {
  OccupationSkillsSchema,
  SkillDetailSchema,
  SkillGapsPageSchema,
  SkillItemSchema,
} from '../schemas/api';
import { apiGet } from './client';

export type GapView = 'top' | 'bottom' | 'all';

export const getSkillGaps = (params: {
  countries?: string[];
  view?: GapView;
  sortBy?: 'gap' | 'demand_growth' | 'supply_growth' | 'occupations';
  order?: 'asc' | 'desc';
  minOccupations?: number;
  emerging?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
} = {}) =>
  apiGet(
    '/skills/gaps',
    SkillGapsPageSchema,
    {
      country: params.countries,
      view: params.view,
      sort_by: params.sortBy,
      order: params.order,
      min_occupations: params.minOccupations,
      emerging: params.emerging,
      q: params.q,
      limit: params.limit,
      offset: params.offset,
    },
    60,
  );

export const getOccupationSkills = (
  code: string,
  params: { skillType?: string; limit?: number } = {},
) =>
  apiGet(
    `/occupations/${encodeURIComponent(code)}/skills`,
    OccupationSkillsSchema,
    { skill_type: params.skillType, limit: params.limit },
    60,
  );

export const getSkills = (params: { q?: string; skillType?: string; limit?: number } = {}) =>
  apiGet(
    '/skills',
    z.array(SkillItemSchema),
    { q: params.q, skill_type: params.skillType, limit: params.limit },
    60,
  );

export const getSkillDetail = (code: string, limit?: number) =>
  apiGet(`/skills/${encodeURIComponent(code)}`, SkillDetailSchema, { limit }, 60);
