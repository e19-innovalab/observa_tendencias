'use client';

import { useActionState, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { login, type LoginState } from '@/lib/auth/actions';

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState<LoginState, FormData>(login, {});
  const [ver, setVer] = useState(false);
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
        <div className="relative">
          <input
            id="password"
            name="password"
            type={ver ? 'text' : 'password'}
            autoComplete="current-password"
            required
            className="w-full rounded-md border border-line bg-white py-2.5 pr-11 pl-3 text-sm text-body focus-visible:outline-2 focus-visible:outline-focus [&::-ms-reveal]:hidden"
          />
          <button
            type="button"
            onClick={() => setVer(!ver)}
            aria-label={ver ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            title={ver ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            className="absolute top-1/2 right-2 flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-text hover:text-heading focus-visible:outline-2 focus-visible:outline-focus"
          >
            {ver ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
          </button>
        </div>
      </div>
      {state.error && (
        <p
          role="alert"
          className="rounded-md border border-alert-critical-border bg-alert-critical-bg px-3 py-2 text-sm text-alert-critical-text"
        >
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
