import { z } from 'zod';
import { getMethodologies } from '@/lib/api/methodologies';

/** Parámetros vigentes de un índice de dos lados (Moctezuma, Ludita), tal como están en analytics.yaml. */
const DimensionParamsSchema = z.object({
  side: z.string(),
  weight: z.number(),
  scope: z.string(),
  measure: z.string(),
  window_years: z.number().optional(),
  exclude_years: z.array(z.number()).optional(),
  min_base: z.number().optional(),
  higher_is_more: z.boolean(),
});
export const TwoSidedParamsSchema = z.object({
  side_weights: z.record(z.string(), z.number()),
  levels: z.object({ low: z.number(), high: z.number() }),
  max_age_years: z.number(),
  min_side_coverage: z.number(),
  flat_cohort_score: z.number(),
  scale_max: z.number(),
  dimensions: z.record(z.string(), DimensionParamsSchema),
  paths: z.object({ exposed_from: z.number(), retreat_below: z.number() }).optional(),
});
export type TwoSidedParams = z.infer<typeof TwoSidedParamsSchema>;

/** Parámetros de la versión vigente de la metodología (la que usan los resultados que se muestran). */
export async function currentParams(type: string): Promise<TwoSidedParams> {
  const items = await getMethodologies(type);
  const current = items.find((m) => m.is_current) ?? items[items.length - 1];
  return TwoSidedParamsSchema.parse(current?.params);
}

const dec = (digits: number) => new Intl.NumberFormat('es-AR', { maximumFractionDigits: digits });
/** Número con coma decimal y hasta `digits` decimales ("0,5", "40"). */
export const num = (v: number, digits = 2) => dec(digits).format(v);

/** Peso de cada lado sobre el total (0,5 y 0,5 con la configuración actual). */
export function shares(params: TwoSidedParams, push: string, counter: string) {
  const total = params.side_weights[push] + params.side_weights[counter];
  return { push: params.side_weights[push] / total, counter: params.side_weights[counter] / total };
}

/** "Indicador = 0,5 × Ritmo + 0,5 × (100 − Capacidad)" con los pesos y nombres vigentes. */
export function formulaText(params: TwoSidedParams, push: { side: string; label: string }, counter: { side: string; label: string }) {
  const w = shares(params, push.side, counter.side);
  return `Indicador = ${num(w.push)} × ${push.label} + ${num(w.counter)} × (${num(params.scale_max)} − ${counter.label})`;
}

/** Con pesos iguales, la misma fórmula como distancia a la diagonal: "50 + (Ritmo − Capacidad) / 2". */
export function diagonalRule(params: TwoSidedParams, push: { side: string; label: string }, counter: { side: string; label: string }) {
  const w = shares(params, push.side, counter.side);
  const mid = params.scale_max * w.counter;
  return w.push === w.counter
    ? `Indicador = ${num(mid)} + (${push.label} − ${counter.label}) / ${num(1 / w.push)}`
    : `Indicador = ${num(mid)} + ${num(w.push)} × ${push.label} − ${num(w.counter)} × ${counter.label}`;
}

/** Fracción como texto: 0,5 -> "la mitad"; otras, en porcentaje. */
export const shareText = (v: number) => (v === 0.5 ? 'la mitad' : `el ${num(v * 100, 0)} %`);

/** Lista en castellano: "a, b y c". */
export const listText = (items: string[]) => (items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} y ${items[items.length - 1]}`);

/** Primera letra en minúscula, sin tocar el resto ("Exposición a la IA" -> "exposición a la IA"). */
export const lowerFirst = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);
