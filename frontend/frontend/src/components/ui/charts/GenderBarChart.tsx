'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatValue } from '@/lib/utils/format';
import { CHART_AXIS, CHART_GRID, COUNTRY_COLORS, FALLBACK_COLOR } from './chartTheme';

export type GenderBarRow = {
  key: string;
  label: string;
  value: number;
};

type Props = {
  rows: GenderBarRow[];
  unit?: string;
  /** Referencia de paridad (50 % por defecto). */
  reference?: number;
};

/**
 * Barras horizontales para comparar el % de mujeres entre países (tituladas u ocupadas).
 * La línea punteada marca la mitad, para leer de un vistazo la relación con la paridad.
 */
export function GenderBarChart({ rows, unit = 'percent', reference = 50 }: Props) {
  const height = Math.max(160, rows.length * 56);

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 8, right: 56, bottom: 4, left: 8 }}
        >
          <CartesianGrid stroke={CHART_GRID} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tick={{ fontSize: 11.5, fill: CHART_AXIS }}
            tickLine={false}
            axisLine={{ stroke: CHART_GRID }}
            tickFormatter={(value: number) => formatValue(value, unit)}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={168}
            tick={{ fontSize: 11.5, fill: CHART_AXIS }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid #e6ebf5',
              boxShadow: '0 10px 30px -18px rgba(15,23,42,.35)',
              fontSize: 12,
            }}
            labelStyle={{ fontWeight: 600, color: '#050c1e', marginBottom: 4 }}
            formatter={(value) => formatValue(Number(value), unit)}
          />
          <ReferenceLine
            x={reference}
            stroke="#050c1e"
            strokeDasharray="4 4"
            label={{
              value: `Mitad (${formatValue(reference, unit)})`,
              position: 'insideTopRight',
              fill: '#050c1e',
              fontSize: 10.5,
            }}
          />
          <Bar dataKey="value" name="% de mujeres" barSize={26} radius={[0, 6, 6, 0]}>
            {rows.map((row) => (
              <Cell key={row.key} fill={COUNTRY_COLORS[row.key] ?? FALLBACK_COLOR} />
            ))}
            <LabelList
              dataKey="value"
              position="right"
              formatter={(value) => formatValue(Number(value), unit)}
              fill="#050c1e"
              fontSize={11.5}
              fontWeight={600}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
