'use client';

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatValue } from '@/lib/utils/format';
import type { ChartRow, ChartSeries } from './chartTheme';

type Props = { data: ChartRow[]; series: ChartSeries[]; unit: string };

export function TrendLineChart({ data, series, unit }: Props) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} />
          <YAxis
            width={64}
            tick={{ fontSize: 12, fill: '#4b5563' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatValue(v, unit)}
          />
          <Tooltip formatter={(v) => formatValue(Number(v), unit)} />
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              dot={data.length <= 40 ? { r: 3 } : false}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
