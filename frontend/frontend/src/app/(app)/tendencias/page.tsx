import type { Metadata } from 'next';
import { io } from 'next/cache';
import { ChipGroup, CountTabs } from '@/components/data/UrlControls';
import { CountryFilter } from '@/components/data/CountryFilter';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { OptionPills } from '@/components/ui/controls/OptionPills';
import { ApiErrorNote, EmptyDataNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { FilterBar, type FilterConfig } from '@/components/ui/filters/FilterBar';
import { FilterLabel, FilterPanel } from '@/components/ui/filters/FilterPanel';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { ApiError } from '@/lib/api/client';
import { getCountries, getIndicators, getObservations, getSectors } from '@/lib/api/panorama';
import { getProjections, getTrends } from '@/lib/api/trends';
import { unitLabel } from '@/lib/constants';
import type { Country, Indicator, ObservationPoint, Sector, TrendItem } from '@/lib/schemas/api';
import { buildCountryChart, buildProjectionChart } from '@/lib/utils/charts';
import { formatDate, formatSignedPercent } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Tendencias' };

type SearchParams = {
  tab?: string;
  country?: string;
  sector?: string;
  group?: string;
  indicator?: string;
  from?: string;
  to?: string;
  freq?: string;
};

const FREQ_LABELS: Record<string, string> = {
  A: 'Anual',
  Q: 'Trimestral',
  M: 'Mensual',
};

function provenance(points: ObservationPoint[]) {
  const dates = points
    .map((point) => point.source_updated_at ?? point.fetched_at)
    .filter((value): value is string => Boolean(value))
    .sort();
  const sources = [...new Set(points.map((point) => point.source.name))];
  return {
    updatedAt: formatDate(dates.at(-1) ?? null),
    sourceName: sources.join(', ') || null,
  };
}

function trendSummary(trends: TrendItem[], countries: Country[]): string | null {
  if (trends.length === 0) return null;
  return trends
    .map((trend) => {
      const name =
        countries.find((country) => country.iso3 === trend.country_iso3)?.name_es ??
        trend.country_iso3;
      const change =
        trend.pct_change === null ? '' : ` (${formatSignedPercent(trend.pct_change)})`;
      return `${name}: ${trend.trend_state_label}${change}`;
    })
    .join(' · ');
}

export default async function TendenciasPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  await io(); // el año actual y las series se calculan por request
  const sp = await searchParams;
  const tab = sp.tab === 'projections' ? 'projections' : 'trends';

  let countries: Country[] = [];
  let indicators: Indicator[] = [];
  let sectors: Sector[] = [];
  let errorMessage = '';

  try {
    [countries, indicators, sectors] = await Promise.all([
      getCountries(),
      getIndicators(),
      getSectors(),
    ]);
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar los catálogos.';
  }

  if (errorMessage || countries.length === 0 || indicators.length === 0) {
    return (
      <>
        <PageHero
          title="Tendencias"
          description="Seguí la evolución de los indicadores socioeconómicos, laborales y educativos de Argentina, Chile y Uruguay."
        />
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <ApiErrorNote message={errorMessage} />
        </div>
      </>
    );
  }

  const domains: { id: string; label: string; count: number }[] = [];
  for (const indicator of indicators) {
    const existing = domains.find((domain) => domain.id === indicator.domain);
    if (existing) existing.count += 1;
    else domains.push({ id: indicator.domain, label: indicator.domain_label, count: 1 });
  }

  const domain = domains.find((item) => item.id === sp.group)?.id ?? domains[0].id;
  const inDomain = indicators.filter((indicator) => indicator.domain === domain);
  const indicator = inDomain.find((item) => item.code === sp.indicator) ?? inDomain[0];

  const selectedCountries =
    sp.country && sp.country !== 'all'
      ? [sp.country]
      : countries.map((country) => country.iso3);

  const currentYear = new Date().getFullYear();
  const from = sp.from ?? String(currentYear - 10);
  const to = sp.to ?? String(currentYear + 1);

  let chart: Awaited<ReturnType<typeof buildCountryChart>> = { data: [], series: [] };
  let points: ObservationPoint[] = [];
  let trends: TrendItem[] = [];
  let error: string | null = null;

  try {
    if (tab === 'projections') {
      const result = await getProjections({
        indicator: indicator.code,
        countries: selectedCountries,
        sector: indicator.has_sector_breakdown ? sp.sector : undefined,
        fromYear: from,
        toYear: to,
      });

      const freq = sp.freq ?? 'all';
      const filtered = {
        ...result,
        items: result.items.map((item) => ({
          ...item,
          observed:
            freq === 'all'
              ? item.observed
              : item.observed.filter((point) => point.frequency === freq),
          projected:
            freq === 'all'
              ? item.projected
              : item.projected.filter((point) => point.frequency === freq),
        })),
      };

      chart = buildProjectionChart(filtered, countries);
      points = filtered.items.flatMap((item) => [...item.observed, ...item.projected]);
    } else {
      const [observations, trendItems] = await Promise.all([
        getObservations({
          indicator: indicator.code,
          countries: selectedCountries,
          sector: indicator.has_sector_breakdown ? sp.sector : undefined,
          fromYear: from,
          toYear: to,
        }),
        getTrends({
          indicator: indicator.code,
          countries: selectedCountries,
          sector: indicator.has_sector_breakdown ? sp.sector : undefined,
          fromYear: from,
          toYear: to,
        }),
      ]);

      points =
        (sp.freq ?? 'all') === 'all'
          ? observations.items
          : observations.items.filter((point) => point.frequency === sp.freq);
      chart = buildCountryChart(points, countries);
      trends = trendItems;
    }
  } catch (caught) {
    error = caught instanceof ApiError ? caught.message : 'Error inesperado al cargar la serie.';
  }

  const frequencies = [...new Set(points.map((point) => point.frequency))].filter(
    (frequency) => FREQ_LABELS[frequency],
  );
  const freqOptions = [
    { value: 'all', label: 'Todas' },
    ...frequencies.map((frequency) => ({ value: frequency, label: FREQ_LABELS[frequency] })),
  ];

  const years = Array.from({ length: currentYear + 2 - 2000 }, (_, index) => {
    const year = String(currentYear + 1 - index);
    return { value: year, label: year };
  });

  const filters: FilterConfig[] = [
    ...(indicator.has_sector_breakdown
      ? [
          {
            name: 'sector',
            label: 'Sector',
            options: sectors.map((sector) => ({ value: sector.sector_code, label: sector.name })),
          },
        ]
      : []),
    { name: 'from', label: 'Desde', defaultValue: from, options: years },
    { name: 'to', label: 'Hasta', defaultValue: to, options: years },
  ];

  const { updatedAt, sourceName } = provenance(points);
  const summary = trendSummary(trends, countries);

  return (
    <>
      <PageHero
        title="Tendencias"
        description="Seguí la evolución de los indicadores socioeconómicos, laborales y educativos de Argentina, Chile y Uruguay, y compará su proyección."
      />

      <div className="mx-auto max-w-7xl space-y-4 px-4 py-6 sm:px-6">
        <SectionTabs
          tabs={[
            { id: 'trends', label: 'Tendencias' },
            { id: 'projections', label: 'Proyecciones' },
          ]}
          active={tab}
        />

        <FilterPanel>
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <FilterLabel>Países</FilterLabel>
              <CountryFilter
                countries={countries}
                value={sp.country && sp.country !== 'all' ? sp.country : ''}
                reset={['page']}
              />
            </div>
            <FilterBar filters={filters} />
          </div>

          <div className="mt-4">
            <CountTabs
              name="group"
              label="Grupo de indicadores"
              options={domains.map((item) => ({
                value: item.id,
                label: item.label,
                count: item.count,
              }))}
              value={domain}
              reset={['indicator']}
            />
          </div>

          <div className="mt-3.5 flex flex-wrap items-center gap-x-6 gap-y-3">
            <div className="flex items-center gap-2.5">
              <FilterLabel>Frecuencia</FilterLabel>
              <OptionPills
                param="freq"
                label="Frecuencia"
                options={freqOptions}
                defaultValue="all"
                variant="segment"
              />
            </div>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <FilterLabel>Indicador</FilterLabel>
              <ChipGroup
                name="indicator"
                label="Indicador"
                hideLabel
                withAll={false}
                options={inDomain.map((item) => ({ value: item.code, label: item.name }))}
                value={indicator.code}
              />
            </div>
          </div>
        </FilterPanel>

        {error && <ApiErrorNote message={error} />}

        <InfoNote title="Indicador activo en visualización">
          {indicator.name} · Unidad: {unitLabel(indicator.unit)}.{' '}
          {indicator.description ?? 'Sin descripción metodológica informada.'}
          {summary && <> Estado de la tendencia: {summary}.</>}
        </InfoNote>

        <ChartCard
          title={tab === 'projections' ? `Proyección · ${indicator.name}` : indicator.name}
          subtitle={
            tab === 'projections'
              ? 'Serie observada y escenario proyectado por el observatorio. La línea punteada no reemplaza los datos observados.'
              : `Evolución ${frequencies.length === 1 ? `(${FREQ_LABELS[frequencies[0]]})` : ''} del indicador para los países seleccionados.`
          }
          legend={chart.series.map((item) => ({ label: item.label, color: item.color }))}
          sourceName={sourceName}
          updatedAt={updatedAt}
          methodologyHref="/panorama-regional"
        >
          {chart.data.length > 0 ? (
            <TrendLineChart data={chart.data} series={chart.series} unit={indicator.unit} />
          ) : (
            <EmptyDataNote>
              No hay datos para esta combinación de filtros. Probá con otro período, frecuencia o
              sector.
            </EmptyDataNote>
          )}
        </ChartCard>

        {tab === 'projections' && (
          <InfoNote tone="warning">
            Las proyecciones son estimaciones y pueden variar cuando se publique una nueva revisión
            de la fuente. Revisá la ficha metodológica antes de usar estos valores en decisiones.
          </InfoNote>
        )}
      </div>
    </>
  );
}
