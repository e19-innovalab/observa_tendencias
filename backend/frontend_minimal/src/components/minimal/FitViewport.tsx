'use client';

import { useLayoutEffect, useRef, type ReactNode } from 'react';

/**
 * Ocupa exactamente el alto que queda de la ventana debajo del encabezado (en pantallas grandes),
 * para que la página entre en una sola pantalla (si no alcanza, el contenido sigue debajo y se desplaza). Mide el encabezado real porque el menú puede
 * ocupar una o dos líneas.
 */
export function FitViewport({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fit = () => el.style.setProperty('--fit-h', `${window.innerHeight - (el.getBoundingClientRect().top + window.scrollY)}px`);
    fit();
    // el encabezado llega después (Suspense) y puede pasar a dos líneas: se vuelve a medir cuando cambia el body
    const ro = new ResizeObserver(fit);
    ro.observe(document.body);
    window.addEventListener('resize', fit);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', fit);
    };
  }, []);
  return (
    <div ref={ref} className={`lg:h-[var(--fit-h,calc(100dvh-57px))] ${className}`}>
      {children}
    </div>
  );
}
