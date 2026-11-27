import type { Metadata } from 'next';
import Link from 'next/link';
import { io } from 'next/cache';
import { GenerationalGapView } from '@/components/data/GenerationalGapView';
import { IndicatorPicker } from '@/components/data/IndicatorPicker';
import { LinesChart, type LineSeries } from '@/components/data/LinesChart';
import { OccupationMotionView } from '@/components/data/OccupationMotionView';
import { Sparkline } from '@/components/data/Sparkline';
import {
  ChartHeader,
  ChartLayout,
  ErrorNote,
  Eyebrow,
  Page,
  RailCard,
  SourceLine,
  linkCls,
} from '@/components/data/ui';
import { UrlSeg } from '@/components/data/UrlSeg';
import { YearRange } from '@/components/data/YearRange';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ApiError } from '@/lib/api/client';
import {
  getCompare,
  getCountries,
  getDashboardSummary,
  getIndicators,
  getObservations,
  getProjections,
  getTrends,
} from '@/lib/api/panorama';
import type { Country, ObservationPoint } from '@/lib/schemas/api';
import { formatChange, formatDate, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Panorama' };

type SearchParams = {
  indicator?: string;
  q?: string;
  periodo?: string;
  desde?: string;
  hasta?: string;
  burbujas?: string;
  tab?: string;
};

const PERIODS = [
  { value: '5', label: '5 años' },
  { value: '', label: '10 años' },
  { value: 'todo', label: 'Todo' },
];
const DEFAULT_YEARS = 10;
const YEARS_BACK = 30;
const SPARKS = 5;
/** Indicadores que ya no se muestran en el panorama. */
const HIDDEN_INDICATORS = new Set(['genai_exposure']);
const FREQUENCIES: Record<string, string> = { A: 'Anual', Q: 'Trimestral', M: 'Mensual' };
const BADGE: Record<string, string> = {
  favorable: 'bg-alert-positive-bg text-alert-positive-text',
  unfavorable: 'bg-alert-critical-bg text-alert-critical-text',
};

export default async function PanoramaPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  if (sp.tab === 'brecha')
    return (
      <Page>
        <GenerationalGapView />
      </Page>
    );
  if (sp.tab === 'movimiento')
    return (
      <Page>
        <OccupationMotionView sp={sp} />
      </Page>
    );
  return <PanoramaContent sp={sp} />;
}

/** Totales (sin sector) en la frecuencia anual si existe; si no, la más común. */
function mainSeries(items: ObservationPoint[]) {
  const totals = items.filter((i) => i.sector_code === null && i.occupation_code === null);
  const base = totals.length ? totals : items;
  const freqs = [...new Set(base.map((i) => i.frequency))];
  const frequency = freqs.includes('A') ? 'A' : (freqs[0] ?? 'A');
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

async function PanoramaContent({ sp }: { sp: SearchParams }) {
  await io(); // el año actual se lee en cada request
  const thisYear = new Date().getFullYear();
  const custom = Boolean(sp.desde || sp.hasta);
  const years = sp.periodo === 'todo' ? null : sp.periodo === '5' ? 5 : DEFAULT_YEARS;
  const fromYear = custom ? sp.desde : years ? String(thisYear - years) : undefined;
  const toYear = custom ? sp.hasta : undefined;
  const yearOptions = Array.from({ length: YEARS_BACK }, (_, i) => thisYear - i);

  let data;
  try {
    const [allIndicators, countries] = await Promise.all([getIndicators(), getCountries()]);
    const indicators = allIndicators.filter((i) => !HIDDEN_INDICATORS.has(i.code));
    const iso = countries.map((c) => c.iso3);
    const highlight = countries[0]
      ? (await getDashboardSummary(countries[0].iso3)).highlights[0]?.indicator.code
      : undefined;
    const query = sp.q?.trim().toLowerCase();
    const byQuery = query
      ? indicators.find((i) =>
          `${i.name} ${i.code} ${i.domain_label} ${i.description ?? ''}`.toLowerCase().includes(query),
        )
      : undefined;
    const indicator =
      indicators.find((i) => i.code === sp.indicator) ??
      byQuery ??
      indicators.find((i) => i.code === highlight) ??
      indicators[0];
    const others = indicators
      .filter((i) => i.domain === indicator.domain && i.code !== indicator.code)
      .slice(0, SPARKS);
    const [observations, compare, sparkObs, projections, trends] = await Promise.all([
      getObservations({ indicator: indicator.code, countries: iso, fromYear, toYear }),
      getCompare(indicator.code, iso),
      Promise.all(
        others.map((o) =>
          getObservations({
            indicator: o.code,
            countries: iso,
            fromYear: String(thisYear - DEFAULT_YEARS),
          }).catch(() => null),
        ),
      ),
      getProjections(indicator.code, iso, undefined, fromYear, toYear).catch(() => null),
      getTrends(indicator.code, iso).catch(() => []),
    ]);
    data = { indicators, countries, indicator, others, observations, compare, sparkObs, projections, trends };
  } catch (e) {
    return (
      <ErrorNote
        message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
      />
    );
  }

  const { indicators, countries, indicator, others, observations, compare, sparkObs, projections, trends } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const { frequency, points } = mainSeries(observations.items);
  const series = toSeries(points, countries).map((s) => ({
    ...s,
    projected: sp.hasta
      ? []
      : (projections?.items.find((i) => i.country_iso3 === s.key)?.projected ?? [])
          .filter((p) => p.frequency === frequency)
          .map((p) => ({
            period: p.period,
            start: p.period_start,
            value: p.value,
            lower: p.lower_bound,
            upper: p.upper_bound,
          })),
  }));
  const hasProjection = series.some((s) => s.projected.length > 0);
  const method = hasProjection ? projections?.items.find((i) => i.methodology)?.methodology : undefined;
  const withTrend = trends.filter((t) => t.trend_state !== 'insufficient_data');
  const updated = formatDate(
    points.map((p) => p.source_updated_at ?? p.fetched_at).sort().at(-1) ?? null,
  );
  const sources = [...new Set(points.map((p) => p.source.name))].join(', ');

  const rows = custom
    ? series.map((sr) => {
        const last = sr.points[sr.points.length - 1];
        const prev = sr.points[sr.points.length - 2];
        const diff =
          last && prev
            ? indicator.unit === 'percent'
              ? last.value - prev.value
              : prev.value
                ? ((last.value - prev.value) / Math.abs(prev.value)) * 100
                : null
            : null;
        return {
          iso: sr.key,
          value: last?.value ?? null,
          period: last?.period ?? null,
          prevPeriod: prev?.period ?? null,
          change:
            diff !== null
              ? formatChange(
                  diff,
                  indicator.unit === 'percent' ? 'absolute' : 'relative',
                  indicator.unit,
                )
              : null,
        };
      })
    : compare.items.map((c) => ({
        iso: c.country_iso3,
        value: c.current?.value ?? null,
        period: c.current?.period ?? null,
        prevPeriod: c.previous?.period ?? null,
        change:
          c.change !== null && c.previous
            ? formatChange(c.change, c.change_kind, indicator.unit)
            : null,
        raw: c.change,
      }));
  const latest = rows.filter((r) => r.value !== null);
  const top = [...latest].sort((a, b) => b.value! - a.value!)[0];
  const moved = custom
    ? undefined
    : compare.items
        .filter((c) => c.current && c.change !== null)
        .sort((a, b) => Math.abs(b.change!) - Math.abs(a.change!))[0];
  const takeaway = [
    top &&
      latest.length > 1 &&
      `${names[top.iso]} tiene el valor más alto de los ${latest.length === 3 ? 'tres' : latest.length} (${formatValue(top.value!, indicator.unit)} en ${top.period}).`,
    moved &&
      moved.previous &&
      (latest.length > 1
        ? `El mayor cambio es el de ${names[moved.country_iso3]}: ${formatChange(moved.change, moved.change_kind, indicator.unit)} respecto de ${moved.previous.period}.`
        : `Solo ${names[moved.country_iso3]} tiene datos: ${formatChange(moved.change, moved.change_kind, indicator.unit)} respecto de ${moved.previous.period}.`),
  ]
    .filter(Boolean)
    .join(' ');

  const sparks = others.map((o, k) => {
    const obs = sparkObs[k];
    const { points: sp2 } = mainSeries(obs?.items ?? []);
    const periods = [...new Set(sp2.map((p) => p.period))].sort();
    const lines = countries.map((c) => ({
      color: COUNTRY_COLORS[c.iso3] ?? FALLBACK_COLOR,
      values: periods.map(
        (p) => sp2.find((q) => q.country_iso3 === c.iso3 && q.period === p)?.value ?? null,
      ),
    }));
    const last = countries
      .map((c) => {
        const v = sp2
          .filter((q) => q.country_iso3 === c.iso3)
          .sort((a, b) => a.period_start.localeCompare(b.period_start))
          .at(-1);
        return v ? `${c.iso3} ${formatValue(v.value, o.unit)}` : null;
      })
      .filter(Boolean)
      .join(' · ');
    return { code: o.code, name: o.name, lines, last };
  });

  return (
    <>
      <div className="mx-auto max-w-[1600px] px-4 py-6 pb-12 sm:px-6">
        <ChartHeader
          eyebrow={`${indicator.domain_label} · ${FREQUENCIES[frequency] ?? frequency}`}
          title={<IndicatorPicker current={indicator} indicators={indicators} />}
          subtitle={
            [
              indicator.description,
              hasProjection
                ? 'Línea continua: observado. Punteada: proyección orientativa. Elegí un país para ver su intervalo.'
                : null,
            ]
              .filter(Boolean)
              .join(' ') || undefined
          }
          controls={
            <>
              <UrlSeg
                name="periodo"
                label="Período"
                value={custom ? 'rango' : (sp.periodo ?? '')}
                options={PERIODS}
                reset={['desde', 'hasta']}
              />
              <YearRange years={yearOptions} desde={sp.desde} hasta={sp.hasta} />
            </>
          }
        />
        <ChartLayout
          className="items-start"
          chart={
            <div className="flex min-h-[420px] flex-col">
              {series.length ? (
                <div className="lg:flex-1">
                  <LinesChart
                    key={indicator.code}
                    series={series}
                    unit={indicator.unit}
                    mode={hasProjection ? 'focus' : 'toggle'}
                    ariaLabel={`${indicator.name} en ${series.map((s) => s.label).join(', ')}`}
                  />
                </div>
              ) : (
                <p className="py-24 text-center text-sm text-muted-text lg:flex-1">
                  No hay datos de este indicador en el período elegido.
                </p>
              )}
              <SourceLine
                source={`Fuente: ${sources || '—'}${updated ? ` · actualizado el ${updated}` : ''} · dato observado${method ? ` · proyección: ${method.name}, metodología #${method.methodology_id} v${method.version}` : ''}`}
              >
                <Link href="/metodologia/indicadores" className="text-link hover:underline">
                  ¿Qué mide?
                </Link>
              </SourceLine>
            </div>
          }
          rail={
            <RailCard>
              <div>
                <Eyebrow>{custom ? 'Último dato del período elegido' : 'Último dato'}</Eyebrow>
                <div className="mt-2">
                  {rows.map((r) => (
                    <div
                      key={r.iso}
                      className="flex items-baseline justify-between gap-3 border-b border-card-border py-2.5 lg:py-2"
                    >
                      <span className="text-sm text-body">{names[r.iso] ?? r.iso}</span>
                      <span className="text-right">
                        <span className="text-[22px] font-bold text-heading">
                          {r.value !== null ? formatValue(r.value, indicator.unit) : '—'}
                        </span>
                        <span className="ml-2 text-xs text-muted-text">
                          {r.period ?? 'sin dato'}
                          {r.change ? ` · ${r.change}` : ''}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              {takeaway && <p className="text-sm leading-relaxed text-body">{takeaway}</p>}
              {withTrend.length > 0 && (
                <div className="flex flex-col gap-2">
                  <Eyebrow>Tendencia reciente</Eyebrow>
                  {withTrend.map((t) => {
                    const end = series.find((s) => s.key === t.country_iso3)?.projected.at(-1);
                    return (
                      <div key={t.country_iso3} className="rounded-xl border border-card-border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-heading">
                            {names[t.country_iso3]}
                          </span>
                          {t.assessment_label && (
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE[t.assessment ?? ''] ?? 'bg-surface-2 text-body'}`}
                            >
                              {t.assessment_label}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-body">
                          {t.trend_state_label}
                          {t.window_start && (
                            <span className="text-muted-text">
                              {' '}
                              ({t.window_start}–{t.window_end})
                            </span>
                          )}
                        </p>
                        {end && (
                          <p className="mt-0.5 text-xs text-muted-text">
                            {end.period}: {formatValue(end.value, indicator.unit)}
                            {end.lower != null && end.upper != null
                              ? ` (entre ${formatValue(end.lower, indicator.unit)} y ${formatValue(end.upper, indicator.unit)})`
                              : ''}
                          </p>
                        )}
                      </div>
                    );
                  })}
                  {hasProjection && (
                    <p className="text-xs leading-relaxed text-muted-text">
                      La proyección prolonga la tendencia histórica: no anticipa cambios de política
                      ni shocks.
                    </p>
                  )}
                </div>
              )}
              <div className="flex flex-col gap-2">
                <Link href="/alertas" className={linkCls}>
                  Ver alertas recientes →
                </Link>
              </div>
            </RailCard>
          }
        />
        {sparks.length > 0 && (
          <section className="mt-9 shrink-0 lg:mt-4" aria-label="Otros indicadores">
            <Eyebrow>
              Otros indicadores de {indicator.domain_label.toLowerCase()} · tocá uno para verlo
              grande
            </Eyebrow>
            <div className="mt-2 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
              {sparks.map((s) => (
                <Link
                  key={s.code}
                  href={`/panorama?${new URLSearchParams({
                    indicator: s.code,
                    ...(sp.periodo ? { periodo: sp.periodo } : {}),
                    ...(sp.desde ? { desde: sp.desde } : {}),
                    ...(sp.hasta ? { hasta: sp.hasta } : {}),
                  })}`}
                  scroll={false}
                  className="flex flex-col gap-1 rounded-xl border border-card-border p-3.5 hover:border-brand lg:px-3 lg:py-2"
                >
                  <span className="truncate text-[13px] font-semibold text-heading" title={s.name}>
                    {s.name}
                  </span>
                  <Sparkline lines={s.lines} className="h-14 lg:h-9" />
                  <span className="text-xs text-muted-text lg:truncate" title={s.last || undefined}>
                    {s.last || 'Sin datos recientes'}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
      <div className="mx-auto max-w-[1600px] px-4 pb-12 sm:px-6">
        <div className="mt-10">
          <HowCalculated
            types={['trend', 'projection']}
            title="¿Cómo se calculan la tendencia y la proyección?"
          />
        </div>
      </div>
    </>
  );
}

