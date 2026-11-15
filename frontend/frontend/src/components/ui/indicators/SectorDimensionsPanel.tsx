import Link from 'next/link';
import {
  BarChart3,
  BrainCircuit,
  Percent,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { DIMENSION_COLORS } from '@/lib/constants';
import type { DimensionRange } from '@/lib/schemas/api';
import { cn } from '@/lib/utils';
import { formatIndex01, formatNumber, formatUsd } from '@/lib/utils/format';

const ICONS: Record<string, LucideIcon> = {
  net_demand: BarChart3,
  salary_ppp: Wallet,
  insertion_rate: Percent,
  automation_risk: BrainCircuit,
};

type Props = {
  ranges: DimensionRange[];
  dimensions: Record<string, number | null>;
  salaryAverage?: number | null;
  automationAverage?: number | null;
  title: string;
  description?: string;
  referenceYear?: number | null;
  noSourceNote?: string | null;
  methodologyHref?: string;
  /** Destino del botón de desglose (la ocupación líder, si existe). */
  breakdownHref?: string;
};

/** Tarjeta grande con el ISE desagregado por dimensión para un sector. */
export function SectorDimensionsPanel({
  ranges,
  dimensions,
  salaryAverage,
  automationAverage,
  title,
  description,
  referenceYear,
  noSourceNote,
  methodologyHref = '/metodologia/ise',
  breakdownHref = '/ocupaciones',
}: Props) {
  return (
    <section className="overflow-hidden rounded-xl border border-card-border bg-canvas shadow-[var(--shadow-card)]">
      <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5 pb-4">
        <div>
          <h2 className="flex items-center gap-2 text-[18px] leading-tight font-semibold text-heading">
            <BarChart3 className="size-5 text-brand" aria-hidden />
            {title}
          </h2>
          {description && (
            <p className="mt-1 max-w-3xl text-[12.5px] leading-relaxed text-muted-text">
              {description}
            </p>
          )}
        </div>
        <Link
          href={breakdownHref}
          className="inline-flex items-center rounded-lg border border-card-border bg-canvas px-3 py-1.5 text-[12px] font-semibold text-link transition-colors hover:bg-surface-alt hover:text-link-hover focus-visible:outline-2 focus-visible:outline-focus"
        >
          Ver desglose completo en Ocupaciones
        </Link>
      </header>

      <div className="space-y-2.5 px-4 pb-4">
        {ranges.map((range, index) => {
          const Icon = ICONS[range.dimension] ?? BarChart3;
          const color =
            DIMENSION_COLORS[range.dimension] ??
            ['#172bc4', '#38bdf8', '#8b5cf6', '#f59e0b'][index % 4];
          const value = dimensions[range.dimension] ?? null;
          const available = range.has_source && value !== null;

          const rawText =
            range.dimension === 'salary_ppp' && salaryAverage !== null && salaryAverage !== undefined
              ? formatUsd(salaryAverage, 0)
              : range.dimension === 'automation_risk' &&
                  automationAverage !== null &&
                  automationAverage !== undefined
                ? formatIndex01(automationAverage)
                : null;

          return (
            <article
              key={range.dimension}
              className={cn(
                'rounded-lg border px-4 py-3',
                available
                  ? 'border-brand/10 bg-[#f7f6ff]'
                  : 'border-dashed border-card-border bg-surface',
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex min-w-0 items-start gap-2.5">
                  <span
                    className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-white"
                    style={{ backgroundColor: available ? color : '#94a3b8' }}
                  >
                    <Icon className="size-3.5" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-heading">
                      {index + 1}. {range.label} sectorial
                    </p>
                    <p className="mt-0.5 text-[10.5px] text-muted-text">
                      Peso ef.: {formatNumber(range.effective_weight * 100, 1)}%
                      {range.unit ? ` · ${range.unit}` : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!available && <Badge tone="neutral">En calibración</Badge>}
                  <p className="text-[19px] leading-none font-semibold text-heading">
                    {available ? formatNumber(value ?? 0, 1) : '—'}
                    <span className="ml-1 text-[11px] font-normal text-muted-text">/ 100</span>
                  </p>
                </div>
              </div>

              {available ? (
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.min(100, value ?? 0)}%`, backgroundColor: color }}
                    aria-hidden
                  />
                </div>
              ) : (
                <p className="mt-2 text-[11px] leading-relaxed text-muted-text">
                  {range.source_status ??
                    'Dimensión temporalmente redistribuida entre los factores activos.'}
                </p>
              )}

              <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[10.5px] text-muted-text">
                <span className="min-w-0">
                  <span className="font-semibold text-body">Indicador:</span>{' '}
                  {range.definition ?? 'Definición en la ficha metodológica.'}
                </span>
                {rawText && <span className="font-semibold text-heading">{rawText}</span>}
              </div>
            </article>
          );
        })}
      </div>

      {(noSourceNote || referenceYear || methodologyHref) && (
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-card-border px-5 py-3 text-[11px] text-muted-text">
          <span>
            {noSourceNote ??
              (referenceYear ? `Año de referencia: ${referenceYear}` : 'Cálculo del Observatorio')}
          </span>
          <Link
            href={methodologyHref}
            className="font-semibold text-link hover:text-link-hover hover:underline"
          >
            Ver fuente y metodología
          </Link>
        </footer>
      )}
    </section>
  );
}
