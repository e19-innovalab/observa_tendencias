import { z } from 'zod';
import {
  OccupationSkillsSchema,
  SkillDetailSchema,
  SkillGapsPageSchema,
  SkillGroupGapsPageSchema,
  SkillItemSchema,
} from '../schemas/api';
import { apiGet } from './client';

export type GapView = 'top' | 'bottom' | 'all';

export const getSkillGaps = (params: {
  countries?: string[];
  country?: string;
  sector?: string;
  relation?: string;
  year?: string;
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
      country: params.country ?? params.countries,
      sector: params.sector,
      relation: params.relation,
      year: params.year,
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

/** Brechas por grupo de habilidades de ESCO. */
export const getSkillGroupGaps = (params: {
  country?: string;
  sector?: string;
  relation?: string;
  view?: GapView;
  q?: string;
  year?: string;
  limit?: number;
  offset?: number;
} = {}) =>
  apiGet(
    '/skills/groups/gaps',
    SkillGroupGapsPageSchema,
    {
      country: params.country,
      sector: params.sector,
      relation: params.relation,
      view: params.view,
      q: params.q,
      year: params.year,
      limit: params.limit,
      offset: params.offset,
    },
    60,
  );

export const getOccupations = (sector?: string) =>
  apiGet(
    '/occupations',
    z.array(z.object({ occupation_code: z.string(), name: z.string() }).loose()),
    { sector },
    3600,
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
