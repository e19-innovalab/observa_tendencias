'use client';

import { ArrowUp } from 'lucide-react';

/**
 * Botón flotante para volver al inicio de la página.
 * Se monta en el layout raíz, así aparece en todas las páginas.
 */
export function BackToTop() {
  function handleClick() {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  }

  return (
    <div className="fixed right-5 bottom-5 z-40 print:hidden sm:right-6 sm:bottom-6">
      <button
        type="button"
        onClick={handleClick}
        aria-label="Ir hacia arriba"
        className="group relative flex size-11 items-center justify-center rounded-full bg-brand text-white shadow-lg transition-colors hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus sm:size-12"
      >
        <ArrowUp className="size-5" aria-hidden />
        <span
          aria-hidden
          className="pointer-events-none absolute right-full mr-2.5 rounded-md bg-heading px-2.5 py-1 text-[11.5px] font-medium whitespace-nowrap text-white opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
        >
          Ir hacia arriba
        </span>
      </button>
    </div>
  );
}
