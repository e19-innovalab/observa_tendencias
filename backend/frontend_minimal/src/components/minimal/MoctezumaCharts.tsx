'use client';

import { useRef, useState, type ReactNode } from 'react';
import { CHART_GRID } from '@/components/ui/charts/chartTheme';

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt1 = (v: number) => one.format(v);

/** Zona donde el cambio supera a la respuesta. */
const ZONE = '#eef4f2';
const DIAGONAL = '#94a3b8';
const TEXT = '#64748b';
const INK = '#0f172a';

/** event: punto hueco de un evento (no es un dato), con su etiqueta en una columna al costado. */
export type PlaneSeries = { key: string; label: string; color: string; points: { x: number; y: number; tip: string; tag?: string; event?: string }[] };
const EVENT = '#0f6b5c';
export type PlaneDot = { x: number; y: number; color: string; tip: string };
/** Punto numerado del anexo de lectura: lleno (promedio del país) o punteado (una ocupación). */
export type PlaneMark = { n: number; x: number; y: number; color: string; tip: string; dashed?: boolean };
export type YearSeries = { key: string; label: string; color: string; points: { year: number; value: number; tip: string }[] };

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
      className="pointer-events-none absolute z-10 max-w-60 whitespace-pre-line rounded-md bg-slate-900 px-2.5 py-1.5 text-xs leading-snug text-white shadow"
      style={{ left: Math.min(tip.x + 12, tip.width - 230), top: tip.y + 12 }}
    >
      {tip.text}
    </div>
  );
  return { box, show, hide: () => setTip(null), node };
}

function Mark({ cx, cy, r, color, tip, onShow, onHide, faint }: { cx: number; cy: number; r: number; color: string; tip: string; onShow: (e: React.PointerEvent, t: string) => void; onHide: () => void; faint?: boolean }) {
  return (
    <g onPointerMove={(e) => onShow(e, tip)} onPointerLeave={onHide}>
      <circle cx={cx} cy={cy} r={r} fill={color} opacity={faint ? 0.4 : 1} stroke={faint ? 'none' : '#fff'} strokeWidth={2} />
      <circle cx={cx} cy={cy} r={Math.max(r + 6, 10)} fill="transparent" />
    </g>
  );
}

/** Ritmo del cambio (x) contra Capacidad de respuesta (y), ambos 0-100. Debajo de la diagonal el cambio supera a la respuesta. */
export function PlaneChart({ series, dots = [], marks = [], ariaLabel, diagonalLabel }: { series: PlaneSeries[]; dots?: PlaneDot[]; marks?: PlaneMark[]; ariaLabel: string; diagonalLabel: string }) {
  const W = 440, H = 400, m = { l: 46, r: 16, t: 12, b: 44 };
  const x = (v: number) => m.l + (v / 100) * (W - m.l - m.r);
  const y = (v: number) => H - m.b - (v / 100) * (H - m.t - m.b);
  const { box, show, hide, node } = useTip();
  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label={ariaLabel}>
        <path d={`M${x(0)},${y(0)} L${x(100)},${y(0)} L${x(100)},${y(100)} Z`} fill={ZONE} />
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={x(0)} x2={x(100)} y1={y(v)} y2={y(v)} stroke={CHART_GRID} />
            <line x1={x(v)} x2={x(v)} y1={y(0)} y2={y(100)} stroke={CHART_GRID} />
            <text x={x(v)} y={y(0) + 16} textAnchor="middle" fontSize={11} fill={TEXT}>{v}</text>
            <text x={x(0) - 8} y={y(v) + 4} textAnchor="end" fontSize={11} fill={TEXT}>{v}</text>
          </g>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(100)} stroke={DIAGONAL} strokeDasharray="4 4" />
        <text x={x(62)} y={y(66)} transform={`rotate(-42 ${x(62)} ${y(66)})`} textAnchor="middle" fontSize={11} fill={TEXT}>{diagonalLabel}</text>
        <text x={x(50)} y={H - 6} textAnchor="middle" fontSize={11.5} fill={TEXT}>Ritmo del cambio →</text>
        <text x={12} y={y(50)} transform={`rotate(-90 12 ${y(50)})`} textAnchor="middle" fontSize={11.5} fill={TEXT}>Capacidad de respuesta →</text>
        {dots.map((d, i) => <Mark key={i} cx={x(d.x)} cy={y(d.y)} r={3} color={d.color} tip={d.tip} onShow={show} onHide={hide} faint />)}
        {series.map((s) => (
          <g key={s.key}>
            <polyline points={s.points.map((p) => `${x(p.x)},${y(p.y)}`).join(' ')} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {s.points.map((p, i) => p.event ? (
              <g key={i} onPointerMove={(e) => show(e, p.tip)} onPointerLeave={hide}>
                <circle cx={x(p.x)} cy={y(p.y)} r={4.5} fill="#fff" stroke={EVENT} strokeWidth={2} />
                <circle cx={x(p.x)} cy={y(p.y)} r={10} fill="transparent" />
              </g>
            ) : (
              <Mark key={i} cx={x(p.x)} cy={y(p.y)} r={i === s.points.length - 1 ? 6 : 4} color={s.color} tip={p.tip} onShow={show} onHide={hide} />
            ))}
            {(() => {
              // etiquetas de eventos en dos columnas (los de la izquierda y los de la derecha del plano),
              // por debajo del recorrido, ordenadas por altura para que las guías no se crucen
              const events = s.points.filter((p) => p.event);
              return (['left', 'right'] as const).flatMap((side) =>
                events
                  .filter((p) => (side === 'left' ? p.x < 50 : p.x >= 50))
                  .sort((a, b) => b.y - a.y)
                  .map((p, row) => {
                    const lx = side === 'left' ? x(6) : x(94);
                    const ly = y(86 - row * 8);
                    return (
                      <g key={`e${side}${row}`} onPointerMove={(e) => show(e, p.tip)} onPointerLeave={hide}>
                        <polyline points={`${x(p.x)},${y(p.y)} ${lx + (side === 'left' ? -3 : 3)},${ly - 4}`} fill="none" stroke={EVENT} strokeOpacity={0.5} />
                        <text x={lx} y={ly} textAnchor={side === 'left' ? 'start' : 'end'} fontSize={11} fill={INK} stroke="#fff" strokeWidth={3} paintOrder="stroke">{p.event}</text>
                      </g>
                    );
                  }),
              );
            })()}
            {s.points.map((p, i) => p.tag && (
              <text key={`t${i}`} x={x(p.x) + (p.x > 80 ? -10 : 10)} y={y(p.y) + 4} textAnchor={p.x > 80 ? 'end' : 'start'} fontSize={11.5} fill={INK}>{p.tag}</text>
            ))}
          </g>
        ))}
        {marks.map((mk) => (
          <g key={mk.n} onPointerMove={(e) => show(e, mk.tip)} onPointerLeave={hide}>
            <circle cx={x(mk.x)} cy={y(mk.y)} r={11} fill={mk.dashed ? '#fff' : mk.color} stroke={mk.color} strokeWidth={2} strokeDasharray={mk.dashed ? '3 2' : undefined} />
            <text x={x(mk.x)} y={y(mk.y) + 4} textAnchor="middle" fontSize={11.5} fontWeight={700} fill={mk.dashed ? mk.color : '#fff'} pointerEvents="none">{mk.n}</text>
          </g>
        ))}
      </svg>
      {node}
    </div>
  );
}

/** Indicador 0-100 por año, con el eje de años en escala real (sirve para años irregulares). */
/**
 * Evento marcado sobre la curva: un punto en su año, sobre la línea que une los datos de antes y
 * después (no es un dato), con una etiqueta corta y la explicación al pasar el mouse.
 */
export type YearMarker = { year: number; label: string; detail?: string };

/** Etiqueta junto a un dato de la serie (un punto que sí es dato), con la explicación al pasar el mouse. */
export type YearAnnotation = { year: number; label: string; detail?: string };

export function YearChart({ series, from, to, ticks, markers = [], annotations = [], ariaLabel, width = 440, height = 300 }: { series: YearSeries[]; from: number; to: number; ticks: number[]; markers?: YearMarker[]; annotations?: YearAnnotation[]; ariaLabel: string; width?: number; height?: number }) {
  // en la versión ancha textos y puntos crecen para leerse igual que en la compacta
  const k = width > 600 ? 1.3 : 1;
  const W = width, H = height, m = { l: 40 * k, r: 16, t: 22 * k, b: 32 * k };
  const x = (v: number) => m.l + ((v - from) / (to - from)) * (W - m.l - m.r);
  const y = (v: number) => H - m.b - (v / 100) * (H - m.t - m.b);
  const { box, show, hide, node } = useTip();
  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label={ariaLabel}>
        <rect x={x(from)} y={y(100)} width={x(to) - x(from)} height={y(50) - y(100)} fill={ZONE} />
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={x(from)} x2={x(to)} y1={y(v)} y2={y(v)} stroke={v === 50 ? DIAGONAL : CHART_GRID} strokeDasharray={v === 50 ? '4 4' : undefined} />
            <text x={x(from) - 8 * k} y={y(v) + 4} textAnchor="end" fontSize={11 * k} fill={TEXT}>{v}</text>
          </g>
        ))}
        {ticks.map((t) => <text key={t} x={x(t)} y={H - 10 * k} textAnchor="middle" fontSize={11 * k} fill={TEXT}>{t}</text>)}
        {annotations.map((a) => {
          const p = series[0]?.points.find((q) => q.year === a.year);
          if (!p) return null;
          const tip = `${a.year} · ${a.label}${a.detail ? `\n${a.detail}` : ''}`;
          return (
            <g key={`a${a.year}`} onPointerMove={(e) => show(e, tip)} onPointerLeave={hide}>
              <text x={x(a.year) + 10 * k} y={y(p.value) + 4 * k} fontSize={11 * k} fill={INK} stroke="#fff" strokeWidth={3} paintOrder="stroke">
                <tspan fontWeight={600}>{a.year}</tspan> · {a.label}
              </text>
            </g>
          );
        })}
        {markers.length > 0 && (() => {
          const pts = series[0]?.points ?? [];
          // valor sobre la línea en ese año (interpolación entre el dato anterior y el siguiente)
          const onLine = (year: number) => {
            const after = pts.findIndex((p) => p.year >= year);
            if (after <= 0) return pts[Math.max(after, 0)]?.value ?? 0;
            const a = pts[after - 1], b = pts[after];
            return a.value + ((year - a.year) / (b.year - a.year)) * (b.value - a.value);
          };
          // etiquetas en columna a la derecha del primer dato después de los eventos, debajo de la curva
          // (zona libre: la curva ya subió)
          const lastYear = Math.max(...markers.map((m) => m.year));
          const nextYear = pts.find((p) => p.year > lastYear)?.year ?? lastYear;
          const labelX = x(nextYear) + 14 * k;
          const top = 46;
          const step = 11;
          // filas de etiquetas en el orden de altura de los puntos (el más alto arriba): las guías no se cruzan
          const row = new Map([...markers].sort((a, b) => onLine(b.year) - onLine(a.year)).map((m, i) => [m.year, i]));
          return markers.map((mk) => {
            const cx = x(mk.year), cy = y(onLine(mk.year));
            const ly = y(top - (row.get(mk.year) ?? 0) * step);
            const tip = `${mk.year} · ${mk.label}${mk.detail ? `\n${mk.detail}` : ''}\n(Punto sobre la línea entre los datos de población: marca el año, no es una estimación.)`;
            return (
              <g key={mk.year} onPointerMove={(e) => show(e, tip)} onPointerLeave={hide}>
                <polyline points={`${cx},${cy} ${labelX - 6},${ly - 4 * k}`} fill="none" stroke="#0f6b5c" strokeOpacity={0.5} />
                <circle cx={cx} cy={cy} r={4.5 * k} fill="#fff" stroke="#0f6b5c" strokeWidth={2} />
                <text x={labelX} y={ly} fontSize={11 * k} fill={INK} stroke="#fff" strokeWidth={3} paintOrder="stroke">
                  <tspan fontWeight={600}>{mk.year}</tspan> · {mk.label}
                </text>
                <circle cx={cx} cy={cy} r={10} fill="transparent" />
              </g>
            );
          });
        })()}
        {series.map((s) => {
          const last = s.points[s.points.length - 1];
          return (
            <g key={s.key}>
              <polyline points={s.points.map((p) => `${x(p.year)},${y(p.value)}`).join(' ')} fill="none" stroke={s.color} strokeWidth={2 * k} strokeLinejoin="round" strokeLinecap="round" />
              {s.points.map((p, i) => (
                <Mark key={i} cx={x(p.year)} cy={y(p.value)} r={(i === s.points.length - 1 ? 5 : 3.5) * k} color={s.color} tip={p.tip} onShow={show} onHide={hide} />
              ))}
              {last && <text x={x(last.year) - 8 * k} y={y(last.value) - 9 * k} textAnchor="end" fontSize={11.5 * k} fill={INK}>{s.label} {fmt1(last.value)}</text>}
            </g>
          );
        })}
      </svg>
      {node}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color?: string; zone?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5">
          <i className={`inline-block size-2.5 ${i.zone ? 'rounded-sm border border-slate-200' : 'rounded-full'}`} style={{ background: i.zone ? ZONE : i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

export function Panel({ era, title, tag, real, children, read }: { era: string; title: string; tag: string; real?: boolean; children: ReactNode; read: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-2.5 rounded-xl border border-slate-200 p-5">
      <p className="text-xs text-slate-500">{era}</p>
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <span className={`self-start rounded border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${real ? 'border-teal-700 text-teal-800' : 'border-slate-300 text-slate-600'}`}>{tag}</span>
      {children}
      <p className="text-sm text-slate-600">{read}</p>
    </div>
  );
}
