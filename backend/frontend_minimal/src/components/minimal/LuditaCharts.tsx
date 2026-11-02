'use client';

import { useId, useRef, useState } from 'react';
import { CHART_GRID } from '@/components/ui/charts/chartTheme';

const TEXT = '#64748b';
const INK = '#0f172a';
const REF = '#94a3b8';

export type IndexSeries = {
  key: string;
  label: string;
  color: string;
  /** Texto de la etiqueta directa al final de la línea (sin texto, no hay etiqueta). */
  endText?: string;
  /** Línea de referencia: fina y sin puntos destacados. */
  muted?: boolean;
  points: { x: number; y: number; tip: string; hollow?: boolean }[];
};

type Tip = { x: number; y: number; width: number; text: string } | null;

function useTip() {
  const box = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<Tip>(null);
  const show = (e: React.PointerEvent, text: string) => {
    const r = box.current?.getBoundingClientRect();
    if (r) setTip({ x: e.clientX - r.left, y: e.clientY - r.top, width: r.width, text });
  };
  const node = tip && (
    <div
      className="pointer-events-none absolute z-10 max-w-64 whitespace-pre-line rounded-md bg-slate-900 px-2.5 py-1.5 text-xs leading-snug text-white shadow"
      style={{ left: Math.max(0, Math.min(tip.x + 12, tip.width - 250)), top: tip.y + 12 }}
    >
      {tip.text}
    </div>
  );
  return { box, show, hide: () => setTip(null), node };
}

/**
 * Empleo indexado (100 = año de llegada de la tecnología) contra los años desde esa llegada.
 * Las líneas se recortan al área del gráfico.
 */
export function IndexChart({ series, from, to, yMin = 0, yMax, yStep = 50, xTicks, ariaLabel, width = 900, height = 420, labelRoom = 0 }: { series: IndexSeries[]; from: number; to: number; yMin?: number; yMax: number; yStep?: number; xTicks: number[]; ariaLabel: string; width?: number; height?: number; labelRoom?: number }) {
  const k = width > 600 ? 1.2 : 1;
  const W = width, H = height, m = { l: 40 * k, r: 12 + labelRoom, t: 14 * k, b: 34 * k };
  const x = (v: number) => m.l + ((v - from) / (to - from)) * (W - m.l - m.r);
  const y = (v: number) => H - m.b - ((Math.max(yMin, Math.min(v, yMax)) - yMin) / (yMax - yMin)) * (H - m.t - m.b);
  const clip = useId();
  const { box, show, hide, node } = useTip();
  const yTicks = Array.from({ length: Math.floor((yMax - yMin) / yStep) + 1 }, (_, i) => yMin + i * yStep);
  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label={ariaLabel}>
        <defs>
          <clipPath id={clip}><rect x={x(from)} y={m.t - 8} width={x(to) - x(from)} height={H - m.t - m.b + 16} /></clipPath>
        </defs>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={x(from)} x2={x(to)} y1={y(v)} y2={y(v)} stroke={v === 100 ? REF : CHART_GRID} strokeDasharray={v === 100 ? '4 4' : undefined} />
            <text x={x(from) - 8} y={y(v) + 4} textAnchor="end" fontSize={11 * k} fill={TEXT}>{v}</text>
          </g>
        ))}
        {xTicks.map((t) => <text key={t} x={x(t)} y={H - 12 * k} textAnchor="middle" fontSize={11 * k} fill={TEXT}>{t === 0 ? 'llegada' : t > 0 ? `+${t}` : t}</text>)}
        {from < 0 && <line x1={x(0)} x2={x(0)} y1={y(yMin)} y2={y(yMax)} stroke={INK} strokeOpacity={0.3} />}
        <g clipPath={`url(#${clip})`}>
          {series.map((s) => (
            <polyline key={s.key} points={s.points.map((p) => `${x(p.x)},${y(p.y)}`).join(' ')} fill="none" stroke={s.color} strokeWidth={(s.muted ? 1.5 : 2.5) * k} strokeOpacity={s.muted ? 0.55 : 1} strokeLinejoin="round" strokeLinecap="round" />
          ))}
        </g>
        {series.map((s) => (
          <g key={`p${s.key}`}>
            {s.points.filter((p) => p.x >= from && p.x <= to).map((p, i) => (
              <g key={i} onPointerMove={(e) => show(e, p.tip)} onPointerLeave={hide}>
                <circle cx={x(p.x)} cy={y(p.y)} r={(s.muted ? 2.5 : 4) * k} fill={p.hollow ? '#fff' : s.color} fillOpacity={s.muted ? 0.6 : 1} stroke={p.hollow ? s.color : '#fff'} strokeWidth={p.hollow ? 1.8 : 1.5} />
                <circle cx={x(p.x)} cy={y(p.y)} r={10} fill="transparent" />
              </g>
            ))}
          </g>
        ))}
        {series.filter((s) => s.endText).map((s) => {
          const last = [...s.points].reverse().find((p) => p.x <= to);
          return last && (
            <text key={`l${s.key}`} x={x(last.x) + 8} y={y(last.y) + 4} fontSize={11.5 * k} fontWeight={s.muted ? 400 : 600} fill={s.muted ? TEXT : INK} stroke="#fff" strokeWidth={3} paintOrder="stroke">{s.endText}</text>
          );
        })}
      </svg>
      {node}
    </div>
  );
}

export type QuadrantDot = { x: number; y: number; color: string; tip: string };

/**
 * Exposición a la IA (x, 0 a 1) contra el crecimiento promedio del empleo y la formación (y, % anual).
 * Las líneas de corte son las reglas de los caminos; cada esquina lleva el nombre de su camino.
 */
export function QuadrantChart({ dots, exposedFrom, retreatBelow, labels, ariaLabel, width = 900, height = 460 }: { dots: QuadrantDot[]; exposedFrom: number; retreatBelow: number; labels: Record<string, string>; ariaLabel: string; width?: number; height?: number }) {
  const small = width < 600;
  const W = width, H = height, m = { l: small ? 40 : 56, r: 12, t: 22, b: 44 };
  const ys = dots.map((d) => d.y);
  const lim = Math.min(25, Math.max(5, ...ys.map(Math.abs)) * 1.1);
  const [x0, x1, y0, y1] = [0, 0.8, -lim, lim];
  const x = (v: number) => m.l + ((v - x0) / (x1 - x0)) * (W - m.l - m.r);
  const y = (v: number) => H - m.b - ((Math.max(y0, Math.min(y1, v)) - y0) / (y1 - y0)) * (H - m.t - m.b);
  const { box, show, hide, node } = useTip();
  const yStep = lim > 12 ? 10 : 5;
  const yTicks = Array.from({ length: Math.floor(lim / yStep) * 2 + 1 }, (_, i) => (i - Math.floor(lim / yStep)) * yStep);
  const corner = (key: string, cx: number, cy: number, anchor: 'start' | 'end') => (
    <text x={cx} y={cy} textAnchor={anchor} fontSize={small ? 10.5 : 13} fontWeight={600} fill={INK} opacity={0.75}>{labels[key]}</text>
  );
  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label={ariaLabel}>
        <rect x={x(exposedFrom)} y={y(retreatBelow)} width={x(x1) - x(exposedFrom)} height={y(y0) - y(retreatBelow)} fill="#fdf2f8" />
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={x(x0)} x2={x(x1)} y1={y(v)} y2={y(v)} stroke={CHART_GRID} />
            <text x={x(x0) - 8} y={y(v) + 4} textAnchor="end" fontSize={11} fill={TEXT}>{v > 0 ? `+${v}` : v}%</text>
          </g>
        ))}
        {[0, 0.2, 0.4, 0.6, 0.8].map((v) => (
          <text key={v} x={x(v)} y={H - m.b + 16} textAnchor="middle" fontSize={11} fill={TEXT}>{v.toLocaleString('es-AR', { minimumFractionDigits: 1 })}</text>
        ))}
        <line x1={x(exposedFrom)} x2={x(exposedFrom)} y1={y(y0)} y2={y(y1)} stroke={REF} strokeDasharray="4 4" />
        <line x1={x(x0)} x2={x(x1)} y1={y(retreatBelow)} y2={y(retreatBelow)} stroke={REF} strokeDasharray="4 4" />
        {corner('out_of_reach', x(x0) + 8, y(y1) + 14, 'start')}
        {corner('teller', x(x1) - 8, y(y1) + 14, 'end')}
        {corner('other_causes', x(x0) + 8, y(y0) - 8, 'start')}
        {corner('weaver', x(x1) - 8, y(y0) - 8, 'end')}
        <text x={(m.l + W - m.r) / 2} y={H - 6} textAnchor="middle" fontSize={11.5} fill={TEXT}>Exposición a la IA {small ? '' : 'generativa '}(OIT, 0 a 1) →</text>
        <text x={4} y={10} fontSize={11.5} fill={TEXT}>↑ {small ? 'Empleo y formación (% anual)' : 'Crecimiento promedio del empleo y la formación (% anual)'}</text>
        {dots.map((d, i) => (
          <g key={i} onPointerMove={(e) => show(e, d.tip)} onPointerLeave={hide}>
            <circle cx={x(d.x)} cy={y(d.y)} r={small ? 4 : 5} fill={d.color} fillOpacity={0.8} stroke="#fff" strokeWidth={1.5} strokeDasharray={d.y < y0 || d.y > y1 ? '2 2' : undefined} />
            <circle cx={x(d.x)} cy={y(d.y)} r={11} fill="transparent" />
          </g>
        ))}
      </svg>
      {node}
    </div>
  );
}
