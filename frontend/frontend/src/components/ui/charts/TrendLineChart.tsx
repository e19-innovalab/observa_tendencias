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
import { CHART_AXIS, CHART_GRID, type ChartRow, type ChartSeries } from './chartTheme';

type Props = {
  data: ChartRow[];
  series: ChartSeries[];
  unit: string;
  heightClassName?: string;
};

export function TrendLineChart({ data, series, unit, heightClassName = 'h-80' }: Props) {
  return (
    <div className={`${heightClassName} w-full`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 20, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={CHART_GRID} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11.5, fill: CHART_AXIS }}
            tickLine={false}
            axisLine={{ stroke: CHART_GRID }}
            tickMargin={10}
          />
          <YAxis
            width={64}
            tick={{ fontSize: 11.5, fill: CHART_AXIS }}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tickFormatter={(v: number) => formatValue(v, unit)}
          />
          <Tooltip
            cursor={{ stroke: '#cbd5e1', strokeDasharray: '4 4' }}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid #e6ebf5',
              boxShadow: '0 10px 30px -18px rgba(15,23,42,.35)',
              fontSize: 12,
            }}
            labelStyle={{ fontWeight: 600, color: '#050c1e', marginBottom: 4 }}
            formatter={(v) => formatValue(Number(v), unit)}
          />
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2.5}
              strokeDasharray={s.dashed ? '6 4' : undefined}
              dot={{ r: 3.5, fill: s.color, strokeWidth: 0 }}
              activeDot={{ r: 5, strokeWidth: 0 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
