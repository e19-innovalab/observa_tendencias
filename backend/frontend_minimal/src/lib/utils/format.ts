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
  // una fecha sin hora ("2026-10-13") es ese día: new Date la tomaría como medianoche UTC y en
  // Argentina mostraría el día anterior
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  const d = dateOnly ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])) : new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString('es-AR');
}

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const two = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

/** Puntaje 0-100 con un decimal. */
export const formatScore = (v: number | null | undefined) => (v === null || v === undefined ? '—' : one.format(v));
/** Variación de puntaje con signo ("+5,4 pts"). */
export const formatPoints = (v: number | null | undefined) =>
  v === null || v === undefined ? null : `${v > 0 ? '+' : ''}${one.format(v)} pts`;
export const formatUsd = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `USD ${whole.format(v)}`);
/** Valor con el formato de su unidad que manda la API ("USD PPA {value} / mes"); sin formato, solo el número. */
export const formatUnit = (v: number | null | undefined, unit: string, formats: Record<string, string> | undefined) =>
  v === null || v === undefined ? '—' : (formats?.[unit] ?? '{value}').replace('{value}', whole.format(v));
export const formatIndex = (v: number | null | undefined) => (v === null || v === undefined ? '—' : two.format(v));
/** Fracción como porcentaje ("0,047" -> "+4,7%"). */
export const formatGrowth = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${one.format(v * 100)}%`;
export const formatShare = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${one.format(v * 100)}%`);
