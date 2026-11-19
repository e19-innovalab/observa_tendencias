import {
  BarChart3,
  BrainCircuit,
  Percent,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import type { EmployabilityComponent, EmployabilityItem } from '@/lib/schemas/api';
import { DIMENSION_COLORS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import {
  formatIndex01,
  formatNumber,
  formatSignedPercent,
  formatUsd,
  riskLabel,
} from '@/lib/utils/format';

const ICONS: Record<string, LucideIcon> = {
  net_demand: BarChart3,
  salary_ppp: Wallet,
  insertion_rate: Percent,
  automation_risk: BrainCircuit,
};

function rawValue(component: EmployabilityComponent): string {
  if (component.raw === null || component.raw === undefined) return '—';
  switch (component.dimension) {
    case 'net_demand':
      return `${formatSignedPercent(component.raw)} anual`;
    case 'salary_ppp':
      return `${formatUsd(component.raw, 2)} PPA / mes`;
    case 'automation_risk':
      return `${formatIndex01(component.raw)} índice 0-1`;
    case 'insertion_rate':
      return `${formatNumber(component.raw * 100, 1)}%`;
    default:
      return formatNumber(component.raw, 1);
  }
}

function provenance(component: EmployabilityComponent): string {
  const detail = component.detail ?? {};
  const indicator = String(
    detail.indicator ?? component.indicator ?? component.measure ?? 'Cálculo del Observatorio',
  );
  const source = detail.source ? String(detail.source) : null;

  if (detail.from_period !== undefined && detail.to_period !== undefined) {
    const from = Number(detail.from_value);
    const to = Number(detail.to_value);
    const fromText = Number.isFinite(from) ? formatNumber(from, Number.isInteger(from) ? 0 : 1) : '—';
    const toText = Number.isFinite(to) ? formatNumber(to, Number.isInteger(to) ? 0 : 1) : '—';
    return `${indicator}: ${fromText} (${String(detail.from_period)}) → ${toText} (${String(detail.to_period)})${source ? ` · ${source}` : ''}`;
  }

  if (detail.period !== undefined) {
    const updated = detail.source_updated_at ? ` · actualizado ${String(detail.source_updated_at)}` : '';
    return `${indicator}: ${String(detail.period)}${source ? ` · ${source}` : ''}${updated}`;
  }

  return component.indicator ?? component.measure;
}

/** Tabla factorial del ISE: valor bruto, escalado, peso, aporte y trazabilidad. */
export function EmployabilityBreakdownTable({
  item,
  terms,
}: {
  item: EmployabilityItem;
  terms?: { normalized?: string; contribution?: string } | null;
}) {
  const availableWeight = item.components
    .filter((component) => component.available && component.weight > 0)
    .reduce((sum, component) => sum + component.weight, 0);

  return (
    <div className="overflow-x-auto rounded-xl border border-card-border bg-canvas">
      <table className="w-full min-w-[62rem] border-collapse text-left">
        <caption className="sr-only">
          Desglose factorial del Índice de Empleabilidad de {item.occupation.name}
        </caption>
        <thead>
          <tr className="border-b border-card-border bg-surface-2 text-[10px] font-bold tracking-[0.08em] text-label uppercase">
            <th scope="col" className="px-4 py-3">Dimensión</th>
            <th scope="col" className="px-4 py-3">Valor bruto</th>
            <th scope="col" className="px-4 py-3 text-center">Escalado (0-100)</th>
            <th scope="col" className="px-4 py-3 text-center">Peso teórico</th>
            <th scope="col" className="px-4 py-3 text-center">Aporte al ISE</th>
            <th scope="col" className="px-4 py-3">De dónde sale / registro de procedencia</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-card-border">
          {item.components.map((component, index) => {
            const Icon = ICONS[component.dimension] ?? BarChart3;
            const color =
              DIMENSION_COLORS[component.dimension] ??
              ['#172bc4', '#38bdf8', '#8b5cf6', '#f59e0b'][index % 4];
            const effective =
              component.available && availableWeight > 0
                ? component.weight / availableWeight
                : 0;

            return (
              <tr key={component.dimension} className="align-top hover:bg-surface">
                <th scope="row" className="px-4 py-4 text-left">
                  <span className="flex items-start gap-2.5">
                    <span
                      className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md text-white"
                      style={{ backgroundColor: component.available ? color : '#94a3b8' }}
                    >
                      <Icon className="size-3.5" aria-hidden />
                    </span>
                    <span>
                      <span className="block text-[12.5px] font-semibold text-heading">
                        {component.label}
                      </span>
                      <span className="mt-0.5 block text-[10.5px] font-normal text-muted-text">
                        {component.dimension === 'automation_risk'
                          ? 'Grado de exposición de tareas nucleares con escalamiento invertido'
                          : component.dimension === 'net_demand'
                            ? 'Tasa de crecimiento compuesto de empleo'
                            : component.dimension === 'salary_ppp'
                              ? 'Ingreso medio estandarizado por paridad de poder adquisitivo'
                              : 'Componente del índice de empleabilidad'}
                      </span>
                    </span>
                  </span>
                </th>

                <td className="px-4 py-4">
                  <span className="block text-[12.5px] font-medium text-heading">
                    {component.available ? rawValue(component) : '—'}
                  </span>
                  {component.display && (
                    <span className="mt-1 block text-[10.5px] text-muted-text">
                      {component.display.label}: {formatUsd(component.display.value, 2)} ·{' '}
                      {component.display.period}
                    </span>
                  )}
                  {component.dimension === 'automation_risk' && component.raw !== null && (
                    <span className="mt-1 block text-[10.5px] text-muted-text">
                      {riskLabel(component.raw)}
                    </span>
                  )}
                </td>

                <td className="px-4 py-4 text-center">
                  {component.normalized === null ? (
                    <span className="text-muted-text">—</span>
                  ) : (
                    <span className="inline-flex flex-col items-center gap-1">
                      <span className="text-[12.5px] font-semibold text-heading">
                        {formatNumber(component.normalized, 1)}
                      </span>
                      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
                        <span
                          className="block h-full rounded-full"
                          style={{
                            width: `${Math.min(100, component.normalized)}%`,
                            backgroundColor: color,
                          }}
                        />
                      </span>
                    </span>
                  )}
                </td>

                <td className="px-4 py-4 text-center">
                  <span className="block text-[12.5px] font-semibold text-heading">
                    {formatNumber(component.weight * 100, 0)}%
                  </span>
                  <span className="mt-1 block text-[10.5px] text-muted-text">
                    efectivo {formatNumber(effective * 100, 1)}%
                  </span>
                </td>

                <td className="px-4 py-4 text-center">
                  <span
                    className={cn(
                      'text-[12.5px] font-semibold',
                      component.contribution === null ? 'text-muted-text' : 'text-heading',
                    )}
                    title={terms?.contribution}
                  >
                    {component.contribution === null
                      ? '—'
                      : formatNumber(component.contribution, 1)}
                  </span>
                </td>

                <td className="px-4 py-4 text-[11px] leading-relaxed text-muted-text">
                  {provenance(component)}
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-heading bg-surface-2">
            <td className="px-4 py-4">
              <span className="block text-[13px] font-semibold text-heading">Puntaje Agregado ISE</span>
              <span className="mt-0.5 block text-[10.5px] text-muted-text">
                Cálculo estandarizado OIT / EXEC-Analytics Regional
              </span>
            </td>
            <td className="px-4 py-4 text-[11px] text-muted-text">—</td>
            <td className="px-4 py-4 text-center">
              <span className="block text-[11px] font-semibold text-heading">
                Ponderación efectiva {formatNumber(availableWeight * 100, 0)}%
              </span>
              <span className="mt-0.5 block text-[10.5px] text-muted-text">
                Cobertura {Math.round(item.coverage_ratio * 100)}%
              </span>
            </td>
            <td className="px-4 py-4 text-center text-[12.5px] font-semibold text-heading">
              {formatNumber(availableWeight * 100, 0)}%
            </td>
            <td className="px-4 py-4 text-center">
              <span className="text-[19px] leading-none font-bold text-heading">
                {item.score === null ? '—' : formatNumber(item.score, 1)}
              </span>
              <span className="ml-1 text-[11px] font-normal text-muted-text">pts</span>
            </td>
            <td className="px-4 py-4 text-[10.5px] text-muted-text">
              {item.level_label ? `Nivel ${item.level_label}` : 'Cálculo del Observatorio'}
              {item.methodology?.version ? ` · Metodología v${item.methodology.version}` : ''}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
