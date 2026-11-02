import { z } from 'zod';
import { LuditaCountrySchema, LuditaHistorySchema, LuditaPageSchema } from '../schemas/ludita';
import { apiGet } from './client';

export const getLudita = (params: {
  country?: string; sector?: string; occupation?: string; featured?: boolean; path?: string;
  year?: string; view?: string; limit?: number; offset?: number;
}) => apiGet('/ludita', LuditaPageSchema, params, 300);

export const getLuditaCountries = (country?: string) =>
  apiGet('/ludita/countries', z.array(LuditaCountrySchema), { country }, 300);

export const getLuditaHistory = () => apiGet('/ludita/history', LuditaHistorySchema, {}, 300);
