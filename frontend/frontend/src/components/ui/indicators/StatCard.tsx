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
        'flex min-h-[120px] flex-col justify-between gap-3 rounded-xl border border-card-border bg-canvas px-4 py-4',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10.5px] leading-snug font-bold tracking-[0.06em] text-label uppercase">{label}</p>
        {badge}
      </div>

      <div>
        <p className={cn('text-[23px] leading-tight font-bold tracking-tight text-heading', valueClassName)}>
          {value}
          {unit && <span className="ml-1 text-[13px] font-medium text-muted-text">{unit}</span>}
        </p>
        {hint && <p className="mt-1 text-[11.5px] leading-relaxed text-muted-text">{hint}</p>}
      </div>

      {action}
    </article>
  );
}
