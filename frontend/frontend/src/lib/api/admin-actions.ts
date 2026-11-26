'use server';

import { revalidatePath } from 'next/cache';
import { commitDataset, uploadDataset } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { getCurrentUser, getToken } from '@/lib/auth/session';
import { PERMISSIONS } from '@/lib/schemas/auth';
import type { DatasetFile, DatasetUploadResult } from '@/lib/schemas/datasets';

const PATH = '/admin/datos';
const NO_SESSION = 'Iniciá sesión para continuar.';
const NO_PERMISSION = 'Tu rol no tiene permiso para cargar datos.';

export type UploadState = {
  status: 'idle' | 'error' | 'ok';
  error?: string;
  result?: DatasetUploadResult;
};

export type CommitState = {
  status: 'idle' | 'error' | 'ok';
  error?: string;
  dataset?: DatasetFile;
};

/** La sesión se vuelve a revisar en cada acción: las Server Actions son alcanzables por POST. */
async function session(): Promise<{ token: string } | { error: string }> {
  const user = await getCurrentUser();
  if (!user) return { error: NO_SESSION };
  if (!user.permissions.includes(PERMISSIONS.manageData)) return { error: NO_PERMISSION };
  const token = await getToken();
  return token ? { token } : { error: NO_SESSION };
}

export async function uploadDatasetAction(
  _prev: UploadState,
  formData: FormData,
): Promise<UploadState> {
  const auth = await session();
  if ('error' in auth) return { status: 'error', error: auth.error };

  const file = formData.get('file');
  const profile = String(formData.get('profile') ?? '').trim();
  if (!profile) return { status: 'error', error: 'Elegí el formato del archivo.' };
  if (!(file instanceof File) || file.size === 0) {
    return { status: 'error', error: 'Elegí un archivo .xlsx o .csv.' };
  }

  const body = new FormData();
  body.set('file', file);
  body.set('profile', profile);
  for (const key of ['declared_source_name', 'declared_source_url', 'reference_date'] as const) {
    const value = String(formData.get(key) ?? '').trim();
    if (value) body.set(key, value);
  }

  try {
    const result = await uploadDataset(body, auth.token);
    revalidatePath(PATH);
    return { status: 'ok', result };
  } catch (e) {
    return {
      status: 'error',
      error: e instanceof ApiError ? e.message : 'No se pudo subir el archivo.',
    };
  }
}

export async function commitDatasetAction(
  _prev: CommitState,
  formData: FormData,
): Promise<CommitState> {
  const auth = await session();
  if ('error' in auth) return { status: 'error', error: auth.error };

  const datasetId = Number(formData.get('dataset_id'));
  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    return { status: 'error', error: 'No se encontró el archivo a cargar.' };
  }

  try {
    const dataset = await commitDataset(
      datasetId,
      formData.get('confirm_overlap') === 'on',
      auth.token,
    );
    revalidatePath(PATH);
    return { status: 'ok', dataset };
  } catch (e) {
    return {
      status: 'error',
      error: e instanceof ApiError ? e.message : 'No se pudo cargar el archivo.',
    };
  }
}
