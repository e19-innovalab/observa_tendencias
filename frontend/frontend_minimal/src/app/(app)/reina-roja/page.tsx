import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { CareerFilter } from '@/components/minimal/CareerFilter';
import { ChipList } from '@/components/minimal/ChipList';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/panorama';
import { getRedQueen, getRedQueenCareers, getRedQueenParams, getRedQueenYears } from '@/lib/api/redQueen';
import { listText, lowerFirst, num } from '@/lib/methodology/twoSided';
import type { RedQueenComponent, RedQueenItem, RedQueenPage, RedQueenParams } from '@/lib/schemas/redQueen';
import { formatScore as fmt1 } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Indicador Reina Roja' };

type SearchParams = { ocupacion?: string; vista?: string; pais?: string; carrera?: string };
/** Tope de filas al listar todas las ocupaciones (pagination.max_limit del backend). */
const ALL_LIMIT = 500;
const LEVEL_BAR: Record<string, string> = { high: 'bg-rose-700', medium: 'bg-rose-400', low: 'bg-rose-200' };
const LEVEL_BADGE: Record<string, string> = {
  high: 'bg-rose-100 text-rose-900',
  medium: 'bg-slate-100 text-slate-700',
  low: 'bg-sky-50 text-sky-800',
};
const VIEWS = [
  { value: '', label: 'Destacadas' },
  { value: 'todas', label: 'Todas' },
];
const monthYear = (iso: string | null) => (iso ? new Date(`${iso}T12:00:00`).toLocaleDateString('es-AR', { month: 'short', year: 'numeric' }) : '—');
const perYear = (v: number | null | undefined) => (v == null ? '—' : num(v, v < 10 ? 1 : 0));

export default function RedQueenPage({ searchParams }: PageProps<'/reina-roja'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <RedQueenContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** "vida media de 23 años" (o "más de 50 años" cuando casi no cambia). */
function halfLifeText(item: { half_life: number | null; half_life_capped?: boolean }, cap: number) {
  if (item.half_life == null) return '—';
  return item.half_life_capped || item.half_life >= cap ? `más de ${num(cap, 0)} años` : `${num(item.half_life, 0)} años`;
}

async function RedQueenContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const all = sp.vista === 'todas';
  const byCareer = Boolean(sp.pais && sp.carrera);
  let data;
  try {
    // destacadas: el ranking usa el tamaño configurado en el backend; todas y por carrera, la lista completa
    const [ranking, years, params, countries, careers] = await Promise.all([
      byCareer
        ? getRedQueen({ country: sp.pais, career: sp.carrera, view: 'all', limit: ALL_LIMIT })
        : getRedQueen({ featured: all ? undefined : true, view: 'top', limit: all ? ALL_LIMIT : undefined }),
      getRedQueenYears(),
      getRedQueenParams(),
      getCountries(),
      sp.pais ? getRedQueenCareers(sp.pais) : Promise.resolve([]),
    ]);
    const code = sp.ocupacion ?? ranking.items[0]?.occupation.occupation_code;
    const detail = code ? (await getRedQueen({ occupation: code, view: 'all', limit: 1 })).items[0] : undefined;
    data = { ranking, years, params, detail, countries, careers };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { ranking, years, params, detail, countries, careers } = data;
  const countryName = countries.find((c) => c.iso3 === sp.pais)?.name_es;
  // los enlaces del ranking conservan la vista y el filtro de carrera
  const keep = Object.fromEntries(Object.entries({ vista: all ? 'todas' : '', pais: sp.pais ?? '', carrera: sp.carrera ?? '' }).filter(([, v]) => v));
  const method = ranking.items[0]?.methodology;
  const latest = years[years.length - 1];
  const dimLabel = Object.fromEntries(ranking.dimensions.map((d) => [d.dimension, d.label]));
  const shortSource = (d: string) => dimLabel[d]?.match(/\(([^)]+)\)/)?.[1] ?? d;
  const sourcesText = listText(ranking.dimensions.map((d) => shortSource(d.dimension)));

  return (
    <Page>
      <ChartHeader
        eyebrow="Indicador experimental · Anual"
        title="Indicador Reina Roja"
        subtitle={`Hay que correr todo lo posible para quedarse en el mismo lugar. ¿Cuánto hay que aprender por año para no quedarse atrás? Novedades por año en ${sourcesText}, de 0 a ${num(params.scale_max)}.`}
        controls={
          <>
            {!byCareer && <UrlSeg name="vista" label="Ocupaciones" value={all ? 'todas' : ''} options={VIEWS} reset={['ocupacion']} />}
            <CareerFilter
              countries={countries.map((c) => ({ value: c.iso3, label: c.name_es }))}
              careers={careers.map((c) => ({ value: c.career, label: `${c.career} (${c.occupations})` }))}
              pais={sp.pais ?? ''}
              carrera={sp.carrera ?? ''}
            />
          </>
        }
      />
      <ChartLayout
        chart={
          <>
            <div id="ranking" className="scroll-mt-24">
              <Eyebrow>
                {ranking.year} ·{' '}
                {byCareer
                  ? `ocupaciones a las que lleva ${sp.carrera} (${countryName ?? sp.pais}): ${ranking.total}`
                  : `${all ? `todas las ocupaciones (${ranking.scored_total} con datos)` : 'ocupaciones destacadas'} con más novedades por año`}
              </Eyebrow>
              <p className="mt-1 text-xs text-slate-500">Tocá una ocupación para ver qué entró y qué salió de su perfil.</p>
            </div>
            <ol className="mt-3 flex flex-col gap-1.5">
              {ranking.items.map((i, k) => {
                const selected = detail?.occupation.occupation_code === i.occupation.occupation_code;
                const news = i.components.filter((c) => c.available).map((c) => `${perYear(c.new_per_year)} en ${shortSource(c.dimension)}`);
                return (
                  <li key={i.occupation.occupation_code}>
                    <Link
                      href={`/reina-roja?${new URLSearchParams({ ...keep, ocupacion: i.occupation.occupation_code }).toString()}#detalle`}
                      className={`grid grid-cols-[1.5rem_minmax(0,1fr)] items-center gap-x-2 rounded-lg px-2 py-1.5 sm:grid-cols-[1.5rem_minmax(0,16rem)_minmax(0,1fr)] ${selected ? 'bg-rose-50' : 'hover:bg-slate-50'}`}
                    >
                      <span className="text-xs tabular-nums text-slate-400">{k + 1}</span>
                      <span className="truncate text-sm text-slate-900">{i.occupation.name}</span>
                      <span className="col-start-2 flex min-w-0 items-center gap-2 sm:col-start-3">
                        <span className="h-3 min-w-0 flex-1 rounded-full bg-slate-100">
                          <span className={`block h-3 rounded-full ${LEVEL_BAR[i.level] ?? 'bg-slate-300'}`} style={{ width: `${Math.max(2, (i.score ?? 0) / params.scale_max * 100)}%` }} />
                        </span>
                        <span className="w-10 shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900">{fmt1(i.score)}</span>
                      </span>
                      <span className="col-start-2 text-xs text-slate-500 sm:col-start-3">Novedades por año: {news.join(' · ') || '—'} · vida media {halfLifeText(i, ranking.half_life_cap)}</span>
                    </Link>
                  </li>
                );
              })}
            </ol>
            {ranking.items.length === 0 && <p className="py-10 text-center text-sm text-slate-500">Esta carrera no lleva a ocupaciones con datos de la Reina Roja.</p>}
            <SourceLine source={`${ranking.dimensions.map((d) => d.source_name).filter(Boolean).join(' · ')}${method ? ` · metodología #${method.methodology_id} v${method.version}` : ''}`} />
          </>
        }
        rail={
          <>
            <Eyebrow>Mediana de las ocupaciones</Eyebrow>
            {latest && (
              <div className="rounded-xl border border-slate-200 p-3.5">
                <p className="text-xs text-slate-500">{latest.year} · {latest.scored} ocupaciones</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{latest.median_half_life != null ? `${num(latest.median_half_life, 0)} años` : '—'}</p>
                <p className="text-xs text-slate-600">vida media del perfil: en ese tiempo cambia la mitad</p>
                <ul className="mt-2 flex flex-col gap-0.5 text-xs text-slate-600">
                  {Object.entries(latest.median_new_per_year).map(([d, v]) => <li key={d}>{shortSource(d)}: {perYear(v)} novedades por año</li>)}
                </ul>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs tabular-nums">
                <thead><tr className="text-left text-slate-500"><th className="py-1 font-medium">Año</th><th className="py-1 text-right font-medium">Vida media</th>{ranking.dimensions.map((d) => <th key={d.dimension} className="py-1 text-right font-medium">{shortSource(d.dimension)}</th>)}</tr></thead>
                <tbody className="text-slate-700">
                  {years.map((y) => (
                    <tr key={y.year} className="border-t border-slate-100">
                      <td className="py-1">{y.year}</td>
                      <td className="py-1 text-right">{y.median_half_life != null ? num(y.median_half_life, 0) : '—'}</td>
                      {ranking.dimensions.map((d) => <td key={d.dimension} className="py-1 text-right">{perYear(y.median_new_per_year[d.dimension])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs leading-relaxed text-slate-500">Vida media en años; las columnas por fuente son novedades por año. Cada año compara versiones separadas por unos {params.window_years} años.</p>
          </>
        }
      />

      {detail && <Detail item={detail} page={ranking} params={params} />}

      <section className="mt-12 grid gap-4 sm:grid-cols-2">
        {ranking.dimensions.map((d) => (
          <div key={d.dimension} className="rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-900">{d.label}</h3>
            {d.definition && <p className="mt-1.5 text-sm text-slate-700">{d.definition}</p>}
            {d.source_url && <a href={d.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-medium text-blue-700 hover:underline">{d.source_name}</a>}
          </div>
        ))}
      </section>

      <HowItsCalculated page={ranking} params={params} shortSource={shortSource} />

      <div className="mt-10">
        <HowCalculated types={['red_queen_index']} title="Metodología y parámetros vigentes" />
      </div>
    </Page>
  );
}

/** Qué entró y qué salió del perfil de una ocupación en cada fuente. */
function Detail({ item, page, params }: { item: RedQueenItem; page: RedQueenPage; params: RedQueenParams }) {
  const sources = item.components;
  const comp = (c: RedQueenComponent) => c.available && c.from_version;
  return (
    <section id="detalle" className="mt-12 flex scroll-mt-24 flex-col gap-4 border-t border-slate-200 pt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <Eyebrow>Qué entró y qué salió · {item.year}</Eyebrow>
          <h2 className="mt-1 text-xl font-bold text-slate-900">{item.occupation.name}</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            {item.score != null
              ? `Indicador ${fmt1(item.score)} (${lowerFirst(item.level_label)}). Su perfil cambia ${num((item.turnover ?? 0) * 100, 1)} % por año: vida media ${halfLifeText(item, page.half_life_cap)}.`
              : `Sin datos suficientes: las fuentes no tienen dos versiones comparables con al menos ${listText([...new Set(Object.values(params.dimensions).map((d) => num(d.min_items)))])} elementos.`}
          </p>
        </div>
        {item.score != null && <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${LEVEL_BADGE[item.level] ?? 'bg-slate-100 text-slate-700'}`}>{item.level_label}</span>}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {sources.map((c) => (
          <div key={c.dimension} className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-200 p-5">
            <div>
              <h3 className="font-semibold text-slate-900">{c.label}</h3>
              {comp(c) ? (
                <p className="text-xs text-slate-500">
                  Versión {c.from_version} ({monthYear(c.from_date)}) contra {c.to_version} ({monthYear(c.to_date)}), {num(c.years ?? 0, 1)} años · {c.n_from} → {c.n_to} elementos
                </p>
              ) : (
                <p className="text-xs text-slate-500">Sin dos versiones comparables para esta ocupación.</p>
              )}
            </div>
            {comp(c) && (
              <>
                <dl className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-[11px] text-slate-500">Novedades por año</dt><dd className="text-lg font-semibold tabular-nums text-slate-900">{perYear(c.new_per_year)}</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-[11px] text-slate-500">Recambio anual</dt><dd className="text-lg font-semibold tabular-nums text-slate-900">{num((c.annual ?? 0) * 100, 1)} %</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-[11px] text-slate-500">Vida media</dt><dd className="text-lg font-semibold tabular-nums text-slate-900">{halfLifeText({ half_life: c.half_life }, page.half_life_cap)}</dd></div>
                </dl>
                <div>
                  <p className="mb-1.5 text-sm font-medium text-slate-900">Entraron ({c.added_count})</p>
                  <ChipList items={c.added} shown={page.examples_shown} tone="in" />
                </div>
                <div>
                  <p className="mb-1.5 text-sm font-medium text-slate-900">Salieron ({c.removed_count})</p>
                  <ChipList items={c.removed} shown={page.examples_shown} tone="out" />
                </div>
                {(c.renamed_count ?? 0) > 0 && <p className="text-xs text-slate-500">{c.renamed_count} solo cambiaron de nombre y no cuentan como cambio.</p>}
              </>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        Los nombres son los de cada fuente, en su idioma original.{' '}
        <a href="#ranking" className="font-medium text-blue-700 hover:underline">Volver al ranking para elegir otra ocupación</a>
      </p>
    </section>
  );
}

function HowItsCalculated({ page, params, shortSource }: { page: RedQueenPage; params: RedQueenParams; shortSource: (d: string) => string }) {
  const lv = page.level_labels;
  const minItems = [...new Set(Object.values(params.dimensions).map((d) => d.min_items))];
  const weights = [...new Set(Object.values(params.dimensions).map((d) => d.weight))];
  return (
    <section className="mt-12 flex flex-col gap-4 border-t border-slate-200 pt-8">
      <h2 className="text-xl font-bold text-slate-900">Cómo se calcula</h2>
      <ol className="flex max-w-3xl list-decimal flex-col gap-2 pl-5 text-sm text-slate-700">
        <li><strong>Perfil</strong>: lo que cada fuente lista para la ocupación en cada versión ({listText(page.dimensions.map((d) => `${shortSource(d.dimension)}: ${lowerFirst(d.label.replace(/ \(.*\)$/, '').replace('Recambio de ', ''))}`))}).</li>
        <li><strong>Versiones comparadas</strong>: para cada año, la última versión publicada hasta ese año contra la última de al menos {num(params.window_years)} años antes (o la más vieja, si tiene al menos {num(params.min_years)} año de diferencia). Solo perfiles con al menos {listText(minItems.map((m) => num(m)))} elementos.</li>
        <li><strong>Renombres</strong>: si un nombre que sale está contenido en uno que entra (o al revés) y tiene al menos {num(params.rename_min_chars)} letras, cuentan como el mismo elemento.</li>
        <li><strong>Novedades por año</strong> = elementos que entraron / años entre versiones. Cada fuente se escala de 0 a {num(params.scale_max)} entre las ocupaciones con dato ese año y el indicador es su promedio{weights.length === 1 ? ' con el mismo peso' : ' ponderado'}. {lv.low} por debajo de {num(params.levels.low)}, {lowerFirst(lv.high ?? '')} por encima de {num(params.levels.high)}.</li>
        <li><strong>Recambio y vida media</strong>: recambio = 1 − (elementos en las dos versiones / elementos en alguna), anualizado; vida media = años hasta que el perfil comparte solo la mitad con el de hoy, ln(0,5) / ln(1 − recambio anual), con un tope de {num(params.half_life_cap, 0)} años.</li>
      </ol>
      <p className="max-w-3xl text-sm text-slate-600">
        Límites: {listText(page.dimensions.map((d) => shortSource(d.dimension)))} no distinguen países: el indicador es el mismo para los tres. Una versión puede cambiar porque la fuente revisó la clasificación y no porque cambió el trabajo, y no todas las ocupaciones se revisan en cada versión. Los perfiles grandes suman más novedades; en O*NET una ocupación puede reunir varias ocupaciones de Estados Unidos.
      </p>
    </section>
  );
}
