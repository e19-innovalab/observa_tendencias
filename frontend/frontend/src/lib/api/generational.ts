import { GenerationalGapSchema } from '../schemas/generational';
import { apiGet } from './client';

export const getGenerationalGap = () => apiGet('/generational-gap', GenerationalGapSchema, {}, 300);
