import { z } from 'zod';
import { DatasetFileSchema, DatasetProfileSchema } from '../schemas/datasets';
import { apiGet } from './client';

export const getDatasetProfiles = () =>
  apiGet('/datasets/profiles', z.array(DatasetProfileSchema), {}, 3600);

export const getDatasets = (params: { profile?: string; origin?: string; limit: number }) =>
  apiGet('/datasets', z.array(DatasetFileSchema), params, 0);
