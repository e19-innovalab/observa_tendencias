'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { CHART_GRID, COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import type { MotionAxis, MotionPage, MotionPoint } from '@/lib/schemas/motion';

const TEXT = '#64748b';
const INK = '#0f172a';
const REF = '#94a3b8';
const STEP_MS = 1100;

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const two = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

function fmt(v: number, axis: MotionAxis) {
  if (axis.unit === 'percent') return `${v > 0 ? '+' : ''}${one.format(v)}%`;
  if (axis.unit === 'ppp_usd_month') return `USD PPA ${whole.format(v)}`;
  if (axis.unit === 'usd_month') return `USD ${whole.format(v)}`;
  if (axis.unit === 'thousands_persons') return `${whole.format(v)} mil`;
  if (axis.unit === 'index_0_1') return two.format(v);
  return one.format(v);
}

/** Marcas "redondas" para un eje lineal (unas 5). */
function niceTicks(lo: number, hi: number) {
  const raw = (hi - lo) / 6;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((s) => s * mag).find((s) => s >= raw) ?? raw;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(Number(v.toFixed(6)));
  return out;
}

const LOG_TICKS = [250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 12000, 16000];
const LOG_TICKS_SMALL = [250, 500, 1000, 2000, 4000, 8000, 16000];

/** Marca de eje: sin decimales cuando es un número entero. */
function fmtTick(v: number, axis: MotionAxis) {
  if (!Number.isInteger(v) || axis.unit === 'index_0_1') return fmt(v, axis);
  return axis.unit === 'percent' ? `${v > 0 ? '+' : ''}${whole.format(v)}%` : whole.format(v);
}

type Tip = { x: number; y: number; text: string } | null;

/**
 * Burbujas animadas al estilo Gapminder: una por gran grupo de ocupaciones y país, que se mueven año a año.
 * Clic en una burbuja: deja su recorrido marcado.
 */
export function MotionChart({ data, names }: { data: MotionPage; names: Record<string, string> }) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);
  const last = data.years.length - 1;
  const [idx, setIdx] = useState(last);
  const [playing, setPlaying] = useState(false);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<string | null>(null);
  const [tip, setTip] = useState<Tip>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!playing) return;
    const t = setTimeout(() => {
      setIdx((i) => Math.min(i + 1, last));
      if (idx + 1 >= last) setPlaying(false);
    }, STEP_MS);
    return () => clearTimeout(t);
  }, [playing, idx, last]);

  const groupName = useMemo(() => Object.fromEntries(data.groups.map((g) => [g.code, g.name ?? g.code])), [data.groups]);
  const countries = useMemo(() => [...new Set(data.points.map((p) => p.country_iso3))].sort(), [data.points]);
  // series por burbuja (país-grupo), en orden fijo: las grandes primero, así las chicas quedan arriba
  const bubbles = useMemo(() => {
    const m = new Map<string, MotionPoint[]>();
    for (const p of data.points) {
      const k = `${p.country_iso3}-${p.group_code}`;
      m.set(k, [...(m.get(k) ?? []), p]);
    }
    return [...m.entries()]
      .map(([key, pts]) => ({ key, pts: pts.sort((a, b) => a.year - b.year), peak: Math.max(...pts.map((p) => p.size)) }))
      .sort((a, b) => b.peak - a.peak);
  }, [data.points]);

  const W = width;
  const H = Math.max(340, Math.min(540, Math.round(W * 0.6)));
  const small = W < 600;
  const m = { l: small ? 40 : 52, r: 16, t: 28, b: small ? 44 : 52 };
  const xs = data.points.map((p) => p.x);
  const xLo = Math.min(...xs) * 0.85, xHi = Math.max(...xs) * 1.15;
  const ys = data.points.map((p) => p.y);
  const pad = (Math.max(...ys) - Math.min(...ys)) * 0.06 || 1;
  const [yLo, yHi] = data.y.domain ?? [Math.min(...ys) - pad, Math.max(...ys) + pad];
  const maxSize = Math.max(...data.points.map((p) => p.size));
  const rMax = small ? 22 : 38;

  const xPos = (v: number) => {
    const t = data.x.scale === 'log' ? Math.log(v / xLo) / Math.log(xHi / xLo) : (v - xLo) / (xHi - xLo);
    return m.l + t * (W - m.l - m.r);
  };
  const clampY = (v: number) => Math.min(yHi, Math.max(yLo, v));
  const yPos = (v: number) => H - m.b - ((clampY(v) - yLo) / (yHi - yLo)) * (H - m.t - m.b);
  const radius = (v: number) => Math.max(3, Math.round(Math.sqrt(v / maxSize) * rMax * 10) / 10);
  const xTicks = data.x.scale === 'log' ? (small ? LOG_TICKS_SMALL : LOG_TICKS).filter((t) => t >= xLo && t <= xHi) : niceTicks(xLo, xHi);
  const yTicks = niceTicks(yLo, yHi);
  const year = data.years[idx];
  const color = (iso: string) => COUNTRY_COLORS[iso] ?? FALLBACK_COLOR;

  const tipText = (p: MotionPoint) => {
    const out = p.y < yLo || p.y > yHi ? ' (fuera de escala)' : '';
    const carried = Object.entries(p.carried).map(([k, y]) => `${(k === 'x' ? data.x : data.size).label.toLowerCase()}: ${y}`);
    return [
      `${names[p.country_iso3] ?? p.country_iso3} · ${p.year}`,
      `${p.group_code} ${groupName[p.group_code]}`,
      `${data.y.label}: ${fmt(p.y, data.y)}${out}`,
      `${data.x.label}: ${fmt(p.x, data.x)}${p.x_secondary != null && data.x_secondary ? ` (${fmt(p.x_secondary, data.x_secondary)})` : ''}`,
      `${data.size.label}: ${fmt(p.size, data.size)}`,
      carried.length ? `Último dato disponible: ${carried.join(', ')}` : '',
    ].filter(Boolean).join('\n');
  };
  const showTip = (e: React.PointerEvent, key: string, text: string) => {
    const r = box.current?.getBoundingClientRect();
    if (r) setTip({ x: Math.min(e.clientX - r.left + 12, r.width - 250), y: e.clientY - r.top + 12, text });
    setHover(key);
  };
  const hideTip = () => {
    setTip(null);
    setHover(null);
  };
  const toggle = (set: Set<string>, k: string) => {
    const n = new Set(set);
    if (n.has(k)) n.delete(k);
    else n.add(k);
    return n;
  };
  const play = () => {
    if (playing) return setPlaying(false);
    if (idx >= last) setIdx(0);
    setPlaying(true);
  };
  const current = data.points.filter((p) => p.year === year && !hidden.has(p.country_iso3));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {countries.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={!hidden.has(c)}
            onClick={() => setHidden((h) => toggle(h, c))}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${hidden.has(c) ? 'border-slate-200 text-slate-400' : 'border-slate-300 text-slate-700'}`}
          >
            <i className="inline-block size-2.5 rounded-full" style={{ background: hidden.has(c) ? '#cbd5e1' : color(c) }} />
            {names[c] ?? c}
          </button>
        ))}
        <span className="text-xs text-slate-500">Tamaño: {data.size.label.toLowerCase()} · clic en una burbuja para ver su recorrido</span>
      </div>

      <div ref={box} className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full select-none overflow-visible" role="img" aria-label={`${data.title}, ${year}`}>
          <text x={W - m.r - 8} y={H - m.b - 12} textAnchor="end" fontSize={small ? 64 : 120} fontWeight={700} fill="#f1f5f9">{year}</text>
          {yTicks.map((v) => (
            <g key={`y${v}`}>
              <line x1={m.l} x2={W - m.r} y1={yPos(v)} y2={yPos(v)} stroke={CHART_GRID} />
              <text x={m.l - 8} y={yPos(v) + 4} textAnchor="end" fontSize={11} fill={TEXT}>{fmtTick(v, data.y)}</text>
            </g>
          ))}
          {xTicks.map((v) => (
            <g key={`x${v}`}>
              <line x1={xPos(v)} x2={xPos(v)} y1={m.t} y2={H - m.b} stroke={CHART_GRID} />
              <text x={xPos(v)} y={H - m.b + 16} textAnchor="middle" fontSize={11} fill={TEXT}>{whole.format(v)}</text>
            </g>
          ))}
          {data.y.reference != null && data.y.reference >= yLo && data.y.reference <= yHi && (
            <line x1={m.l} x2={W - m.r} y1={yPos(data.y.reference)} y2={yPos(data.y.reference)} stroke={REF} strokeDasharray="4 4" />
          )}
          <text x={(m.l + W - m.r) / 2} y={H - 8} textAnchor="middle" fontSize={11.5} fill={TEXT}>{data.x.label} →</text>
          <text x={4} y={12} fontSize={11.5} fill={TEXT}>↑ {data.y.label}</text>

          {bubbles.filter((b) => selected.has(b.key) && !hidden.has(b.key.split('-')[0])).map((b) => {
            const trail = b.pts.filter((p) => p.year <= year);
            const c = color(b.pts[0].country_iso3);
            return (
              <g key={`t${b.key}`} pointerEvents="none">
                <polyline points={trail.map((p) => `${xPos(p.x)},${yPos(p.y)}`).join(' ')} fill="none" stroke={c} strokeWidth={1.5} strokeOpacity={0.6} />
                {trail.slice(0, -1).map((p) => <circle key={p.year} cx={xPos(p.x)} cy={yPos(p.y)} r={2.5} fill={c} opacity={0.6} />)}
              </g>
            );
          })}

          {bubbles.map((b) => {
            const iso = b.pts[0].country_iso3;
            if (hidden.has(iso)) return null;
            const p = b.pts.find((q) => q.year === year);
            const shown = p ?? [...b.pts].reverse().find((q) => q.year < year) ?? b.pts[0];
            const r = radius(shown.size);
            const out = shown.y < yLo || shown.y > yHi;
            const dim = (hover && hover !== b.key) || (selected.size > 0 && !selected.has(b.key) && !hover);
            return (
              <g
                key={b.key}
                className="cursor-pointer transition-transform duration-700 ease-in-out motion-reduce:transition-none"
                // redondeado: el navegador guarda los estilos con pocos decimales y si no, la hidratación no coincide
                style={{ transform: `translate(${xPos(shown.x).toFixed(1)}px, ${yPos(shown.y).toFixed(1)}px)`, opacity: p ? 1 : 0, pointerEvents: p ? undefined : 'none' }}
                onPointerMove={(e) => p && showTip(e, b.key, tipText(p))}
                onPointerLeave={hideTip}
                onClick={() => setSelected((s) => toggle(s, b.key))}
              >
                <circle
                  className="transition-all duration-700 ease-in-out motion-reduce:transition-none"
                  style={{ r }}
                  fill={color(iso)}
                  fillOpacity={dim ? 0.25 : 0.72}
                  stroke={selected.has(b.key) ? INK : '#fff'}
                  strokeWidth={selected.has(b.key) ? 2 : 1.5}
                  strokeDasharray={out ? '3 2' : undefined}
                />
                {r >= 9 && <text y={4} textAnchor="middle" fontSize={11} fontWeight={600} fill="#fff" pointerEvents="none">{b.pts[0].group_code}</text>}
                {selected.has(b.key) && (
                  <text x={r + 4} y={4} fontSize={11.5} fill={INK} pointerEvents="none" stroke="#fff" strokeWidth={3} paintOrder="stroke">
                    {names[iso] ?? iso} · {groupName[b.pts[0].group_code]}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
        {tip && (
          <div className="pointer-events-none absolute z-10 max-w-64 whitespace-pre-line rounded-md bg-slate-900 px-2.5 py-1.5 text-xs leading-snug text-white shadow" style={{ left: tip.x, top: tip.y }}>
            {tip.text}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={play}
          aria-label={playing ? 'Pausar' : 'Reproducir la animación'}
          className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          {playing ? (
            <svg viewBox="0 0 16 16" className="size-3.5" fill="currentColor" aria-hidden><rect x="3" y="2" width="3.5" height="12" rx="1" /><rect x="9.5" y="2" width="3.5" height="12" rx="1" /></svg>
          ) : (
            <svg viewBox="0 0 16 16" className="size-3.5" fill="currentColor" aria-hidden><path d="M4 2.5v11a.5.5 0 0 0 .77.42l8.5-5.5a.5.5 0 0 0 0-.84l-8.5-5.5A.5.5 0 0 0 4 2.5Z" /></svg>
          )}
        </button>
        <div className="flex min-w-0 flex-1 flex-col">
          <input
            type="range"
            min={0}
            max={last}
            value={idx}
            onChange={(e) => {
              setPlaying(false);
              setIdx(Number(e.target.value));
            }}
            aria-label="Año"
            aria-valuetext={String(year)}
            className="w-full accent-slate-900"
          />
          <div className="flex justify-between text-[11px] text-slate-500">
            {data.years.map((y, i) => (
              <span key={y} className={`${i === idx ? 'font-semibold text-slate-900' : ''} ${small && i % 2 && i !== last ? 'invisible' : ''}`}>{y}</span>
            ))}
          </div>
        </div>
      </div>

      <ul className="grid gap-x-6 gap-y-1 text-xs text-slate-600 sm:grid-cols-2">
        {data.groups.map((g) => (
          <li key={g.code} className="flex gap-2">
            <span className="w-3 shrink-0 text-right font-semibold text-slate-900">{g.code}</span>
            {g.name}
          </li>
        ))}
      </ul>

      <details className="text-sm">
        <summary className="cursor-pointer text-slate-600 hover:text-slate-900">Ver los datos de {year}</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">País</th>
                <th className="py-1 pr-3 font-medium">Grupo</th>
                <th className="py-1 pr-3 text-right font-medium">{data.y.label}</th>
                <th className="py-1 pr-3 text-right font-medium">{data.x.label}</th>
                {data.x_secondary && <th className="py-1 pr-3 text-right font-medium">{data.x_secondary.label}</th>}
                <th className="py-1 text-right font-medium">{data.size.label}</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {current.map((p) => (
                <tr key={`${p.country_iso3}-${p.group_code}`} className="border-t border-slate-100">
                  <td className="py-1 pr-3">{names[p.country_iso3] ?? p.country_iso3}</td>
                  <td className="py-1 pr-3">{p.group_code} {groupName[p.group_code]}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{fmt(p.y, data.y)}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{fmt(p.x, data.x)}{p.carried.x ? ` (${p.carried.x})` : ''}</td>
                  {data.x_secondary && <td className="py-1 pr-3 text-right tabular-nums">{p.x_secondary != null ? fmt(p.x_secondary, data.x_secondary) : '—'}</td>}
                  <td className="py-1 text-right tabular-nums">{fmt(p.size, data.size)}{p.carried.size ? ` (${p.carried.size})` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
