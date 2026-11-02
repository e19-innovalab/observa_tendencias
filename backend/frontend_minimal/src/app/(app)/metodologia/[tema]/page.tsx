import { ExternalLink } from 'lucide-react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { PageHero } from '@/components/ui/layout/PageHero';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { getIndicators } from '@/lib/api/panorama';
import { getSources } from '@/lib/api/sources';
import { formatDate } from '@/lib/utils/format';

/** Temas de la sección: los de cálculo muestran las metodologías del backend tal como se usaron. */
const TOPICS: Record<string, { label: string; intro: string; types?: string[] }> = {
  ise: {
    label: 'Índice de empleabilidad (ISE)',
    intro: 'Cómo se combina la demanda, el salario y la exposición a la IA de cada ocupación en un puntaje de 0 a 100.',
    types: ['employability_index'],
  },
  brechas: {
    label: 'Brechas de habilidades',
    intro: 'Cómo se compara el crecimiento de la demanda de cada habilidad con el crecimiento de la formación que la enseña.',
    types: ['skill_gap'],
  },
  tendencias: {
    label: 'Tendencias y proyecciones',
    intro: 'Cómo se clasifica la tendencia reciente de cada serie y cómo se calcula su proyección orientativa.',
    types: ['trend', 'projection'],
  },
  alertas: {
    label: 'Alertas',
    intro: 'Qué cambios se detectan después de cada actualización de datos y con qué umbrales.',
    types: ['alert'],
  },
  indicadores: { label: 'Indicadores', intro: 'Qué mide cada indicador, en qué unidad y de qué fuente viene.' },
  fuentes: { label: 'Fuentes de datos', intro: 'De dónde vienen los datos, cada cuánto se actualizan y cuándo se descargaron por última vez.' },
};

const STATUS: Record<string, { label: string; style: string }> = {
  ok: { label: 'Al día', style: 'border-success/40 bg-success-soft text-success' },
  stale: { label: 'Desactualizada', style: 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text' },
  unavailable: { label: 'Con errores', style: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text' },
  never_run: { label: 'Sin descargas', style: 'border-line bg-surface text-muted-text' },
};
const FREQUENCY: Record<string, string> = { daily: 'Diaria', weekly: 'Semanal', monthly: 'Mensual', quarterly: 'Trimestral', annual: 'Anual', yearly: 'Anual' };
const UNITS: Record<string, string> = {
  percent: 'Porcentaje',
  thousands_persons: 'Miles de personas',
  ppp_usd: 'USD PPA',
  ppp_usd_month: 'USD PPA por mes',
  index_0_1: 'Índice de 0 a 1',
};

export function generateStaticParams() {
  return Object.keys(TOPICS).map((tema) => ({ tema }));
}

export async function generateMetadata({ params }: PageProps<'/metodologia/[tema]'>): Promise<Metadata> {
  const { tema } = await params;
  return { title: `Metodología: ${TOPICS[tema]?.label ?? 'tema'}` };
}

export default function MetodologiaPage({ params }: PageProps<'/metodologia/[tema]'>) {
  return (
    <>
      <PageHero
        title="Metodología"
        description="Cómo se calcula cada dato del observatorio. Los textos y parámetros salen de la misma configuración que usa el cálculo, así que siempre coinciden con lo que se ve en pantalla."
      />
      <Suspense fallback={<PageSkeleton />}>
        <MetodologiaContent params={params} />
      </Suspense>
    </>
  );
}

async function MetodologiaContent({ params }: { params: Promise<{ tema: string }> }) {
  const { tema } = await params;
  const topic = TOPICS[tema];
  if (!topic) notFound();
  return (
    <div className="mx-auto grid max-w-7xl gap-8 px-6 py-8 lg:grid-cols-[14rem_1fr]">
      <nav aria-label="Temas de metodología">
        <ul className="space-y-1 text-sm">
          {Object.entries(TOPICS).map(([key, t]) => (
            <li key={key}>
              <Link
                href={`/metodologia/${key}`}
                aria-current={key === tema ? 'page' : undefined}
                className={`block rounded-md px-3 py-2 ${key === tema ? 'bg-heading font-medium text-white' : 'text-body hover:bg-surface'}`}
              >
                {t.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="min-w-0 space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-heading">{topic.label}</h2>
          <p className="mt-1 text-body">{topic.intro}</p>
        </div>
        {topic.types ? (
          <HowCalculated types={topic.types} title="Método vigente" open />
        ) : tema === 'indicadores' ? (
          <Indicators />
        ) : (
          <Sources />
        )}
      </div>
    </div>
  );
}

async function Indicators() {
  const indicators = await getIndicators();
  const domains = [...new Map(indicators.map((i) => [i.domain, i.domain_label])).entries()];
  return (
    <div className="space-y-6">
      {domains.map(([domain, label]) => (
        <section key={domain} className="overflow-hidden rounded-lg border border-line bg-white">
          <h3 className="border-b border-line/70 p-4 font-semibold text-heading">{label}</h3>
          <dl className="divide-y divide-line/60">
            {indicators.filter((i) => i.domain === domain).map((i) => (
              <div key={i.code} className="grid gap-1 p-4 text-sm md:grid-cols-[16rem_1fr]">
                <dt className="font-medium text-heading">{i.name}</dt>
                <dd className="text-body">
                  {i.description}
                  <p className="mt-1 text-xs text-muted-text">
                    {[
                      UNITS[i.unit] ?? i.unit,
                      i.higher_is_better === null ? 'Sin dirección deseable' : i.higher_is_better ? 'Más alto es mejor' : 'Más bajo es mejor',
                      i.has_sector_breakdown ? 'Con apertura por sector' : null,
                      `Fuente: ${i.sources.map((s) => s.name).join(', ')}`,
                    ].filter(Boolean).join(' · ')}
                  </p>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}

async function Sources() {
  const sources = await getSources();
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-white">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[48rem] text-sm">
          <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
            <tr>
              <th scope="col" className="px-4 py-3">Fuente</th>
              <th scope="col" className="px-4 py-3">Actualización esperada</th>
              <th scope="col" className="px-4 py-3">Carga</th>
              <th scope="col" className="px-4 py-3">Última descarga exitosa</th>
              <th scope="col" className="px-4 py-3">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {sources.map((s) => {
              const st = STATUS[s.status] ?? { label: s.status, style: 'border-line' };
              return (
                <tr key={s.code} className="align-top">
                  <td className="px-4 py-3">
                    <p className="font-medium text-heading">{s.name}</p>
                    {s.base_url && (
                      <a href={s.base_url} target="_blank" rel="noreferrer" className="mt-0.5 inline-flex items-center gap-1 text-xs text-link hover:underline">
                        Sitio de la fuente <ExternalLink className="size-3" aria-hidden />
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3">{s.expected_frequency ? FREQUENCY[s.expected_frequency] ?? s.expected_frequency : '—'}</td>
                  <td className="px-4 py-3 text-body">{s.has_connector ? 'Automática' : 'Manual (archivo)'}</td>
                  <td className="px-4 py-3">{formatDate(s.last_success_at) ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${st.style}`}>{st.label}</span>
                    {s.last_run?.error_message && <p className="mt-1 text-xs text-alert-critical-text">{s.last_run.error_message}</p>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
