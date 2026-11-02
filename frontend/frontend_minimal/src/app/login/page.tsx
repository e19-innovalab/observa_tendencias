import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { Suspense } from 'react';
import { LoginForm } from '@/components/auth/LoginForm';
import { Logo } from '@/components/brand/Logo';
import { safeNext } from '@/lib/auth/constants';
import { getCurrentUser } from '@/lib/auth/session';

export const metadata: Metadata = { title: 'Ingresar' };

/** Lee la URL y la sesión: va dentro de un Suspense. */
async function LoginGate({ searchParams }: { searchParams: PageProps<'/login'>['searchParams'] }) {
  const next = safeNext((await searchParams).next);
  if (await getCurrentUser()) redirect(next);
  return <LoginForm next={next} />;
}

export default function LoginPage({ searchParams }: PageProps<'/login'>) {
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section
        className="hidden flex-col justify-between p-12 text-white lg:flex"
        style={{ backgroundImage: 'var(--gradient-hero)' }}
      >
        <Logo inverted />
        <div className="max-w-md space-y-4">
          <h1 className="text-3xl font-semibold leading-tight">
            Datos oficiales para entender el mercado laboral del Cono Sur.
          </h1>
          <p className="text-blue-50">
            Indicadores, ocupaciones, habilidades y proyecciones de Argentina, Chile y Uruguay, con
            la fuente y la fecha de cada dato.
          </p>
        </div>
        <p className="text-sm text-blue-100">Observatorio de tendencias · InnovaLab</p>
      </section>
      <section className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden">
            <Logo />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-heading">Ingresar al observatorio</h2>
            <p className="text-sm text-muted-text">Usá la cuenta que te dio tu institución.</p>
          </div>
          <Suspense fallback={<div className="h-72 animate-pulse rounded-md bg-surface-2" aria-hidden />}>
            <LoginGate searchParams={searchParams} />
          </Suspense>
        </div>
      </section>
    </main>
  );
}
