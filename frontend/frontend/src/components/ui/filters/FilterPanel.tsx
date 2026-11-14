import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

/** Tarjeta blanca que agrupa los filtros de una vista. */
export function FilterPanel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-label="Filtros"
      className={cn(
        'rounded-xl border border-card-border bg-canvas p-4 shadow-[var(--shadow-card)] sm:px-6 sm:py-5',
        className,
      )}
    >
      {children}
    </section>
  );
}

export function FilterLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'shrink-0 text-[10.5px] font-bold tracking-[0.08em] text-label uppercase',
        className,
      )}
    >
      {children}
    </span>
  );
}

export function FilterRow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn('flex flex-wrap items-center gap-x-3 gap-y-2', className)}>{children}</div>;
}
