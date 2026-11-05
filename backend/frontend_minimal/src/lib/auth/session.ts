import 'server-only';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { cache } from 'react';
import { ApiError, apiGet } from '@/lib/api/client';
import { UserSchema, type User } from '@/lib/schemas/auth';

import { HOME_PATH, LOGIN_PATH, SESSION_COOKIE } from './constants';

export async function getToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/** Solo desde acciones del servidor o route handlers (los componentes no pueden escribir cookies). */
export async function setSession(token: string, expiresAt: string): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    expires: new Date(expiresAt),
  });
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

/**
 * Usuario de la sesión, verificado con el backend (GET /auth/me) una vez por request.
 * null sin sesión o con un token vencido, inválido o de una cuenta suspendida.
 */
export const getCurrentUser = cache(async (): Promise<User | null> => {
  const token = await getToken();
  if (!token) return null;
  try {
    return await apiGet('/auth/me', UserSchema, {}, 0, { token });
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
    throw e;
  }
});

export async function requireUser(): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect(LOGIN_PATH);
  return user;
}

/** Usuario con el permiso pedido; sin permiso vuelve a Inicio. */
export async function requirePermission(permission: string): Promise<User> {
  const user = await requireUser();
  if (!user.permissions.includes(permission)) redirect(`${HOME_PATH}?sin_permiso=1`);
  return user;
}
