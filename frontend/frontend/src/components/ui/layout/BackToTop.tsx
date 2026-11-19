'use client';

import { ArrowUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

/** Píxeles de scroll a partir de los cuales aparece el botón. */
const SHOW_AFTER = 240;

/**
 * Botón flotante para volver al inicio de la página.
 * Se monta en el layout raíz, así aparece en todas las páginas.
 * Arranca oculto y se muestra recién cuando la persona bajó en la página.
 */
export function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > SHOW_AFTER);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  function handleClick() {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  }

  return (
    <div
      aria-hidden={!visible}
      className={cn(
        'fixed right-5 bottom-5 z-40 print:hidden sm:right-6 sm:bottom-6',
        'transition-all duration-200',
        visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-3 opacity-0',
      )}
    >
      <button
        type="button"
        onClick={handleClick}
        tabIndex={visible ? 0 : -1}
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
