'use server';

import { revalidatePath } from 'next/cache';
import { ApiError, apiSend, apiUpload } from '@/lib/api/client';
import { getToken } from '@/lib/auth/session';
import { UserSchema } from '@/lib/schemas/auth';
import { DatasetFileSchema, DatasetUploadResultSchema, type DatasetFile, type DatasetUploadResult } from '@/lib/schemas/datasets';

export type FormState = { ok?: boolean; error?: string; message?: string };

const text = (form: FormData, key: string) => {
  const v = String(form.get(key) ?? '').trim();
  return v === '' ? null : v;
};
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

/* ---------- Usuarios ---------- */
export async function createUser(_prev: FormState, form: FormData): Promise<FormState> {
  try {
    const user = await apiSend('POST', '/users', UserSchema, {
      email: text(form, 'email'),
      full_name: text(form, 'full_name'),
      password: String(form.get('password') ?? ''),
      role: text(form, 'role'),
      sector_code: text(form, 'sector_code'),
      countries: form.getAll('countries').map(String),
    }, { token: await getToken() });
    revalidatePath('/admin/usuarios');
    return { ok: true, message: `Cuenta creada para ${user?.email}.` };
  } catch (e) {
    return { error: errorText(e, 'No se pudo crear la cuenta.') };
  }
}

export async function updateUser(userId: number, _prev: FormState, form: FormData): Promise<FormState> {
  const body: Record<string, unknown> = {
    full_name: text(form, 'full_name'),
    role: text(form, 'role'),
    sector_code: text(form, 'sector_code') ?? '',
    countries: form.getAll('countries').map(String),
    status: text(form, 'status'),
  };
  const password = String(form.get('password') ?? '');
  if (password) body.password = password;
  try {
    await apiSend('PATCH', `/users/${userId}`, UserSchema, body, { token: await getToken() });
    revalidatePath('/admin/usuarios');
    return { ok: true, message: 'Cambios guardados.' };
  } catch (e) {
    return { error: errorText(e, 'No se pudieron guardar los cambios.') };
  }
}

export async function setUserStatus(userId: number, status: string): Promise<void> {
  await apiSend('PATCH', `/users/${userId}`, UserSchema, { status }, { token: await getToken() });
  revalidatePath('/admin/usuarios');
}

/* ---------- Carga de datos ---------- */
export type UploadState = { error?: string; result?: DatasetUploadResult; committed?: DatasetFile };

export async function uploadDataset(_prev: UploadState, form: FormData): Promise<UploadState> {
  const file = form.get('file');
  if (!(file instanceof File) || file.size === 0) return { error: 'Elegí un archivo .csv o .xlsx.' };
  const body = new FormData();
  body.set('file', file);
  for (const key of ['profile', 'declared_source_name', 'declared_source_url', 'reference_date']) {
    const v = text(form, key);
    if (v) body.set(key, v);
  }
  try {
    const result = await apiUpload('/datasets/upload', DatasetUploadResultSchema, body, { token: await getToken() });
    revalidatePath('/admin/datos');
    return { result };
  } catch (e) {
    return { error: errorText(e, 'No se pudo subir el archivo.') };
  }
}

/** confirmOverlap: el archivo repite valores oficiales y la persona acepta cargarlos como fuente aparte. */
export async function commitDataset(prev: UploadState, confirmOverlap = false): Promise<UploadState> {
  if (!prev.result) return prev;
  try {
    const committed = await apiSend('POST', `/datasets/${prev.result.dataset_id}/commit`, DatasetFileSchema, { confirm_overlap: confirmOverlap }, { token: await getToken() });
    revalidatePath('/', 'layout');
    return { ...prev, committed: committed ?? undefined };
  } catch (e) {
    return { ...prev, error: errorText(e, 'No se pudo cargar el archivo.') };
  }
}
