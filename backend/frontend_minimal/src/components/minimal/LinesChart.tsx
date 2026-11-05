'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { formatValue } from '@/lib/utils/format';

export type LinePoint = { period: string; start: string; value: number; lower?: number | null; upper?: number | null };
export type LineSeries = { key: string; label: string; color: string; points: LinePoint[]; projected?: LinePoint[] };

type Props = {
  series: LineSeries[];
  unit: string;
  /** toggle: los chips prenden y apagan series. focus: eligen la serie cuyo intervalo se sombrea. */
  mode?: 'toggle' | 'focus';
  ariaLabel: string;
  /** Ocupa el alto del contenedor (en pantallas grandes) en lugar de una proporción fija. */
  fill?: boolean;
};

const W = 900;
const H = 400;
const L = 52;
const R = 760;
const T = 16;
const B = 368;
const MAX_X_LABELS = 12;
/** Alto mínimo del lienzo con fill, en unidades del viewBox. */
const MIN_H = 160;

/** Paso "redondo" para las marcas del eje (1, 2, 2.5, 5 × 10^n). */
function niceTicks(lo: number, hi: number, count = 5): number[] {
  const raw = (hi - lo) / count || 1;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const ticks: number[] = [];
  const end = Math.ceil(hi / step - 1e-9) * step; // la última marca cubre el valor más alto
  for (let v = Math.floor(lo / step) * step; v <= end + step * 1e-9; v += step) ticks.push(Number(v.toFixed(10)));
  return ticks;
}

/**
 * Gráfico de líneas del rediseño: etiquetas directas al final de cada línea (sin leyenda aparte),
 * chips de país que también son la leyenda, tooltip al pasar el mouse y, si hay, proyección
 * punteada con el intervalo de la serie elegida.
 */
export function LinesChart({ series, unit, mode = 'toggle', ariaLabel, fill = false }: Props) {
  const [off, setOff] = useState<Record<string, boolean>>({});
  const withProjection = series.filter((s) => s.projected?.length);
  const [focus, setFocus] = useState(withProjection[0]?.key ?? series[0]?.key);
  const [hover, setHover] = useState<number | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const [h, setH] = useState(H);
  const bottom = h - (H - B);

  // con fill, el viewBox toma la proporción del contenedor: el texto no se deforma y no quedan franjas vacías
  useEffect(() => {
    const el = frame.current;
    if (!fill || !el) return;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      if (width > 0 && height > 0) setH(Math.max(MIN_H, Math.round((W * height) / width)));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fill]);

  const shown = series.filter((s) => mode === 'focus' || !off[s.key]);

  const geo = useMemo(() => {
    const byPeriod = new Map<string, string>();
    for (const s of series) for (const p of [...s.points, ...(s.projected ?? [])]) byPeriod.set(p.period, p.start);
    const periods = [...byPeriod.entries()].sort((a, b) => a[1].localeCompare(b[1])).map(([p]) => p);
    const index = new Map(periods.map((p, i) => [p, i]));
    const values: number[] = [];
    for (const s of shown) {
      for (const p of s.points) values.push(p.value);
      for (const p of s.projected ?? []) {
        values.push(p.value);
        if (mode === 'focus' && s.key === focus) {
          if (p.lower != null) values.push(p.lower);
          if (p.upper != null) values.push(p.upper);
        }
      }
    }
    let lo = Math.min(...values);
    let hi = Math.max(...values);
    if (!values.length) { lo = 0; hi = 1; }
    if (lo >= 0 && lo < hi * 0.5) lo = 0;
    const pad = (hi - lo) * 0.08 || 1;
    const ticks = niceTicks(lo === 0 ? 0 : lo - pad, hi + pad);
    const y0 = ticks[0];
    const y1 = ticks[ticks.length - 1];
    const x = (i: number) => (periods.length <= 1 ? (L + R) / 2 : L + ((R - L) * i) / (periods.length - 1));
    const y = (v: number) => T + (bottom - T) * (1 - (v - y0) / (y1 - y0 || 1));
    return { periods, index, ticks, x, y };
  }, [series, shown, mode, focus, bottom]);

  const { periods, index, ticks, x, y } = geo;
  const path = (pts: LinePoint[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${x(index.get(p.period) ?? 0).toFixed(1)} ${y(p.value).toFixed(1)}`).join(' ');

  // etiquetas en una columna a la derecha del gráfico (aunque una serie termine antes), separadas para que no se pisen
  const labels = shown
    .map((s) => {
      const last = s.projected?.length ? s.projected[s.projected.length - 1] : s.points[s.points.length - 1];
      return last ? { key: s.key, color: s.color, text: `${s.label} ${formatValue(last.value, unit)}`, ly: y(last.value) + 4, lx: R + 10 } : null;
    })
    .filter((l): l is NonNullable<typeof l> => l !== null)
    .sort((a, b) => a.ly - b.ly);
  for (let i = 1; i < labels.length; i++) if (labels[i].ly - labels[i - 1].ly < 16) labels[i].ly = labels[i - 1].ly + 16;

  const step = Math.max(1, Math.ceil(periods.length / MAX_X_LABELS));
  const firstProjected = Math.min(...withProjection.map((s) => index.get(s.projected![0].period) ?? Infinity));
  const focused = series.find((s) => s.key === focus);
  let band = '';
  if (mode === 'focus' && focused?.projected?.length) {
    const lastObs = focused.points[focused.points.length - 1];
    const pts = focused.projected.filter((p) => p.lower != null && p.upper != null);
    if (lastObs && pts.length) {
      const up = [lastObs, ...pts].map((p, i) => `${i ? 'L' : 'M'}${x(index.get(p.period) ?? 0).toFixed(1)} ${y(i ? p.upper! : p.value).toFixed(1)}`).join(' ');
      const down = [...pts].reverse().map((p) => `L${x(index.get(p.period) ?? 0).toFixed(1)} ${y(p.lower!).toFixed(1)}`).join(' ');
      band = `${up} ${down} Z`;
    }
  }

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const box = svg.current?.getBoundingClientRect();
    if (!box || periods.length === 0) return;
    const vx = ((e.clientX - box.left) / box.width) * W;
    const i = Math.round(((vx - L) / (R - L)) * (periods.length - 1));
    setHover(Math.max(0, Math.min(periods.length - 1, i)));
  };
  const hoverRows = hover === null ? [] : shown
    .map((s) => {
      const p = [...s.points, ...(s.projected ?? [])].find((q) => q.period === periods[hover]);
      return p ? { key: s.key, label: s.label, color: s.color, value: p.value, projected: !s.points.includes(p) } : null;
    })
    .filter((r): r is NonNullable<typeof r> => r !== null)
    .sort((a, b) => b.value - a.value);

  return (
    <div className={fill ? 'flex h-full flex-col' : undefined}>
      <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label={mode === 'focus' ? 'País con intervalo' : 'Países (también es la leyenda)'}>
        {series.map((s) => {
          const pressed = mode === 'focus' ? s.key === focus : !off[s.key];
          return (
            <button
              key={s.key}
              type="button"
              aria-pressed={pressed}
              onClick={() => (mode === 'focus' ? setFocus(s.key) : setOff((o) => ({ ...o, [s.key]: !o[s.key] })))}
              className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-[13px] font-medium ${
                mode === 'focus'
                  ? pressed ? 'border-slate-900 text-slate-900 ring-1 ring-slate-900' : 'border-slate-200 text-slate-700'
                  : pressed ? 'border-slate-200 bg-white text-slate-700' : 'border-slate-200 bg-slate-50 text-slate-400'
              }`}
            >
              <span className="size-2.5 rounded-full" style={{ background: mode === 'toggle' && !pressed ? '#cbd5e1' : s.color }} aria-hidden />
              {s.label}
            </button>
          );
        })}
      </div>
      <div ref={frame} className={fill ? 'relative aspect-[9/4] lg:aspect-auto lg:min-h-[180px] lg:flex-1' : 'relative'}>
        <svg ref={svg} viewBox={`0 0 ${W} ${h}`} className={fill ? 'absolute inset-0 block size-full' : 'block h-auto w-full'} role="img" aria-label={ariaLabel}>
          {Number.isFinite(firstProjected) && (
            <>
              <rect x={x(firstProjected - 1)} y={T} width={R - x(firstProjected - 1)} height={bottom - T} fill="#f8fafc" />
              <text x={(x(firstProjected - 1) + R) / 2} y={T + 14} textAnchor="middle" fontSize="11" fill="#64748b">Proyección</text>
            </>
          )}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={L} x2={R} y1={y(t)} y2={y(t)} stroke="#e2e8f0" />
              <text x={L - 8} y={y(t) + 4} textAnchor="end" fontSize="12" fill="#64748b">{formatValue(t, unit)}</text>
            </g>
          ))}
          {periods.map((p, i) => (i % step === 0 || i === periods.length - 1) && (
            <text key={p} x={x(i)} y={h - 8} textAnchor="middle" fontSize="12" fill="#64748b">{p}</text>
          ))}
          {band && <path d={band} fill={focused?.color} fillOpacity={0.14} />}
          {shown.map((s) => {
            const dim = mode === 'focus' && s.key !== focus;
            const lastObs = s.points[s.points.length - 1];
            return (
              <g key={s.key} opacity={dim ? 0.55 : 1}>
                <path d={path(s.points)} fill="none" stroke={s.color} strokeWidth={dim ? 2 : 2.5} strokeLinejoin="round" strokeLinecap="round" />
                {s.projected?.length && lastObs ? (
                  <path d={path([lastObs, ...s.projected])} fill="none" stroke={s.color} strokeWidth={dim ? 2 : 2.5} strokeDasharray="6 5" strokeLinecap="round" />
                ) : null}
              </g>
            );
          })}
          {labels.map((l) => (
            <text key={l.key} x={l.lx} y={l.ly} fontSize="13" fontWeight="600" fill={l.color} opacity={mode === 'focus' && l.key !== focus ? 0.7 : 1}>{l.text}</text>
          ))}
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={bottom} stroke="#94a3b8" strokeDasharray="3 3" />}
          {hover !== null && hoverRows.map((r) => {
            const p = [...(series.find((s) => s.key === r.key)?.points ?? []), ...(series.find((s) => s.key === r.key)?.projected ?? [])].find((q) => q.period === periods[hover]);
            return p ? <circle key={r.key} cx={x(hover)} cy={y(p.value)} r={4} fill={r.color} stroke="#fff" strokeWidth={2} /> : null;
          })}
          <rect x={L} y={T} width={R - L} height={bottom - T} fill="transparent" onMouseMove={onMove} onMouseLeave={() => setHover(null)} />
        </svg>
        {hover !== null && hoverRows.length > 0 && (
          <div
            className="pointer-events-none absolute top-2 z-10 min-w-40 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md"
            style={{ left: `${(x(hover) / W) * 100}%`, transform: x(hover) > R * 0.6 ? 'translateX(calc(-100% - 12px))' : 'translateX(12px)' }}
          >
            <p className="mb-1 font-semibold text-slate-900">{periods[hover]}</p>
            {hoverRows.map((r) => (
              <p key={r.key} className="flex justify-between gap-4">
                <span className="flex items-center gap-1.5 text-slate-600"><span className="size-2 rounded-full" style={{ background: r.color }} />{r.label}{r.projected ? ' (proy.)' : ''}</span>
                <span className="font-semibold text-slate-900">{formatValue(r.value, unit)}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
