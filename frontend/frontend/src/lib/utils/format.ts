const compact = new Intl.NumberFormat('es-AR', { notation: 'compact', maximumFractionDigits: 1 });
const plain = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2 });
const signed = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1, signDisplay: 'exceptZero' });

export function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${plain.format(value)}%`;
  return Math.abs(value) >= 10_000 ? compact.format(value) : plain.format(value);
}

/** Texto de la variación para la pill de un KPI. */
export function formatChange(change: number | null, kind: string, unit: string): string | null {
  if (change === null) return null;
  const n = signed.format(change);
  if (kind === 'relative') return `${n}%`;
  return unit === 'percent' ? `${n} pp` : n;
}

export function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString('es-AR');
}
