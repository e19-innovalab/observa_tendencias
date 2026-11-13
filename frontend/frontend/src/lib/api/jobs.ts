import { JobsPageSchema, JobsSummarySchema } from '../schemas/api';
import { apiGet } from './client';

/** Ofertas de LinkedIn (recolección con Apify): no es una fuente oficial. */
export const getJobsSummary = (country?: string) =>
  apiGet('/jobs/summary', JobsSummarySchema, { country }, 300);

export const getJobs = (params: {
  country?: string;
  provincia?: string;
  sector?: string;
  q?: string;
  limit: number;
  offset: number;
}) => apiGet('/jobs', JobsPageSchema, params, 300);
