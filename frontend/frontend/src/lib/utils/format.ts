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

/* ---------- Formateadores para las pantallas conectadas a la API ---------- */

const decimal = (digits: number) =>
  new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

/** Número simple con separadores es-AR. */
export function formatNumber(value: number, digits = 1): string {
  return decimal(digits).format(value);
}

/** Fracción 0,32 → "32,0 pp" (puntos porcentuales). */
export function formatPoints(fraction: number, digits = 1): string {
  return `${decimal(digits).format(fraction * 100)} pp`;
}

/** Fracción 0,32 → "+32,0 pp". */
export function formatSignedPoints(fraction: number, digits = 1): string {
  const n = decimal(digits).format(fraction * 100);
  return `${fraction > 0 ? '+' : ''}${n} pp`;
}

/** Fracción 0,032 → "+3,2%". */
export function formatSignedPercent(fraction: number, digits = 2): string {
  const n = decimal(digits).format(fraction * 100);
  return `${fraction > 0 ? '+' : ''}${n}%`;
}

/** Índice 0-1 (exposición a IA) → "0,31". */
export function formatIndex01(value: number): string {
  return decimal(2).format(value);
}

/** Monto en USD PPA → "USD 1.864". */
export function formatUsd(value: number, digits = 0): string {
  return `USD ${decimal(digits).format(value)}`;
}

/** Valor de componente del ISE según su dimensión. */
export function formatComponentValue(
  dimension: string,
  raw: number | null,
  unit?: string | null,
): string {
  if (raw === null) return 'Sin dato';
  if (dimension === 'net_demand') return formatSignedPercent(raw);
  if (dimension === 'salary_ppp') return formatUsd(raw);
  if (dimension === 'insertion_rate') return formatValue(raw * 100, 'percent');
  if (dimension === 'automation_risk') return formatIndex01(raw);
  if (unit === 'percent') return formatValue(raw, 'percent');
  return decimal(1).format(raw);
}

/** Etiqueta de riesgo de automatización a partir del índice 0-1. */
export function riskLabel(value: number | null): string {
  if (value === null) return 'Sin dato';
  if (value < 0.35) return 'Exposición baja';
  if (value < 0.6) return 'Exposición media';
  return 'Exposición alta';
}

