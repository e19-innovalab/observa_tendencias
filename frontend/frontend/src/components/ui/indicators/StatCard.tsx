import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Props = {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  badge?: ReactNode;
  action?: ReactNode;
  valueClassName?: string;
  className?: string;
};

/** Tarjeta de indicador flexible para las pantallas maquetadas desde Figma. */
export function StatCard({
  label,
  value,
  unit,
  hint,
  badge,
  action,
  valueClassName,
  className,
}: Props) {
  return (
    <article
      className={cn(
        'flex min-h-36 flex-col justify-between gap-3 rounded-lg border border-line bg-canvas p-5 shadow-[0_1px_2px_var(--shadow-color)]',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold tracking-wide text-muted-text uppercase">{label}</p>
        {badge}
      </div>

      <div>
        <p className={cn('text-2xl font-semibold text-heading', valueClassName)}>
          {value}
          {unit && <span className="ml-1 text-sm font-normal text-muted-text">{unit}</span>}
        </p>
        {hint && <p className="mt-1 text-xs leading-relaxed text-muted-text">{hint}</p>}
      </div>

      {action}
    </article>
  );
}
