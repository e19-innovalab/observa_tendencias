import { z } from 'zod';
import { SisyphusCountrySchema, SisyphusPageSchema } from '../schemas/sisyphus';
import { apiGet } from './client';

export const getSisyphus = (params: { country?: string; year?: string } = {}) => apiGet('/sisyphus', SisyphusPageSchema, params, 300);

export const getSisyphusCountries = () => apiGet('/sisyphus/countries', z.array(SisyphusCountrySchema), {}, 300);
