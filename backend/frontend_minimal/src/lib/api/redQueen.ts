import { z } from 'zod';
import { CareerOptionSchema, RedQueenPageSchema, RedQueenParamsSchema, RedQueenYearSchema } from '../schemas/redQueen';
import { getMethodologies } from './methodologies';
import { apiGet } from './client';

export const getRedQueen = (params: { occupation?: string; featured?: boolean; year?: string; view?: string; limit?: number; country?: string; career?: string }) =>
  apiGet('/red-queen', RedQueenPageSchema, params, 300);

export const getRedQueenYears = () => apiGet('/red-queen/years', z.array(RedQueenYearSchema), {}, 300);

/** Parámetros de la versión vigente de la metodología. */
export async function getRedQueenParams() {
  const items = await getMethodologies('red_queen_index');
  const current = items.find((m) => m.is_current) ?? items[items.length - 1];
  return RedQueenParamsSchema.parse(current?.params);
}

export const getRedQueenCareers = (country: string) => apiGet('/red-queen/careers', z.array(CareerOptionSchema), { country }, 300);
