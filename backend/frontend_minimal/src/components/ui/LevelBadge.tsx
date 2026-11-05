const STYLE: Record<string, string> = {
  high: 'bg-success-soft text-success',
  medium: 'bg-info-soft text-info',
  low: 'bg-warning-soft text-warning',
};

/** Nivel del ISE (Alta / Media / Baja / sin datos). */
export function LevelBadge({ level, label }: { level: string; label: string }) {
  return <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${STYLE[level] ?? 'bg-surface-2 text-muted-text'}`}>{label}</span>;
}
