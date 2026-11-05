'use client';

import { useActionState } from 'react';
import { login, type LoginState } from '@/lib/auth/actions';

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState<LoginState, FormData>(login, {});
  return (
    <form action={action} className="space-y-5" noValidate>
      <input type="hidden" name="next" value={next} />
      <div className="space-y-1.5">
        <label htmlFor="email" className="block text-sm font-medium text-heading">
          Correo electrónico
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          defaultValue={state.email}
          className="w-full rounded-md border border-line bg-white px-3 py-2.5 text-sm text-body placeholder:text-placeholder focus-visible:outline-2 focus-visible:outline-focus"
          placeholder="nombre@institucion.org"
        />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="password" className="block text-sm font-medium text-heading">
          Contraseña
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="w-full rounded-md border border-line bg-white px-3 py-2.5 text-sm text-body focus-visible:outline-2 focus-visible:outline-focus"
        />
      </div>
      {state.error && (
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg px-3 py-2 text-sm text-alert-critical-text">
          {state.error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:opacity-60"
      >
        {pending ? 'Ingresando…' : 'Ingresar'}
      </button>
      <p className="text-xs text-muted-text">
        Las cuentas las crea un administrador del observatorio. Si no tenés acceso o olvidaste tu
        contraseña, escribile a quien administra tu institución.
      </p>
    </form>
  );
}
