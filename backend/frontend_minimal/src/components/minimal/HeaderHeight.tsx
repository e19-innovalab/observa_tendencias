'use client';

import { useEffect, useRef } from 'react';

/** Publica el alto real del encabezado fijo (una o dos líneas) en --header-h, para lo que se pega debajo. */
export function HeaderHeight() {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const header = ref.current?.closest('header');
    if (!header) return;
    const ro = new ResizeObserver(() => document.documentElement.style.setProperty('--header-h', `${header.offsetHeight}px`));
    ro.observe(header);
    return () => ro.disconnect();
  }, []);
  return <span ref={ref} hidden />;
}
