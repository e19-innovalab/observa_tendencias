import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatNumber, formatScore } from '@/lib/utils/format';

export type ScoreSegment = { label: string; value: number; color: string };

type Props = {
  score: number | null;
  levelLabel?: string | null;
  coverage?: { active: number; total: number };
  segments: ScoreSegment[];
  className?: string;
};

/** Tarjeta blanca de puntaje que acompaña al héroe azul del detalle. */
export function ScoreHeroCard({ score, levelLabel, coverage, segments, className }: Props) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const coverageRatio =
    coverage && coverage.total > 0 ? Math.round((coverage.active / coverage.total) * 100) : null;

  return (
    <section
      aria-label="Resumen del puntaje ISE"
      className={cn(
        'rounded-2xl border border-white/60 bg-canvas px-5 py-5 text-body shadow-[0_18px_45px_-24px_rgb(15_23_42_/_0.55)]',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
          Puntaje ISE global
        </p>
        {levelLabel && (
          <Badge tone={score === null ? 'neutral' : 'brand'}>{levelLabel}</Badge>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-[44px] leading-none font-bold tracking-tight text-heading">
          {formatScore(score)}
        </span>
        <span className="text-[13px] font-normal text-muted-text">/ 100</span>
      </div>

      {coverage && (
        <div className="mt-4 text-[11.5px] text-muted-text">
          <div className="flex items-center justify-between gap-3">
            <span>Cobertura de dimensiones</span>
            <span className="font-semibold text-heading">
              {coverageRatio === null ? '—' : `${coverageRatio}%`}{' '}
              <span className="font-normal text-muted-text">
                ({coverage.active}/{coverage.total} activas)
              </span>
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
            {coverageRatio !== null && (
              <div
                className="h-full rounded-full bg-heading"
                style={{ width: `${coverageRatio}%` }}
                aria-hidden
              />
            )}
          </div>
        </div>
      )}

      {segments.length > 0 && (
        <>
          <div
            className="mt-4 flex h-2.5 overflow-hidden rounded-full bg-surface-2"
            role="img"
            aria-label="Aporte de cada dimensión al puntaje ISE"
          >
            {segments.map((segment) => (
              <div
                key={segment.label}
                title={`${segment.label}: ${formatNumber(segment.value, 1)} pts`}
                style={{
                  width: total > 0 ? `${(segment.value / total) * 100}%` : '0%',
                  backgroundColor: segment.color,
                }}
              />
            ))}
          </div>

          <ul className="mt-3 space-y-1.5">
            {segments.map((segment) => (
              <li key={segment.label} className="flex items-center gap-2 text-[11.5px]">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: segment.color }}
                  aria-hidden
                />
                <span className="min-w-0 truncate text-body">{segment.label}</span>
                <span className="ml-auto font-semibold text-heading">
                  {formatNumber(segment.value, 1)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
