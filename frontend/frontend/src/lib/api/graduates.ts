import { z } from 'zod';
import { GraduateProjectionItemSchema, GraduateTrendsSchema } from '../schemas/api';
import { apiGet } from './client';

export const getGraduateTrends = (params: { countries?: string[]; tendencia?: string } = {}) =>
  apiGet(
    '/graduates/trends',
    GraduateTrendsSchema,
    { country: params.countries, tendencia: params.tendencia },
    300,
  );

export const getGraduateProjections = (params: { countries?: string[]; nombre?: string } = {}) =>
  apiGet(
    '/graduates/projections',
    z.array(GraduateProjectionItemSchema),
    { country: params.countries, nombre: params.nombre },
    300,
  );
