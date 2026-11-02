import type { Metadata } from 'next';
import { Badge } from '@/components/ui/badge';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { OptionPills } from '@/components/ui/controls/OptionPills';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { FilterBar, type FilterConfig } from '@/components/ui/filters/FilterBar';
import { StatCard } from '@/components/ui/indicators/StatCard';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { GapsMatrix } from '@/components/ui/tables/GapsMatrix';
import { Pagination } from '@/components/ui/tables/Pagination';
import { ApiError } from '@/lib/api/client';
import { getGraduateProjections } from '@/lib/api/graduates';
import { getCountries } from '@/lib/api/panorama';
import { getSkillGaps } from '@/lib/api/skills';
import type {
  Country,
  GraduateProjectionItem,
  SkillGapItem,
  SkillGapsPage,
} from '@/lib/schemas/api';
import type { GapRow } from '@/lib/ui-types';
import {
  formatNumber,
  formatSignedPercent,
} from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Habilidades' };

const PAGE_SIZE = 20;

const GAP_OPTIONS = [
  { value: 'largest', label: 'Mayores' },
  { value: 'smallest', label: 'Menores' },
  { value: 'all', label: 'Todas' },
];

type SearchParams = {
  tab?: string;
  country?: string;
  gap?: string;
  min?: string;
  emerging?: string;
  page?: string;
};

function buildBaseHref(sp: SearchParams): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    if (key !== 'page' && value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/habilidades?${query}` : '/habilidades';
}

function gapMode(value: string | undefined): 'largest' | 'smallest' | 'all' {
  if (value === 'smallest') return 'smallest';
  if (value === 'all') return 'all';
  return 'largest';
}

function toGapRow(item: SkillGapItem): GapRow {
  const mainOccupations = item.top_occupations
    .slice(0, 3)
    .flatMap((occupation) => (typeof occupation.name === 'string' ? [occupation.name] : []))
    .join(', ');

  return {
    skill: item.skill.name,
    country: item.country_iso3,
    demand:
      item.demand_growth === null ? '—' : formatSignedPercent(item.demand_growth),
    training:
      item.supply_growth === null ? '—' : formatSignedPercent(item.supply_growth),
    // La API expresa la brecha como (demanda − oferta): positiva = déficit.
    // En la matriz se muestra con el signo invertido, como en el diseño.
    gap: item.gap === null ? 0 : Number((-item.gap * 100).toFixed(1)),
    occupations: item.occupations,
    mainOccupations: mainOccupations || 'Sin ocupaciones informadas',
  };
}

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export default async function HabilidadesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const tab = sp.tab === 'projections' ? 'projections' : 'gaps';

  let countries: Country[] = [];
  let catalogError = '';
  try {
    countries = await getCountries();
  } catch (error) {
    catalogError =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar los catálogos.';
  }

  return (
    <>
      <PageHero
        title="Habilidades"
        description="Identificá las brechas entre la demanda del mercado laboral y la formación disponible, y anticipá las necesidades futuras."
      />

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <SectionTabs
          tabs={[
            { id: 'gaps', label: 'Brechas de Habilidades' },
            { id: 'projections', label: 'Proyecciones' },
          ]}
          active={tab}
        />

        {catalogError && <ApiErrorNote message={catalogError} />}

        {tab === 'projections' ? <ProjectionsView /> : <GapsView sp={sp} countries={countries} />}
      </div>
    </>
  );
}

async function GapsView({ sp, countries }: { sp: SearchParams; countries: Country[] }) {
  const mode = gapMode(sp.gap);
  const requestedMin = Math.max(1, Number(sp.min ?? '3') || 3);
  const effectiveMin = mode === 'all' ? 1 : requestedMin;
  const emerging = sp.emerging === 'true';
  const page = Math.max(1, Number(sp.page ?? '1') || 1);
  const order = mode === 'smallest' ? 'asc' : 'desc';
  const selectedCountries =
    sp.country && sp.country !== 'all' ? [sp.country] : undefined;

  let payload: SkillGapsPage | null = null;
  let dataError = '';

  try {
    payload = await getSkillGaps({
      countries: selectedCountries,
      view: 'all',
      sortBy: 'gap',
      order,
      minOccupations: effectiveMin,
      emerging: emerging ? true : undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    });
  } catch (error) {
    dataError =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar las brechas.';
  }

  const items = payload?.items ?? [];
  const withGap = items.filter((item) => item.gap !== null);
  const gaps = withGap.flatMap((item) => (item.gap === null ? [] : [-item.gap * 100]));
  const averageGap = average(gaps);
  const largest = withGap.reduce<SkillGapItem | null>((best, item) => {
    if (item.gap === null) return best;
    if (!best || best.gap === null) return item;
    return item.gap > best.gap ? item : best;
  }, null);
  const emergingCount = items.filter((item) => item.is_emerging).length;
  const demandCoverage = average(items.map((item) => item.demand_coverage));

  const largestGap = largest?.gap ?? null;

  const total = payload?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const countryLabel =
    selectedCountries && selectedCountries.length === 1
      ? (countries.find((country) => country.iso3 === selectedCountries[0])?.name_es ??
        selectedCountries[0])
      : 'los 3 países';

  const filters: FilterConfig[] = [
    {
      name: 'min',
      label: 'Mínimo de ocupaciones',
      defaultValue: String(requestedMin),
      options: [1, 3, 5, 10, 20, 50].map((value) => ({
        value: String(value),
        label: `Al menos ${value}`,
      })),
    },
  ];

  const updatedAt = payload?.year ? `Período ${payload.year}` : null;

  return (
    <>
      <section aria-label="Filtros" className="space-y-4 rounded-lg border border-line bg-surface p-4 sm:p-5">
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-text">
            Países
          </p>
          <OptionPills
            param="country"
            label="Países"
            options={[
              { value: 'all', label: `Todos (${countries.length || 3})` },
              ...countries.map((country) => ({ value: country.iso3, label: country.iso3 })),
            ]}
            defaultValue="all"
          />
        </div>

        <FilterBar filters={filters} />

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              Tipo de brecha
            </p>
            <OptionPills
              param="gap"
              label="Tipo de brecha"
              options={GAP_OPTIONS}
              defaultValue="largest"
              variant="segment"
            />
          </div>

          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              Habilidades emergentes
            </p>
            <OptionPills
              param="emerging"
              label="Habilidades emergentes"
              options={[
                { value: 'all', label: 'Todas' },
                { value: 'true', label: 'Solo emergentes' },
              ]}
              defaultValue="all"
              variant="segment"
            />
          </div>
        </div>
      </section>

      {dataError && <ApiErrorNote message={dataError} />}

      <p className="text-sm text-muted-text">
        {payload?.full_total ?? 0} habilidades con brechas y usadas por al menos{' '}
        {payload?.min_occupations ?? effectiveMin}{' '}
        {(payload?.min_occupations ?? effectiveMin) === 1 ? 'ocupación' : 'ocupaciones'} ·{' '}
        {payload?.year ?? 'último año'} · {countryLabel}
      </p>

      <InfoNote title="Correspondencia carrera · ocupación">
        Las brechas combinan la demanda observada en las ocupaciones (ESCO) con la oferta
        formativa de Chile, Argentina y Uruguay. Cuando falta uno de los dos lados, la API lo
        informa como cobertura parcial y la brecha se calcula solo con los datos disponibles.
      </InfoNote>

      <section aria-label="Indicadores de brechas" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Brecha promedio"
          value={averageGap === null ? '—' : `${averageGap > 0 ? '+' : ''}${formatNumber(averageGap, 1)}`}
          unit="pp"
          hint="Signo negativo = déficit de formación"
          badge={
            averageGap === null ? undefined : (
              <Badge tone={averageGap < 0 ? 'danger' : 'success'}>
                {averageGap < 0 ? 'Déficit' : 'Superávit'}
              </Badge>
            )
          }
        />
        <StatCard
          label="Mayor brecha detectada"
          value={largestGap === null ? '—' : formatNumber(-largestGap * 100, 1)}
          unit="pp"
          hint={
            largest
              ? `${largest.country_iso3} · ${largest.skill.name}`
              : 'Sin brechas para este filtro'
          }
          badge={<Badge tone="warning">Alerta</Badge>}
        />
        <StatCard
          label="Habilidades con brecha"
          value={formatNumber(payload?.full_total ?? 0, 0)}
          hint={`${emergingCount} emergentes en la página actual`}
          badge={<Badge tone="info">ESCO</Badge>}
        />
        <StatCard
          label="Cobertura de demanda"
          value={demandCoverage === null ? '—' : formatNumber(demandCoverage * 100, 1)}
          unit="%"
          hint="Promedio de microdatos de demanda disponibles"
        />
      </section>

      <section className="space-y-4">
        <SectionHeading
          title="Matriz comparativa de brechas"
          description="Diferencia entre la demanda del mercado y la oferta formativa. Los valores negativos indican déficit."
        />

        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-text">
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-danger" aria-hidden />
            Déficit (−)
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full border border-line bg-canvas" aria-hidden />
            Superávit (+)
          </span>
          <span className="ml-auto">
            Página {page} de {totalPages}
          </span>
        </div>

        {items.length > 0 ? (
          <GapsMatrix rows={items.map(toGapRow)} />
        ) : (
          <p className="rounded-lg border border-dashed border-line bg-surface px-4 py-10 text-center text-sm text-muted-text">
            No hay brechas de habilidades para esta combinación de filtros.
          </p>
        )}

        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={PAGE_SIZE}
          baseHref={buildBaseHref(sp)}
        />
      </section>

      <DataSourceFooter
        source="ESCO · Ocupaciones y habilidades · ILOSTAT"
        updatedAt={updatedAt ?? 'Sin fecha informada'}
        methodologyHref="/panorama-regional"
      />
    </>
  );
}

function ProjectionsView() {
  return <ProjectionsContent />;
}

async function ProjectionsContent() {
  let projections: GraduateProjectionItem[] = [];
  let errorMessage = '';

  try {
    projections = await getGraduateProjections();
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar las proyecciones.';
  }

  const years = [...new Set(projections.map((item) => item.anio))].sort((a, b) => a - b);
  const firstYear = years[0];
  const lastYear = years.at(-1);
  const byYear = years.map((year) => {
    const rows = projections.filter((item) => item.anio === year);
    return {
      year,
      total: rows.reduce((sum, item) => sum + item.graduados_proyectado, 0),
      lower: rows.reduce((sum, item) => sum + item.limite_inferior, 0),
      upper: rows.reduce((sum, item) => sum + item.limite_superior, 0),
    };
  });

  const firstTotal = byYear[0]?.total ?? 0;
  const lastTotal = byYear.at(-1)?.total ?? 0;
  const growth = firstTotal > 0 ? (lastTotal - firstTotal) / firstTotal : null;
  const lastBounds = byYear.at(-1);
  const careers = [...new Set(projections.map((item) => item.nombre))];

  const chartRows = byYear.map((row) => ({ label: String(row.year), total: row.total }));
  const chartSeries = [{ key: 'total', label: 'Graduados proyectados', color: '#172bc4' }];

  const careerRows = careers.map((career) => {
    const series = projections
      .filter((item) => item.nombre === career)
      .sort((a, b) => a.anio - b.anio);
    const first = series[0];
    const last = series.at(-1);
    const careerGrowth =
      first && last && first.graduados_proyectado > 0
        ? (last.graduados_proyectado - first.graduados_proyectado) /
          first.graduados_proyectado
        : null;
    return { career, first, last, careerGrowth };
  });

  const updatedAt = null;

  if (errorMessage) {
    return <ApiErrorNote message={errorMessage} />;
  }

  return (
    <>
      <section aria-label="Indicadores proyectados" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={`Proyección de egresados ${lastYear ?? ''}`}
          value={formatNumber(lastTotal, 0)}
          hint={`Total de las ${careers.length} carreras con proyección`}
          badge={<Badge tone="info">Proyectado</Badge>}
        />
        <StatCard
          label={`Variación ${firstYear ?? ''}–${lastYear ?? ''}`}
          value={growth === null ? '—' : formatSignedPercent(growth)}
          hint="Crecimiento del total proyectado en el período"
        />
        <StatCard
          label="Carreras con proyección"
          value={String(careers.length)}
          hint="Series disponibles en la API"
        />
        <StatCard
          label="Rango del escenario"
          value={
            lastBounds
              ? `${formatNumber(lastBounds.lower, 0)} – ${formatNumber(lastBounds.upper, 0)}`
              : '—'
          }
          hint={lastYear ? `Límites inferior y superior en ${lastYear}` : undefined}
        />
      </section>

      <ChartCard
        title="Proyección de egresados"
        subtitle="Total anual proyectado para las carreras con serie suficiente."
        legend={chartSeries.map((item) => ({ label: item.label, color: item.color }))}
        sourceName="Graduados · proyecciones del observatorio"
        updatedAt={updatedAt}
        methodologyHref="/panorama-regional"
      >
        {chartRows.length > 0 ? (
          <TrendLineChart data={chartRows} series={chartSeries} unit="persons" />
        ) : (
          <p className="rounded-lg border border-dashed border-line bg-surface px-4 py-10 text-center text-sm text-muted-text">
            La API no devolvió proyecciones de egresados.
          </p>
        )}
      </ChartCard>

      {careerRows.length > 0 && (
        <section className="space-y-4">
          <SectionHeading
            title="Proyección por carrera"
            description="Valores proyectados y variación entre el primer y el último año disponible."
          />
          <div className="overflow-x-auto rounded-lg border border-line bg-canvas">
            <table className="w-full min-w-[52rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-surface-2 text-[11px] uppercase tracking-wide text-muted-text">
                  <th scope="col" className="px-4 py-3 font-semibold">Carrera</th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {firstYear ?? 'Inicio'}
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {lastYear ?? 'Fin'}
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">Variación</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Rango final</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {careerRows.map((row) => (
                  <tr key={row.career} className="hover:bg-surface">
                    <td className="px-4 py-3 font-medium capitalize text-heading">{row.career}</td>
                    <td className="px-4 py-3 text-body">
                      {row.first ? formatNumber(row.first.graduados_proyectado, 0) : '—'}
                    </td>
                    <td className="px-4 py-3 font-semibold text-heading">
                      {row.last ? formatNumber(row.last.graduados_proyectado, 0) : '—'}
                    </td>
                    <td className="px-4 py-3 text-body">
                      {row.careerGrowth === null ? '—' : formatSignedPercent(row.careerGrowth)}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-text">
                      {row.last
                        ? `${formatNumber(row.last.limite_inferior, 0)} – ${formatNumber(row.last.limite_superior, 0)}`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <InfoNote tone="warning" title="Alcance de las proyecciones">
        La API todavía no publica proyecciones de brechas de habilidades. Esta pestaña muestra las
        proyecciones de egresados disponibles: solo Chile, con series 2026–2029. Se actualizará
        cuando el observatorio publique proyecciones de demanda y oferta formativa por habilidad.
      </InfoNote>

      <DataSourceFooter
        source="Graduados · proyecciones del observatorio"
        updatedAt={updatedAt ?? 'Sin fecha informada'}
        methodologyHref="/panorama-regional"
      />
    </>
  );
}
