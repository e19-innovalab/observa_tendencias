import { Lock } from 'lucide-react';
import Link from 'next/link';

/** Lo que ve una cuenta gratuita en una sección del acceso completo. */
export function ProOnly() {
  return (
    <section className="mx-auto max-w-xl px-6 py-20 text-center">
      <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-slate-100 text-slate-600">
        <Lock className="size-5" aria-hidden />
      </span>
      <h1 className="mt-4 text-xl font-semibold text-slate-900">Esta sección es del acceso completo</h1>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">
        Con tu cuenta gratuita podés ver Inicio y Panorama. Para ver ocupaciones, sectores, habilidades
        y el resto de las secciones, y usar el asistente, pedile el acceso completo a un administrador
        del observatorio.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link href="/panorama" className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-hover">Ir a Panorama</Link>
        <Link href="/inicio" className="rounded-md border border-line px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Ir a Inicio</Link>
      </div>
    </section>
  );
}
