'use client';

import { useEffect, useRef, type ReactNode } from 'react';

/**
 * En el teléfono la ficha queda debajo de la lista: al elegir una fila se la trae a la vista.
 * En pantallas grandes no hace nada (la columna está pegada al costado).
 */
export function RailFocus({ selection, children }: { selection: string | undefined; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!selection || !el || window.matchMedia('(min-width: 1024px)').matches) return;
    const box = el.getBoundingClientRect();
    if (box.top < 0 || box.top > window.innerHeight * 0.6) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [selection]);
  return <div ref={ref} className="scroll-mt-20">{children}</div>;
}
