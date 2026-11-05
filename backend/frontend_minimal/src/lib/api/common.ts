import { z } from 'zod';
import { AlertsPageSchema, CountrySchema, DashboardSummarySchema, SectorSchema } from '../schemas/api';
import { apiGet } from './client';

export const getCountries = () => apiGet('/countries', z.array(CountrySchema), {}, 3600);
export const getSectors = () => apiGet('/sectors', z.array(SectorSchema), {}, 3600);
export const getDashboardSummary = (country: string) =>
  apiGet('/dashboard/summary', DashboardSummarySchema, { country }, 300);
export const getAlerts = (params: { limit?: number; offset?: number; country?: string; severity?: string; type?: string }) =>
  apiGet('/alerts', AlertsPageSchema, params, 60);
