import type { Metadata } from 'next';
import Link from 'next/link';
import { connection } from 'next/server';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { IndicatorPicker } from '@/components/minimal/IndicatorPicker';
import { LinesChart, type LineSeries } from '@/components/minimal/LinesChart';
import { MotionChart } from '@/components/minimal/MotionChart';
import { Sparkline } from '@/components/minimal/Sparkline';
import { FitViewport } from '@/components/minimal/FitViewport';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine, linkCls } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { YearRange } from '@/components/minimal/YearRange';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getGenerationalGap } from '@/lib/api/generational';
import { getMotion } from '@/lib/api/motion';
import { getCompare, getCountries, getDashboardSummary, getIndicators, getObservations, getProjections, getTrends } from '@/lib/api/panorama';
import type { GenerationalGap } from '@/lib/schemas/generational';
import type { Country, ObservationPoint } from '@/lib/schemas/api';
import { formatChange, formatDate, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Panorama' };

type SearchParams = { indicator?: string; periodo?: string; desde?: string; hasta?: string; burbujas?: string; tab?: string };
const PERIODS = [
  { value: '5', label: '5 años' },
  { value: '', label: '10 años' },
  { value: 'todo', label: 'Todo' },
];
const DEFAULT_YEARS = 10;
/** Años que ofrece el filtro Desde / Hasta (hacia atrás desde el actual). */
const YEARS_BACK = 30;
const SPARKS = 5;
const FREQUENCIES: Record<string, string> = { A: 'Anual', Q: 'Trimestral', M: 'Mensual' };
const BADGE: Record<string, string> = {
  favorable: 'bg-green-100 text-green-800',
  unfavorable: 'bg-red-100 text-red-800',
};

export default function PanoramaPage({ searchParams }: PageProps<'/panorama'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PanoramaContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** Totales (sin sector) en la frecuencia anual si existe; si no, la más común. */
function mainSeries(items: ObservationPoint[]) {
  const totals = items.filter((i) => i.sector_code === null && i.occupation_code === null);
  const base = totals.length ? totals : items;
  const freqs = [...new Set(base.map((i) => i.frequency))];
  const frequency = freqs.includes('A') ? 'A' : freqs[0] ?? 'A';
  return { frequency, points: base.filter((i) => i.frequency === frequency) };
}

function toSeries(points: ObservationPoint[], countries: Country[]): LineSeries[] {
  return countries
    .map((c) => ({
      key: c.iso3,
      label: c.name_es,
      color: COUNTRY_COLORS[c.iso3] ?? FALLBACK_COLOR,
      points: points
        .filter((p) => p.country_iso3 === c.iso3)
        .sort((a, b) => a.period_start.localeCompare(b.period_start))
        .map((p) => ({ period: p.period, start: p.period_start, value: p.value })),
    }))
    .filter((s) => s.points.length > 0);
}

async function PanoramaContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  if (sp.tab === 'brecha') return <GapTab />;
  if (sp.tab === 'movimiento') return <MotionTab y={sp.burbujas} />;
  await connection(); // el año actual se lee en cada request
  const thisYear = new Date().getFullYear();
  const custom = Boolean(sp.desde || sp.hasta);
  const years = sp.periodo === 'todo' ? null : sp.periodo === '5' ? 5 : DEFAULT_YEARS;
  const fromYear = custom ? sp.desde : years ? String(thisYear - years) : undefined;
  const toYear = custom ? sp.hasta : undefined;
  const yearOptions = Array.from({ length: YEARS_BACK }, (_, i) => thisYear - i);

  let data;
  try {
    const [indicators, countries] = await Promise.all([getIndicators(), getCountries()]);
    const iso = countries.map((c) => c.iso3);
    const highlight = countries[0] ? (await getDashboardSummary(countries[0].iso3)).highlights[0]?.indicator.code : undefined;
    const indicator = indicators.find((i) => i.code === sp.indicator) ?? indicators.find((i) => i.code === highlight) ?? indicators[0];
    const others = indicators.filter((i) => i.domain === indicator.domain && i.code !== indicator.code).slice(0, SPARKS);
    const [observations, compare, sparkObs, projections, trends] = await Promise.all([
      getObservations({ indicator: indicator.code, countries: iso, fromYear, toYear }),
      getCompare(indicator.code, iso),
      Promise.all(others.map((o) => getObservations({ indicator: o.code, countries: iso, fromYear: String(thisYear - DEFAULT_YEARS) }).catch(() => null))),
      // tendencia y proyección son un complemento: no todos los indicadores las tienen
      getProjections(indicator.code, iso, undefined, fromYear, toYear).catch(() => null),
      getTrends(indicator.code, iso).catch(() => []),
    ]);
    data = { indicators, countries, indicator, others, observations, compare, sparkObs, projections, trends };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { indicators, countries, indicator, others, observations, compare, sparkObs, projections, trends } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const { frequency, points } = mainSeries(observations.items);
  // La proyección arranca después del último dato: con un "Hasta" elegido quedaría separada de la línea.
  const series = toSeries(points, countries).map((s) => ({
    ...s,
    projected: sp.hasta ? [] : (projections?.items.find((i) => i.country_iso3 === s.key)?.projected ?? [])
      .filter((p) => p.frequency === frequency)
      .map((p) => ({ period: p.period, start: p.period_start, value: p.value, lower: p.lower_bound, upper: p.upper_bound })),
  }));
  const hasProjection = series.some((s) => s.projected.length > 0);
  const method = hasProjection ? projections?.items.find((i) => i.methodology)?.methodology : undefined;
  const withTrend = trends.filter((t) => t.trend_state !== 'insufficient_data');
  const updated = formatDate(points.map((p) => p.source_updated_at ?? p.fetched_at).sort().at(-1) ?? null);
  const sources = [...new Set(points.map((p) => p.source.name))].join(', ');

  // Columna de lectura: el último dato publicado o, con un rango de años elegido, el último del rango
  const rows = custom
    ? series.map((sr) => {
        const last = sr.points[sr.points.length - 1];
        const prev = sr.points[sr.points.length - 2];
        const diff = last && prev ? (indicator.unit === 'percent' ? last.value - prev.value : prev.value ? ((last.value - prev.value) / Math.abs(prev.value)) * 100 : null) : null;
        return { iso: sr.key, value: last?.value ?? null, period: last?.period ?? null, prevPeriod: prev?.period ?? null, change: diff !== null ? formatChange(diff, indicator.unit === 'percent' ? 'absolute' : 'relative', indicator.unit) : null };
      })
    : compare.items.map((c) => ({
        iso: c.country_iso3,
        value: c.current?.value ?? null,
        period: c.current?.period ?? null,
        prevPeriod: c.previous?.period ?? null,
        change: c.change !== null && c.previous ? formatChange(c.change, c.change_kind, indicator.unit) : null,
        raw: c.change,
      }));
  const latest = rows.filter((r) => r.value !== null);
  const top = [...latest].sort((a, b) => b.value! - a.value!)[0];
  const moved = custom ? undefined : compare.items.filter((c) => c.current && c.change !== null).sort((a, b) => Math.abs(b.change!) - Math.abs(a.change!))[0];
  const takeaway = [
    top && latest.length > 1 && `${names[top.iso]} tiene el valor más alto de los ${latest.length === 3 ? 'tres' : latest.length} (${formatValue(top.value!, indicator.unit)} en ${top.period}).`,
    moved && moved.previous && (latest.length > 1
      ? `El mayor cambio es el de ${names[moved.country_iso3]}: ${formatChange(moved.change, moved.change_kind, indicator.unit)} respecto de ${moved.previous.period}.`
      : `Solo ${names[moved.country_iso3]} tiene datos: ${formatChange(moved.change, moved.change_kind, indicator.unit)} respecto de ${moved.previous.period}.`),
  ].filter(Boolean).join(' ');

  const sparks = others.map((o, k) => {
    const obs = sparkObs[k];
    const { points: sp2 } = mainSeries(obs?.items ?? []);
    const periods = [...new Set(sp2.map((p) => p.period))].sort();
    const lines = countries.map((c) => ({
      color: COUNTRY_COLORS[c.iso3] ?? FALLBACK_COLOR,
      values: periods.map((p) => sp2.find((q) => q.country_iso3 === c.iso3 && q.period === p)?.value ?? null),
    }));
    const last = countries
      .map((c) => {
        const v = sp2.filter((q) => q.country_iso3 === c.iso3).sort((a, b) => a.period_start.localeCompare(b.period_start)).at(-1);
        return v ? `${c.iso3} ${formatValue(v.value, o.unit)}` : null;
      })
      .filter(Boolean)
      .join(' · ');
    return { code: o.code, name: o.name, lines, last };
  });

  return (
    <>
    <FitViewport className="mx-auto flex max-w-[1360px] flex-col px-4 pb-12 pt-7 sm:px-8 lg:pb-4 lg:pt-5">
      <ChartHeader
        eyebrow={`${indicator.domain_label} · ${FREQUENCIES[frequency] ?? frequency}`}
        title={<IndicatorPicker current={indicator} indicators={indicators} />}
        subtitle={[indicator.description, hasProjection ? 'Línea continua: observado. Punteada: proyección orientativa. Elegí un país para ver su intervalo.' : null].filter(Boolean).join(' ') || undefined}
        controls={
          <>
            <UrlSeg name="periodo" label="Período" value={custom ? 'rango' : sp.periodo ?? ''} options={PERIODS} reset={['desde', 'hasta']} />
            <YearRange years={yearOptions} desde={sp.desde} hasta={sp.hasta} />
          </>
        }
      />
      <ChartLayout
        className="items-start lg:min-h-[270px] lg:flex-1 lg:flex-nowrap lg:items-stretch lg:[&>aside]:overflow-y-auto"
        chart={
          <div className="flex h-full flex-col">
            {series.length ? (
              <div className="lg:flex-1">
                <LinesChart key={indicator.code} fill series={series} unit={indicator.unit} mode={hasProjection ? 'focus' : 'toggle'} ariaLabel={`${indicator.name} en ${series.map((s) => s.label).join(', ')}`} />
              </div>
            ) : (
              <p className="py-24 text-center text-sm text-slate-500 lg:flex-1">No hay datos de este indicador en el período elegido.</p>
            )}
            <SourceLine source={`Fuente: ${sources || '—'}${updated ? ` · actualizado el ${updated}` : ''} · dato observado${method ? ` · proyección: ${method.name}, metodología #${method.methodology_id} v${method.version}` : ''}`}>
              <Link href="/metodologia/indicadores" className="text-blue-700 hover:underline">¿Qué mide?</Link>
            </SourceLine>
          </div>
        }
        rail={
          <>
            <div>
              <Eyebrow>{custom ? 'Último dato del período elegido' : 'Último dato'}</Eyebrow>
              <div className="mt-2">
                {rows.map((r) => (
                  <div key={r.iso} className="flex items-baseline justify-between gap-3 border-b border-slate-100 py-2.5 lg:py-2">
                    <span className="text-sm text-slate-700">{names[r.iso] ?? r.iso}</span>
                    <span className="text-right">
                      <span className="text-[22px] font-bold text-slate-900">{r.value !== null ? formatValue(r.value, indicator.unit) : '—'}</span>
                      <span className="ml-2 text-xs text-slate-500">
                        {r.period ?? 'sin dato'}
                        {r.change ? ` · ${r.change}` : ''}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
            {takeaway && <p className="text-sm leading-relaxed text-slate-700">{takeaway}</p>}
            {withTrend.length > 0 && (
              <div className="flex flex-col gap-2">
                <Eyebrow>Tendencia reciente</Eyebrow>
                {withTrend.map((t) => {
                  const end = series.find((s) => s.key === t.country_iso3)?.projected.at(-1);
                  return (
                    <div key={t.country_iso3} className="rounded-xl border border-slate-200 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-slate-900">{names[t.country_iso3]}</span>
                        {t.assessment_label && <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE[t.assessment ?? ''] ?? 'bg-slate-100 text-slate-700'}`}>{t.assessment_label}</span>}
                      </div>
                      <p className="mt-1 text-sm text-slate-700">
                        {t.trend_state_label}
                        {t.window_start && <span className="text-slate-500"> ({t.window_start}–{t.window_end})</span>}
                      </p>
                      {end && (
                        <p className="mt-0.5 text-xs text-slate-500">
                          {end.period}: {formatValue(end.value, indicator.unit)}
                          {end.lower != null && end.upper != null ? ` (entre ${formatValue(end.lower, indicator.unit)} y ${formatValue(end.upper, indicator.unit)})` : ''}
                        </p>
                      )}
                    </div>
                  );
                })}
                {hasProjection && <p className="text-xs leading-relaxed text-slate-500">La proyección prolonga la tendencia histórica: no anticipa cambios de política ni shocks.</p>}
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Link href="/alertas" className={linkCls}>Ver alertas recientes →</Link>
            </div>
          </>
        }
      />
      {sparks.length > 0 && (
        <section className="mt-9 shrink-0 lg:mt-4" aria-label="Otros indicadores">
          <Eyebrow>Otros indicadores de {indicator.domain_label.toLowerCase()} · tocá uno para verlo grande</Eyebrow>
          <div className="mt-2 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            {sparks.map((s) => (
              <Link key={s.code} href={`/panorama?${new URLSearchParams({ indicator: s.code, ...(sp.periodo ? { periodo: sp.periodo } : {}), ...(sp.desde ? { desde: sp.desde } : {}), ...(sp.hasta ? { hasta: sp.hasta } : {}) })}`} scroll={false} className="flex flex-col gap-1 rounded-xl border border-slate-200 p-3.5 hover:border-blue-700 lg:px-3 lg:py-2">
                <span className="truncate text-[13px] font-semibold text-slate-900" title={s.name}>{s.name}</span>
                <Sparkline lines={s.lines} className="h-14 lg:h-9" />
                <span className="text-xs text-slate-500 lg:truncate" title={s.last || undefined}>{s.last || 'Sin datos recientes'}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </FitViewport>
    <div className="mx-auto max-w-[1360px] px-4 pb-12 sm:px-8">
      <div className="mt-10">
        <HowCalculated types={['trend', 'projection']} title="¿Cómo se calculan la tendencia y la proyección?" />
      </div>
    </div>
    </>
  );
}

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

async function GapTab() {
  let gap, countries;
  try {
    [gap, countries] = await Promise.all([getGenerationalGap(), getCountries()]);
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  return (
    <Page>
      {gap.countries.some((c) => c.latest)
        ? <GenerationalGapSection gap={gap} names={names} />
        : <p className="py-24 text-center text-sm text-slate-500">Todavía no hay datos de la brecha generacional.</p>}
    </Page>
  );
}

async function MotionTab({ y }: { y?: string }) {
  let motion, countries;
  try {
    [motion, countries] = await Promise.all([getMotion(y), getCountries()]);
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  if (motion.points.length === 0) {
    return <Page><p className="py-24 text-center text-sm text-slate-500">Todavía no hay datos de las ocupaciones en movimiento.</p></Page>;
  }
  return (
    <Page>
      <section className="flex flex-col gap-4" aria-labelledby="motion-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex max-w-3xl flex-col gap-1">
            <Eyebrow>Por grandes grupos de ocupaciones · {motion.years[0]}–{motion.years.at(-1)}</Eyebrow>
            <h1 id="motion-title" className="text-xl font-semibold text-slate-900">{motion.title}</h1>
            <p className="text-sm text-slate-600">
              {[motion.description, motion.y.description].filter(Boolean).join(' ')}
            </p>
          </div>
          <UrlSeg
            name="burbujas"
            label="Eje vertical"
            value={motion.y.key === motion.y_options[0]?.key ? '' : motion.y.key}
            options={motion.y_options.map((o, i) => ({ value: i === 0 ? '' : o.key, label: o.short_label ?? o.label }))}
            reset={[]}
          />
        </div>
        <MotionChart key={motion.y.key} data={motion} names={names} />
        <ul className="flex flex-col gap-1 text-xs leading-relaxed text-slate-500">
          {motion.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      </section>
    </Page>
  );
}

/** Brecha generacional: la desocupación de los jóvenes dividida por la del total, por país. */
function GenerationalGapSection({ gap, names }: { gap: GenerationalGap; names: Record<string, string> }) {
  const withData = gap.countries.filter((c) => c.latest).sort((a, b) => b.latest!.ratio - a.latest!.ratio);
  const series = withData.map((c) => ({
    key: c.country_iso3,
    label: names[c.country_iso3] ?? c.country_iso3,
    color: COUNTRY_COLORS[c.country_iso3] ?? FALLBACK_COLOR,
    points: c.points.map((p) => ({ period: String(p.year), start: `${p.year}-01-01`, value: p.ratio })),
  }));
  return (
    <section aria-labelledby="brecha-generacional">
      <Eyebrow>{gap.youth.name} sobre {gap.total.name.toLowerCase()}</Eyebrow>
      <h1 id="brecha-generacional" className="mt-1 text-xl font-bold text-slate-900">{gap.title}</h1>
      <p className="mt-1 max-w-3xl text-sm text-slate-600">{gap.description}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {withData.map((c) => (
          <div key={c.country_iso3} className="rounded-xl border border-slate-200 p-4">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-semibold text-slate-900">{names[c.country_iso3] ?? c.country_iso3}</span>
              <span className="text-3xl font-bold tabular-nums" style={{ color: COUNTRY_COLORS[c.country_iso3] ?? FALLBACK_COLOR }}>{one.format(c.latest!.ratio)}×</span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{c.headline}</p>
            <p className="mt-1.5 text-xs text-slate-500">
              Jóvenes {formatValue(c.latest!.youth, gap.youth.unit)} · todos {formatValue(c.latest!.total, gap.total.unit)}
              {c.points.length > 1 && ` · en ${c.points[0].year} era ${one.format(c.points[0].ratio)}×`}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-col gap-2">
        <p className="text-xs text-slate-500">Desocupación joven dividida por la general, por año (1 = sin brecha).</p>
        <LinesChart series={series} unit="ratio" ariaLabel="Brecha generacional por país y año" />
        <SourceLine source={`Fuente: ${gap.source ?? '—'} · ${gap.youth.name} y ${gap.total.name.toLowerCase()}, de las mismas encuestas de hogares`} />
      </div>
    </section>
  );
}
