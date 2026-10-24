'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { API_URL } from '@/lib/api/client';

type SessionState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'authenticated'; email: string | null }
  | { status: 'error'; message: string };

type AuthResponse = {
  authenticated: boolean;
  user: { email: string | null };
};

const linkClassName =
  'rounded-md border border-blue-600 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-600';
const buttonClassName =
  'rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-wait disabled:opacity-60';

export function SessionControl() {
  const [session, setSession] = useState<SessionState>({ status: 'loading' });
  const [busy, setBusy] = useState(false);
  const [logoutError, setLogoutError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    async function loadSession() {
      try {
        const response = await fetch(`${API_URL}/api/v1/auth/me`, {
          credentials: 'include',
          cache: 'no-store',
          signal: controller.signal,
        });

        if (response.status === 401) {
          setSession({ status: 'anonymous' });
          return;
        }
        if (!response.ok) {
          throw new Error(`No se pudo consultar la sesión (HTTP ${response.status}).`);
        }

        const result = (await response.json()) as AuthResponse;
        if (!result.authenticated) {
          setSession({ status: 'anonymous' });
          return;
        }
        setSession({ status: 'authenticated', email: result.user.email });
      } catch (cause) {
        if (controller.signal.aborted) return;
        setSession({
          status: 'error',
          message: cause instanceof Error ? cause.message : 'No se pudo consultar la sesión.',
        });
      }
    }

    void loadSession();
    return () => controller.abort();
  }, []);

  async function signOut() {
    setBusy(true);
    setLogoutError('');

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`No se pudo cerrar la sesión (HTTP ${response.status}).`);
      }
      setSession({ status: 'anonymous' });
    } catch (cause) {
      setLogoutError(cause instanceof Error ? cause.message : 'No se pudo cerrar la sesión.');
    } finally {
      setBusy(false);
    }
  }

  if (session.status === 'loading') {
    return <p className="text-sm text-gray-600" role="status">Verificando sesión…</p>;
  }

  if (session.status === 'authenticated') {
    return (
      <div className="flex flex-wrap items-center justify-end gap-3">
        <p className="text-sm text-gray-700">
          Sesión activa: <strong>{session.email ?? 'Usuario'}</strong>
        </p>
        <button className={buttonClassName} type="button" disabled={busy} onClick={signOut}>
          {busy ? 'Cerrando sesión…' : 'Cerrar sesión'}
        </button>
        {logoutError && (
          <p className="basis-full text-right text-sm text-red-700" role="alert">
            {logoutError}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      <Link href="/auth" className={linkClassName}>
        Iniciar sesión (opcional)
      </Link>
      {session.status === 'error' && (
        <p className="basis-full text-right text-sm text-red-700" role="alert">
          {session.message}
        </p>
      )}
    </div>
  );
}
