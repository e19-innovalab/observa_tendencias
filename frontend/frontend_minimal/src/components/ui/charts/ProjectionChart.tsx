'use client';

import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { CHART_GRID } from './chartTheme';

export type ProjectionRow = { anio: number; valor: number; banda: [number, number] };

const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

/** Titulados proyectados con su intervalo (banda sombreada). */
export function ProjectionChart({ data, color }: { data: ProjectionRow[]; color: string }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART_GRID} vertical={false} />
          <XAxis dataKey="anio" tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} />
          <YAxis width={56} tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => whole.format(v)} />
          <Tooltip
            formatter={(v, name) =>
              Array.isArray(v) ? [`${whole.format(Number(v[0]))} – ${whole.format(Number(v[1]))}`, name] : [whole.format(Number(v)), name]
            }
          />
          <Area dataKey="banda" name="Intervalo" stroke="none" fill={color} fillOpacity={0.15} isAnimationActive={false} />
          <Line dataKey="valor" name="Proyección" stroke={color} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
