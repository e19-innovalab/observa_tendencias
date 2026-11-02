import { ChevronDown } from 'lucide-react';
import { getMethodologies } from '@/lib/api/methodologies';
import type { MethodologyItem } from '@/lib/schemas/api';

/** Parámetros anidados en una lista plana: { weights: { net_demand: 0.35 } } -> weights.net_demand = 0.35. */
function flatten(params: Record<string, unknown>, prefix = ''): [string, string][] {
  return Object.entries(params).flatMap(([k, v]): [string, string][] => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) return flatten(v as Record<string, unknown>, key);
    return [[key, Array.isArray(v) ? `[${v.join(', ')}]` : String(v)]];
  });
}

/** Parámetros que son textos de la interfaz, no del cálculo. */
const HIDDEN_PARAMS = new Set(['messages']);

function Params({ m }: { m: MethodologyItem }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      {flatten(Object.fromEntries(Object.entries(m.params).filter(([k]) => !HIDDEN_PARAMS.has(k)))).map(([k, v]) => (
        <code key={k} className="max-w-full truncate rounded border border-line bg-surface px-1.5 py-0.5 text-[11px] text-body" title={`${k} = ${v}`}>
          {k} = {v}
        </code>
      ))}
      <span className="text-[11px] text-muted-text">metodología #{m.methodology_id} · v{m.version}</span>
    </div>
  );
}

/**
 * "¿Cómo se calcula?" desplegable, como en el Explorer: el texto y los parámetros vienen de
 * /methodologies/{tipo} (config/analytics.yaml del backend), así que lo que se lee es lo que se usó.
 * Varias metodologías (por ejemplo tendencia y proyección) se muestran lado a lado.
 */
export async function HowCalculated({ types, title = '¿Cómo se calcula?', open = false }: { types: string[]; title?: string; open?: boolean }) {
  const lists = await Promise.all(types.map((t) => getMethodologies(t).catch(() => [] as MethodologyItem[])));
  const blocks = lists.map((list) => list.filter((m) => m.is_current)).filter((list) => list.length > 0);
  if (blocks.length === 0) return null;
  return (
    <details open={open} className="group rounded-lg border border-line bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-5 [&::-webkit-details-marker]:hidden">
        <span className="text-lg font-semibold text-heading">{title}</span>
        <ChevronDown className="size-5 text-muted-text transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className={`grid grid-cols-1 gap-6 border-t border-line/70 p-5 ${blocks.length > 1 ? 'lg:grid-cols-2' : ''}`}>
        {blocks.map((current) => (
          <section key={current[0].methodology_type} className="min-w-0">
            <h3 className="font-semibold text-heading">{current[0].name ?? current[0].methodology_type}</h3>
            <div className="mt-2 space-y-2 text-sm leading-relaxed text-body">
              {(current[0].description_md ?? '').split('\n').filter(Boolean).map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
            {current.length > 1 && (
              <p className="mt-3 text-xs text-muted-text">Algunos indicadores usan parámetros propios: {current.length} juegos de parámetros vigentes.</p>
            )}
            {current.map((m) => <Params key={m.methodology_id} m={m} />)}
          </section>
        ))}
        <p className="text-xs text-muted-text lg:col-span-2">
          Texto y parámetros vienen de la configuración del backend (config/analytics.yaml). Cada resultado guarda el número de metodología con el que se calculó.
        </p>
      </div>
    </details>
  );
}
