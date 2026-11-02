import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  baseHref: string;
};

function hrefFor(baseHref: string, page: number) {
  const separator = baseHref.includes('?') ? '&' : '?';
  return `${baseHref}${separator}page=${page}`;
}

function pageNumbers(page: number, totalPages: number) {
  if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1);

  const pages = new Set([1, totalPages, page - 1, page, page + 1]);
  const sorted = [...pages].filter((p) => p > 0 && p <= totalPages).sort((a, b) => a - b);

  const result: (number | '…')[] = [];
  for (const p of sorted) {
    const previous = result[result.length - 1];
    if (typeof previous === 'number' && p - previous > 1) result.push('…');
    result.push(p);
  }
  return result;
}

/** Paginación simple con links que conservan la query actual. */
export function Pagination({ page, totalPages, total, pageSize, baseHref }: Props) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
      <p className="text-muted-text">
        Mostrando {from} a {to} de {total} registros
      </p>

      <nav aria-label="Paginación" className="flex items-center gap-1">
        <Link
          href={hrefFor(baseHref, Math.max(1, page - 1))}
          aria-disabled={page === 1}
          className={cn(
            'inline-flex size-9 items-center justify-center rounded-md border border-line text-body hover:bg-surface-alt',
            page === 1 && 'pointer-events-none opacity-40',
          )}
        >
          <ChevronLeft className="size-4" aria-hidden />
          <span className="sr-only">Anterior</span>
        </Link>

        {pageNumbers(page, totalPages).map((item, index) =>
          item === '…' ? (
            <span key={`ellipsis-${index}`} className="px-2 text-muted-text">
              …
            </span>
          ) : (
            <Link
              key={item}
              href={hrefFor(baseHref, item)}
              aria-current={item === page ? 'page' : undefined}
              className={cn(
                'inline-flex size-9 items-center justify-center rounded-md border text-sm font-medium',
                item === page
                  ? 'border-heading bg-heading text-white'
                  : 'border-line text-body hover:bg-surface-alt',
              )}
            >
              {item}
            </Link>
          ),
        )}

        <Link
          href={hrefFor(baseHref, Math.min(totalPages, page + 1))}
          aria-disabled={page === totalPages}
          className={cn(
            'inline-flex h-9 items-center gap-1 rounded-md border border-line px-3 text-body hover:bg-surface-alt',
            page === totalPages && 'pointer-events-none opacity-40',
          )}
        >
          Siguiente
          <ChevronRight className="size-4" aria-hidden />
        </Link>
      </nav>
    </div>
  );
}
