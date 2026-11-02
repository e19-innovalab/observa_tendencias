import { z } from 'zod';
import {
  EmployabilityHistorySchema,
  EmployabilityPageSchema,
  OccupationProfileSchema,
} from '../schemas/api';
import { apiGet } from './client';

export type EmployabilityView = 'top' | 'bottom' | 'all';

export const getEmployability = (params: {
  countries?: string[];
  sector?: string;
  occupation?: string;
  featured?: boolean;
  year?: number;
  view?: EmployabilityView;
  sortBy?: string;
  order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
} = {}) =>
  apiGet(
    '/employability',
    EmployabilityPageSchema,
    {
      country: params.countries,
      sector: params.sector,
      occupation: params.occupation,
      featured: params.featured,
      year: params.year,
      view: params.view,
      sort_by: params.sortBy,
      order: params.order,
      limit: params.limit,
      offset: params.offset,
    },
    60,
  );

export const getOccupationProfile = (code: string) =>
  apiGet(`/occupations/${encodeURIComponent(code)}`, OccupationProfileSchema, {}, 60);

export const getEmployabilityHistory = (occupation: string, countries?: string[]) =>
  apiGet(
    '/employability/history',
    z.array(EmployabilityHistorySchema),
    { occupation, country: countries },
    60,
  );
