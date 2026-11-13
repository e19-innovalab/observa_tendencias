'use client';

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_GRID } from './chartTheme';

export type ProjectionRow = {
  anio: number;
  observado?: number;
  valor?: number;
  banda?: [number, number];
  /** Solo une el último año observado con el primero proyectado. */
  union?: number;
};

const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

/** Titulados observados (línea continua) y proyectados (línea punteada, con su intervalo sombreado). */
export function ProjectionChart({ data, color }: { data: ProjectionRow[]; color: string }) {
  const hasProjection = data.some((row) => row.valor !== undefined);
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART_GRID} vertical={false} />
          <XAxis dataKey="anio" tick={{ fontSize: 12, fill: '#4b5563' }} tickLine={false} />
          <YAxis
            width={56}
            tick={{ fontSize: 12, fill: '#4b5563' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => whole.format(value)}
          />
          <Tooltip
            formatter={(value, name) =>
              Array.isArray(value)
                ? [`${whole.format(Number(value[0]))} – ${whole.format(Number(value[1]))}`, name]
                : [whole.format(Number(value)), name]
            }
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {hasProjection && (
            <Area
              dataKey="banda"
              name="Intervalo de la proyección"
              stroke="none"
              fill={color}
              fillOpacity={0.15}
              isAnimationActive={false}
            />
          )}
          <Line
            dataKey="observado"
            name="Observado"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
          {hasProjection && (
            <Line
              dataKey="union"
              stroke={color}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              legendType="none"
              tooltipType="none"
              connectNulls
              isAnimationActive={false}
            />
          )}
          {hasProjection && (
            <Line
              dataKey="valor"
              name="Proyección"
              stroke={color}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
