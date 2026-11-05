'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { PublicHeader } from '@/components/ui/layout/PublicHeader';

const campo =
  'h-12 w-full rounded-md border-b border-line bg-surface-2 px-4 text-base text-body placeholder:text-placeholder focus-visible:outline-2 focus-visible:outline-focus';

function Google() {
  return (
    <svg viewBox="0 0 48 48" className="size-5" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

export default function LoginPage() {
  const [ver, setVer] = useState(false);

  return (
    <>
      <PublicHeader />
      <main className="grid flex-1 lg:grid-cols-2">
        <div className="flex items-center justify-center px-4 py-16 sm:px-6">
          <div className="w-full max-w-sm space-y-8">
            <h1 className="text-4xl font-bold tracking-tight text-heading">Iniciar sesión</h1>

            <form onSubmit={(e) => e.preventDefault()} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm text-body">
                  Correo electrónico
                </label>
                <input id="email" type="email" autoComplete="email" placeholder="nombre@correo.com" className={campo} />
              </div>

              <div className="space-y-2">
                <label htmlFor="pass" className="text-sm text-body">
                  Contraseña
                </label>
                <div className="relative">
                  <input
                    id="pass"
                    type={ver ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Tu contraseña"
                    className={`${campo} pr-12`}
                  />
                  <button
                    type="button"
                    onClick={() => setVer(!ver)}
                    aria-label={ver ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded text-muted-text focus-visible:outline-2 focus-visible:outline-focus"
                  >
                    {ver ? <EyeOff className="size-5" aria-hidden /> : <Eye className="size-5" aria-hidden />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between gap-4 text-sm text-body">
                <label className="flex items-center gap-2">
                  <input type="checkbox" className="size-4 accent-brand" />
                  Recordar contraseña
                </label>
                <Link href="#" className="text-link hover:text-link-hover">
                  ¿Olvidaste tu contraseña?
                </Link>
              </div>

              <button
                type="submit"
                className="h-12 w-full rounded-md bg-brand font-medium tracking-wide text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              >
                Iniciar sesión
              </button>
            </form>

            <button
              type="button"
              className="flex h-12 w-full items-center justify-center gap-3 rounded-md border-2 border-brand font-medium tracking-wide text-brand hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              <Google />
              Iniciar sesión con Google
              <ArrowRight className="size-5" aria-hidden />
            </button>

            <hr className="border-line" />

            <p className="text-sm text-body">
              ¿No tienes una cuenta?{' '}
              <Link href="#" className="text-link hover:text-link-hover">
                Crear cuenta
              </Link>
            </p>
          </div>
        </div>

        <div className="hidden items-center justify-center bg-surface-2 p-12 lg:flex">
          <div className="max-w-md space-y-6 rounded-xl bg-heading p-12 text-white">
            <h2 className="text-xl font-bold">¿Aún no estás registrado?</h2>
            <p className="text-white/90">Creá tu cuenta para guardar tus consultas y usar todas las herramientas del observatorio.</p>
            <ul className="list-disc space-y-4 pl-5 text-white/90">
              <li>Guardá tus filtros y vistas favoritas.</li>
              <li>Recibí alertas cuando cambie un indicador.</li>
              <li>Descargá los datos con su fuente y fecha.</li>
            </ul>
          </div>
        </div>
      </main>
    </>
  );
}
