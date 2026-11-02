'use server';

import { redirect } from 'next/navigation';
import { ApiError, apiSend } from '@/lib/api/client';
import { LoginResponseSchema } from '@/lib/schemas/auth';
import { LOGIN_PATH, safeNext } from './constants';
import { clearSession, setSession } from './session';

export type LoginState = { error?: string; email?: string };

export async function login(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const email = String(formData.get('email') ?? '').trim();
  const password = String(formData.get('password') ?? '');
  const next = safeNext(formData.get('next'));
  if (!email || !password) return { error: 'Ingresá tu correo y tu contraseña.', email };
  try {
    const res = await apiSend('POST', '/auth/login', LoginResponseSchema, { email, password });
    if (res) await setSession(res.access_token, res.expires_at);
  } catch (e) {
    return { error: e instanceof ApiError ? e.message : 'No se pudo iniciar sesión.', email };
  }
  redirect(next);
}

export async function logout(): Promise<void> {
  await clearSession();
  redirect(LOGIN_PATH);
}
