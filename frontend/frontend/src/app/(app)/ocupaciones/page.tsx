import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { ArrowRight } from 'lucide-react';
import { Badge, type BadgeTone } from '@/components/ui/badge';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import {
  ChartHeader,
  ChartLayout,
  ErrorNote,
  Eyebrow,
  Page,
  RailCard,
  SourceLine,
  buttonCls,
} from '@/components/data/ui';
import { UrlSeg } from '@/components/data/UrlSeg';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ApiError } from '@/lib/api/client';
import { getEmployability } from '@/lib/api/employability';
import { getCountries, getSectors } from '@/lib/api/panorama';
import type {
  Country,
  DimensionRange,
  EmployabilityItem,
  EmployabilityPage,
  Sector,
} from '@/lib/schemas/api';
import { cn } from '@/lib/utils';
import { formatDate, formatNumber, formatScore } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Ocupaciones' };

/** Filas país × ocupación: alcanza para el sector más grande (≈55 ocupaciones × 3). */
const MAX_ROWS = 300;
const YEARS_OFFERED = 3;

const TONES: Record<string, BadgeTone> = {
  net_demand: 'brand',
  salary_ppp: 'info',
  insertion_rate: 'neutral',
  automation_risk: 'warning',
};

const LEVEL_TONES: Record<string, BadgeTone> = {
  high: 'success',
  medium: 'info',
  low: 'warning',
};

type SearchParams = {
  sector?: string;
  year?: string;
  orden?: string;
  sel?: string;
};

type DotRow = {
  code: string;
  name: string;
  sector: string | null;
  items: EmployabilityItem[];
  max: number;
  min: number;
  scored: EmployabilityItem[];
};

function weightValue(range: DimensionRange): string {
  if (!range.has_source || range.effective_weight === 0) return 'En espera de fuente';
  return `+${formatNumber(range.effective_weight * 100, 1)}%`;
}

export default function OcupacionesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <OcupacionesContent searchParams={searchParams} />
    </Suspense>
  );
}

async function OcupacionesContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;

  let countries: Country[] = [];
  let sectors: Sector[] = [];
  try {
    [countries, sectors] = await Promise.all([getCountries(), getSectors()]);
  } catch (error) {
    return (
      <ErrorNote
        message={
          error instanceof ApiError ? error.message : 'Error inesperado al cargar los catálogos.'
        }
      />
    );
  }

  if (sectors.length === 0) {
    return <ErrorNote message="No hay sectores disponibles en este momento." />;
  }

  const sectorParam = sectors.find((sector) => sector.sector_code === sp.sector)?.sector_code;
  const featured = sectorParam ? undefined : true;
  const yearParam = sp.year && /^\d{4}$/.test(sp.year) ? Number(sp.year) : undefined;

  let chartData: EmployabilityPage;
  try {
    chartData = await getEmployability({
      sector: sectorParam,
      featured,
      year: yearParam,
      view: 'all',
      limit: MAX_ROWS,
    });
  } catch (error) {
    return (
      <ErrorNote
        message={
          error instanceof ApiError ? error.message : 'Error inesperado al cargar los datos.'
        }
      />
    );
  }

  const names = Object.fromEntries(countries.map((country) => [country.iso3, country.name_es]));
  const year = chartData.year;
  const latestYear = chartData.available_years.at(-1);
  const years = chartData.available_years.slice(-YEARS_OFFERED);
  const yearOptions = years.map((value) => ({
    value: value === latestYear ? '' : String(value),
    label: String(value),
  }));
  const yearValue =
    sp.year && chartData.available_years.includes(Number(sp.year)) ? sp.year : '';

  const byCode = new Map<string, DotRow>();
  for (const item of chartData.items) {
    const code = item.occupation.occupation_code;
    const row =
      byCode.get(code) ??
      ({
        code,
        name: item.occupation.name,
        sector: item.sector_name,
        items: [],
        max: -Infinity,
        min: Infinity,
        scored: [],
      } satisfies DotRow);
    row.items.push(item);
    if (item.score !== null) {
      row.scored.push(item);
      row.max = Math.max(row.max, item.score);
      row.min = Math.min(row.min, item.score);
    }
    byCode.set(code, row);
  }

  const allRows = [...byCode.values()];
  const scoredRows = allRows.filter((row) => Number.isFinite(row.max));
  const unscored = allRows.length - scoredRows.length;
  const rows = [...scoredRows].sort((a, b) =>
    sp.orden === 'diferencia' ? b.max - b.min - (a.max - a.min) : b.max - a.max,
  );
  const selected = rows.find((row) => row.code === sp.sel) ?? rows[0];

  const lo = rows.length
    ? Math.max(0, Math.floor(Math.min(...rows.map((row) => row.min)) / 10) * 10)
    : 0;
  const hi = rows.length
    ? Math.min(100, Math.ceil(Math.max(...rows.map((row) => row.max)) / 10) * 10)
    : 100;
  const span = hi - lo || 1;
  const ticks = Array.from({ length: Math.round((hi - lo) / 10) + 1 }, (_, i) => lo + i * 10);
  const pct = (value: number) => `${((value - lo) / span) * 100}%`;

  const sectorName = sectors.find((sector) => sector.sector_code === sectorParam)?.name;
  const sectorScope = sectorParam ? ` · ${sectorName}` : '';
  const href = (code: string) => {
    const params = new URLSearchParams();
    if (sectorParam) params.set('sector', sectorParam);
    if (sp.orden) params.set('orden', sp.orden);
    if (sp.year) params.set('year', sp.year);
    params.set('sel', code);
    return `/ocupaciones?${params.toString()}`;
  };

  const ranges = chartData.dimension_ranges;
  const updatedAt = formatDate(
    [...(chartData.items ?? []).map((item) => item.computed_at)].sort().at(-1) ?? null,
  );

  return (
    <>
      <PageHero
        title="Ocupaciones"
        description="Compará el índice de empleabilidad (ISE) de las ocupaciones entre Argentina, Chile y Uruguay y abrí la ficha de cada una."
      />

      <Page>
        <ChartHeader
          eyebrow={`Índice de empleabilidad (ISE) · ${year ?? ''} · ${sectorName ?? 'ocupaciones destacadas'}`}
          title="La misma ocupación, tres países"
          subtitle="Cada fila es una ocupación y cada punto, su ISE en un país (0 a 100). Cuanto más larga la línea, más difiere entre países."
          controls={
            <>
              <UrlSeg
                name="sector"
                label="Conjunto"
                value={sectorParam ?? ''}
                options={[
                  { value: '', label: 'Destacadas' },
                  ...sectors.map((sector) => ({
                    value: sector.sector_code,
                    label: sector.name,
                  })),
                ]}
                reset={['sel']}
              />
              <UrlSeg
                name="orden"
                label="Orden"
                value={sp.orden === 'diferencia' ? 'diferencia' : ''}
                options={[
                  { value: '', label: 'Mayor ISE' },
                  { value: 'diferencia', label: 'Mayor diferencia' },
                ]}
              />
              {yearOptions.length > 1 && (
                <UrlSeg
                  name="year"
                  label="Año"
                  value={yearValue}
                  options={yearOptions}
                  reset={['sel']}
                />
              )}
            </>
          }
        />

        <ChartLayout
          stickyRail
          chart={
            rows.length === 0 ? (
              <p className="py-24 text-center text-sm text-muted-text">
                No hay ocupaciones con ISE en este conjunto.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <div className="min-w-[34rem] pr-8">
                  <div className="grid grid-cols-[minmax(8rem,260px)_minmax(0,1fr)] gap-4 px-2 pb-1.5 text-[11px] text-label">
                    <span className="flex flex-wrap gap-3.5">
                      {countries.map((country) => (
                        <span key={country.iso3} className="inline-flex items-center gap-1.5">
                          <span
                            className="size-2.5 rounded-full"
                            style={{
                              background: COUNTRY_COLORS[country.iso3] ?? FALLBACK_COLOR,
                            }}
                            aria-hidden
                          />
                          {country.iso3}
                        </span>
                      ))}
                    </span>
                    <span className="flex justify-between">
                      {ticks.map((tick) => (
                        <span key={tick}>{tick}</span>
                      ))}
                    </span>
                  </div>
                  <ul>
                    {rows.map((row) => {
                      const on = row.code === selected?.code;
                      return (
                        <li
                          key={row.code}
                          className={cn(
                            'group flex items-center rounded-md',
                            on ? 'bg-brand/8' : 'hover:bg-surface',
                          )}
                        >
                          <Link
                            href={href(row.code)}
                            scroll={false}
                            aria-current={on ? 'true' : undefined}
                            className="grid min-h-[30px] min-w-0 flex-1 grid-cols-[minmax(8rem,260px)_minmax(0,1fr)] items-center gap-4 px-2 py-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                          >
                            <span
                              className="truncate text-[13px] text-heading"
                              title={row.name}
                            >
                              {row.name}
                            </span>
                            <span className="relative block h-[22px]">
                              <span className="absolute inset-x-0 top-[10px] h-px bg-surface-2" />
                              <span
                                className="absolute top-[9px] h-[3px] rounded bg-line"
                                style={{
                                  left: pct(row.min),
                                  width: `calc(${pct(row.max)} - ${pct(row.min)})`,
                                }}
                              />
                              {row.scored.map((item) => (
                                <span
                                  key={item.country_iso3}
                                  title={`${names[item.country_iso3] ?? item.country_iso3}: ${formatScore(item.score)}`}
                                  className="absolute top-1 -ml-1.5 size-[13px] rounded-full border-2 border-white"
                                  style={{
                                    left: pct(item.score!),
                                    background:
                                      COUNTRY_COLORS[item.country_iso3] ?? FALLBACK_COLOR,
                                  }}
                                />
                              ))}
                            </span>
                          </Link>
                          <Link
                            href={`/ocupaciones/${row.code}`}
                            aria-label={`Abrir la ficha de ${row.name}`}
                            title="Abrir ficha"
                            className={cn(
                              'flex size-8 shrink-0 items-center justify-center rounded-md text-brand hover:bg-brand/10 focus-visible:opacity-100',
                              on ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
                            )}
                          >
                            <ArrowRight className="size-4" aria-hidden />
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                  <SourceLine
                    source={`${rows.length} ocupaciones${unscored ? ` (${unscored} sin ISE por falta de datos)` : ''} · Fuentes: ILOSTAT, SIMEL (INE Chile) y OIT (2025)`}
                  >
                    <Link href="/metodologia/ise" className="text-link hover:underline">
                      ¿Cómo se calcula el ISE?
                    </Link>
                  </SourceLine>
                </div>
              </div>
            )
          }
          rail={
            selected && (
              <RailCard>
                <Eyebrow>
                  CIUO {selected.code}
                  {selected.sector ? ` · ${selected.sector}` : ''}
                </Eyebrow>
                <h2 className="text-[22px] leading-tight font-bold text-heading">
                  {selected.name}
                </h2>
                <Link href={`/ocupaciones/${selected.code}`} className={buttonCls}>
                  Abrir ficha <ArrowRight className="size-4" aria-hidden />
                </Link>
                <p className="-mt-2 text-[11px] text-muted-text">
                  Dimensiones del ISE, evolución y habilidades
                </p>
                <div>
                  {countries.map((country) => {
                    const item = selected.items.find(
                      (candidate) => candidate.country_iso3 === country.iso3,
                    );
                    return (
                      <div
                        key={country.iso3}
                        className="flex items-center justify-between gap-3 border-b border-card-border py-2"
                      >
                        <span className="text-sm text-body">{country.name_es}</span>
                        <span className="flex items-center gap-2">
                          {item && item.score !== null && (
                            <Badge tone={LEVEL_TONES[item.level] ?? 'neutral'}>
                              {item.level_label}
                            </Badge>
                          )}
                          <span className="text-xl font-bold text-heading">
                            {item && item.score !== null ? formatScore(item.score) : 'sin dato'}
                          </span>
                        </span>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[13px] leading-relaxed text-body">
                  Diferencia entre países: {formatScore(selected.max - selected.min)} puntos. Las
                  ocupaciones de un mismo grupo CIUO comparten los datos de demanda y salario del
                  grupo.
                </p>
              </RailCard>
            )
          }
        />

        <div className="mt-8">
          <InfoNote title="Nota metodológica: ponderación dinámica del ISE">
            <p>
              El índice redistribuye los pesos cuando un componente no tiene fuente disponible. Para{' '}
              {year ?? 'el año seleccionado'} la demanda neta aporta{' '}
              {formatNumber(
                (ranges.find((range) => range.dimension === 'net_demand')?.effective_weight ?? 0) *
                  100,
                1,
              )}
              %, el salario PPA{' '}
              {formatNumber(
                (ranges.find((range) => range.dimension === 'salary_ppp')?.effective_weight ?? 0) *
                  100,
                1,
              )}
              % y el riesgo de IA{' '}
              {formatNumber(
                (ranges.find((range) => range.dimension === 'automation_risk')?.effective_weight ??
                  0) * 100,
                1,
              )}
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
        </div>

        <DataSourceFooter
          className="mt-6"
          source={`Observatorio · Índice de Empleabilidad Sectorial (datos calculados)${sectorScope}`}
          updatedAt={updatedAt ?? 'Sin fecha informada'}
          methodologyHref="/panorama-regional"
        />
      </Page>
    </>
  );
}
