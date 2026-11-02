import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { SectorBarChart } from '@/components/ui/charts/SectorBarChart';
import { OptionPills } from '@/components/ui/controls/OptionPills';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { FilterBar, type FilterConfig } from '@/components/ui/filters/FilterBar';
import { RankingList } from '@/components/ui/indicators/RankingList';
import { StatCard } from '@/components/ui/indicators/StatCard';
import { WeightBar } from '@/components/ui/indicators/WeightBar';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { ApiError } from '@/lib/api/client';
import { getEmployability } from '@/lib/api/employability';
import { getCountries, getSectors } from '@/lib/api/panorama';
import { DIMENSION_COLORS } from '@/lib/constants';
import type {
  Country,
  DimensionRange,
  EmployabilityItem,
  EmployabilityPage,
  Sector,
} from '@/lib/schemas/api';
import type { RankingItem } from '@/lib/ui-types';
import {
  formatDate,
  formatIndex01,
  formatNumber,
  formatSignedPercent,
  formatUsd,
  riskLabel,
} from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Sectores' };

type SearchParams = { country?: string; sector?: string; year?: string };

const DIMENSION_ORDER = ['net_demand', 'salary_ppp', 'insertion_rate', 'automation_risk'];

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function countryCodes(sp: SearchParams): string[] | undefined {
  return sp.country && sp.country !== 'all' ? [sp.country] : undefined;
}

function componentRaw(item: EmployabilityItem, dimension: string): number | null {
  return item.components.find((component) => component.dimension === dimension)?.raw ?? null;
}

function componentNormalized(item: EmployabilityItem, dimension: string): number | null {
  return item.components.find((component) => component.dimension === dimension)?.normalized ?? null;
}

function buildComponentRanking(
  items: EmployabilityItem[],
  ranges: DimensionRange[],
): RankingItem[] {
  const ordered = [...ranges].sort(
    (a, b) => DIMENSION_ORDER.indexOf(a.dimension) - DIMENSION_ORDER.indexOf(b.dimension),
  );

  return ordered.map((range, index) => {
    const available = items.filter(
      (item) => item.components.find((c) => c.dimension === range.dimension)?.available,
    );
    const score = average(
      available.flatMap((item) => {
        const value = componentNormalized(item, range.dimension);
        return value === null ? [] : [value];
      }),
    );
    const rawValues = available.flatMap((item) => {
      const value = componentRaw(item, range.dimension);
      return value === null ? [] : [value];
    });
    const raw = average(rawValues);

    const delta =
      raw === null
        ? undefined
        : range.dimension === 'net_demand'
          ? `${formatSignedPercent(raw)} anual`
          : range.dimension === 'salary_ppp'
            ? `Promedio: ${formatUsd(raw)}`
            : range.dimension === 'automation_risk'
              ? `${formatIndex01(raw)} · ${riskLabel(raw)}`
              : undefined;

    return {
      rank: index + 1,
      title: `${range.label} sectorial`,
      meta: `Peso efectivo: ${formatNumber(range.effective_weight * 100, 1)}%${
        range.unit ? ` · ${range.unit}` : ''
      }`,
      score,
      delta,
      badge: range.has_source ? undefined : 'En calibración',
      note: range.has_source
        ? undefined
        : (range.source_status ?? 'Componente a la espera de una fuente oficial.'),
    };
  });
}

export default async function SectoresPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;

  let countries: Country[] = [];
  let sectors: Sector[] = [];
  let errorMessage = '';

  try {
    [countries, sectors] = await Promise.all([getCountries(), getSectors()]);
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar los catálogos.';
  }

  if (errorMessage || sectors.length === 0) {
    return (
      <>
        <PageHero
          title="Sectores"
          description="Explorá el índice de empleabilidad sectorial (ISE) y detectá qué sectores concentran la demanda, el salario y el riesgo de automatización."
        />
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <ApiErrorNote message={errorMessage} />
        </div>
      </>
    );
  }

  const sectorCode =
    sectors.find((sector) => sector.sector_code === sp.sector)?.sector_code ??
    (sectors.some((sector) => sector.sector_code === 'knowledge_economy')
      ? 'knowledge_economy'
      : sectors[0].sector_code);
  const selectedCountries = countryCodes(sp);

  let payload: EmployabilityPage | null = null;
  let dataError = '';

  try {
    payload = await getEmployability({
      countries: selectedCountries,
      sector: sectorCode,
      year: sp.year ? Number(sp.year) : undefined,
      view: 'all',
      sortBy: 'score',
      order: 'desc',
      limit: 500,
    });
  } catch (error) {
    dataError =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar el sector.';
  }

  const years = payload?.available_years ?? [];
  const year = payload?.year ?? years.at(-1) ?? null;

  let sectorPage: { sector: Sector; average: number | null }[] = [];
  if (payload && !dataError) {
    const results = await Promise.all(
      sectors.map(async (sector) => {
        try {
          const page = await getEmployability({
            countries: selectedCountries,
            sector: sector.sector_code,
            year: year ?? undefined,
            view: 'all',
            limit: 500,
          });
          return {
            sector,
            average: average(
              page.items.flatMap((item) => (item.score === null ? [] : [item.score])),
            ),
          };
        } catch {
          return { sector, average: null };
        }
      }),
    );
    sectorPage = results;
  }

  const items = payload?.items ?? [];
  const scored = items.filter((item) => item.score !== null);
  const leader = scored[0] ?? null;
  const sectorAverage = average(scored.flatMap((item) => (item.score === null ? [] : [item.score])));
  const salaryAverage = average(
    items.flatMap((item) => {
      const value = componentRaw(item, 'salary_ppp');
      return value === null ? [] : [value];
    }),
  );
  const riskAverage = average(
    items.flatMap((item) => {
      const value = componentRaw(item, 'automation_risk');
      return value === null ? [] : [value];
    }),
  );

  const sectorName = sectors.find((sector) => sector.sector_code === sectorCode)?.name ?? sectorCode;
  const countryLabel =
    selectedCountries && selectedCountries.length === 1
      ? (countries.find((country) => country.iso3 === selectedCountries[0])?.name_es ??
        selectedCountries[0])
      : 'los 3 países';

  const weights = (payload?.dimension_ranges ?? []).map((range, index) => ({
    label: range.label,
    value: Number((range.effective_weight * 100).toFixed(1)),
    color: DIMENSION_COLORS[range.dimension] ?? ['#172bc4', '#38bdf8', '#8b5cf6', '#f59e0b'][index % 4],
  }));

  const ranking = buildComponentRanking(items, payload?.dimension_ranges ?? []);

  const chartItems = sectorPage.map(({ sector, average: value }) => ({
    label: sector.name,
    value: value ?? 0,
    active: sector.sector_code === sectorCode,
  }));
  const chartValues = sectorPage.flatMap(({ average: value }) =>
    value === null ? [] : [value],
  );
  const chartAverage = average(chartValues) ?? 0;

  const definitions = (payload?.dimension_ranges ?? [])
    .filter((range) => ['salary_ppp', 'automation_risk'].includes(range.dimension))
    .flatMap((range) =>
      range.definition ? [{ title: `Definición de ${range.label}`, text: range.definition }] : [],
    );
  definitions.push({
    title: 'Gobernanza de calibración',
    text:
      payload?.no_source_note ??
      'Los pesos del ISE se recalibran cada año con fuentes oficiales. Si falta un componente, su peso se redistribuye entre los disponibles y queda documentado en la ficha metodológica.',
  });

  const updatedAt = formatDate(
    [...items.map((item) => item.computed_at)].sort().at(-1) ?? null,
  );

  const filters: FilterConfig[] = [
    {
      name: 'year',
      label: 'Año',
      defaultValue: year ? String(year) : undefined,
      options: [...years].reverse().map((value) => ({ value: String(value), label: String(value) })),
    },
  ];

  return (
    <>
      <PageHero
        title="Sectores"
        description="Explorá el índice de empleabilidad sectorial (ISE) y detectá qué sectores concentran la demanda, el salario y el riesgo de automatización."
      />

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6">
        <section aria-label="Filtros" className="space-y-4 rounded-lg border border-line bg-surface p-4 sm:p-5">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              Países
            </p>
            <OptionPills
              param="country"
              label="Países"
              options={[
                { value: 'all', label: `Todos (${countries.length})` },
                ...countries.map((country) => ({ value: country.iso3, label: country.iso3 })),
              ]}
              defaultValue="all"
            />
          </div>

          <FilterBar filters={filters} />

          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              Sector
            </p>
            <OptionPills
              param="sector"
              label="Sector"
              options={sectors.map((sector) => ({
                value: sector.sector_code,
                label: sector.name,
              }))}
              defaultValue={sectorCode}
            />
          </div>
        </section>

        {dataError && <ApiErrorNote message={dataError} />}

        <section aria-label="Indicadores del sector" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label={`ISE promedio · ${sectorName}`}
            value={sectorAverage === null ? '—' : formatNumber(sectorAverage, 1)}
            unit="/100 pts"
            hint={`${scored.length} ocupaciones con puntaje · ${countryLabel}${
              year ? ` · ${year}` : ''
            }`}
          />
          <StatCard
            label="Ocupación líder (rank #1)"
            value={leader?.occupation.name ?? 'Sin datos'}
            valueClassName="text-base leading-snug"
            unit={leader?.score === null || !leader ? undefined : `${formatNumber(leader.score, 1)} pts`}
            hint={
              leader
                ? `${leader.country_iso3} · CIUO ${leader.occupation.occupation_code}`
                : 'No hay ocupaciones con puntaje para este filtro.'
            }
            action={
              leader ? (
                <Link
                  href={`/ocupaciones/${leader.occupation.occupation_code}?country=${leader.country_iso3}`}
                  className="inline-flex items-center gap-1 text-xs font-medium text-link hover:text-link-hover hover:underline"
                >
                  Ver desglose ISE de la ocupación
                  <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              ) : undefined
            }
          />
          <StatCard
            label="Salario PPA promedio"
            value={salaryAverage === null ? '—' : formatUsd(salaryAverage)}
            unit="/ mes"
            hint={`Promedio de los componentes disponibles · ${countryLabel}`}
          />
          <StatCard
            label="Riesgo de automatización (IA generativa)"
            value={riskAverage === null ? '—' : formatIndex01(riskAverage)}
            unit="/1"
            hint={riskAverage === null ? 'Sin dato para este filtro' : riskLabel(riskAverage)}
            badge={
              riskAverage === null ? undefined : (
                <Badge tone="warning">{riskLabel(riskAverage)}</Badge>
              )
            }
          />
        </section>

        {weights.length > 0 && (
          <section className="space-y-4 rounded-lg border border-line bg-canvas p-5">
            <WeightBar
              title="Índice orientativo por ocupación"
              description="El ISE combina cuatro componentes. Si un componente no tiene fuente disponible, su peso se redistribuye entre los demás y queda documentado."
              segments={weights}
            />
          </section>
        )}

        <section className="space-y-4">
          <SectionHeading
            title="Índice de empleabilidad (ISE) sectorial"
            description={`Componentes que explican el desempeño de ${sectorName} en ${countryLabel}.`}
            action={{ label: 'Ver desglose completo en Ocupaciones', href: '/ocupaciones' }}
          />
          {ranking.length > 0 ? (
            <RankingList items={ranking} />
          ) : (
            <p className="rounded-lg border border-dashed border-line bg-surface px-4 py-8 text-center text-sm text-muted-text">
              No hay componentes disponibles para este sector.
            </p>
          )}
        </section>

        <section className="space-y-4">
          <SectionHeading
            title="Cómo leer el índice"
            description="Definiciones de los conceptos que acompañan al ISE."
          />
          <div className="grid gap-4 md:grid-cols-3">
            {definitions.map((definition) => (
              <article key={definition.title} className="rounded-lg border border-line bg-surface p-5">
                <h3 className="text-sm font-semibold text-heading">{definition.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-text">{definition.text}</p>
              </article>
            ))}
          </div>
        </section>

        <InfoNote title="Sobre la comparación entre sectores">
          Los valores están expresados sobre 100 puntos y se calculan con la misma metodología para
          los tres países. La línea punteada marca el promedio simple de los sectores con datos
          disponibles.
        </InfoNote>

        <ChartCard
          title={`Comparativa intersectorial de empleabilidad (ISE ${year ?? ''})`}
          subtitle={`Promedio de los sectores: ${formatNumber(chartAverage, 1)} pts · ${countryLabel}`}
          legend={[{ label: `ISE ${year ?? ''}`, color: '#172bc4' }]}
          sourceName="Observatorio · Índice de Empleabilidad Sectorial"
          updatedAt={updatedAt}
          methodologyHref="/panorama-regional"
        >
          <SectorBarChart items={chartItems} average={chartAverage} />
        </ChartCard>

        <DataSourceFooter
          source="Observatorio · Índice de Empleabilidad Sectorial (datos calculados)"
          updatedAt={updatedAt ?? 'Sin fecha informada'}
          methodologyHref="/panorama-regional"
        />
      </div>
    </>
  );
}
