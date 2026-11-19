import { Suspense } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import {
  Activity,
  BrainCircuit,
  MonitorPlay,
  Plane,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { CountryFilter } from '@/components/data/CountryFilter';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import { SectorKpisView } from '@/components/data/SectorKpisView';
import {
  ChartHeader,
  ChartLayout,
  ErrorNote,
  Eyebrow,
  Page,
  RailCard,
  SourceLine,
  Stat,
  buttonCls,
} from '@/components/data/ui';
import { UrlSeg } from '@/components/data/UrlSeg';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { ApiError } from '@/lib/api/client';
import { getSectorSummaries } from '@/lib/api/employability';
import { getCountries, getSectors } from '@/lib/api/panorama';
import type { Country, Sector, SectorsPage } from '@/lib/schemas/api';
import { cn } from '@/lib/utils';
import { formatIndex01, formatNumber, formatScore, formatUsd } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Sectores' };

type SearchParams = {
  country?: string;
  sector?: string;
  year?: string;
  tab?: string;
  anio?: string;
  sector_kpi?: string;
};

const TABS = [
  { id: 'ise', label: 'Índice de empleabilidad (ISE) sectorial' },
  { id: 'densidad', label: 'Densidad profesional' },
  { id: 'ocupados', label: 'Personas ocupadas' },
];

const YEARS_OFFERED = 3;

const SECTOR_STYLE: Record<string, { icon: LucideIcon; className: string }> = {
  technology: { icon: MonitorPlay, className: 'bg-sector-tech-soft text-sector-tech' },
  energy: { icon: Zap, className: 'bg-sector-energy-soft text-sector-energy' },
  health: { icon: Activity, className: 'bg-sector-health-soft text-sector-health' },
  knowledge_economy: {
    icon: BrainCircuit,
    className: 'bg-sector-knowledge-soft text-sector-knowledge',
  },
  tourism: { icon: Plane, className: 'bg-sector-tourism-soft text-sector-tourism' },
};

const DEFAULT_SECTOR_STYLE = { icon: Activity, className: 'bg-surface-2 text-brand' };

const clamp = (value: number) => Math.max(0, Math.min(100, value));

function countryCodes(sp: SearchParams): string[] | undefined {
  return sp.country && sp.country !== 'all' ? [sp.country] : undefined;
}

function sectorHref(sp: SearchParams, sectorCode: string): string {
  const params = new URLSearchParams();
  if (sp.country && sp.country !== 'all') params.set('country', sp.country);
  if (sp.year) params.set('year', sp.year);
  params.set('sector', sectorCode);
  return `/sectores?${params.toString()}`;
}

function signedPoints(value: number): string {
  return `${value > 0 ? '+' : ''}${formatNumber(value, 1)}`;
}

export default function SectoresPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SectoresContent searchParams={searchParams} />
    </Suspense>
  );
}

async function SectoresContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const tab: 'ise' | 'densidad' | 'ocupados' =
    sp.tab === 'densidad' || sp.tab === 'ocupados' ? sp.tab : 'ise';

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

  const tabs = <SectionTabs tabs={TABS} active={tab} />;

  if (tab !== 'ise') {
    return (
      <Page>
        <div className="space-y-6">
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
      </Page>
    );
  }

  let data: SectorsPage;
  try {
    const year =
      sp.year && /^\d{4}$/.test(sp.year) ? Number(sp.year) : undefined;
    data = await getSectorSummaries({ countries: countryCodes(sp), year });
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
  const items = [...data.items].sort(
    (a, b) => (b.average_score ?? -1) - (a.average_score ?? -1),
  );
  const selected = items.find((item) => item.sector_code === sp.sector) ?? items[0];
  const average = data.regional_average;
  const scope =
    sp.country && sp.country !== 'all' ? (names[sp.country] ?? sp.country) : 'los 3 países';
  const years = data.available_years.slice(-YEARS_OFFERED);
  const latestYear = data.available_years.at(-1);
  const yearOptions = years.map((value) => ({
    value: value === latestYear ? '' : String(value),
    label: String(value),
  }));
  const yearValue =
    sp.year && data.available_years.includes(Number(sp.year)) ? sp.year : '';

  const salaryUsd = selected?.salary_usd_average ?? null;
  const salaryPpp = selected?.salary_ppp_average ?? null;

  return (
    <Page>
      <div className="space-y-4">
        {tabs}

        <ChartHeader
          eyebrow={`Índice de empleabilidad (ISE) · ${data.year ?? ''} · ${scope}`}
          title="¿Qué sector ofrece mejor empleabilidad?"
          subtitle={`Promedio del ISE (0 a 100) de las ocupaciones de cada sector. La marca gris es ${data.year ? data.year - 1 : 'el año anterior'}.`}
          controls={
            <>
              <CountryFilter
                countries={countries}
                value={sp.country && sp.country !== 'all' ? sp.country : ''}
                compact
              />
              {yearOptions.length > 1 && (
                <UrlSeg
                  name="year"
                  label="Año"
                  value={yearValue}
                  options={yearOptions}
                  reset={[]}
                />
              )}
            </>
          }
        />

        <ChartLayout
          stickyRail
          chart={
            items.length === 0 ? (
              <p className="py-24 text-center text-sm text-muted-text">
                No hay datos del ISE sectorial para esta combinación de filtros.
              </p>
            ) : (
              <>
                <div className="grid grid-cols-[minmax(6.5rem,200px)_minmax(4rem,1fr)_5.5rem] gap-4 px-3 pb-2 text-[11px] text-label">
                  <span>Sector</span>
                  <span className="flex justify-between">
                    <span>0</span>
                    <span>25</span>
                    <span>50</span>
                    <span>75</span>
                    <span>100</span>
                  </span>
                  <span className="text-right">ISE · cambio</span>
                </div>
                <ul className="flex flex-col gap-1">
                  {items.map((item) => {
                    const on = item.sector_code === selected?.sector_code;
                    const style = SECTOR_STYLE[item.sector_code] ?? DEFAULT_SECTOR_STYLE;
                    const Icon = style.icon;
                    return (
                      <li key={item.sector_code}>
                        <Link
                          href={sectorHref(sp, item.sector_code)}
                          scroll={false}
                          aria-current={on ? 'true' : undefined}
                          className={cn(
                            'grid grid-cols-[minmax(6.5rem,200px)_minmax(4rem,1fr)_5.5rem] items-center gap-4 rounded-xl px-3 py-3.5 transition-colors',
                            'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                            on ? 'bg-brand/8' : 'hover:bg-surface',
                          )}
                        >
                          <span className="flex min-w-0 items-center gap-2.5 text-[14px] font-semibold text-heading">
                            <span
                              className={cn(
                                'flex size-7 shrink-0 items-center justify-center rounded-md',
                                style.className,
                              )}
                            >
                              <Icon className="size-4" aria-hidden />
                            </span>
                            <span className="truncate">{item.name}</span>
                          </span>
                          <span className="relative block h-7 rounded-md bg-surface-2">
                            {item.average_score !== null && (
                              <span
                                className={cn(
                                  'absolute inset-y-0 left-0 rounded-md',
                                  on ? 'bg-brand' : 'bg-brand/45',
                                )}
                                style={{ width: `${clamp(item.average_score)}%` }}
                              />
                            )}
                            {item.previous_average !== null && (
                              <span
                                className="absolute -inset-y-1 w-[3px] rounded bg-label"
                                style={{
                                  left: `calc(${clamp(item.previous_average)}% - 1px)`,
                                }}
                                title={`Año anterior: ${formatScore(item.previous_average)}`}
                              />
                            )}
                            {average !== null && (
                              <span
                                className="absolute -inset-y-1.5 w-0.5 bg-heading"
                                style={{ left: `${clamp(average)}%` }}
                                title={`Promedio regional: ${formatScore(average)}`}
                              />
                            )}
                          </span>
                          <span className="text-right">
                            <span className="text-xl font-bold text-heading">
                              {formatScore(item.average_score)}
                            </span>
                            {item.change !== null && (
                              <span
                                className={cn(
                                  'ml-1.5 text-xs font-semibold',
                                  item.change >= 0 ? 'text-success' : 'text-danger',
                                )}
                              >
                                {signedPoints(item.change)}
                              </span>
                            )}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
                {average !== null && (
                  <p className="mx-3 mt-3 text-[11px] text-muted-text">
                    Línea vertical oscura: promedio de todas las ocupaciones (
                    {formatScore(average)}).
                  </p>
                )}
                <SourceLine source="Fuentes: ILOSTAT, SIMEL (INE Chile) y OIT (2025)">
                  <Link href="/metodologia/ise" className="text-link hover:underline">
                    ¿Cómo se calcula el ISE?
                  </Link>
                </SourceLine>
              </>
            )
          }
          rail={
            selected && (
              <RailCard>
                <Eyebrow>Sector elegido</Eyebrow>
                <h2 className="text-[22px] leading-tight font-bold text-heading">
                  {selected.name}
                </h2>
                <div className="grid grid-cols-2 gap-3">
                  <Stat label="Ocupaciones" value={String(selected.occupations)} />
                  <Stat label="Nivel" value={selected.level_label ?? '—'} />
                  {salaryUsd !== null ? (
                    <Stat
                      label="Salario medio"
                      value={formatUsd(salaryUsd)}
                      sub={salaryPpp !== null ? `${formatUsd(salaryPpp)} PPA` : undefined}
                    />
                  ) : salaryPpp !== null ? (
                    <Stat label="Salario medio (PPA)" value={formatUsd(salaryPpp)} />
                  ) : (
                    <Stat label="Salario medio" value="—" />
                  )}
                  <Stat
                    label="Exposición a la IA"
                    value={`${selected.automation_average === null ? '—' : formatIndex01(selected.automation_average)} de 1`}
                  />
                </div>
                {selected.top_occupation && (
                  <div className="border-t border-card-border pt-3">
                    <p className="text-[11px] text-label">Ocupación con mayor ISE</p>
                    <Link
                      href={`/ocupaciones/${selected.top_occupation.occupation_code}?country=${selected.top_occupation.country_iso3}`}
                      className="mt-1 block text-sm leading-snug font-semibold text-heading hover:text-link"
                    >
                      {selected.top_occupation.name}
                    </Link>
                    <p className="mt-0.5 text-[13px] text-body">
                      {names[selected.top_occupation.country_iso3] ??
                        selected.top_occupation.country_iso3}{' '}
                      · ISE {formatScore(selected.top_occupation.score)}
                    </p>
                  </div>
                )}
                <Link
                  href={`/ocupaciones?${new URLSearchParams({
                    sector: selected.sector_code,
                    ...(sp.year ? { year: sp.year } : {}),
                  })}`}
                  className={buttonCls}
                >
                  Ver las ocupaciones del sector{data.year ? ` en ${data.year}` : ''} →
                </Link>
              </RailCard>
            )
          }
        />

        <HowCalculated types={['employability_index']} title="¿Cómo se calcula el ISE?" />
      </div>
    </Page>
  );
}
