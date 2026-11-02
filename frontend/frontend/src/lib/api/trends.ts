import { z } from 'zod';
import { ProjectionResultSchema, TrendItemSchema } from '../schemas/api';
import { apiGet } from './client';

export const getTrends = (params: {
  indicator?: string;
  domain?: string;
  countries?: string[];
  sector?: string;
  occupation?: string;
  fromYear?: string;
  toYear?: string;
  state?: string;
} = {}) =>
  apiGet(
    '/trends',
    z.array(TrendItemSchema),
    {
      indicator: params.indicator,
      domain: params.domain,
      country: params.countries,
      sector: params.sector,
      occupation: params.occupation,
      from_year: params.fromYear,
      to_year: params.toYear,
      state: params.state,
    },
    60,
  );

export const getProjections = (params: {
  indicator: string;
  countries?: string[];
  sector?: string;
  occupation?: string;
  fromYear?: string;
  toYear?: string;
}) =>
  apiGet(
    '/projections',
    ProjectionResultSchema,
    {
      indicator: params.indicator,
      country: params.countries,
      sector: params.sector,
      occupation: params.occupation,
      from_year: params.fromYear,
      to_year: params.toYear,
    },
    60,
  );
