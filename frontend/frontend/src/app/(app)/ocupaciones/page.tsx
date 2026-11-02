import type { Metadata } from 'next';
import { Badge, type BadgeTone } from '@/components/ui/badge';
import { OptionPills } from '@/components/ui/controls/OptionPills';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { FilterBar, type FilterConfig } from '@/components/ui/filters/FilterBar';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { Pagination } from '@/components/ui/tables/Pagination';
import { RankingTable } from '@/components/ui/tables/RankingTable';
import { ApiError } from '@/lib/api/client';
import { getEmployability } from '@/lib/api/employability';
import { getCountries, getSectors } from '@/lib/api/panorama';
import type { Country, DimensionRange, EmployabilityPage, Sector } from '@/lib/schemas/api';
import { toOccupationRow } from '@/lib/utils/employability';
import { formatDate, formatNumber } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Ocupaciones' };

const PAGE_SIZE = 20;

const TONES: Record<string, BadgeTone> = {
  net_demand: 'brand',
  salary_ppp: 'info',
  insertion_rate: 'neutral',
  automation_risk: 'warning',
};

type SearchParams = {
  country?: string;
  sector?: string;
  year?: string;
  order?: string;
  page?: string;
};

function weightValue(range: DimensionRange): string {
  if (!range.has_source || range.effective_weight === 0) return 'En espera de fuente';
  return `+${formatNumber(range.effective_weight * 100, 1)}%`;
}

function buildBaseHref(sp: SearchParams): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    if (key !== 'page' && value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/ocupaciones?${query}` : '/ocupaciones';
}

export default async function OcupacionesPage({
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
          title="Ocupaciones"
          description="Consultá el ranking de ocupaciones por coeficiente ISE y el desglose de cada uno de sus componentes."
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
  const sectorLabel = sectors.find((sector) => sector.sector_code === sectorCode)?.name ?? sectorCode;
  const order = sp.order === 'asc' ? 'asc' : 'desc';
  const page = Math.max(1, Number(sp.page ?? '1') || 1);
  const selectedCountries =
    sp.country && sp.country !== 'all' ? [sp.country] : undefined;

  let payload: EmployabilityPage | null = null;
  let dataError = '';

  try {
    payload = await getEmployability({
      countries: selectedCountries,
      sector: sectorCode,
      year: sp.year ? Number(sp.year) : undefined,
      view: 'all',
      sortBy: 'score',
      order,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    });
  } catch (error) {
    dataError =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar el ranking.';
  }

  const year = payload?.year ?? null;
  const years = payload?.available_years ?? [];
  const ranges = payload?.dimension_ranges ?? [];
  const rows = (payload?.items ?? [])
    .filter((item) => item.score !== null)
    .map((item, index) => toOccupationRow(item, (page - 1) * PAGE_SIZE + index + 1));

  const scoredTotal = payload?.scored_total ?? 0;
  const totalPages = Math.max(1, Math.ceil(scoredTotal / PAGE_SIZE));
  const countryLabel =
    selectedCountries && selectedCountries.length === 1
      ? (countries.find((country) => country.iso3 === selectedCountries[0])?.name_es ??
        selectedCountries[0])
      : 'los 3 países';

  const filters: FilterConfig[] = [
    {
      name: 'year',
      label: 'Año',
      defaultValue: year ? String(year) : undefined,
      options: [...years].reverse().map((value) => ({ value: String(value), label: String(value) })),
    },
  ];

  const updatedAt = formatDate(
    [...(payload?.items ?? []).map((item) => item.computed_at)].sort().at(-1) ?? null,
  );

  return (
    <>
      <PageHero
        title="Ocupaciones"
        description="Consultá el ranking de ocupaciones por coeficiente ISE y el desglose de cada uno de sus componentes."
      />

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
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

        <InfoNote title="Nota metodológica: ponderación dinámica del ISE">
          <p>
            El índice redistribuye los pesos cuando un componente no tiene fuente disponible. Para{' '}
            {year ?? 'el año seleccionado'} la demanda neta aporta{' '}
            {formatNumber((ranges.find((r) => r.dimension === 'net_demand')?.effective_weight ?? 0) * 100, 1)}
            %, el salario PPA{' '}
            {formatNumber((ranges.find((r) => r.dimension === 'salary_ppp')?.effective_weight ?? 0) * 100, 1)}
            % y el riesgo de IA{' '}
            {formatNumber((ranges.find((r) => r.dimension === 'automation_risk')?.effective_weight ?? 0) * 100, 1)}
            %. La tasa de inserción sigue en espera de una fuente oficial.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {ranges.map((range) => (
              <Badge key={range.dimension} tone={TONES[range.dimension] ?? 'neutral'}>
                {range.label} · {weightValue(range)}
              </Badge>
            ))}
          </div>
        </InfoNote>

        <section className="space-y-4">
          <SectionHeading
            title={`Ranking de ocupaciones y coeficientes ISE (${sectorLabel}, ${year ?? ''})`}
            description={`Puntaje relativo dentro de ${countryLabel}: no compara ocupaciones de países distintos.`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-text">
                Puntaje
              </span>
              <OptionPills
                param="order"
                label="Orden del ranking"
                options={[
                  { value: 'desc', label: 'Mayor' },
                  { value: 'asc', label: 'Menor' },
                ]}
                defaultValue="desc"
                variant="segment"
              />
            </div>
          </SectionHeading>

          {rows.length > 0 ? (
            <RankingTable rows={rows} />
          ) : (
            <p className="rounded-lg border border-dashed border-line bg-surface px-4 py-10 text-center text-sm text-muted-text">
              No hay ocupaciones con puntaje ISE para esta combinación de filtros.
            </p>
          )}

          <Pagination
            page={page}
            totalPages={totalPages}
            total={scoredTotal}
            pageSize={PAGE_SIZE}
            baseHref={buildBaseHref(sp)}
          />
        </section>

        <DataSourceFooter
          source="Observatorio · Índice de Empleabilidad Sectorial (datos calculados)"
          updatedAt={updatedAt ?? 'Sin fecha informada'}
          methodologyHref="/panorama-regional"
        />
      </div>
    </>
  );
}
