import { Suspense } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, BarChart3, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { SectorPicker } from '@/components/data/SectorPicker';
import { CountryFilter } from '@/components/data/CountryFilter';
import { YearRange } from '@/components/data/YearRange';
import { SectorKpisView } from '@/components/data/SectorKpisView';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { SectorBarChart } from '@/components/ui/charts/SectorBarChart';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { FilterLabel, FilterPanel } from '@/components/ui/filters/FilterPanel';
import { MetricCard } from '@/components/ui/indicators/MetricCard';
import { SectorDimensionsPanel } from '@/components/ui/indicators/SectorDimensionsPanel';
import { WeightBar } from '@/components/ui/indicators/WeightBar';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { ApiError } from '@/lib/api/client';
import { getSectorSummaries } from '@/lib/api/employability';
import { getCountries, getSectors } from '@/lib/api/panorama';
import { DIMENSION_COLORS } from '@/lib/constants';
import type { Country, Sector, SectorsPage } from '@/lib/schemas/api';
import { cn } from '@/lib/utils';
import {
  formatIndex01,
  formatNumber,
  formatSignedPercent,
  formatUsd,
  riskLabel,
} from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Sectores' };

type SearchParams = {
  country?: string;
  sector?: string;
  desde?: string;
  hasta?: string;
  tab?: string;
};

const TABS = [
  { id: 'ise', label: 'Índice de empleabilidad (ISE) sectorial' },
  { id: 'densidad', label: 'Densidad profesional' },
  { id: 'ocupados', label: 'Personas ocupadas' },
];

function countryCodes(sp: SearchParams): string[] | undefined {
  return sp.country && sp.country !== 'all' ? [sp.country] : undefined;
}

function sectorHref(sp: SearchParams, sectorCode: string): string {
  const params = new URLSearchParams();
  if (sp.country) params.set('country', sp.country);
  if (sp.desde) params.set('desde', sp.desde);
  if (sp.hasta) params.set('hasta', sp.hasta);
  if (sp.tab && sp.tab !== 'ise') params.set('tab', sp.tab);
  params.set('sector', sectorCode);
  return `/sectores?${params.toString()}`;
}

export default async function SectoresPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const tab: 'ise' | 'densidad' | 'ocupados' =
    sp.tab === 'densidad' || sp.tab === 'ocupados' ? sp.tab : 'ise';

  let countries: Country[] = [];
  let sectors: Sector[] = [];
  let errorMessage = '';

  try {
    [countries, sectors] = await Promise.all([getCountries(), getSectors()]);
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar los catálogos.';
  }

  const hero = (
    <PageHero
      title="Sectores"
      description="Explorá el índice de empleabilidad sectorial (ISE), la densidad profesional y las personas ocupadas en los cinco sectores estratégicos del Cono Sur."
    />
  );

  if (errorMessage || sectors.length === 0) {
    return (
      <>
        {hero}
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <ApiErrorNote message={errorMessage} />
        </div>
      </>
    );
  }

  const countryLabel =
    sp.country && sp.country !== 'all'
      ? (countries.find((country) => country.iso3 === sp.country)?.name_es ?? sp.country)
      : 'los 3 países';

  const tabs = (
    <SectionTabs tabs={TABS} active={tab} />
  );

  if (tab !== 'ise') {
    return (
      <>
        {hero}
        <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
          {tabs}
          <Suspense
            fallback={
              <p className="rounded-xl border border-dashed border-card-border bg-rail px-4 py-10 text-center text-[12.5px] text-muted-text">
                Cargando indicadores sectoriales…
              </p>
            }
          >
            <SectorKpisView sp={sp} mode={tab} />
          </Suspense>
        </div>
      </>
    );
  }

  let payload: SectorsPage | null = null;
  let dataError = '';

  try {
    payload = await getSectorSummaries({
      countries: countryCodes(sp),
      year: sp.hasta ? Number(sp.hasta) : undefined,
    });
  } catch (error) {
    dataError =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar el sector.';
  }

  const year = payload?.year ?? null;
  const availableYears = payload?.available_years ?? [];
  const previousYear =
    [...availableYears].sort((a, b) => a - b).filter((value) => year === null || value < year).at(-1) ??
    (year !== null ? year - 1 : null);

  const desdeValue = Number(sp.desde);
  const hastaValue = Number(sp.hasta);
  const desde = sp.desde && Number.isFinite(desdeValue) ? desdeValue : previousYear;
  const hasta = sp.hasta && Number.isFinite(hastaValue) ? hastaValue : year;

  let baseline: SectorsPage | null = null;
  if (payload && desde !== null && year !== null && desde !== year) {
    try {
      baseline = await getSectorSummaries({
        countries: countryCodes(sp),
        year: desde,
      });
    } catch {
      baseline = null;
    }
  }

  const summaries = payload?.items ?? [];
  const sectorCode =
    summaries.find((item) => item.sector_code === sp.sector)?.sector_code ??
    (summaries.some((item) => item.sector_code === 'knowledge_economy')
      ? 'knowledge_economy'
      : (summaries[0]?.sector_code ?? sectors[0].sector_code));
  const selected = summaries.find((item) => item.sector_code === sectorCode) ?? null;
  const baselineSelected = baseline?.items.find((item) => item.sector_code === sectorCode) ?? null;

  const sectorName =
    selected?.name ?? sectors.find((sector) => sector.sector_code === sectorCode)?.name ?? sectorCode;
  const sectorOptions = summaries.length
    ? summaries.map((item) => ({ sector_code: item.sector_code, name: item.name }))
    : sectors.map((sector) => ({ sector_code: sector.sector_code, name: sector.name }));

  const ranges = payload?.dimension_ranges ?? [];
  const weights = ranges.map((range, index) => ({
    label: range.label,
    value: Number((range.weight * 100).toFixed(1)),
    color:
      DIMENSION_COLORS[range.dimension] ??
      ['#172bc4', '#38bdf8', '#8b5cf6', '#f59e0b'][index % 4],
  }));

  const scoreDelta =
    selected?.average_score !== null &&
    selected?.average_score !== undefined &&
    baselineSelected?.average_score !== null &&
    baselineSelected?.average_score !== undefined
      ? selected.average_score - baselineSelected.average_score
      : (selected?.change ?? null);

  const salary =
    selected?.salary_ppp_average ?? selected?.salary_usd_average ?? null;
  const baselineSalary =
    baselineSelected?.salary_ppp_average ?? baselineSelected?.salary_usd_average ?? null;
  const salaryChange =
    salary !== null && baselineSalary !== null && baselineSalary > 0
      ? salary / baselineSalary - 1
      : null;

  const chartItems = summaries.map((item) => ({
    label: item.name,
    value: item.average_score ?? 0,
    active: item.sector_code === sectorCode,
  }));
  const chartAverage = payload?.regional_average ?? 0;

  const definitions = ranges
    .filter(
      (range) =>
        range.definition && ['salary_ppp', 'automation_risk'].includes(range.dimension),
    )
    .map((range) => ({
      title:
        range.dimension === 'automation_risk'
          ? 'Índice de exposición a la IA'
          : `Definición de ${range.label}`,
      text: range.definition!,
    }));
  definitions.push({
    title: 'Gobernanza de calibración',
    text:
      payload?.no_source_note ??
      'Los pesos del ISE se recalibran cada año con fuentes oficiales. Si falta un componente, su peso se redistribuye entre los disponibles y queda documentado en la ficha metodológica.',
  });

  const updatedAt = formatDateLabel(year);

  return (
    <>
      {hero}

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {tabs}

        <FilterPanel className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <FilterLabel>Países</FilterLabel>
              <CountryFilter
                countries={countries}
                value={sp.country && sp.country !== 'all' ? sp.country : ''}
                reset={['page']}
                compact
              />
            </div>
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <FilterLabel>Período</FilterLabel>
                <YearRange
                  years={availableYears.length ? [...availableYears].reverse() : year ? [year] : []}
                  desde={desde !== null ? String(desde) : undefined}
                  hasta={hasta !== null ? String(hasta) : undefined}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-card-border pt-4">
            <FilterLabel className="mb-2.5 block">Sectores</FilterLabel>
            <SectorPicker
              sectors={sectorOptions}
              active={sectorCode}
              hrefFor={(code) => sectorHref(sp, code)}
            />
          </div>
        </FilterPanel>

        {dataError && <ApiErrorNote message={dataError} />}

        {selected ? (
          <>
            <section
              aria-label="Indicadores del sector"
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <MetricCard
                label={`ISE promedio · ${sectorName}`}
                value={
                  selected.average_score === null ? '—' : formatNumber(selected.average_score, 1)
                }
                unit="/ 100 pts"
                badge={
                  selected.level_label ? <Badge tone="brand">{selected.level_label}</Badge> : undefined
                }
                chip={
                  scoreDelta !== null && scoreDelta !== undefined ? (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold',
                        scoreDelta >= 0
                          ? 'border-success/25 bg-success-soft text-success'
                          : 'border-danger/25 bg-danger-soft text-danger',
                      )}
                    >
                      {formatSignedPoints(scoreDelta)} pts
                    </span>
                  ) : undefined
                }
                meta={desde !== null ? `vs ${desde}` : undefined}
                hint={`${selected.scored} ocupaciones con puntaje · ${countryLabel}`}
              />

              <MetricCard
                label="Ocupación líder (rank #1)"
                value={selected.top_occupation?.name ?? 'Sin datos'}
                valueClassName="text-[17px] leading-snug"
                unit={
                  selected.top_occupation
                    ? `${formatNumber(selected.top_occupation.score, 1)} pts`
                    : undefined
                }
                hint={
                  selected.top_occupation
                    ? `${selected.top_occupation.country_iso3} · CIUO ${selected.top_occupation.occupation_code}`
                    : 'No hay ocupaciones con puntaje para este filtro.'
                }
                action={
                  selected.top_occupation ? (
                    <Link
                      href={`/ocupaciones/${selected.top_occupation.occupation_code}?country=${selected.top_occupation.country_iso3}`}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-card-border bg-canvas px-3 py-1.5 text-[12px] font-semibold text-link transition-colors hover:bg-surface-alt hover:text-link-hover"
                    >
                      Ver desglose ISE de la ocupación
                      <ArrowRight className="size-3.5" aria-hidden />
                    </Link>
                  ) : undefined
                }
              />

              <MetricCard
                label="Salario PPA promedio"
                value={salary === null ? '—' : formatUsd(salary, 2)}
                unit="/ mes"
                chip={
                  salaryChange !== null ? (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold',
                        salaryChange >= 0
                          ? 'border-success/25 bg-success-soft text-success'
                          : 'border-danger/25 bg-danger-soft text-danger',
                      )}
                    >
                      {formatSignedPercent(salaryChange, 1)}
                      <span className="font-normal">vs {desde ?? 'año anterior'}</span>
                    </span>
                  ) : undefined
                }
                hint={`Ingreso mensual promedio de las ocupaciones del sector · ${countryLabel}`}
              />

              <MetricCard
                label="Riesgo de automatización (exposición a la IA generativa)"
                value={
                  selected.automation_average === null
                    ? '—'
                    : formatIndex01(selected.automation_average)
                }
                unit="escala 0 a 1"
                chip={
                  <Badge tone="warning">
                    {riskLabel(selected.automation_average)}
                  </Badge>
                }
                meta={selected.scored ? `${selected.scored} ocupaciones` : undefined}
                hint="Penalización por tareas cognitivas rutinarias expuestas a LLMs."
              />
            </section>

            {weights.length > 0 && (
              <section className="rounded-xl border border-card-border bg-rail px-5 py-4">
                <WeightBar
                  title="Índice orientativo por ocupación"
                  description="El ISE combina las dimensiones con fuente disponible. Si falta una, su peso se redistribuye entre las demás y queda documentado en la metodología."
                  segments={weights}
                />
              </section>
            )}

            <SectorDimensionsPanel
              ranges={ranges}
              dimensions={selected.dimensions}
              salaryAverage={selected.salary_ppp_average}
              automationAverage={selected.automation_average}
              title="Índice de empleabilidad (ISE) sectorial"
              description={`Estructura de las ${ranges.length} dimensiones analíticas que componen el puntaje de ${sectorName}.`}
              referenceYear={year}
              noSourceNote={payload?.no_source_note}
              methodologyHref="/metodologia/ise"
              breakdownHref={
                selected.top_occupation
                  ? `/ocupaciones/${selected.top_occupation.occupation_code}?country=${selected.top_occupation.country_iso3}`
                  : undefined
              }
            />

            <section className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                {definitions.map((definition) => (
                  <article
                    key={definition.title}
                    className="rounded-xl border border-card-border bg-canvas p-4"
                  >
                    <h3 className="flex items-center gap-2 text-[13px] font-semibold text-heading">
                      <Sparkles className="size-4 text-brand" aria-hidden />
                      {definition.title}
                    </h3>
                    <p className="mt-2 text-[12px] leading-relaxed text-muted-text">
                      {definition.text}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            {chartItems.some((item) => item.value > 0) && (
              <ChartCard
                title={`Comparativa intersectorial de empleabilidad (ISE ${year ?? ''})`}
                subtitle={`Puntaje sintético promedio y competitividad relativa en los ${summaries.length} sectores estratégicos evaluados.`}
                icon={<BarChart3 className="size-5" />}
                meta={
                  <span className="inline-flex items-center gap-1.5 rounded-lg border border-card-border bg-canvas px-2.5 py-1 text-[11px] font-semibold text-body">
                    <BarChart3 className="size-3.5 text-brand" aria-hidden />
                    Promedio ponderado regional: {formatNumber(chartAverage, 1)} pts
                  </span>
                }
                sourceName="Observatorio · Índice de Empleabilidad Sectorial"
                updatedAt={updatedAt}
                methodologyHref="/metodologia/ise"
              >
                <SectorBarChart items={chartItems} average={chartAverage} />
              </ChartCard>
            )}

          </>
        ) : (
          <p className="rounded-xl border border-dashed border-card-border bg-rail px-4 py-12 text-center text-[12.5px] text-muted-text">
            No hay datos del ISE sectorial para esta combinación de filtros.
          </p>
        )}
      </div>
    </>
  );
}

function formatSignedPoints(value: number): string {
  return `${value > 0 ? '+' : ''}${formatNumber(value, 1)}`;
}

function formatDateLabel(year: number | null): string | null {
  return year === null ? null : String(year);
}
