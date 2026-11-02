import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { OccupationRow } from '@/lib/ui-types';
import { formatNumber } from '@/lib/utils/format';

const HEADERS = [
  'Rank',
  'Ocupación & CIUO',
  'País',
  'Puntaje ISE',
  'Demanda neta',
  'Salario (USD PPA)',
  'Tasa inserción',
  'Riesgo IA',
  'Cobertura ponderada',
  'Acción',
];

/** Tabla de ranking de ocupaciones con el desglose del ISE. */
export function RankingTable({ rows }: { rows: OccupationRow[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-canvas">
      <table className="w-full min-w-[64rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-surface-2 text-[11px] uppercase tracking-wide text-muted-text">
            {HEADERS.map((header) => (
              <th key={header} scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={`${row.country}-${row.ciuo}`} className="align-middle hover:bg-surface">
              <td className="px-4 py-4 font-semibold text-heading">{row.rank}</td>
              <td className="px-4 py-4">
                <p className="font-medium text-heading">{row.name}</p>
                <p className="text-xs text-muted-text">
                  {row.family} · CIUO {row.ciuo}
                </p>
              </td>
              <td className="px-4 py-4">
                <Badge tone="neutral">{row.country}</Badge>
              </td>
              <td className="whitespace-nowrap px-4 py-4 font-semibold text-heading">
                {formatNumber(row.score, 1)} pts
              </td>
              <td className="whitespace-nowrap px-4 py-4 font-medium text-success">{row.demand}</td>
              <td className="whitespace-nowrap px-4 py-4 text-body">{row.salary}</td>
              <td className="px-4 py-4 text-body">{row.insertion}</td>
              <td className="whitespace-nowrap px-4 py-4">
                <p className="font-medium text-heading">{row.risk}</p>
                <p className="text-xs text-muted-text">{row.riskLabel}</p>
              </td>
              <td className="px-4 py-4">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${row.coverage}%` }}
                      aria-hidden
                    />
                  </div>
                  <span className="text-xs text-muted-text">{row.coverage}%</span>
                </div>
              </td>
              <td className="px-4 py-4">
                <Link
                  href={`/ocupaciones/${row.ciuo}`}
                  className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-link hover:text-link-hover hover:underline"
                >
                  Ver ocupación
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
