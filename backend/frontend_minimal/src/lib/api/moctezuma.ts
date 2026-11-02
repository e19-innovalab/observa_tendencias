import { z } from 'zod';
import { MoctezumaCountrySchema, MoctezumaPageSchema, MoctezumaReferenceSchema } from '../schemas/moctezuma';
import { apiGet } from './client';

export const getMoctezuma = (params: {
  country?: string; sector?: string; occupation?: string; featured?: boolean; year?: string;
  view?: string; limit?: number; offset?: number;
}) => apiGet('/moctezuma', MoctezumaPageSchema, params, 300);

export const getMoctezumaCountries = (country?: string) =>
  apiGet('/moctezuma/countries', z.array(MoctezumaCountrySchema), { country }, 300);

export const getMoctezumaReference = () => apiGet('/moctezuma/reference', MoctezumaReferenceSchema, {}, 300);
