'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

/** Paginación por ?page= (1, 2, ...). */
export function Pager({ total, pageSize, label = 'registros' }: { total: number; pageSize: number; label?: string }) {
  const pathname = usePathname();
  const search = useSearchParams();
  const page = Math.max(1, Number(search.get('page') ?? '1') || 1);
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const href = (p: number) => {
    const params = new URLSearchParams(search.toString());
    if (p > 1) params.set('page', String(p));
    else params.delete('page');
    const qs = params.toString();
    return qs ? `${pathname}?${qs}` : pathname;
  };
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const btn = 'inline-flex size-8 items-center justify-center rounded-md border border-line text-sm focus-visible:outline-2 focus-visible:outline-focus';
  return (
    <nav aria-label="Paginación" className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-text">
      <span>
        Mostrando {from}–{to} de {total} {label}
      </span>
      {pages > 1 && (
        <span className="flex items-center gap-2">
          {page > 1 ? (
            <Link href={href(page - 1)} className={btn} aria-label="Anterior"><ChevronLeft className="size-4" aria-hidden /></Link>
          ) : (
            <span className={`${btn} opacity-40`} aria-hidden><ChevronLeft className="size-4" /></span>
          )}
          <span className="px-1">
            Página <strong className="text-heading">{page}</strong> de {pages}
          </span>
          {page < pages ? (
            <Link href={href(page + 1)} className={btn} aria-label="Siguiente"><ChevronRight className="size-4" aria-hidden /></Link>
          ) : (
            <span className={`${btn} opacity-40`} aria-hidden><ChevronRight className="size-4" /></span>
          )}
        </span>
      )}
    </nav>
  );
}
