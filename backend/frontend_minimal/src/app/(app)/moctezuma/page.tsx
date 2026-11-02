import type { Metadata } from 'next';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { Legend, Panel, PlaneChart, YearChart, type PlaneDot, type PlaneMark, type PlaneSeries, type YearSeries } from '@/components/minimal/MoctezumaCharts';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getMoctezuma, getMoctezumaCountries, getMoctezumaReference } from '@/lib/api/moctezuma';
import { getCountries } from '@/lib/api/panorama';
import { currentParams, lowerFirst, diagonalRule, formulaText, listText, num, shareText, shares, type TwoSidedParams } from '@/lib/methodology/twoSided';
import type { MoctezumaCountry, MoctezumaItem, MoctezumaPage, MoctezumaReference, MoctezumaSide, ReferenceSource } from '@/lib/schemas/moctezuma';
import { formatScore as fmt1 } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Indicador Moctezuma' };

type SearchParams = { pais?: string };
const LEVEL_BADGE: Record<string, string> = {
  high: 'bg-amber-100 text-amber-900',
  medium: 'bg-slate-100 text-slate-700',
  low: 'bg-teal-50 text-teal-800',
};
const HIST_COLOR = '#0f172a';
const ZONE_ITEM = { label: 'el cambio supera a la respuesta', zone: true };

export default function MoctezumaPage({ searchParams }: PageProps<'/moctezuma'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <MoctezumaContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** Valor crudo de una dimensión con su unidad: crecimientos y tasas en %, la exposición a la IA de 0 a 1. */
function rawText(measure: string, indicator: string, v: number | null | undefined) {
  if (v === null || v === undefined) return '—';
  if (measure === 'growth') return `${(v * 100).toLocaleString('es-AR', { minimumFractionDigits: Math.abs(v) < 0.1 ? 2 : 1, maximumFractionDigits: Math.abs(v) < 0.1 ? 2 : 1 })} %`;
  if (indicator === 'genai_exposure') return v.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${fmt1(v)} %`;
}

/** "Ritmo del cambio" -> "Ritmo". */
const short = (s: MoctezumaSide) => s.label.split(' ')[0];
/** Población con su unidad ("25,2 millones"). */
const popText = (ref: MoctezumaReference, v: number) => `${num(v, 3)} ${ref.population_unit}`;
const capitalize = (s: string) => s.replace(/^./, (c) => c.toUpperCase());

async function MoctezumaContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  let data;
  try {
    const [countries, byCountry, featured, reference, params] = await Promise.all([
      getCountries(),
      getMoctezumaCountries(),
      getMoctezuma({ featured: true, view: 'all', limit: 500 }),
      getMoctezumaReference(),
      currentParams('moctezuma_index'),
    ]);
    // sin limit: el ranking usa el tamaño configurado en el backend
    const ranking = await getMoctezuma({ featured: true, view: 'top', country: sp.pais || undefined });
    data = { countries, byCountry, featured, ranking, reference, params };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { countries, byCountry, featured, ranking, reference: ref, params } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const color = (iso: string) => COUNTRY_COLORS[iso] ?? FALLBACK_COLOR;
  const withData = byCountry.filter((c) => c.points.length);
  const method = withData.find((c) => c.methodology)?.methodology;
  const [push, counter] = featured.sides;
  const mid = params.scale_max / 2;

  const latest = withData.map((c) => ({ iso: c.country_iso3, p: c.points[c.points.length - 1], prev: c.points[c.points.length - 2] }));
  const above = latest.filter((l) => l.p.score > mid).map((l) => names[l.iso]);
  const year = featured.year;

  const tipToday = (who: string, pace: number, readiness: number, score: number) =>
    `${who}\n${short(push)} ${fmt1(pace)} · ${short(counter)} ${fmt1(readiness)}\nIndicador ${fmt1(score)}`;
  const planeToday: PlaneSeries[] = withData.map((c) => ({
    key: c.country_iso3,
    label: names[c.country_iso3],
    color: color(c.country_iso3),
    points: c.points.map((p, i) => ({
      x: p.pace,
      y: p.readiness,
      tip: tipToday(`${names[c.country_iso3]} ${p.year}`, p.pace, p.readiness, p.score),
      tag: i === c.points.length - 1 ? `${names[c.country_iso3]} ${p.year}` : undefined,
    })),
  }));
  const dots: PlaneDot[] = featured.items
    .filter((i) => i.score !== null)
    .map((i) => ({ x: i.pace!, y: i.readiness!, color: color(i.country_iso3), tip: tipToday(`${i.occupation.name}\n${names[i.country_iso3]} ${i.year}`, i.pace!, i.readiness!, i.score!) }));

  // versión histórica: todo sale de /moctezuma/reference
  const hist = ref.points;
  const [h0, hLast] = [hist[0], hist[hist.length - 1]];
  const hTags = new Set([h0.year, hist[1]?.year, ref.example_year, hLast.year]);
  const histTip = (h: (typeof hist)[number]) => `${h.year}\n${short(push)} ${fmt1(h.pace)} · ${short(counter)} ${fmt1(h.readiness)}\nPoblación ${popText(ref, h.population)}\nIndicador ${fmt1(h.score)}`;
  const planeHist: PlaneSeries[] = [{
    key: 'hist', label: ref.region, color: HIST_COLOR,
    // los eventos entran al recorrido: ritmo según el supuesto (máximo desde pace_full_from) y
    // capacidad sobre la línea entre las cifras de población de antes y después
    points: [
      ...hist.map((h) => ({ year: h.year, x: h.pace, y: h.readiness, tip: histTip(h), tag: hTags.has(h.year) ? String(h.year) : undefined, event: undefined as string | undefined })),
      ...ref.events.map((e) => {
        const after = hist.findIndex((h) => h.year > e.year);
        const a = hist[Math.max(after - 1, 0)], b = hist[after] ?? a;
        const readiness = b === a ? a.readiness : a.readiness + ((e.year - a.year) / (b.year - a.year)) * (b.readiness - a.readiness);
        const pace = e.year >= ref.pace_full_from ? hLast.pace : h0.pace;
        return { year: e.year, x: pace, y: readiness, tag: undefined, event: `${e.year} · ${e.label}`, tip: `${e.year} · ${e.label}\n${e.detail}\n${short(push)} ${fmt1(pace)} (supuesto) · ${short(counter)} sobre la línea entre ${a.year} y ${b.year}: no es una estimación.` };
      }),
    ].sort((p, q) => p.year - q.year),
  }];
  const yearsHist: YearSeries[] = [{ key: 'hist', label: '', color: HIST_COLOR, points: hist.map((h) => ({ year: h.year, value: h.score, tip: histTip(h) })) }];
  const hFrom = Math.floor((h0.year - 3) / 5) * 5;
  const hTo = Math.ceil((hLast.year + 5) / 5) * 5;
  const hTicks = Array.from({ length: 10 }, (_, i) => Math.ceil(hFrom / 20) * 20 + i * 20).filter((t) => t > hFrom && t < hTo);
  const decades = Math.round((hLast.year - ref.base_year) / 10);
  const paceYears = ref.pace_full_from - ref.contact_year;

  const yearsToday: YearSeries[] = withData.map((c) => ({
    key: c.country_iso3, label: names[c.country_iso3], color: color(c.country_iso3),
    points: c.points.map((p) => ({ year: p.year, value: p.score, tip: tipToday(`${names[c.country_iso3]} ${p.year}`, p.pace, p.readiness, p.score) })),
  }));
  const allYears = withData.flatMap((c) => c.points.map((p) => p.year));
  const [y0, y1] = [Math.min(...allYears), Math.max(...allYears)];
  const yearTicks = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  const countryLegend = withData.map((c) => ({ label: names[c.country_iso3], color: color(c.country_iso3) }));
  const zoneTime = { label: `por encima de ${num(mid)}: el cambio supera a la respuesta`, zone: true };
  const alt = ref.alternative;
  const altBase = hist.find((h) => h.year === alt.year);
  const markers = ref.events.map((e) => ({ year: e.year, label: e.label, detail: e.detail }));
  const annotations = Object.entries(ref.point_labels).map(([y, label]) => ({ year: Number(y), label, detail: ref.point_notes[y] }));
  const nationalDims = featured.sides.flatMap((s) => s.dimensions.filter((d) => d.scope === 'country').map((d) => lowerFirst(d.label)));

  return (
    <Page>
      <ChartHeader
        eyebrow="Indicador experimental · Anual"
        title="Indicador Moctezuma"
        subtitle={`¿El cambio tecnológico llega más rápido de lo que la sociedad puede responder? ${formulaText(params, push, counter)}. ${num(mid)} es equilibrio; por encima, el cambio supera a la respuesta.`}
      />
      <ChartLayout
        chart={
          <>
            {yearsToday.length ? (
              <div className="flex flex-col gap-3">
                <Legend items={[...countryLegend, zoneTime]} />
                <div className="hidden sm:block">
                  <YearChart series={yearsToday} from={y0} to={y1} ticks={yearTicks} width={900} height={420} ariaLabel="Indicador Moctezuma promedio por país" />
                </div>
                <div className="sm:hidden">
                  <YearChart series={yearsToday} from={y0} to={y1} ticks={yearTicks.filter((t) => t === y0 || t === y1 || (t - y0) % 2 === 0)} ariaLabel="Indicador Moctezuma promedio por país" />
                </div>
              </div>
            ) : (
              <p className="py-24 text-center text-sm text-slate-500">Todavía no hay resultados del indicador.</p>
            )}
            <SourceLine source={`Promedio simple de las ocupaciones con indicador de cada país · OIT, Banco Mundial y titulados oficiales${method ? ` · metodología #${method.methodology_id} v${method.version}` : ''}`} />
          </>
        }
        rail={
          <>
            <Eyebrow>Último año por país</Eyebrow>
            {latest.map(({ iso, p, prev }) => (
              <div key={iso} className="rounded-xl border border-slate-200 p-3.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900">{names[iso]}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${LEVEL_BADGE[p.level] ?? 'bg-slate-100 text-slate-700'}`}>{p.level_label}</span>
                </div>
                <p className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-900">
                  {fmt1(p.score)}
                  {prev && <span className="ml-2 text-xs font-normal text-slate-500">{p.score - prev.score >= 0 ? '+' : ''}{fmt1(p.score - prev.score)} vs {prev.year}</span>}
                </p>
                <p className="mt-1 text-xs text-slate-600">{short(push)} {fmt1(p.pace)} · {short(counter)} {fmt1(p.readiness)} · {p.year}</p>
                <p className="mt-0.5 text-xs text-slate-500">{p.scored} de {p.total} ocupaciones con datos</p>
              </div>
            ))}
            <p className="text-xs leading-relaxed text-slate-500">Puntajes relativos al grupo de los {countries.length} países: comparan países y ocupaciones entre sí, no miden un nivel absoluto.</p>
          </>
        }
      />

      <section className="mt-12">
        <h2 className="text-xl font-bold text-slate-900">Qué mide cada lado</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          {featured.sides.map((s) => (
            <div key={s.side} className="flex min-w-0 flex-col gap-3 border-t-[3px] border-teal-700 pt-4">
              <h3 className="text-lg font-semibold text-slate-900">{s.label}</h3>
              {s.definition && <p className="max-w-prose text-sm leading-relaxed text-slate-700">{s.definition}</p>}
              <dl className="flex flex-col gap-2.5">
                {s.dimensions.map((d) => (
                  <div key={d.dimension}>
                    <dt className="text-sm font-medium text-slate-900">{d.label}</dt>
                    {d.definition && <dd className="text-sm text-slate-600">{d.definition}</dd>}
                  </div>
                ))}
              </dl>
              {ref.side_history[s.side] && <p className="text-sm italic text-slate-500">En {ref.contact_year}: {ref.side_history[s.side]}</p>}
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-bold text-slate-900">{ref.contact_year} frente a hoy: {lowerFirst(push.label)} y {lowerFirst(counter.label)}</h2>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">Cada punto es una sociedad en un momento. Sobre la diagonal la respuesta acompaña al cambio; debajo, en la zona sombreada, el cambio va más rápido.</p>
        <div className="mt-4 grid gap-5 lg:grid-cols-2">
          <Panel era={`${h0.year} – ${hLast.year} · ${ref.region}`} title="Una sociedad que no alcanzó a responder" tag="ilustrativo · proxies históricos" read={`El ritmo llega al máximo en ${paceYears} años (${ref.contact_year}–${ref.pace_full_from}) y la capacidad cae de ${fmt1(h0.readiness)} a ${fmt1(hLast.readiness)} en ${decades} décadas.`}>
            <Legend items={[{ label: ref.region, color: HIST_COLOR }, ZONE_ITEM]} />
            <PlaneChart diagonalLabel={`equilibrio (${num(params.scale_max / 2)})`} series={planeHist} ariaLabel={`Trayectoria de ${ref.region} entre ${h0.year} y ${hLast.year}`} />
            {ref.events.length > 0 && <p className="text-xs text-slate-500">Puntos huecos: eventos. El ritmo sigue el supuesto ({fmt1(h0.pace)} hasta {ref.pace_full_from}, {fmt1(hLast.pace)} desde entonces) y la capacidad está sobre la línea entre las cifras de población de antes y después: marcan cuándo pasó, no son una estimación. Pasá el mouse para ver qué pasó.</p>}
          </Panel>
          <Panel era={`${y0} – ${y1} · promedio por país`} title={listText(withData.map((c) => names[c.country_iso3]))} tag="datos del observatorio" real read={`Los puntos chicos son las ocupaciones destacadas en ${year}. ${above.length ? `Por encima de ${num(mid)} en el último año: ${above.join(', ')}.` : `Ningún país supera ${num(mid)} en el último año.`}`}>
            <Legend items={[...countryLegend, ZONE_ITEM]} />
            <PlaneChart diagonalLabel={`equilibrio (${num(params.scale_max / 2)})`} series={planeToday} dots={dots} ariaLabel="Trayectorias por país en el plano ritmo contra capacidad" />
          </Panel>
          <Panel era={`${hFrom} – ${hTo}`} title={`El indicador en el tiempo, ${ref.region}`} tag="ilustrativo · proxies históricos" read={`De ${fmt1(h0.score)} antes del contacto a ${fmt1(hLast.score)} en ${hLast.year}.${hist.every((h, i) => i === 0 || h.score >= hist[i - 1].score) ? ' No vuelve a bajar.' : ''}`}>
            <Legend items={[{ label: ref.region, color: HIST_COLOR }, zoneTime]} />
            <YearChart series={yearsHist} from={hFrom} to={hTo} ticks={hTicks} markers={markers} annotations={annotations} ariaLabel={`Indicador ilustrativo de ${ref.region}`} />
            {markers.length > 0 && <p className="text-xs text-slate-500">Puntos huecos: {listText(markers.map((m) => `${m.year} ${lowerFirst(m.label)}`))}. Están sobre la línea entre las cifras de población de {ref.points[0].year} y {ref.points[1]?.year}: marcan cuándo pasó, no son una estimación. Pasá el mouse para ver qué pasó.</p>}
          </Panel>
          <Panel era={`${y0} – ${y1}`} title="El indicador en el tiempo, por país" tag="datos del observatorio" real read={`Misma fórmula y misma escala de 0 a ${num(params.scale_max)} que el panel histórico.`}>
            <Legend items={[...countryLegend, zoneTime]} />
            <YearChart series={yearsToday} from={y0} to={y1} ticks={yearTicks} ariaLabel="Indicador por país y año" />
          </Panel>
        </div>
      </section>

      <ReadingGuide page={featured} byCountry={withData} names={names} params={params} reference={ref} methodVersion={method?.version} />

      <Ranking page={ranking} names={names} pais={sp.pais ?? ''} countries={countries.map((c) => ({ value: c.iso3, label: c.name_es }))} />

      <section className="mt-12 flex flex-col gap-3 border-t border-slate-200 pt-8">
        <h2 className="text-xl font-bold text-slate-900">Cómo leer la comparación</h2>
        <ul className="flex max-w-3xl list-disc flex-col gap-2 pl-5 text-sm leading-relaxed text-slate-600">
          <li><strong className="text-slate-800">Las dos columnas no se miden en la misma escala.</strong> Hoy, ritmo y capacidad son puntajes relativos al grupo de los {countries.length} países (0 = el menor, {num(params.scale_max)} = el mayor). En {ref.contact_year} son proxies absolutos. La comparación es de forma y dirección, no de magnitud.</li>
          <li><strong className="text-slate-800">{h0.year}–{hLast.year}, capacidad:</strong> población de {ref.region} indexada a {ref.base_year} = {num(params.scale_max)} ({popText(ref, h0.population)} en {h0.year}, {popText(ref, hLast.population)} en {hLast.year}; las cifras más altas de la literatura, en debate; fuentes abajo). La caída se debió sobre todo a epidemias, violencia y trabajo forzado, no a una falta de adaptación: la población se usa como medida de la capacidad material que le quedó a esa sociedad.</li>
          {altBase && (
            <li><strong className="text-slate-800">Con otras estimaciones la curva cambia.</strong> Con las cifras de {alt.label} ({popText(ref, alt.base_population)} en {alt.base_year} y {popText(ref, alt.population)} en {alt.year}, una caída del {num(params.scale_max - alt.readiness, 0)} %), la capacidad en {alt.year} sería {fmt1(alt.readiness)} y el indicador {fmt1(alt.score)}, en lugar de {fmt1(altBase.score)} con la serie principal. {alt.score > mid ? 'En las dos estimaciones el cambio queda por encima de la respuesta; lo que varía es cuánto.' : 'Con esa estimación el cambio ya no supera a la respuesta: la conclusión depende de la fuente.'}</li>
          )}
          <li><strong className="text-slate-800">{h0.year}–{hLast.year}, ritmo:</strong> {ref.pace_note}</li>
          {nationalDims.length > 0 && <li><strong className="text-slate-800">Limitación actual:</strong> con {countries.length} países, las dimensiones nacionales ({listText(nationalDims)}) se escalan entre {countries.length} valores y pesan mucho en el promedio de cada país.</li>}
        </ul>
        <Chronology reference={ref} />
        <div className="mt-2 grid max-w-5xl gap-6 md:grid-cols-2">
          <SourceList title="Fuentes de la serie de población" items={ref.sources.series ?? []} />
          <SourceList title="Otras estimaciones y el debate" items={ref.sources.debate ?? []} />
          {(ref.sources.events ?? []).length > 0 && <SourceList title="Fuentes de la cronología" items={ref.sources.events} />}
        </div>
      </section>

      <HowItsCalculated page={featured} names={names} params={params} reference={ref} />

      <div className="mt-8">
        <HowCalculated types={['moctezuma_index']} title="Metodología y parámetros vigentes" />
      </div>
    </Page>
  );
}

/** Posición en un ranking: "el más alto", "intermedio" o "el más bajo" (y femenino). */
function rankWord(value: number, all: number[], fem: boolean) {
  const sorted = [...all].sort((a, b) => b - a);
  const i = sorted.indexOf(value);
  if (i === 0) return fem ? 'la más alta' : 'el más alto';
  if (i === sorted.length - 1) return fem ? 'la más baja' : 'el más bajo';
  return fem ? 'intermedia' : 'intermedio';
}

/** Dónde queda un punto respecto de la diagonal. */
function positionText(pace: number, readiness: number) {
  const gap = pace - readiness;
  if (Math.abs(gap) < 10) return 'Queda cerca de la diagonal, casi en equilibrio';
  return gap > 0 ? 'Está debajo de la diagonal: el cambio le gana a la respuesta' : 'Está por encima de la diagonal: la respuesta va por delante del cambio';
}

/**
 * Anexo de lectura en vivo: el plano con los países y la ocupación de ejemplo numerados, y cada lectura armada con
 * los datos vigentes (si los datos cambian, el texto cambia con ellos).
 */
function ReadingGuide({ page, byCountry, names, params, reference: ref, methodVersion }: { page: MoctezumaPage; byCountry: MoctezumaCountry[]; names: Record<string, string>; params: TwoSidedParams; reference: MoctezumaReference; methodVersion?: string }) {
  const year = page.year;
  const [push, counter] = page.sides;
  const color = (iso: string) => COUNTRY_COLORS[iso] ?? FALLBACK_COLOR;
  const countryPts = byCountry.flatMap((c) => {
    const p = c.points.find((x) => x.year === year);
    return p ? [{ iso: c.country_iso3, p }] : [];
  });
  const occ = page.items.filter((i) => i.occupation.occupation_code === ref.example_occupation && i.score !== null);
  if (!countryPts.length || !occ.length) return null;
  const occName = occ[0].occupation.name;
  const w = shares(params, push.side, counter.side);
  const equal = w.push === w.counter;
  const calc = (pace: number, readiness: number, score: number) =>
    equal
      ? `${num(params.scale_max * w.counter)} + (${fmt1(pace)} − ${fmt1(readiness)}) / ${num(1 / w.push)} = ${fmt1(score)}`
      : `${num(w.push)} × ${fmt1(pace)} + ${num(w.counter)} × (${num(params.scale_max)} − ${fmt1(readiness)}) = ${fmt1(score)}`;
  // los valores nacionales son los mismos para todas las ocupaciones del país: se leen de cualquiera
  const nationalComp = (iso: string, dim: string) =>
    page.items.find((i) => i.country_iso3 === iso && i.components.some((c) => c.dimension === dim && c.raw !== null))?.components.find((c) => c.dimension === dim);
  const dimText = (iso: string, side: MoctezumaSide, scope: string, item?: MoctezumaItem) =>
    side.dimensions
      .filter((d) => d.scope === scope)
      .map((d) => {
        const c = item ? item.components.find((x) => x.dimension === d.dimension) : nationalComp(iso, d.dimension);
        return c && c.raw !== null ? `${lowerFirst(d.label)}: ${rawText(c.measure, c.indicator, c.raw)}` : null;
      })
      .filter(Boolean)
      .join('; ');
  const paces = countryPts.map((c) => c.p.pace);
  const readies = countryPts.map((c) => c.p.readiness);
  const n = countryPts.length;

  const readings = [
    ...countryPts.map(({ iso, p }) => {
      const paceWhy = dimText(iso, push, 'country');
      const readyWhy = dimText(iso, counter, 'country');
      return {
        mark: { x: p.pace, y: p.readiness, color: color(iso), dashed: false },
        title: `${names[iso]} ${year}`,
        level: p.level, levelLabel: p.level_label, pace: p.pace, readiness: p.readiness, score: p.score,
        text: `${positionText(p.pace, p.readiness)}. Su ritmo es ${rankWord(p.pace, paces, false)} de los ${n}${paceWhy ? ` (${paceWhy})` : ''} y su capacidad, ${rankWord(p.readiness, readies, true)}${readyWhy ? ` (${readyWhy})` : ''}.`,
      };
    }),
    ...occ.map((o) => {
      const avg = countryPts.find((c) => c.iso === o.country_iso3)?.p;
      const own = [dimText(o.country_iso3, push, 'occupation', o), dimText(o.country_iso3, counter, 'occupation', o)].filter(Boolean).join('; ');
      const vs = avg
        ? `${o.pace! >= avg.pace ? 'Más' : 'Menos'} ritmo que el promedio de ${names[o.country_iso3]} (${fmt1(o.pace!)} contra ${fmt1(avg.pace)}) y ${o.readiness! >= avg.readiness ? 'más' : 'menos'} capacidad (${fmt1(o.readiness!)} contra ${fmt1(avg.readiness)})`
        : `${short(push)} ${fmt1(o.pace!)} y ${lowerFirst(short(counter))} ${fmt1(o.readiness!)}`;
      return {
        mark: { x: o.pace!, y: o.readiness!, color: color(o.country_iso3), dashed: true },
        title: `${occName} · ${names[o.country_iso3]}`,
        level: o.level, levelLabel: o.level_label, pace: o.pace!, readiness: o.readiness!, score: o.score!,
        text: `${vs}${own ? `, con ${own}` : ''}. ${positionText(o.pace!, o.readiness!)}.`,
      };
    }),
  ];
  const marks: PlaneMark[] = readings.map((r, i) => ({ n: i + 1, ...r.mark, tip: `${i + 1}. ${r.title}\nIndicador ${fmt1(r.score)}` }));

  // qué enseña la comparación: la misma ocupación en los distintos países
  const occDims = page.sides.flatMap((s) => s.dimensions.filter((d) => d.scope === 'occupation'));
  const rawOf = (o: MoctezumaItem, dim: string) => o.components.find((c) => c.dimension === dim);
  const sameText = occDims
    .filter((d) => rawOf(occ[0], d.dimension)?.raw != null && occ.every((o) => rawOf(o, d.dimension)?.raw === rawOf(occ[0], d.dimension)?.raw))
    .map((d) => {
      const c = rawOf(occ[0], d.dimension)!;
      return `${lowerFirst(d.label)} (${rawText(c.measure, c.indicator, c.raw)})`;
    });
  const top = occ.reduce((a, b) => (b.score! > a.score! ? b : a));
  const bottom = occ.reduce((a, b) => (b.score! < a.score! ? b : a));
  const histEx = ref.points.find((h) => h.year === ref.example_year);
  const todayMax = Math.max(...countryPts.map((c) => c.p.score), ...occ.map((o) => o.score!));
  const nationalDims = page.sides.flatMap((s) => s.dimensions.filter((d) => d.scope === 'country').map((d) => lowerFirst(d.label)));

  return (
    <section className="mt-12 rounded-xl border border-slate-200 bg-slate-50/60 p-5 sm:p-7">
      <Eyebrow>Anexo · cómo se lee</Eyebrow>
      <h2 className="mt-1 text-xl font-bold text-slate-900">Ejemplo de lectura: los {n} países y {occName} en {year}</h2>
      <p className="mt-1 max-w-3xl text-sm text-slate-600">Círculo lleno: promedio del país. Círculo punteado: {occName} en ese país. El gráfico y las lecturas se arman con los datos vigentes: si llegan datos nuevos, cambian con ellos.</p>
      <div className="mt-5 flex flex-wrap items-start gap-7">
        <figure className="m-0 min-w-0 flex-[1_1_380px] lg:max-w-[560px]">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <PlaneChart diagonalLabel={`equilibrio (${num(params.scale_max / 2)})`} series={[]} marks={marks} ariaLabel={`Plano ritmo contra capacidad con los ${n} países y ${occName} numerados`} />
          </div>
          <figcaption className="mt-2 text-xs text-slate-500">Datos {year}{methodVersion ? ` · metodología vigente v${methodVersion}` : ''}.</figcaption>
        </figure>
        <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-4">
          <div className="rounded-lg border border-teal-700/30 bg-white p-4">
            <h3 className="font-semibold text-slate-900">La regla para leer cualquier punto</h3>
            {equal && <p className="mt-1 text-sm leading-relaxed text-slate-600">Sobre la diagonal el indicador vale {num(params.scale_max * w.counter)}. Cada punto de distancia vertical por debajo suma {num(w.push)} punto (el cambio va más rápido que la respuesta) y cada punto por encima resta {num(w.push)} punto (la respuesta acompaña).</p>}
            <div className="mt-2.5"><Formula>{diagonalRule(params, { side: push.side, label: short(push) }, { side: counter.side, label: short(counter) })}</Formula></div>
            <p className="mt-2 text-xs text-slate-500">Es la misma fórmula de siempre, {formulaText(params, { side: push.side, label: short(push) }, { side: counter.side, label: short(counter) }).replace('Indicador = ', '')}, escrita de otra forma.</p>
          </div>
          <ol className="flex flex-col gap-3.5">
            {readings.map((r, i) => (
              <li key={r.title} className="flex gap-3">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">{i + 1}</span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">
                    {r.title}
                    <span className={`ml-2 rounded-full px-2 py-0.5 text-[11px] font-semibold ${LEVEL_BADGE[r.level] ?? 'bg-slate-100 text-slate-700'}`}>{r.levelLabel}</span>
                  </p>
                  <p className="mt-0.5 font-mono text-[12.5px] text-slate-700">{calc(r.pace, r.readiness, r.score)}</p>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">{r.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="text-sm leading-relaxed text-slate-600">
            <strong className="text-slate-800">Qué enseña la comparación.</strong>{' '}
            {sameText.length ? `La ocupación tiene la misma ${listText(sameText)} en los ${n} países. ` : ''}
            {nationalDims.length ? `Lo que cambia su lectura es el país: ${listText(nationalDims)}. ` : ''}
            {top.level !== bottom.level
              ? `Por eso la misma ocupación es de ${lowerFirst(top.level_label)} en ${names[top.country_iso3]} y de ${lowerFirst(bottom.level_label)} en ${names[bottom.country_iso3]}.`
              : `En los ${n} países queda en ${lowerFirst(top.level_label)}: de ${fmt1(bottom.score!)} en ${names[bottom.country_iso3]} a ${fmt1(top.score!)} en ${names[top.country_iso3]}.`}
          </p>
          {histEx && (
            <p className="text-sm leading-relaxed text-slate-600">
              <strong className="text-slate-800">Y frente a {ref.contact_year}.</strong> {ref.region} en {histEx.year} estaría en {short(push)} {fmt1(histEx.pace)} y {short(counter)} {fmt1(histEx.readiness)}: {calc(histEx.pace, histEx.readiness, histEx.score)}, {histEx.score > todayMax ? 'más lejos de la diagonal que cualquier punto de hoy' : 'dentro del rango de los puntos de hoy'}. Las escalas no son las mismas, así que sirve para ver la forma del desfase, no para comparar magnitudes.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

/** Eventos y cifras de población en orden: qué pasó y cuánto quedaba en cada momento. */
function Chronology({ reference: ref }: { reference: MoctezumaReference }) {
  const base = ref.points.find((p) => p.year === ref.base_year);
  const rows = [
    ...ref.events.map((e) => ({ year: e.year, n: true, title: e.label, text: e.detail })),
    ...ref.points.map((p) => ({
      year: p.year,
      n: false,
      title: `Población estimada: ${popText(ref, p.population)}${base && p.year !== base.year ? ` (${num((p.population / base.population - 1) * 100, 0)} % desde ${base.year})` : ''}`,
      text: ref.point_notes[String(p.year)] ?? null,
    })),
  ].sort((a, b) => a.year - b.year || (a.n ? -1 : 1));
  return (
    <div className="mt-2 max-w-3xl">
      <h3 className="text-sm font-semibold text-slate-900">Cronología</h3>
      <ol className="mt-2 flex flex-col gap-2.5 border-l-2 border-slate-200 pl-4">
        {rows.map((r) => (
          <li key={`${r.year}-${r.title}`} className="relative text-sm leading-relaxed">
            <span className={`absolute -left-[23px] top-1 size-3.5 rounded-full ${r.n ? 'border-2 border-teal-800 bg-white' : 'bg-slate-400'}`} />
            <span className="font-semibold tabular-nums text-slate-900">{r.year}</span>
            <span className="text-slate-900"> · {r.title}</span>
            {r.text && <p className="text-slate-600">{r.text}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function SourceList({ title, items }: { title: string; items: ReferenceSource[] }) {
  return (
    <div className="min-w-0">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <ul className="mt-2 flex flex-col gap-2.5">
        {items.map((s) => (
          <li key={s.url} className="text-sm leading-relaxed">
            <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-700 hover:underline">{s.label}</a>
            {s.detail && <p className="text-slate-600">{s.detail}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Ranking({ page, names, pais, countries }: { page: MoctezumaPage; names: Record<string, string>; pais: string; countries: { value: string; label: string }[] }) {
  const [push, counter] = page.sides;
  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Ocupaciones destacadas con mayor asimetría</h2>
          <p className="mt-1 text-sm text-slate-600">Donde el cambio más le gana a la respuesta, {page.year}.</p>
        </div>
        <UrlSeg name="pais" label="País" value={pais} options={[{ value: '', label: `Los ${countries.length}` }, ...countries]} reset={[]} />
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm tabular-nums">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
              <th className="py-2 pr-3 font-medium">Ocupación</th>
              <th className="py-2 pr-3 font-medium">País</th>
              <th className="py-2 pr-3 text-right font-medium">Indicador</th>
              <th className="py-2 pr-3 font-medium">Nivel</th>
              <th className="py-2 pr-3 text-right font-medium">{short(push)}</th>
              <th className="py-2 text-right font-medium">{short(counter)}</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((i) => (
              <tr key={`${i.country_iso3}-${i.occupation.occupation_code}`} className="border-b border-slate-100">
                <td className="py-2 pr-3 text-slate-900">{i.occupation.name}</td>
                <td className="py-2 pr-3 text-slate-600">{names[i.country_iso3]}</td>
                <td className="py-2 pr-3 text-right font-semibold text-slate-900">{i.score !== null ? fmt1(i.score) : '—'}</td>
                <td className="py-2 pr-3"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${LEVEL_BADGE[i.level] ?? 'bg-slate-100 text-slate-700'}`}>{i.level_label}</span></td>
                <td className="py-2 pr-3 text-right text-slate-700">{i.pace !== null ? fmt1(i.pace) : '—'}</td>
                <td className="py-2 text-right text-slate-700">{i.readiness !== null ? fmt1(i.readiness) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const Formula = ({ children }: { children: React.ReactNode }) => (
  <div className="overflow-x-auto rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2.5 font-mono text-[13px] leading-relaxed text-slate-800">{children}</div>
);

/** Pasos del cálculo armados con los parámetros vigentes, y un ejemplo con los datos vigentes de la API. */
function HowItsCalculated({ page, names, params, reference: ref }: { page: MoctezumaPage; names: Record<string, string>; params: TwoSidedParams; reference: MoctezumaReference }) {
  const [push, counter] = page.sides;
  const example = page.items.filter((i) => i.occupation.occupation_code === ref.example_occupation && i.score !== null);
  const dims = page.sides.flatMap((s) => s.dimensions.map((d) => ({ ...d, side: s.side, p: params.dimensions[d.dimension] })));
  type Dim = (typeof dims)[number];
  const comp = (item: MoctezumaItem, dim: string) => item.components.find((c) => c.dimension === dim);
  const lower = (ds: Dim[]) => listText(ds.map((d) => lowerFirst(d.label)));
  const sideOf = (side: string) => page.sides.find((s) => s.side === side)!;
  const sideSum = (item: MoctezumaItem, side: string) => {
    const vals = dims.filter((d) => d.side === side).map((d) => comp(item, d.dimension)?.normalized).filter((v): v is number => v != null).map((v) => fmt1(v));
    return `(${vals.join(' + ')}) / ${vals.length}`;
  };
  const w = shares(params, push.side, counter.side);
  const pushShort = { side: push.side, label: short(push) };
  const counterShort = { side: counter.side, label: short(counter) };
  const latest = dims.filter((d) => d.p?.measure === 'latest');
  const growth = dims.filter((d) => d.p?.measure === 'growth');
  const windows = [...new Set(growth.map((d) => d.p.window_years))];
  const growthText = windows.length === 1
    ? `${lower(growth)}, el crecimiento anual promedio en ${windows[0]} años`
    : listText(growth.map((d) => `${lowerFirst(d.label)}, el crecimiento anual promedio en ${d.p.window_years} años`));
  const conditions = [
    ...growth.filter((d) => d.p.min_base).map((d) => `${lowerFirst(d.label)}: solo si el valor inicial es al menos ${num(d.p.min_base!)}`),
    ...growth.filter((d) => d.p.exclude_years?.length).map((d) => `${lowerFirst(d.label)}: sin contar ${listText(d.p.exclude_years!.map(String))}`),
  ];
  const national = dims.filter((d) => d.scope === 'country');
  const inverted = dims.filter((d) => !d.higher_is_more);
  const equalWeights = page.sides.every((s) => new Set(dims.filter((d) => d.side === s.side).map((d) => d.p?.weight)).size === 1);
  const lv = page.level_labels;
  const histFirst = ref.points[0];
  const histLast = ref.points[ref.points.length - 1];
  const histEx = ref.points.find((h) => h.year === ref.example_year);
  const histBase = ref.points.find((h) => h.year === ref.base_year);
  const steps = [
    {
      title: 'Valor de cada dimensión para el año',
      body: `Para cada ocupación, país y año se toma el dato de cada dimensión, con datos de hasta ${params.max_age_years} años antes. ${latest.length ? `${capitalize(lower(latest))} usan el último valor; ` : ''}${growthText}${conditions.length ? ` (${conditions.join('; ')})` : ''}.${national.length ? ` ${capitalize(lower(national))} son nacionales: todas las ocupaciones del país comparten el valor.` : ''}`,
      formula: 'crecimiento = (valor final / valor inicial)^(1 / años) − 1',
    },
    {
      title: `Escala de 0 a ${num(params.scale_max)} dentro del grupo`,
      body: `El grupo son todas las ocupaciones de los países en el mismo año.${inverted.length ? ` Si un valor alto significa menos ritmo o menos capacidad (${lower(inverted)}), se invierte: ${num(params.scale_max)} − puntaje.` : ''} Si todo el grupo tiene el mismo valor, el puntaje es ${num(params.flat_cohort_score)}.`,
      formula: `puntaje = (valor − mínimo del grupo) / (máximo − mínimo) × ${num(params.scale_max)}`,
    },
    {
      title: `${push.label} y ${counter.label}`,
      body: `Promedio de las dimensiones de cada lado${equalWeights ? ', con el mismo peso' : ', ponderado por el peso de cada dimensión'}. Si falta una dimensión, se promedian las que hay. Si un lado tiene datos para menos de ${shareText(params.min_side_coverage)} de su peso, la ocupación queda como ${lv.insufficient_data ?? 'datos insuficientes'}.`,
      formula: page.sides.map((s) => `${short(s)} = promedio(${lower(dims.filter((d) => d.side === s.side))})`).join(' · '),
    },
    {
      title: 'Indicador de la ocupación',
      body: `${lv.low ?? 'Bajo'} por debajo de ${num(params.levels.low)}, ${(lv.high ?? 'alto').toLowerCase()} por encima de ${num(params.levels.high)}, ${(lv.medium ?? 'medio').toLowerCase()} en el medio.`,
      formula: formulaText(params, pushShort, counterShort),
    },
    {
      title: 'Valor global del país en cada año',
      body: `Promedio simple de las ocupaciones del país con indicador: cada ocupación pesa lo mismo, sin ponderar por ocupados. Como la fórmula es lineal, también vale ${formulaText(params, { side: push.side, label: `${short(push)} del país` }, { side: counter.side, label: `${short(counter)} del país` }).replace('Indicador', 'Indicador del país')}.`,
      formula: `Indicador del país = promedio del Indicador de sus ocupaciones (igual para ${short(push)} y ${short(counter)})`,
    },
  ];
  return (
    <section className="mt-12 flex flex-col gap-5 border-t border-slate-200 pt-8">
      <h2 className="text-xl font-bold text-slate-900">Cómo se calcula</h2>
      <ol className="flex flex-col gap-5">
        {steps.map((s, i) => (
          <li key={s.title} className="relative flex min-w-0 flex-col gap-2 pl-10">
            <span className="absolute left-0 top-0 grid size-6 place-items-center rounded-full border-[1.5px] border-teal-700 text-xs font-semibold text-teal-800">{i + 1}</span>
            <h3 className="font-semibold text-slate-900">{s.title}</h3>
            <p className="max-w-3xl text-sm leading-relaxed text-slate-600">{s.body}</p>
            <Formula>{s.formula}</Formula>
          </li>
        ))}
      </ol>

      {example.length > 0 && (
        <>
          <h3 className="mt-2 font-semibold text-slate-900">Ejemplo: {example[0].occupation.name}, {page.year}</h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-sm tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500">
                  <th className="py-2 pr-3 text-left font-medium">Dimensión</th>
                  <th className="py-2 pr-3 text-left font-medium">Lado</th>
                  <th className="py-2 pr-3 text-right font-medium">Mín. grupo</th>
                  <th className="py-2 pr-3 text-right font-medium">Máx. grupo</th>
                  {example.map((e) => (
                    <th key={e.country_iso3} colSpan={2} className="py-2 pr-3 text-right font-medium">{names[e.country_iso3]}: valor · puntaje</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dims.map((d) => {
                  const r = page.dimension_ranges[d.dimension];
                  const measure = comp(example[0], d.dimension)?.measure ?? 'latest';
                  return (
                    <tr key={d.dimension} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-900">{d.label}{d.higher_is_more ? '' : ' · invertida'}</td>
                      <td className="py-2 pr-3 text-slate-600">{short(sideOf(d.side))}</td>
                      <td className="py-2 pr-3 text-right text-slate-600">{rawText(measure, d.indicator, r?.observed_min)}</td>
                      <td className="py-2 pr-3 text-right text-slate-600">{rawText(measure, d.indicator, r?.observed_max)}</td>
                      {example.map((e) => {
                        const c = comp(e, d.dimension);
                        return [
                          <td key={`${e.country_iso3}v`} className="py-2 pr-3 text-right text-slate-700">{rawText(measure, d.indicator, c?.raw)}</td>,
                          <td key={`${e.country_iso3}n`} className="py-2 pr-3 text-right font-medium text-slate-900">{c?.normalized != null ? fmt1(c.normalized) : '—'}</td>,
                        ];
                      })}
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="text-slate-600">
                {page.sides.map((s, k) => (
                  <tr key={s.side}>
                    <td colSpan={4} className="pt-2.5 pr-3">{s.label}</td>
                    {example.map((e) => (
                      <td key={e.country_iso3} colSpan={2} className="pt-2.5 pr-3 text-right">{sideSum(e, s.side)} = <b className="font-semibold text-teal-800">{fmt1(k === 0 ? e.pace! : e.readiness!)}</b></td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <td colSpan={4} className="pt-2.5 pr-3">Indicador</td>
                  {example.map((e) => (
                    <td key={e.country_iso3} colSpan={2} className="pt-2.5 pr-3 text-right">{num(w.push)} × {fmt1(e.pace!)} + {num(w.counter)} × {fmt1(params.scale_max - e.readiness!)} = <b className="font-semibold text-teal-800">{fmt1(e.score!)}</b></td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}

      <h3 className="mt-2 font-semibold text-slate-900">La versión histórica ({histFirst.year}–{histLast.year})</h3>
      <Formula>
        {short(push)} = {fmt1(histFirst.pace)} en {histFirst.year} y {fmt1(histLast.pace)} desde {ref.pace_full_from} · {short(counter)} = población del año / población de {ref.base_year} × {num(params.scale_max)} · {formulaText(params, pushShort, counterShort)}
      </Formula>
      {histEx && histBase && (
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">
          Ejemplo {histEx.year}: {short(counter)} = {num(histEx.population, 3)} / {num(histBase.population, 3)} × {num(params.scale_max)} = {fmt1(histEx.readiness)}, así que Indicador = {num(w.push)} × {fmt1(histEx.pace)} + {num(w.counter)} × {fmt1(params.scale_max - histEx.readiness)} = {fmt1(histEx.score)}. La fórmula es la misma; cambian los datos de entrada, que son proxies y no puntajes relativos a un grupo.
        </p>
      )}
    </section>
  );
}
