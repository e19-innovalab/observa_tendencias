import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { LinesChart, type LineSeries } from '@/components/minimal/LinesChart';
import { Legend } from '@/components/minimal/MoctezumaCharts';
import { SisyphusChart, type SisyphusDot } from '@/components/minimal/SisyphusChart';
import { UrlSelect } from '@/components/minimal/UrlSelect';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine } from '@/components/minimal/ui';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/panorama';
import { getSisyphus, getSisyphusCountries } from '@/lib/api/sisyphus';
import { currentParams, formulaText, listText, lowerFirst, num, shareText } from '@/lib/methodology/twoSided';
import type { SisyphusItem, SisyphusPage as SisyphusData } from '@/lib/schemas/sisyphus';
import { formatScore as fmt1 } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Indicador Sísifo' };

const QUADRANT_BADGE: Record<string, string> = {
  sisyphus: 'bg-rose-100 text-rose-900',
  overqualified_paid: 'bg-amber-50 text-amber-900',
  low_pay: 'bg-slate-100 text-slate-700',
  fits: 'bg-teal-50 text-teal-800',
};
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
/** Salarios: USD primero y USD PPA al lado (la medida que usan los índices). */
const money = (usd: number | null | undefined, ppp: number | null | undefined) =>
  [usd != null ? `USD ${whole.format(usd)}` : null, ppp != null ? `USD PPA ${whole.format(ppp)}` : null].filter(Boolean).join(' · ') || '—';
const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `${num(v * 100, digits)} %`);

type SearchParams = { anio?: string };

export default function SisyphusPage({ searchParams }: PageProps<'/sisifo'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SisyphusContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

async function SisyphusContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  let data;
  try {
    const [countries, page, byCountry, params] = await Promise.all([
      getCountries(),
      getSisyphus({ year: sp.anio || undefined }),
      getSisyphusCountries(),
      currentParams('sisyphus_index'),
    ]);
    data = { countries, page, byCountry, params };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { countries, page, byCountry, params } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const color = (iso: string) => COUNTRY_COLORS[iso] ?? FALLBACK_COLOR;
  const [stone, reward] = page.sides;
  const rules = page.quadrant_rules;
  const qLabel = Object.fromEntries(page.quadrants.map((q) => [q.path, q.label]));
  const withData = page.items.filter((i) => i.overeducation != null && i.earnings_ratio != null);
  const groups = [...new Map(withData.map((i) => [i.group_code, i.group_name])).entries()].sort();
  const scored = page.items.filter((i) => i.score != null);
  const noData = [...new Map(page.items.filter((i) => i.score == null).map((i) => [i.group_code, i.group_name])).entries()];
  const tip = (i: SisyphusItem) =>
    `${names[i.country_iso3]} · ${i.group_code} ${i.group_name ?? ''}\n${i.quadrant_label ?? '—'}${i.score != null ? ` · indicador ${fmt1(i.score)}` : ''}\nSobreeducación: ${num(i.overeducation ?? 0, 1)} %\nIngreso del grupo: ${money(i.earnings_usd, i.earnings_ppp)}\nCon educación superior: USD PPA ${whole.format(i.tertiary_ppp ?? 0)} → ${num(i.earnings_ratio ?? 0, 2)} de lo que paga un título`;
  const dots: SisyphusDot[] = withData.map((i) => ({ key: `${i.country_iso3}-${i.group_code}`, x: i.overeducation!, y: i.earnings_ratio!, color: color(i.country_iso3), code: i.group_code, tip: tip(i) }));
  const countryLegend = [...new Set(page.items.map((i) => i.country_iso3))].sort().map((iso) => ({ label: names[iso], color: color(iso) }));
  const series = (pick: (p: (typeof byCountry)[number]['points'][number]) => number | null): LineSeries[] =>
    byCountry.map((c) => ({
      key: c.country_iso3,
      label: names[c.country_iso3],
      color: color(c.country_iso3),
      points: c.points.filter((p) => pick(p) != null).map((p) => ({ period: String(p.year), start: `${p.year}-01-01`, value: pick(p)! * 100 })),
    })).filter((s) => s.points.length);
  const sisyphusNow = withData.filter((i) => i.quadrant === 'sisyphus');

  return (
    <Page>
      <ChartHeader
        eyebrow="Indicador experimental · Anual"
        title="Indicador Sísifo"
        subtitle={`¿Dónde estudiar más no rinde? ${formulaText(params, stone, reward)}. Por encima de ${num(params.scale_max / 2)}, mucha gente tiene más estudios de los que pide el puesto y el puesto paga poco frente a un título.`}
        controls={
          <UrlSelect
            name="anio"
            label="Año"
            value={sp.anio && page.available_years.includes(Number(sp.anio)) ? sp.anio : ''}
            options={[...page.available_years].reverse().map((y, i) => ({ value: i === 0 ? '' : String(y), label: i === 0 ? `${y} (último)` : String(y) }))}
          />
        }
      />
      <ChartLayout
        chart={
          <>
            <Eyebrow>{page.year} · grandes grupos de ocupación por país</Eyebrow>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Cada círculo es un gran grupo de ocupación en un país (el número es el grupo). A la derecha de la línea vertical, al menos {num(rules.overeducated_from)} % tiene más estudios de los que pide el puesto; debajo de la horizontal, el grupo paga menos de {num(rules.paid_below, 2)} de lo que gana en promedio quien tiene educación superior. La zona roja es la piedra que vuelve a caer{sisyphusNow.length ? `: ${listText(sisyphusNow.map((i) => `${i.group_code} en ${names[i.country_iso3]}`))}` : ''}.
            </p>
            <div className="mt-3 flex flex-col gap-2">
              <Legend items={countryLegend} />
              <div className="hidden sm:block">
                <SisyphusChart dots={dots} overFrom={rules.overeducated_from} paidBelow={rules.paid_below} labels={qLabel} ariaLabel="Sobreeducación contra ingreso frente a un título, por grupo y país" />
              </div>
              <div className="sm:hidden">
                <SisyphusChart dots={dots} overFrom={rules.overeducated_from} paidBelow={rules.paid_below} labels={qLabel} width={440} height={420} ariaLabel="Sobreeducación contra ingreso frente a un título" />
              </div>
              <GroupList groups={page.groups.filter((g) => groups.some(([code]) => code === g.code))} source={page.groups_source} />
              <p className="text-xs text-slate-500">Los grupos {listText(page.excluded_groups)} no aparecen: piden educación superior, así que nadie puede tener más estudios de los que piden.</p>
            </div>
            <SourceLine source={`OIT (ILOSTAT): ocupados por ocupación y educación, ingresos por ocupación y por nivel educativo${page.methodology ? ` · metodología #${page.methodology.methodology_id} v${page.methodology.version}` : ''}`} />
          </>
        }
        rail={
          <>
            <Eyebrow>Por país · {page.year} o el último dato anterior</Eyebrow>
            {byCountry.map((c) => {
              const upTo = c.points.filter((p) => page.year == null || p.year <= page.year).reverse();
              const below = upTo.find((p) => p.graduates_below_share != null);
              const prem = upTo.find((p) => p.premium != null);
              return (
                <div key={c.country_iso3} className="rounded-xl border border-slate-200 p-3.5">
                  <p className="text-sm font-semibold text-slate-900">{names[c.country_iso3]}</p>
                  {below && (
                    <p className="mt-1.5 text-sm text-slate-700">
                      <span className="text-xl font-semibold tabular-nums text-slate-900">{pct(below.graduates_below_share)}</span> de quienes tienen educación superior trabaja en un puesto que no la pide ({below.year}).
                    </p>
                  )}
                  {prem && (
                    <p className="mt-1.5 text-xs text-slate-600">
                      El título paga {prem.premium! >= 0 ? '+' : ''}{pct(prem.premium)} más que la secundaria ({prem.year}): {money(prem.tertiary_usd, prem.tertiary_ppp)} contra {money(prem.secondary_usd, prem.secondary_ppp)}.
                    </p>
                  )}
                </div>
              );
            })}
            <p className="text-xs leading-relaxed text-slate-500">Ingresos mensuales medios de los asalariados (OIT). USD al tipo de cambio de mercado; USD PPA corrige las diferencias de precios entre países y es la medida que usa el indicador.</p>
          </>
        }
      />

      <section className="mt-12 grid gap-8 border-t border-slate-200 pt-8 lg:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-2">
          <h2 className="text-lg font-bold text-slate-900">Graduados en puestos que no piden título</h2>
          <p className="text-sm text-slate-600">Ocupados con educación superior que trabajan en un gran grupo que no la pide, como % de todos los ocupados con educación superior.</p>
          <LinesChart series={series((p) => p.graduates_below_share)} unit="percent" ariaLabel="Graduados en puestos que no piden título, por país" />
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <h2 className="text-lg font-bold text-slate-900">La prima salarial del título</h2>
          <p className="text-sm text-slate-600">Cuánto más gana en promedio quien tiene educación superior que quien tiene secundaria (USD PPA). Si sube a la vez que los graduados en puestos por debajo de su nivel, el título paga pero no a todos.</p>
          <LinesChart series={series((p) => p.premium)} unit="percent" ariaLabel="Prima salarial de la educación superior, por país" />
        </div>
      </section>

      <section className="mt-12 grid gap-3 sm:grid-cols-2">
        {page.quadrants.map((q) => (
          <div key={q.path} className="rounded-xl border border-slate-200 p-4">
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${QUADRANT_BADGE[q.path] ?? 'bg-slate-100 text-slate-700'}`}>{q.label}</span>
            <p className="mt-2 text-xs font-medium text-slate-500">{q.short}</p>
            <p className="mt-1 text-sm text-slate-700">{q.description}</p>
          </div>
        ))}
      </section>

      <section className="mt-12 grid gap-4 sm:grid-cols-2">
        {page.sides.map((s) => (
          <div key={s.side} className="rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-900">{s.label}</h3>
            <p className="mt-1.5 text-sm text-slate-700">{s.definition}</p>
            <ul className="mt-3 flex flex-col gap-2">
              {s.dimensions.map((d) => <li key={d.dimension} className="text-sm"><span className="font-medium text-slate-900">{d.label}</span><span className="text-slate-600"> · {d.definition}</span></li>)}
            </ul>
          </div>
        ))}
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-bold text-slate-900">Todos los grupos, {page.year}</h2>
        <p className="mt-1 text-sm text-slate-600">De más a menos Sísifo.{noData.length ? ` Sin datos de sobreeducación: ${listText(noData.map(([code, name]) => `${code} ${lowerFirst(name ?? '')}`))}.` : ''}</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm tabular-nums">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="py-2 pr-3 font-medium">Grupo</th>
                <th className="py-2 pr-3 font-medium">País</th>
                <th className="py-2 pr-3 text-right font-medium">Indicador</th>
                <th className="py-2 pr-3 font-medium">Cuadrante</th>
                <th className="py-2 pr-3 text-right font-medium">Sobreeducación</th>
                <th className="py-2 pr-3 text-right font-medium">Ingreso del grupo</th>
                <th className="py-2 text-right font-medium">Frente a un título</th>
              </tr>
            </thead>
            <tbody>
              {scored.map((i) => (
                <tr key={`${i.country_iso3}-${i.group_code}`} className="border-b border-slate-100">
                  <td className="py-2 pr-3 text-slate-900">
                    <a href={`#grupo-${i.group_code}`} className="hover:text-blue-700 hover:underline"><span className="font-semibold">{i.group_code}</span> {i.group_name}</a>
                  </td>
                  <td className="py-2 pr-3 text-slate-600">{names[i.country_iso3]}</td>
                  <td className="py-2 pr-3 text-right font-semibold text-slate-900">{fmt1(i.score)}</td>
                  <td className="py-2 pr-3">{i.quadrant && <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${QUADRANT_BADGE[i.quadrant]}`}>{i.quadrant_label}</span>}</td>
                  <td className="py-2 pr-3 text-right text-slate-700">{i.overeducation != null ? `${num(i.overeducation, 1)} %` : '—'}</td>
                  <td className="py-2 pr-3 text-right text-slate-700">{money(i.earnings_usd, i.earnings_ppp)}</td>
                  <td className="py-2 text-right text-slate-700">{i.earnings_ratio != null ? num(i.earnings_ratio, 2) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-12 flex flex-col gap-4 border-t border-slate-200 pt-8">
        <h2 className="text-xl font-bold text-slate-900">Cómo se calcula</h2>
        <ol className="flex max-w-3xl list-decimal flex-col gap-2 pl-5 text-sm text-slate-700">
          <li><strong>Unidad</strong>: gran grupo de ocupación (CIUO-08, 1 dígito) por país y año, porque la OIT publica así la sobreeducación y los ingresos por ocupación. Se usa el último dato de hasta {params.max_age_years} años antes.</li>
          {page.sides.map((s) => (
            <li key={s.side}><strong>{s.label}</strong>: {listText(s.dimensions.map((d) => lowerFirst(d.label)))}. Se escala de 0 a {num(params.scale_max)} entre todos los grupos de los {countries.length} países ese año.</li>
          ))}
          <li><strong>Indicador</strong>: {formulaText(params, stone, reward)}. Cada lado necesita datos para al menos {shareText(params.min_side_coverage)} de su peso. {page.level_labels.low} por debajo de {num(params.levels.low)}, {lowerFirst(page.level_labels.high ?? '')} por encima de {num(params.levels.high)}.</li>
          <li><strong>Cuadrante</strong>: con los valores sin escalar. Sobreeducado desde {num(rules.overeducated_from)} %; paga poco por debajo de {num(rules.paid_below, 2)} del ingreso medio con educación superior.</li>
          <li><strong>Por país</strong>: graduados en puestos que no piden título = ocupados con educación superior en grupos que no la piden / ocupados con educación superior; prima salarial = ingreso con educación superior / ingreso con secundaria − 1.</li>
        </ol>
        <p className="max-w-3xl text-sm text-slate-600">
          Límites: la OIT no publica ingresos por educación dentro de cada ocupación, así que la recompensa compara el promedio del grupo con el de quienes tienen educación superior, no lo que gana un graduado en ese grupo. En las ocupaciones elementales (grupo 9) la norma de la OIT pide solo primaria: cuenta como sobreeducado cualquiera con secundaria, por eso ese grupo queda siempre arriba.
        </p>
      </section>

      <div className="mt-10">
        <HowCalculated types={['sisyphus_index']} title="Metodología y parámetros vigentes" />
      </div>
    </Page>
  );
}

/** Qué incluye cada gran grupo (definición de la OIT) y ocupaciones de ejemplo con enlace a su ficha. */
function GroupList({ groups, source }: { groups: SisyphusData['groups']; source: Record<string, string> }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-medium text-slate-700">Qué incluye cada grupo</p>
      <ul className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
        {groups.map((g) => (
          <li key={g.code} id={`grupo-${g.code}`} className="scroll-mt-24">
            <details className="group rounded-lg border border-slate-200 px-3 py-2 text-xs open:bg-slate-50">
              <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                <span className="flex items-start gap-1.5">
                  <span className="mt-px text-[10px] text-slate-400 transition-transform group-open:rotate-90" aria-hidden>▶</span>
                  <span>
                    <span className="font-semibold text-slate-900">{g.code} {g.name}</span>
                    {g.definition && <span className="block text-slate-600">{g.definition}</span>}
                  </span>
                </span>
              </summary>
              {g.examples.length > 0 && (
                <div className="mt-2 pl-4">
                  <p className="text-slate-500">Por ejemplo ({g.examples.length} de {g.occupations} ocupaciones):</p>
                  <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    {g.examples.map((e) => (
                      <li key={e.occupation_code}>
                        <Link href={`/ocupaciones/${e.occupation_code}`} className="text-blue-700 hover:underline">{e.name}</Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </details>
          </li>
        ))}
      </ul>
      {source.url && (
        <p className="text-xs text-slate-500">
          Definiciones: <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">{source.label}</a>
        </p>
      )}
    </div>
  );
}
