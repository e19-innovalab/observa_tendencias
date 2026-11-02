import type { Metadata } from 'next';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { IndexChart, QuadrantChart, type IndexSeries, type QuadrantDot } from '@/components/minimal/LuditaCharts';
import { Legend } from '@/components/minimal/MoctezumaCharts';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getLudita, getLuditaCountries, getLuditaHistory } from '@/lib/api/ludita';
import { getCountries } from '@/lib/api/panorama';
import type { LuditaCase, LuditaItem, LuditaPage } from '@/lib/schemas/ludita';
import { currentParams, lowerFirst, formulaText, listText, num, shareText } from '@/lib/methodology/twoSided';
import { formatScore as fmt1 } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Indicador Ludita' };

type SearchParams = { pais?: string };
/** Colores de los casos históricos: distintos de los de país, que quedan para las curvas de hoy. */
const CASE_COLORS: Record<string, string> = { weaver: '#6d28d9', telephone_operator: '#be185d', teller: '#0f766e' };
const PATH_BADGE: Record<string, string> = {
  weaver: 'bg-pink-100 text-pink-900',
  teller: 'bg-teal-50 text-teal-800',
  other_causes: 'bg-slate-100 text-slate-700',
  out_of_reach: 'bg-sky-50 text-sky-800',
};
const PATH_BAR: Record<string, string> = { weaver: '#be185d', teller: '#0f766e', other_causes: '#94a3b8', out_of_reach: '#7dd3fc' };
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const thousands = (v: number) => (v < 10 ? `${v.toLocaleString('es-AR', { maximumFractionDigits: 2 })} mil` : `${whole.format(v)} mil`);

export default function LuditaPage({ searchParams }: PageProps<'/ludita'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <LuditaContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** Crecimiento promedio (fracción) de las dimensiones de vitalidad con dato: la regla de los caminos. */
function vitalityGrowth(i: LuditaItem) {
  const c = i.components.filter((x) => x.side === 'vitality' && x.raw !== null);
  const w = c.reduce((a, x) => a + x.weight, 0);
  return w ? c.reduce((a, x) => a + x.raw! * x.weight, 0) / w : null;
}

/** "Tejedores manuales de algodón (Gran Bretaña)" -> "Tejedores manuales de algodón". */
const shortCase = (c: LuditaCase) => c.label.replace(/ \(.*\)$/, '');

function caseSeries(c: LuditaCase, color: string, label: string, extra: Partial<IndexSeries> = {}): IndexSeries {
  return {
    key: c.key,
    label,
    color,
    ...extra,
    points: c.points.map((p) => ({
      x: p.years_since,
      y: p.index,
      hollow: p.approx,
      tip: `${label} · ${p.year}\n${p.years_since === 0 ? 'Año de llegada' : `${p.years_since > 0 ? '+' : ''}${p.years_since} años desde la llegada`} (${lowerFirst(c.technology)})\n${thousands(p.value)} personas${p.note ? ` (${p.note})` : p.approx ? ' (aprox.)' : ''}\nÍndice ${whole.format(p.index)} (${c.base_year} = 100)`,
    })),
  };
}

async function LuditaContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  let data;
  try {
    const [countries, byCountry, featured, history, params] = await Promise.all([
      getCountries(),
      getLuditaCountries(),
      getLudita({ featured: true, view: 'all', limit: 500 }),
      getLuditaHistory(),
      currentParams('ludita_index'),
    ]);
    // sin limit: el ranking usa el tamaño configurado en el backend
    const ranking = await getLudita({ featured: true, view: 'top', country: sp.pais || undefined });
    data = { countries, byCountry, featured, history, ranking, params };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { countries, byCountry, featured, history, ranking, params } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const color = (iso: string) => COUNTRY_COLORS[iso] ?? FALLBACK_COLOR;
  const pathLabel = Object.fromEntries(featured.paths.map((p) => [p.path, p.label]));
  const method = byCountry.find((c) => c.methodology)?.methodology;
  const year = featured.year;

  const todayLabel = history.today[0]?.label;
  const yMax = Math.ceil(Math.max(...history.cases.flatMap((c) => c.points.map((p) => p.index)), 100) / 50) * 50;
  const lastToday = history.today.map((c) => ({ iso: c.country_iso3!, p: c.points[c.points.length - 1] })).filter((t) => t.p);
  const change = (index: number) => `${index >= 100 ? '+' : ''}${fmt1(index - 100)} %`;
  // primeros años: las curvas de hoy, con los tejedores (la única serie histórica con datos en esos años) de referencia
  const yearsToday = Math.max(0, ...history.today.flatMap((c) => c.points.map((p) => p.years_since)));
  const zoomTo = history.zoom_years;
  const hasEarlyData = (c: LuditaCase) => c.points.filter((p) => p.years_since >= 0 && p.years_since <= zoomTo).length >= 3;
  const zoomRef = history.cases.filter(hasEarlyData).map((c) => {
    const s = caseSeries(c, '#64748b', c.label, { muted: true, endText: shortCase(c).split(' ')[0] });
    return { ...s, points: s.points.filter((p) => p.x >= -1 && p.x <= zoomTo) };
  });
  const zoomSkipped = history.cases.filter((c) => !hasEarlyData(c));
  const zoomToday = history.today.filter((c) => c.country_iso3).map((c) => {
    const last = c.points[c.points.length - 1];
    return caseSeries(c, color(c.country_iso3!), `${names[c.country_iso3!]}, hoy`, { endText: `${names[c.country_iso3!]} ${change(last.index)}` });
  });
  // cuándo empezó a caer cada caso de referencia: el primer dato por debajo de 100 después de la llegada
  const fallText = listText(zoomRef.map((s) => {
    const c = history.cases.find((x) => x.key === s.key)!;
    const fall = c.points.find((p) => p.years_since > 0 && p.index < 100);
    return fall ? `los ${lowerFirst(shortCase(c))} recién quedaron por debajo del año de llegada ${fall.years_since} años después (${fall.year})` : null;
  }).filter((t): t is string => Boolean(t)));
  const [push, counter] = featured.sides;
  const mid = params.scale_max / 2;
  const rules = featured.path_rules;
  const sources = [...new Set([...history.cases, ...history.today].map((c) => c.source_short).filter((v): v is string => Boolean(v)))];
  const dims = featured.sides.flatMap((s) => s.dimensions.map((d) => ({ ...d, side: s.side, p: params.dimensions[d.dimension] })));
  const growthDetail = (d: (typeof dims)[number]) =>
    d.p?.measure === 'growth'
      ? `${lowerFirst(d.label)} (crecimiento anual promedio en ${d.p.window_years} años${d.p.exclude_years?.length ? `, sin ${listText(d.p.exclude_years.map(String))}` : ''}${d.p.min_base ? `, si el valor inicial es al menos ${num(d.p.min_base)}` : ''})`
      : lowerFirst(d.label);
  const zoomValues = [...zoomRef, ...zoomToday].flatMap((s) => s.points.map((p) => p.y));
  const zoomMin = Math.floor(Math.min(95, ...zoomValues) / 5) * 5 - 5;
  const zoomMax = Math.ceil(Math.max(105, ...zoomValues) / 5) * 5 + 5;

  const dots: QuadrantDot[] = featured.items
    .filter((i) => i.score !== null && vitalityGrowth(i) !== null)
    .map((i) => {
      const exposure = i.components.find((c) => c.dimension === 'ai_exposure')?.raw ?? 0;
      const g = vitalityGrowth(i)! * 100;
      return {
        x: exposure,
        y: g,
        color: color(i.country_iso3),
        tip: `${i.occupation.name}\n${names[i.country_iso3]} ${i.year} · ${i.path_label ?? '—'}\nExposición ${exposure.toLocaleString('es-AR', { minimumFractionDigits: 2 })} · Crecimiento ${g > 0 ? '+' : ''}${fmt1(g)} % anual\nIndicador ${fmt1(i.score!)}`,
      };
    });
  const countryLegend = [...new Set(featured.items.map((i) => i.country_iso3))].sort().map((iso) => ({ label: names[iso], color: color(iso) }));
  const weaverToday = featured.items.filter((i) => i.path === 'weaver');

  return (
    <Page>
      <ChartHeader
        eyebrow="Indicador experimental · Anual"
        title="Indicador Ludita"
        subtitle={`¿Qué ocupaciones se parecen hoy a los oficios que la tecnología desplazó? ${formulaText(params, push, counter)}. Por encima de ${num(mid)}, la ocupación está expuesta y el mercado se retira.`}
      />
      <ChartLayout
        chart={
          <>
            <div className="flex flex-col gap-1">
              <Eyebrow>Tres caminos de la historia</Eyebrow>
              <p className="max-w-3xl text-sm text-slate-600">
                Empleo de tres oficios después de que llegó la tecnología que podía hacer su trabajo (100 = el año de llegada; misma escala en los tres). Debajo de cada panel, su máximo y su último dato.
              </p>
            </div>
            <div className="mt-4 grid gap-6 sm:grid-cols-3">
              {history.cases.map((c) => {
                const peak = c.points.reduce((a, p) => (p.value > a.value ? p : a));
                const peakYears = c.points.filter((p) => p.value === peak.value).map((p) => p.year);
                const last = c.points[c.points.length - 1];
                return (
                  <div key={c.key} className="flex min-w-0 flex-col gap-2">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">{shortCase(c)}</h3>
                      <p className="min-h-8 text-xs text-slate-500">{c.label.match(/\((.*)\)$/)?.[1]} · {lowerFirst(c.technology)} desde {c.arrival_year}</p>
                    </div>
                    <IndexChart
                      series={[caseSeries(c, CASE_COLORS[c.key] ?? FALLBACK_COLOR, shortCase(c), { endText: thousands(last.value) })]}
                      from={-5}
                      to={100}
                      yMax={yMax}
                      xTicks={[0, 25, 50, 75, 100]}
                      width={340}
                      height={260}
                      labelRoom={52}
                      ariaLabel={`${c.label}: empleo desde la llegada de ${lowerFirst(c.technology)}`}
                    />
                    <p className="text-xs leading-relaxed text-slate-600">
                      Máximo: {thousands(peak.value)} en {peakYears.length > 1 ? `${peakYears[0]}–${peakYears[peakYears.length - 1]}` : peak.year} (índice {whole.format(peak.index)}). Último dato: {thousands(last.value)} en {last.year}.
                    </p>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-slate-500">Eje horizontal: años desde la llegada de la tecnología. Puntos huecos: cifras aproximadas. Las líneas unen los años con dato; entre dato y dato no hay información.</p>
            <SourceLine source={sources.join(' · ')} />
          </>
        }
        rail={
          <>
            <Eyebrow>{year} · indicador por país</Eyebrow>
            {byCountry.filter((c) => c.points.length).map((c) => {
              const p = c.points[c.points.length - 1];
              const scored = Object.values(p.paths).reduce((a, b) => a + b, 0) || 1;
              return (
                <div key={c.country_iso3} className="rounded-xl border border-slate-200 p-3.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-900">{names[c.country_iso3]}</span>
                    <span className="text-lg font-semibold tabular-nums text-slate-900">{fmt1(p.score)}</span>
                  </div>
                  <div className="mt-2 flex h-2 overflow-hidden rounded-full" aria-hidden>
                    {featured.paths.map((x) => <span key={x.path} style={{ width: `${(p.paths[x.path] ?? 0) / scored * 100}%`, background: PATH_BAR[x.path] }} />)}
                  </div>
                  <p className="mt-1.5 text-xs text-slate-600">
                    {p.paths.weaver ?? 0} de {p.scored} ocupaciones en el camino del tejedor · {p.paths.teller ?? 0} en el del cajero
                  </p>
                </div>
              );
            })}
            <Legend items={featured.paths.map((x) => ({ label: x.label, color: PATH_BAR[x.path] }))} />
            {lastToday.length > 0 && (
              <p className="text-xs leading-relaxed text-slate-500">
                {todayLabel} desde {history.today[0].arrival_year}: {lastToday.map((t) => `${names[t.iso]} ${t.p.index >= 100 ? '+' : ''}${fmt1(t.p.index - 100)} %`).join(' · ')}.
              </p>
            )}
          </>
        }
      />

      <section className="mt-12 flex flex-col gap-3 border-t border-slate-200 pt-8">
        <h2 className="text-xl font-bold text-slate-900">Los primeros años: ¿dónde estamos?</h2>
        <p className="max-w-3xl text-sm text-slate-600">
          {todayLabel} en los {zoomToday.length} países desde {history.today[0]?.arrival_year ?? ''} ({history.today[0]?.technology}), con 100 = ese año. Estamos en el año {yearsToday}.{zoomRef.length > 0 && ` De referencia, en gris, ${listText(zoomRef.map((s) => shortCase(history.cases.find((c) => c.key === s.key)!).toLowerCase()))} en sus primeros ${zoomTo} años.`}{fallText && ` Para comparar: ${fallText}.`} {yearsToday} años de datos no alcanzan para saber qué camino sigue una ocupación.
        </p>
        <div className="hidden sm:block">
          <IndexChart series={[...zoomRef, ...zoomToday]} from={-1} to={zoomTo} yMin={zoomMin} yMax={zoomMax} yStep={5} xTicks={Array.from({ length: zoomTo + 1 }, (_, i) => i)} labelRoom={170} width={1100} height={400} ariaLabel="Primeros años desde la llegada de la tecnología: personal administrativo hoy y tejedores" />
        </div>
        <div className="sm:hidden">
          <IndexChart series={[...zoomRef, ...zoomToday]} from={-1} to={zoomTo} yMin={zoomMin} yMax={zoomMax} yStep={5} xTicks={[0, 2, 4, 6, 8, 10]} labelRoom={110} width={440} height={340} ariaLabel="Primeros años desde la llegada de la tecnología" />
        </div>
        {zoomSkipped.length > 0 && (
          <p className="text-xs text-slate-500">
            {zoomSkipped.map((c) => shortCase(c)).join(' y ')} no se muestran aquí: no hay datos en sus primeros {zoomTo} años (el siguiente dato es de {zoomSkipped.map((c) => c.points.find((p) => p.years_since > 0)?.year).join(' y ')}).
          </p>
        )}
      </section>

      <section className="mt-12 flex flex-col gap-3 border-t border-slate-200 pt-8">
        <h2 className="text-xl font-bold text-slate-900">¿Qué camino sigue cada ocupación?</h2>
        <p className="max-w-3xl text-sm text-slate-600">
          Ocupaciones destacadas en {year}. A la derecha de la línea vertical, la IA puede hacer buena parte de sus tareas (exposición desde {num(rules.exposed_from)}); debajo de la horizontal, el empleo y la formación crecen menos de {num(rules.retreat_below * 100)} % por año en promedio. La zona rosa es el camino del tejedor
          {weaverToday.length ? `: ${weaverToday.length} casos este año.` : '.'}
        </p>
        <Legend items={countryLegend} />
        {[{ cls: 'hidden sm:block', width: 900, height: 460 }, { cls: 'sm:hidden', width: 440, height: 420 }].map((v) => (
          <div key={v.cls} className={v.cls}>
            <QuadrantChart
              dots={dots}
              exposedFrom={rules.exposed_from}
              retreatBelow={rules.retreat_below * 100}
              labels={pathLabel}
              width={v.width}
              height={v.height}
              ariaLabel="Exposición a la IA contra crecimiento del empleo y la formación, ocupaciones destacadas"
            />
          </div>
        ))}
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {featured.paths.map((p) => (
            <div key={p.path} className="rounded-xl border border-slate-200 p-4">
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PATH_BADGE[p.path]}`}>{p.label}</span>
              <p className="mt-2 text-xs font-medium text-slate-500">{p.short}</p>
              <p className="mt-1 text-sm text-slate-700">{p.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12 grid gap-4 sm:grid-cols-2">
        {featured.sides.map((s) => (
          <div key={s.side} className="rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-900">{s.label}</h3>
            <p className="mt-1.5 text-sm text-slate-700">{s.definition}</p>
            <ul className="mt-3 flex flex-col gap-2">
              {s.dimensions.map((d) => (
                <li key={d.dimension} className="text-sm">
                  <span className="font-medium text-slate-900">{d.label}</span>
                  <span className="text-slate-600"> · {d.definition}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <Ranking page={ranking} names={names} pais={sp.pais ?? ''} countries={countries.map((c) => ({ value: c.iso3, label: c.name_es }))} />

      <section className="mt-12 flex flex-col gap-5 border-t border-slate-200 pt-8">
        <h2 className="text-xl font-bold text-slate-900">Cómo se calcula</h2>
        <ol className="flex max-w-3xl list-decimal flex-col gap-2 pl-5 text-sm text-slate-700">
          {featured.sides.map((s) => (
            <li key={s.side}><strong>{s.label}</strong>: {listText(dims.filter((d) => d.side === s.side).map(growthDetail))}, con datos de hasta {params.max_age_years} años antes; cada dimensión escalada de 0 a {num(params.scale_max)} entre todas las ocupaciones de los {countries.length} países ese año y promediadas.</li>
          ))}
          <li><strong>Indicador</strong>: {formulaText(params, push, counter)}. {num(mid)} es neutro; cada lado necesita datos para al menos {shareText(params.min_side_coverage)} de su peso. {featured.level_labels.low ?? 'Bajo'} por debajo de {num(params.levels.low)}, {(featured.level_labels.high ?? 'alto').toLowerCase()} por encima de {num(params.levels.high)}.</li>
          <li><strong>Camino</strong>: con los valores sin escalar, para que signifique lo mismo todos los años. Expuesta: exposición desde {num(rules.exposed_from)}. El mercado se retira: el crecimiento promedio de {listText(dims.filter((d) => d.side === counter.side).map((d) => lowerFirst(d.label)))} es menor que {num(rules.retreat_below * 100)} % anual.</li>
          <li><strong>País</strong>: promedio simple de sus ocupaciones con indicador.</li>
        </ol>
        <p className="max-w-3xl text-sm text-slate-600">
          Límites: la exposición no cambia por año ni por país; el empleo por ocupación se publica por grupos de ocupaciones, así que las ocupaciones de un grupo comparten esa señal; y las series históricas tienen pocos puntos y algunos aproximados. Es una analogía para leer los datos, no un pronóstico.
        </p>
        <div className="grid gap-6 sm:grid-cols-3">
          {history.cases.map((c) => (
            <div key={c.key} className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-900">{c.label}</h3>
              <p className="mt-1 text-xs text-slate-500">{c.arrival_note}</p>
              <ul className="mt-2 flex flex-col gap-2.5">
                {c.sources.map((s) => (
                  <li key={s.url} className="text-sm leading-relaxed">
                    <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-700 hover:underline">{s.label}</a>
                    {s.detail && <p className="text-slate-600">{s.detail}</p>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <SourceLine source={`Exposición: OIT (2025), WP 140 · empleo: OIT y SIMEL (INE Chile) · titulados: fuentes oficiales de cada país${method ? ` · metodología #${method.methodology_id} v${method.version}` : ''}`} />
      </section>

      <div className="mt-10">
        <HowCalculated types={['ludita_index']} title="Metodología y parámetros vigentes" />
      </div>
    </Page>
  );
}

function Ranking({ page, names, pais, countries }: { page: LuditaPage; names: Record<string, string>; pais: string; countries: { value: string; label: string }[] }) {
  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Ocupaciones destacadas que más se parecen al tejedor</h2>
          <p className="mt-1 text-sm text-slate-600">Más expuestas y con menos vitalidad, {page.year}.</p>
        </div>
        <UrlSeg name="pais" label="País" value={pais} options={[{ value: '', label: 'Los 3' }, ...countries]} reset={[]} />
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm tabular-nums">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
              <th className="py-2 pr-3 font-medium">Ocupación</th>
              <th className="py-2 pr-3 font-medium">País</th>
              <th className="py-2 pr-3 text-right font-medium">Indicador</th>
              <th className="py-2 pr-3 font-medium">Camino</th>
              <th className="py-2 pr-3 text-right font-medium">Exposición</th>
              <th className="py-2 text-right font-medium">Vitalidad</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((i) => (
              <tr key={`${i.country_iso3}-${i.occupation.occupation_code}`} className="border-b border-slate-100">
                <td className="py-2 pr-3 text-slate-900">{i.occupation.name}</td>
                <td className="py-2 pr-3 text-slate-600">{names[i.country_iso3]}</td>
                <td className="py-2 pr-3 text-right font-semibold text-slate-900">{i.score !== null ? fmt1(i.score) : '—'}</td>
                <td className="py-2 pr-3">{i.path && <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PATH_BADGE[i.path]}`}>{i.path_label}</span>}</td>
                <td className="py-2 pr-3 text-right text-slate-700">{i.exposure !== null ? fmt1(i.exposure) : '—'}</td>
                <td className="py-2 text-right text-slate-700">{i.vitality !== null ? fmt1(i.vitality) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
