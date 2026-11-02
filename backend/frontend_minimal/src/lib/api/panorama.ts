import { z } from 'zod';
import {
  CompareResultSchema,
  CountrySchema,
  DashboardSummarySchema,
  IndicatorSchema,
  ObservationsPageSchema,
  ProjectionResultSchema,
  SectorSchema,
  TrendItemSchema,
} from '../schemas/api';
import { apiGet } from './client';

export const getCountries = () => apiGet('/countries', z.array(CountrySchema));
export const getSectors = () => apiGet('/sectors', z.array(SectorSchema));
export const getIndicators = () => apiGet('/indicators', z.array(IndicatorSchema));

export const getDashboardSummary = (country: string) =>
  apiGet('/dashboard/summary', DashboardSummarySchema, { country }, 60);

export const getObservations = (params: {
  indicator: string;
  countries: string[];
  sector?: string;
  fromYear?: string;
  toYear?: string;
}) =>
  apiGet(
    '/observations',
    ObservationsPageSchema,
    {
      indicator: params.indicator,
      country: params.countries,
      sector: params.sector,
      from_year: params.fromYear,
      to_year: params.toYear,
      data_type: 'observed',
      limit: 1000,
    },
    60,
  );

export const getCompare = (indicator: string, countries: string[], sector?: string) =>
  apiGet('/compare', CompareResultSchema, { indicator, countries, sector }, 300);

export const getTrends = (indicator: string, countries: string[], sector?: string) =>
  apiGet('/trends', z.array(TrendItemSchema), { indicator, country: countries, sector }, 300);

export const getProjections = (indicator: string, countries: string[], sector?: string, fromYear?: string, toYear?: string) =>
  apiGet('/projections', ProjectionResultSchema, { indicator, country: countries, sector, from_year: fromYear, to_year: toYear }, 300);
