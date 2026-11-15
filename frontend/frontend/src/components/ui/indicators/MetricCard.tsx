import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Props = {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  badge?: ReactNode;
  /** Pastilla inferior izquierda (variación, nivel de riesgo, etc.). */
  chip?: ReactNode;
  /** Información secundaria alineada a la derecha. */
  meta?: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  valueClassName?: string;
  className?: string;
};

/** Tarjeta de indicador con jerarquía valor → contexto → acción. */
export function MetricCard({
  label,
  value,
  unit,
  badge,
  chip,
  meta,
  hint,
  action,
  valueClassName,
  className,
}: Props) {
  return (
    <article
      className={cn(
        'flex min-h-[132px] flex-col rounded-xl border border-card-border bg-canvas px-4 py-4',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10.5px] leading-snug font-bold tracking-[0.07em] text-label uppercase">
          {label}
        </p>
        {badge}
      </div>

      <div className="mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <p
          className={cn(
            'text-[28px] leading-none font-bold tracking-tight text-heading',
            valueClassName,
          )}
        >
          {value}
        </p>
        {unit && <span className="text-[12px] font-medium text-muted-text">{unit}</span>}
      </div>

      {hint && <div className="mt-2 text-[11.5px] leading-relaxed text-muted-text">{hint}</div>}

      {(chip || meta) && (
        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-2 pt-4">
          {chip}
          {meta && <span className="ml-auto text-[10.5px] text-muted-text">{meta}</span>}
        </div>
      )}

      {action && <div className="mt-3 border-t border-card-border pt-3">{action}</div>}
    </article>
  );
}
