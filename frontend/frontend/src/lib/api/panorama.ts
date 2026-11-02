import { z } from 'zod';
import {
  CountrySchema,
  DashboardSummarySchema,
  IndicatorSchema,
  ObservationsPageSchema,
  SectorSchema,
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
