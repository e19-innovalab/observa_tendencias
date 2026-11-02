'use client';

import { useRef, useState } from 'react';
import { CHART_GRID } from '@/components/ui/charts/chartTheme';

const TEXT = '#64748b';
const INK = '#0f172a';
const REF = '#94a3b8';
const ZONE = '#fef2f2';

export type SisyphusDot = { key: string; x: number; y: number; color: string; code: string; tip: string };

/**
 * Sobreeducación (x, %) contra lo que paga el grupo frente a un título (y, cociente). Las líneas de corte son las
 * reglas de los cuadrantes; la zona sombreada (mucha sobreeducación y paga poco) es "la piedra vuelve a caer".
 */
export function SisyphusChart({ dots, overFrom, paidBelow, labels, ariaLabel, width = 900, height = 460 }: { dots: SisyphusDot[]; overFrom: number; paidBelow: number; labels: Record<string, string>; ariaLabel: string; width?: number; height?: number }) {
  const small = width < 600;
  const W = width, H = height, m = { l: small ? 40 : 52, r: 12, t: 22, b: 44 };
  const yMax = Math.max(1, Math.ceil(Math.max(...dots.map((d) => d.y), paidBelow) * 10) / 10);
  const x = (v: number) => m.l + (v / 100) * (W - m.l - m.r);
  const y = (v: number) => H - m.b - (v / yMax) * (H - m.t - m.b);
  const box = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; w: number; text: string } | null>(null);
  const show = (e: React.PointerEvent, text: string) => {
    const r = box.current?.getBoundingClientRect();
    if (r) setTip({ x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, text });
  };
  const yTicks = Array.from({ length: Math.round(yMax / 0.25) + 1 }, (_, i) => i * 0.25);
  const corner = (key: string, cx: number, cy: number, anchor: 'start' | 'end') => (
    <text x={cx} y={cy} textAnchor={anchor} fontSize={small ? 10.5 : 13} fontWeight={600} fill={INK} opacity={0.75}>{labels[key]}</text>
  );
  const fmt = (v: number) => v.toLocaleString('es-AR', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 });
  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label={ariaLabel}>
        <rect x={x(overFrom)} y={y(paidBelow)} width={x(100) - x(overFrom)} height={y(0) - y(paidBelow)} fill={ZONE} />
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={x(0)} x2={x(100)} y1={y(v)} y2={y(v)} stroke={v === 1 ? REF : CHART_GRID} strokeDasharray={v === 1 ? '4 4' : undefined} />
            <text x={x(0) - 8} y={y(v) + 4} textAnchor="end" fontSize={11} fill={TEXT}>{fmt(v)}</text>
          </g>
        ))}
        {[0, 20, 40, 60, 80, 100].map((v) => <text key={v} x={x(v)} y={H - m.b + 16} textAnchor="middle" fontSize={11} fill={TEXT}>{v}%</text>)}
        <line x1={x(overFrom)} x2={x(overFrom)} y1={y(0)} y2={y(yMax)} stroke={REF} strokeDasharray="4 4" />
        <line x1={x(0)} x2={x(100)} y1={y(paidBelow)} y2={y(paidBelow)} stroke={REF} strokeDasharray="4 4" />
        {corner('low_pay', x(0) + 8, y(0) - 8, 'start')}
        {corner('sisyphus', x(100) - 8, y(0) - 8, 'end')}
        {corner('fits', x(0) + 8, y(yMax) + 14, 'start')}
        {corner('overqualified_paid', x(100) - 8, y(yMax) + 14, 'end')}
        <text x={(m.l + W - m.r) / 2} y={H - 6} textAnchor="middle" fontSize={11.5} fill={TEXT}>Sobreeducación: ocupados con más estudios de los que pide el puesto →</text>
        <text x={4} y={10} fontSize={11.5} fill={TEXT}>↑ {small ? 'Paga frente a un título' : 'Ingreso del grupo / ingreso con educación superior (1 = paga como un título)'}</text>
        {dots.map((d) => (
          <g key={d.key} onPointerMove={(e) => show(e, d.tip)} onPointerLeave={() => setTip(null)}>
            <circle cx={x(d.x)} cy={y(d.y)} r={small ? 9 : 11} fill={d.color} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
            <text x={x(d.x)} y={y(d.y) + 4} textAnchor="middle" fontSize={small ? 10 : 11.5} fontWeight={700} fill="#fff" pointerEvents="none">{d.code}</text>
          </g>
        ))}
      </svg>
      {tip && (
        <div className="pointer-events-none absolute z-10 max-w-72 whitespace-pre-line rounded-md bg-slate-900 px-2.5 py-1.5 text-xs leading-snug text-white shadow" style={{ left: Math.max(0, Math.min(tip.x + 12, tip.w - 290)), top: tip.y + 12 }}>
          {tip.text}
        </div>
      )}
    </div>
  );
}
