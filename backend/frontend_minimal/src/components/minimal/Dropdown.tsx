'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, useRef, type ReactNode } from 'react';

/**
 * Menú desplegable (<details>) que se cierra solo: al navegar (la página no se recarga entera,
 * así que sin esto quedaría abierto), al hacer clic afuera, con Esc y al elegir una opción.
 */
export function Dropdown({ summary, summaryClassName, className = 'relative', children }: {
  summary: ReactNode;
  summaryClassName: string;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();
  const search = useSearchParams();

  useEffect(() => {
    if (ref.current) ref.current.open = false;
  }, [pathname, search]);

  useEffect(() => {
    const close = (e: MouseEvent | KeyboardEvent) => {
      const el = ref.current;
      if (!el?.open) return;
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !el.contains(e.target as Node)) el.open = false;
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, []);

  return (
    <details ref={ref} className={`group ${className}`}>
      <summary className={`list-none [&::-webkit-details-marker]:hidden ${summaryClassName}`}>{summary}</summary>
      {/* elegir un enlace también cierra (aunque lleve a la misma URL) */}
      <div onClick={(e) => { if ((e.target as HTMLElement).closest('a')) ref.current?.removeAttribute('open'); }}>{children}</div>
    </details>
  );
}
