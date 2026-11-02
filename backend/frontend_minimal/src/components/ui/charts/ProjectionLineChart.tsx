'use client';

import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatValue } from '@/lib/utils/format';
import { CHART_GRID } from './chartTheme';

export type ProjectionRow = Record<string, string | number | null | [number, number]>;

export type ProjectionSeries = { key: string; label: string; color: string; band: boolean };
type Props = { data: ProjectionRow[]; series: ProjectionSeries[]; unit: string };

/**
 * Serie observada (línea continua) y proyección (línea punteada) por país. Cada fila trae
 * `ISO` (observado), `ISO_p` (proyectado, empieza en el último observado para que se vean unidas)
 * y, si band, `ISO_band` = [inferior, superior].
 */
export function ProjectionLineChart({ data, series, unit }: Props) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART_GRID} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} minTickGap={24} />
          <YAxis width={64} tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatValue(v, unit)} />
          <Tooltip
            formatter={(v, name) =>
              Array.isArray(v) ? [`${formatValue(Number(v[0]), unit)} – ${formatValue(Number(v[1]), unit)}`, name] : [formatValue(Number(v), unit), name]
            }
          />
          {series.filter((s) => s.band).map((s) => (
            <Area key={`${s.key}_band`} dataKey={`${s.key}_band`} name={`${s.label}: intervalo`} stroke="none" fill={s.color} fillOpacity={0.12} isAnimationActive={false} connectNulls />
          ))}
          {series.map((s) => (
            <Line key={s.key} dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={data.length <= 40 ? { r: 2.5 } : false} isAnimationActive={false} connectNulls />
          ))}
          {series.map((s) => (
            <Line key={`${s.key}_p`} dataKey={`${s.key}_p`} name={`${s.label}: proyección`} stroke={s.color} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 2.5, fill: '#fff' }} isAnimationActive={false} connectNulls />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
