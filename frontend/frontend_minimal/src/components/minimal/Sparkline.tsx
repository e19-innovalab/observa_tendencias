type Line = { color: string; values: (number | null)[] };

/** Mini gráfico de tendencia (sin ejes): sirve de vista previa y de botón. */
export function Sparkline({ lines, className = 'h-14' }: { lines: Line[]; className?: string }) {
  const all = lines.flatMap((l) => l.values).filter((v): v is number => v !== null);
  if (all.length === 0) return <div className={className} />;
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const n = Math.max(...lines.map((l) => l.values.length));
  const x = (i: number) => 4 + (192 * i) / Math.max(1, n - 1);
  const y = (v: number) => 4 + 48 * (1 - (v - lo) / (hi - lo || 1));
  return (
    <svg viewBox="0 0 200 56" className={`${className} w-full`} preserveAspectRatio="none" aria-hidden>
      {lines.map((l, k) => {
        let d = '';
        l.values.forEach((v, i) => { if (v !== null) d += `${d ? ' L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`; });
        return <path key={k} d={d} fill="none" stroke={l.color} strokeWidth={1.75} strokeLinejoin="round" />;
      })}
    </svg>
  );
}
