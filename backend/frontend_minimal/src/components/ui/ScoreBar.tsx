/** Barra 0-100 (puntajes escalados del ISE). */
export function ScoreBar({ value, color = 'var(--color-brand)', marker }: { value: number | null; color?: string; marker?: number | null }) {
  return (
    <div className="relative h-2.5 w-full overflow-visible rounded-full bg-surface-2" aria-hidden>
      {value !== null && <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />}
      {marker !== null && marker !== undefined && (
        <span className="absolute -top-1 h-4.5 w-0.5 bg-muted-text" style={{ left: `${marker}%` }} title="Promedio regional" />
      )}
    </div>
  );
}
