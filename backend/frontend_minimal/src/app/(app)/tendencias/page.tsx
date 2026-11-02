import type { Metadata } from 'next';
import Link from 'next/link';
import { connection } from 'next/server';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { IndicatorPicker } from '@/components/minimal/IndicatorPicker';
import { LinesChart, type LineSeries } from '@/components/minimal/LinesChart';
import { MotionChart } from '@/components/minimal/MotionChart';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { YearRange } from '@/components/minimal/YearRange';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, SourceLine } from '@/components/minimal/ui';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getMotion } from '@/lib/api/motion';
import { getCountries, getDashboardSummary, getIndicators, getProjections, getTrends } from '@/lib/api/panorama';
import { formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Tendencias' };

type SearchParams = { indicator?: string; periodo?: string; desde?: string; hasta?: string; burbujas?: string };
const YEARS_SHOWN = 10;
const YEARS_BACK = 30;
const PERIODS = [
  { value: '5', label: '5 años' },
  { value: '', label: '10 años' },
  { value: 'todo', label: 'Todo' },
];
const FREQUENCIES: Record<string, string> = { A: 'Anual', Q: 'Trimestral', M: 'Mensual' };
const BADGE: Record<string, string> = {
  favorable: 'bg-green-100 text-green-800',
  unfavorable: 'bg-red-100 text-red-800',
};
const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export default function TendenciasPage({ searchParams }: PageProps<'/tendencias'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <TendenciasContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

async function TendenciasContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  await connection();
  const thisYear = new Date().getFullYear();
  const custom = Boolean(sp.desde || sp.hasta);
  const shown = sp.periodo === 'todo' ? null : sp.periodo === '5' ? 5 : YEARS_SHOWN;
  const fromYear = custom ? sp.desde : shown ? String(thisYear - shown) : undefined;
  const toYear = custom ? sp.hasta : undefined;
  const yearOptions = Array.from({ length: YEARS_BACK }, (_, i) => thisYear - i);
  let data;
  try {
    const [indicators, countries] = await Promise.all([getIndicators(), getCountries()]);
    const iso = countries.map((c) => c.iso3);
    const highlight = countries[0] ? (await getDashboardSummary(countries[0].iso3)).highlights[0]?.indicator.code : undefined;
    const indicator = indicators.find((i) => i.code === sp.indicator) ?? indicators.find((i) => i.code === highlight) ?? indicators[0];
    const [projections, trends, motion] = await Promise.all([
      getProjections(indicator.code, iso, undefined, fromYear, toYear),
      getTrends(indicator.code, iso),
      // las burbujas son un complemento: si fallan, el resto de la página se muestra igual
      getMotion(sp.burbujas).catch(() => null),
    ]);
    data = { indicators, countries, indicator, projections, trends, motion };
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const { indicators, countries, indicator, projections, trends, motion } = data;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const unit = indicator.unit;
  const series: LineSeries[] = projections.items
    .filter((i) => i.observed.length)
    .map((i) => ({
      key: i.country_iso3,
      label: names[i.country_iso3] ?? i.country_iso3,
      color: COUNTRY_COLORS[i.country_iso3] ?? FALLBACK_COLOR,
      points: i.observed.map((p) => ({ period: p.period, start: p.period_start, value: p.value })),
      projected: i.projected.map((p) => ({ period: p.period, start: p.period_start, value: p.value, lower: p.lower_bound, upper: p.upper_bound })),
    }));
  const observed = projections.items.flatMap((i) => i.observed);
  const frequency = observed.at(-1)?.frequency ?? 'A';
  const method = projections.items.find((i) => i.methodology)?.methodology;
  const noProjection = projections.items.filter((i) => i.observed.length && !i.projected.length).map((i) => names[i.country_iso3]);

  return (
    <Page>
      <ChartHeader
        eyebrow={`Tendencia y proyección · ${FREQUENCIES[frequency] ?? frequency}`}
        title={<IndicatorPicker current={indicator} indicators={indicators} />}
        subtitle="Línea continua: observado. Punteada: proyección orientativa. Elegí un país para ver su intervalo."
        controls={
          <>
            <UrlSeg name="periodo" label="Período" value={custom ? 'rango' : sp.periodo ?? ''} options={PERIODS} reset={['desde', 'hasta']} />
            <YearRange years={yearOptions} desde={sp.desde} hasta={sp.hasta} />
          </>
        }
      />
      <ChartLayout
        chart={
          <>
            {series.length ? (
              <LinesChart series={series} unit={unit} mode="focus" ariaLabel={`${indicator.name}: observado y proyectado`} />
            ) : (
              <p className="py-24 text-center text-sm text-slate-500">No hay datos de este indicador.</p>
            )}
            <SourceLine
              source={`Fuente: ${[...new Set(observed.map((p) => p.source.name))].join(', ') || '—'}${method ? ` · proyección: ${method.name}, metodología #${method.methodology_id} v${method.version}` : ''}${noProjection.length ? ` · sin proyección: ${noProjection.join(', ')}` : ''}`}
            >
              <Link href={`/panorama?indicator=${indicator.code}`} className="text-blue-700 hover:underline">Ver en Panorama</Link>
            </SourceLine>
          </>
        }
        rail={
          <>
            <Eyebrow>Tendencia reciente</Eyebrow>
            {trends.map((t) => {
              const s = projections.items.find((i) => i.country_iso3 === t.country_iso3);
              const first = s?.observed.find((p) => p.period === t.window_start);
              const last = s?.observed.find((p) => p.period === t.window_end);
              const end = s?.projected.at(-1);
              const change = unit === 'percent' && first && last
                ? `${last.value - first.value > 0 ? '+' : ''}${one.format(last.value - first.value)} pp`
                : t.pct_change !== null ? `${t.pct_change > 0 ? '+' : ''}${one.format(t.pct_change * 100)}%` : null;
              return (
                <div key={t.country_iso3} className="rounded-xl border border-slate-200 p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-900">{names[t.country_iso3]}</span>
                    {t.assessment_label && <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE[t.assessment ?? ''] ?? 'bg-slate-100 text-slate-700'}`}>{t.assessment_label}</span>}
                  </div>
                  <p className="mt-1.5 text-sm text-slate-700">
                    {t.trend_state_label}{change ? ` · ${change}` : ''}
                    {t.window_start && <span className="text-slate-500"> ({t.window_start}–{t.window_end})</span>}
                  </p>
                  {end && (
                    <p className="mt-1 text-xs text-slate-500">
                      {end.period}: {formatValue(end.value, unit)}
                      {end.lower_bound != null && end.upper_bound != null ? ` (entre ${formatValue(end.lower_bound, unit)} y ${formatValue(end.upper_bound, unit)})` : ''}
                    </p>
                  )}
                </div>
              );
            })}
            <p className="text-xs leading-relaxed text-slate-500">La proyección prolonga la tendencia histórica: no anticipa cambios de política ni shocks.</p>
          </>
        }
      />
      {motion && motion.points.length > 0 && (
        <section className="mt-12 flex flex-col gap-4 border-t border-slate-200 pt-8" aria-labelledby="motion-title">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex max-w-3xl flex-col gap-1">
              <Eyebrow>Por grandes grupos de ocupaciones · {motion.years[0]}–{motion.years.at(-1)}</Eyebrow>
              <h2 id="motion-title" className="text-xl font-semibold text-slate-900">{motion.title}</h2>
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
      )}
      <div className="mt-10">
        <HowCalculated types={['trend', 'projection']} title="¿Cómo se calculan la tendencia y la proyección?" />
      </div>
    </Page>
  );
}
