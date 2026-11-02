'use client';

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatValue } from '@/lib/utils/format';
import { CHART_GRID } from './chartTheme';

export type CompareRow = { label: string; current: number | null; previous: number | null; currentPeriod?: string; previousPeriod?: string };

/** Último valor y valor anterior de cada país, en barras horizontales. */
export function CompareBarChart({ rows, unit }: { rows: CompareRow[]; unit: string }) {
  return (
    <div className="w-full" style={{ height: 70 + rows.length * 56 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }} barGap={2}>
          <CartesianGrid stroke={CHART_GRID} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12, fill: '#475569' }} tickFormatter={(v: number) => formatValue(v, unit)} />
          <YAxis type="category" dataKey="label" width={80} tick={{ fontSize: 12, fill: '#475569' }} />
          <Tooltip formatter={(v) => formatValue(Number(v), unit)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="current" name="Último dato" fill="#172bc4" radius={[0, 3, 3, 0]} isAnimationActive={false} />
          <Bar dataKey="previous" name="Período anterior" fill="#aebdde" radius={[0, 3, 3, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
