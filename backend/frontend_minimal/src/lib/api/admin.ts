import 'server-only';
import { z } from 'zod';
import { getToken } from '@/lib/auth/session';
import { AuthOptionsSchema, UsersPageSchema } from '../schemas/auth';
import { DatasetFileSchema, DatasetProfileSchema } from '../schemas/datasets';
import { apiGet } from './client';

export async function getUsers(params: { q?: string; role?: string; sector?: string; status?: string; limit: number; offset: number }) {
  return apiGet('/users', UsersPageSchema, params, 0, { token: await getToken() });
}

export async function getUserOptions() {
  return apiGet('/users/options', AuthOptionsSchema, {}, 0, { token: await getToken() });
}

export const getDatasetProfiles = () => apiGet('/datasets/profiles', z.array(DatasetProfileSchema), {}, 3600);

export async function getDatasets(params: { profile?: string; origin?: string; limit: number }) {
  return apiGet('/datasets', z.array(DatasetFileSchema), params, 0, { token: await getToken() });
}
