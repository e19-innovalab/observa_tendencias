import { ArrowDownRight, ArrowUpRight, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

export type KpiTone = 'positive' | 'negative' | 'warning' | 'neutral';

type Props = {
  label: string;
  value: string;
  caption?: string; // país y período del dato
  changeText: string | null;
  negative?: boolean;
  year?: string | number | null;
  codes?: string | null;
  tone?: KpiTone;
};

const BORDER: Record<KpiTone, string> = {
  positive: 'border-success/35',
  negative: 'border-danger/30',
  warning: 'border-warning/35',
  neutral: 'border-card-border',
};

const PILL: Record<KpiTone, string> = {
  positive: 'border-success/30 bg-success-soft text-success',
  negative: 'border-danger/25 bg-danger-soft text-danger',
  warning: 'border-warning/30 bg-warning-soft text-warning',
  neutral: 'border-card-border bg-surface-2 text-muted-text',
};

export function KpiCard({
  label,
  value,
  caption,
  changeText,
  negative = false,
  year,
  codes,
  tone,
}: Props) {
  const resolved: KpiTone = tone ?? (negative ? 'negative' : changeText ? 'positive' : 'neutral');
  const Icon = resolved === 'negative' ? ArrowDownRight : resolved === 'warning' ? TriangleAlert : ArrowUpRight;

  return (
    <article
      className={cn(
        'flex min-h-[88px] flex-col justify-between gap-2 rounded-xl border bg-canvas px-4 py-3.5',
        BORDER[resolved],
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10.5px] leading-snug font-bold tracking-[0.06em] text-label uppercase">
          {label}
        </p>
        {year && (
          <span className="shrink-0 rounded-md bg-slate-100 px-1.5 py-0.5 text-[10.5px] font-medium text-muted-text">
            {year}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="text-[26px] leading-none font-bold tracking-tight text-heading">{value}</p>
        {codes && (
          <span className="text-[10px] font-medium tracking-wide text-placeholder uppercase">{codes}</span>
        )}
        {changeText && (
          <span
            className={cn(
              'ml-auto inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-bold',
              PILL[resolved],
            )}
          >
            <Icon className="size-3" aria-hidden />
            {changeText}
          </span>
        )}
      </div>

      {caption && <p className="text-[11px] text-muted-text">{caption}</p>}
    </article>
  );
}
