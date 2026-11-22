'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { INDEX_PATHS } from '@/components/ui/layout/MainNav';

const TIEMPO_REAL = [{ href: '/pulso', label: 'Pulso laboral' }];

const INDICADORES = [
  { href: '/moctezuma', label: 'Moctezuma' },
  { href: '/ludita', label: 'Ludita' },
  { href: '/reina-roja', label: 'Reina Roja' },
  { href: '/sisifo', label: 'Sísifo' },
];

function Grupo({ titulo, items, pathname }: { titulo: string; items: { href: string; label: string }[]; pathname: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-6">
      <span className="text-[11px] font-semibold tracking-[0.12em] text-muted-text uppercase">{titulo}</span>
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              '-mb-px border-b-2 py-3 text-[13px] whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
              active ? 'border-brand font-semibold text-heading' : 'border-transparent text-muted-text hover:text-heading',
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

function Pestanias() {
  const pathname = usePathname();
  const enIndices = INDEX_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  if (!enIndices) return null;

  return (
    <nav aria-label="Indicadores experimentales" className="border-b border-card-border bg-canvas">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-10 px-4 sm:px-6">
        <Grupo titulo="Tiempo real" items={TIEMPO_REAL} pathname={pathname} />
        <Grupo titulo="Indicadores" items={INDICADORES} pathname={pathname} />
      </div>
    </nav>
  );
}

export function ExperimentalTabs() {
  return (
    <Suspense fallback={null}>
      <Pestanias />
    </Suspense>
  );
}
