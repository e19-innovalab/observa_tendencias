import { ChartCard } from '@/components/ui/charts/ChartCard';
import {
  COUNTRY_COLORS,
  FALLBACK_COLOR,
  type ChartRow,
  type ChartSeries,
} from '@/components/ui/charts/chartTheme';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { FilterBar, type FilterConfig } from '@/components/ui/filters/FilterBar';
import { IndicatorSidebar } from '@/components/ui/indicators/IndicatorSidebar';
import { KpiCard } from '@/components/ui/indicators/KpiCard';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { SessionControl } from '@/components/auth/SessionControl';
import { ApiError } from '@/lib/api/client';
import {
  getCountries,
  getDashboardSummary,
  getIndicators,
  getObservations,
  getSectors,
} from '@/lib/api/panorama';
import { connection } from 'next/server';
import type { Country, ObservationPoint } from '@/lib/schemas/api';
import { formatChange, formatDate, formatValue } from '@/lib/utils/format';

type SearchParams = {
  tab?: string;
  indicator?: string;
  country?: string;
  sector?: string;
  period?: string;
};
type Props = { searchParams: Promise<SearchParams> };

/** Una fila por período y una columna por país, lista para Recharts. */
function buildChart(items: ObservationPoint[], countries: Country[]) {
  const sorted = [...items].sort((a, b) => a.period_start.localeCompare(b.period_start));
  const rows = new Map<string, ChartRow>();
  const present = new Set<string>();
  for (const it of sorted) {
    const row = rows.get(it.period) ?? { label: it.period };
    row[it.country_iso3] = it.value;
    rows.set(it.period, row);
    present.add(it.country_iso3);
  }
  const series: ChartSeries[] = countries
    .filter((c) => present.has(c.iso3))
    .map((c) => ({
      key: c.iso3,
      label: c.name_es,
      color: COUNTRY_COLORS[c.iso3] ?? FALLBACK_COLOR,
    }));
  return { data: [...rows.values()], series };
}

async function load(sp: SearchParams) {
  const [countries, sectors, indicators] = await Promise.all([
    getCountries(),
    getSectors(),
    getIndicators(),
  ]);

  // Las secciones salen de los dominios que devuelve el backend
  const domains: { id: string; label: string }[] = [];
  for (const i of indicators) {
    if (!domains.some((d) => d.id === i.domain)) domains.push({ id: i.domain, label: i.domain_label });
  }
  const tab = domains.find((d) => d.id === sp.tab)?.id ?? domains[0]?.id ?? '';
  const inDomain = indicators.filter((i) => i.domain === tab);
  const indicator = inDomain.find((i) => i.code === sp.indicator) ?? inDomain[0];

  const kpiCountry = sp.country ?? countries[0]?.iso3;
  const chartCountries = sp.country ? [sp.country] : countries.map((c) => c.iso3);

  const [summary, observations] = await Promise.all([
    kpiCountry ? getDashboardSummary(kpiCountry) : null,
    indicator
      ? getObservations({
          indicator: indicator.code,
          countries: chartCountries,
          sector: indicator.has_sector_breakdown ? sp.sector : undefined,
          fromYear: sp.period,
        })
      : null,
  ]);

  return { countries, sectors, domains, tab, inDomain, indicator, kpiCountry, summary, observations };
}

export default async function PanoramaRegionalPage({ searchParams }: Props) {
  await connection();
  const sp = await searchParams;

  let result: Awaited<ReturnType<typeof load>> | null = null;
  let errorMessage = '';
  try {
    result = await load(sp);
  } catch (e) {
    errorMessage = e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.';
  }

  if (!result) {
    return (
      <>
        <PageHero title="Panorama regional" description="Indicadores de Argentina, Uruguay y Chile." />
        <div className="mx-auto max-w-3xl px-6 py-10">
          <p role="alert" className="border border-red-300 bg-red-50 p-4 text-sm text-red-900">
            {errorMessage} Revisá la consola donde corre <code>npm run dev</code> para ver el detalle.
          </p>
        </div>
      </>
    );
  }

  const { countries, sectors, domains, tab, inDomain, indicator, kpiCountry, summary, observations } = result;

  const thisYear = new Date().getFullYear();
  const filters: FilterConfig[] = [
    { name: 'country', label: 'País', options: countries.map((c) => ({ value: c.iso3, label: c.name_es })) },
    ...(indicator?.has_sector_breakdown
      ? [{ name: 'sector', label: 'Sector', options: sectors.map((s) => ({ value: s.sector_code, label: s.name })) }]
      : []),
    {
      name: 'period',
      label: 'Período',
      options: Array.from({ length: 10 }, (_, i) => String(thisYear - i)).map((y) => ({
        value: y,
        label: `Desde ${y}`,
      })),
    },
  ];

  // KPIs de la sección activa (si no hay, los destacados en general)
  const highlights = summary?.highlights ?? [];
  const inTab = highlights.filter((h) => h.indicator.domain === tab);
  const kpis = (inTab.length ? inTab : highlights).slice(0, 4);
  const kpiCountryName = countries.find((c) => c.iso3 === kpiCountry)?.name_es;

  // Serie del gráfico: sin sector elegido se usan los totales
  const items = observations?.items ?? [];
  const totals = items.filter((i) => i.sector_code === null && i.occupation_code === null);
  const used = sp.sector ? items : totals.length ? totals : items;
  const chart = buildChart(used, countries);
  const updatedAt = formatDate(
    used.map((i) => i.source_updated_at ?? i.fetched_at).sort().at(-1) ?? null,
  );
  const sourceName = [...new Set(used.map((i) => i.source.name))].join(', ') || null;

  return (
    <>
      <PageHero
        title="Panorama regional"
        description="Compará indicadores de Argentina, Uruguay y Chile con datos de fuentes oficiales."
      />

      <div className="mx-auto max-w-7xl px-6 pt-4">
        <SessionControl />
      </div>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-6">
        <div className="space-y-6">
          <SectionTabs tabs={domains.map((d) => ({ id: d.id, label: d.label }))} active={tab} />
          <FilterBar filters={filters} />
        </div>

        {kpis.length > 0 && (
          <section aria-label="Indicadores destacados" className="space-y-3">
            <h2 className="text-sm text-gray-600">Indicadores destacados de {kpiCountryName}</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map((k) => (
                <KpiCard
                  key={k.indicator.code}
                  label={k.indicator.name}
                  value={k.current ? formatValue(k.current.value, k.indicator.unit) : 'Sin dato'}
                  caption={k.current?.period}
                  changeText={formatChange(k.change, k.change_kind, k.indicator.unit)}
                  negative={k.change !== null && k.change < 0}
                />
              ))}
            </div>
          </section>
        )}

        <div className="grid gap-8 lg:grid-cols-[14rem_1fr]">
          <IndicatorSidebar
            items={inDomain.map((i) => ({ code: i.code, name: i.name }))}
            active={indicator?.code ?? ''}
          />
          {indicator ? (
            <ChartCard
              title={indicator.name}
              subtitle={indicator.description ?? undefined}
              legend={chart.series.map((s) => ({ label: s.label, color: s.color }))}
              sourceName={sourceName}
              updatedAt={updatedAt}
            >
              {chart.data.length > 0 ? (
                <TrendLineChart data={chart.data} series={chart.series} unit={indicator.unit} />
              ) : (
                <p className="py-16 text-center text-sm text-gray-600">
                  No hay datos observados para esta combinación de filtros. Probá con otro período
                  o quitá el filtro de sector.
                </p>
              )}
            </ChartCard>
          ) : (
            <p className="text-sm text-gray-600">No hay indicadores disponibles en esta sección.</p>
          )}
        </div>
      </div>
    </>
  );
}
