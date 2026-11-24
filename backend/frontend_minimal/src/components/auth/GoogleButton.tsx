'use client';

import Script from 'next/script';
import { useRef, useState, useTransition } from 'react';
import { loginWithGoogle } from '@/lib/auth/actions';

type GoogleId = {
  initialize(options: { client_id: string; callback: (r: { credential: string }) => void }): void;
  renderButton(parent: HTMLElement, options: Record<string, string | number>): void;
};
declare global {
  interface Window { google?: { accounts: { id: GoogleId } } }
}

/** Botón oficial de Google (Google Identity Services): devuelve un token que valida el backend. */
export function GoogleButton({ clientId, next }: { clientId: string; next: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string>();
  const [pending, start] = useTransition();

  const render = () => {
    const id = window.google?.accounts.id;
    if (!id || !box.current) return;
    id.initialize({
      client_id: clientId,
      callback: ({ credential }) => start(async () => {
        setError(undefined);
        const res = await loginWithGoogle(credential, next);
        if (res?.error) setError(res.error);
      }),
    });
    id.renderButton(box.current, { theme: 'outline', size: 'large', text: 'continue_with', shape: 'rectangular', locale: 'es', width: Math.min(box.current.offsetWidth || 384, 400) });
  };

  return (
    <div className="space-y-2">
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={render} />
      <div ref={box} aria-busy={pending} className="flex min-h-10 w-full justify-center" />
      {error && (
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg px-3 py-2 text-sm text-alert-critical-text">
          {error}
        </p>
      )}
    </div>
  );
}
