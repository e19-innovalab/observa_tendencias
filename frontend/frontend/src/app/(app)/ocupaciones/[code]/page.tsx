import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, ArrowRight, ArrowUpRight, Star } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { CountryFilter } from '@/components/data/CountryFilter';
import { OccupationChangeCards } from '@/components/data/OccupationChangeCards';
import { OccupationJumpSelect } from '@/components/data/OccupationJumpSelect';
import { SectorPicker } from '@/components/data/SectorPicker';
import { SkillsCloud } from '@/components/data/SkillsCloud';
import { YearRange } from '@/components/data/YearRange';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { FilterLabel, FilterPanel } from '@/components/ui/filters/FilterPanel';
import { MetricCard } from '@/components/ui/indicators/MetricCard';
import { ScoreHeroCard } from '@/components/ui/indicators/ScoreHeroCard';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { EmployabilityBreakdownTable } from '@/components/ui/tables/EmployabilityBreakdownTable';
import { ApiError } from '@/lib/api/client';
import {
  getEmployabilityHistory,
  getOccupationProfile,
} from '@/lib/api/employability';
import { getCountries, getIndicators, getSectors } from '@/lib/api/panorama';
import { getOccupationSkills, getOccupations } from '@/lib/api/skills';
import { DIMENSION_COLORS } from '@/lib/constants';
import type {
  Country,
  EmployabilityComponent,
  EmployabilityHistory,
  Indicator,
  Occupation,
  OccupationProfile,
  OccupationSkills,
  Sector,
  SkillItem,
} from '@/lib/schemas/api';
import { findComponent } from '@/lib/utils/employability';
import {
  formatComponentValue,
  formatDate,
  formatIndex01,
  formatNumber,
  formatSignedPercent,
  formatValue,
  riskLabel,
} from '@/lib/utils/format';

type Props = {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ country?: string; desde?: string; hasta?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { code } = await params;
  try {
    const profile = await getOccupationProfile(code);
    return { title: profile.occupation.name };
  } catch {
    return { title: `Ocupación ${code}` };
  }
}

const COUNTRY_NAMES: Record<string, string> = {
  ARG: 'Argentina',
  CHL: 'Chile',
  URY: 'Uruguay',
};

function expansionLabel(raw: number | null): string {
  if (raw === null) return 'Sin dato';
  if (raw >= 0.03) return 'Expansión alta';
  if (raw > 0) return 'Expansión moderada';
  if (raw < 0) return 'Contracción';
  return 'Estable';
}

function componentValue(component?: EmployabilityComponent): string {
  if (!component || component.raw === null || component.raw === undefined) return '—';
  return formatComponentValue(component.dimension, component.raw, component.unit);
}

function detailRange(component?: EmployabilityComponent): string | undefined {
  if (!component) return undefined;
  const detail = component.detail ?? {};
  if (detail.from_period !== undefined && detail.to_period !== undefined) {
    return `${String(detail.from_period)}–${String(detail.to_period)}`;
  }
  if (detail.period !== undefined) return String(detail.period);
  return undefined;
}

export default async function OcupacionDetallePage({ params, searchParams }: Props) {
  const { code } = await params;
  const sp = await searchParams;

  let profile: OccupationProfile | null = null;
  let errorMessage = '';

  try {
    profile = await getOccupationProfile(code);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar la ocupación.';
  }

  if (!profile) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-10 sm:px-6">
        <Link
          href="/ocupaciones"
          className="inline-flex items-center gap-2 text-sm font-medium text-link hover:text-link-hover hover:underline"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Volver al ranking de ocupaciones
        </Link>
        <ApiErrorNote message={errorMessage} />
      </div>
    );
  }

  const selected =
    profile.employability.find((item) => item.country_iso3 === sp.country) ??
    profile.employability.find((item) => item.country_iso3 === 'ARG') ??
    profile.employability[0] ??
    null;

  const sectorCode = profile.occupation.sector_code ?? undefined;

  const [historyResult, indicatorsResult, countriesResult, sectorsResult, occupationsResult, skillsResult] =
    await Promise.allSettled([
      selected
        ? getEmployabilityHistory(code, [selected.country_iso3])
        : Promise.resolve<EmployabilityHistory[]>([]),
      getIndicators(),
      getCountries(),
      getSectors(),
      getOccupations(sectorCode),
      getOccupationSkills(code, { limit: 300 }),
    ]);

  const history = historyResult.status === 'fulfilled' ? historyResult.value : [];
  const indicators: Indicator[] = indicatorsResult.status === 'fulfilled' ? indicatorsResult.value : [];
  const countries: Country[] = countriesResult.status === 'fulfilled' ? countriesResult.value : [];
  const sectors: Sector[] = sectorsResult.status === 'fulfilled' ? sectorsResult.value : [];
  const occupations: Occupation[] =
    occupationsResult.status === 'fulfilled' ? occupationsResult.value : [];
  const skills: OccupationSkills | null =
    skillsResult.status === 'fulfilled' ? skillsResult.value : null;

  const countryName = selected
    ? (COUNTRY_NAMES[selected.country_iso3] ?? selected.country_iso3)
    : '';

  const demand = selected ? findComponent(selected, 'net_demand') : undefined;
  const salary = selected ? findComponent(selected, 'salary_ppp') : undefined;
  const risk = selected ? findComponent(selected, 'automation_risk') : undefined;
  const insertion = selected ? findComponent(selected, 'insertion_rate') : undefined;

  const historyPoints = history[0]?.points ?? [];
  const historyYears = [...new Set(historyPoints.map((point) => point.year))].sort((a, b) => a - b);
  const fallbackYear = selected?.year ?? new Date().getFullYear();
  const years = historyYears.length ? historyYears : [fallbackYear];
  const minYear = years[0] ?? fallbackYear;
  const maxYear = years.at(-1) ?? fallbackYear;

  const desdeNumber = Number(sp.desde);
  const hastaNumber = Number(sp.hasta);
  const desde = sp.desde && Number.isFinite(desdeNumber) ? desdeNumber : minYear;
  const hasta = sp.hasta && Number.isFinite(hastaNumber) ? hastaNumber : maxYear;

  const historyRows = historyPoints
    .filter((point) => point.year >= desde && point.year <= hasta)
    .map((point) => ({ label: String(point.year), score: point.score }));
  const historySeries = [{ key: 'score', label: `ISE · ${countryName}`, color: '#172bc4' }];

  const segments = (selected?.components ?? [])
    .filter(
      (component) =>
        component.contribution !== null && component.contribution !== undefined && component.available,
    )
    .map((component) => ({
      label: component.label,
      value: component.contribution ?? 0,
      color: DIMENSION_COLORS[component.dimension] ?? '#172bc4',
    }));

  const activeDimensions = (selected?.components ?? []).filter((component) => component.available).length;
  const totalDimensions = selected?.components.length ?? 0;

  const occupationOptions = occupations.length
    ? occupations
    : [
        {
          occupation_code: profile.occupation.occupation_code,
          name: profile.occupation.name,
          isco08_code: profile.occupation.isco08_code,
          sector_code: profile.occupation.sector_code,
        },
      ];

  const occupationFromSector = occupationOptions.some(
    (occupation) => occupation.occupation_code === profile.occupation.occupation_code,
  );
  if (!occupationFromSector) {
    occupationOptions.unshift({
      occupation_code: profile.occupation.occupation_code,
      name: profile.occupation.name,
      isco08_code: profile.occupation.isco08_code,
      sector_code: profile.occupation.sector_code,
    });
  }

  const sectorCodes = sectorCode ? [sectorCode] : undefined;

  const occupationHref = (occupation: Occupation) => {
    const query = new URLSearchParams();
    if (sp.country) query.set('country', sp.country);
    if (sp.desde) query.set('desde', sp.desde);
    if (sp.hasta) query.set('hasta', sp.hasta);
    const qs = query.toString();
    return `/ocupaciones/${occupation.occupation_code}${qs ? `?${qs}` : ''}`;
  };

  const sectorHref = (code: string) => {
    const query = new URLSearchParams();
    if (sp.country) query.set('country', sp.country);
    query.set('sector', code);
    return `/ocupaciones?${query.toString()}`;
  };

  const allSectorHref = sectorCode ? `/ocupaciones?sector=${sectorCode}` : '/ocupaciones';

  const topSkills: SkillItem[] = skills?.items?.length ? skills.items : profile.top_skills;
  const skillsTotal = skills?.total ?? topSkills.length;

  const indicatorName = (indicatorCode: string) =>
    indicators.find((indicator) => indicator.code === indicatorCode)?.name ?? indicatorCode;

  const updatedAt = formatDate(selected?.computed_at ?? null);
  const methodology = selected?.methodology;

  const topGroup = profile.hierarchy.at(-1);

  const description = [
    topGroup
      ? `Ocupación del catálogo CIUO-08 dentro del grupo ${topGroup.code} · ${topGroup.name}.`
      : 'Ocupación del catálogo CIUO-08.',
    profile.sector_name
      ? `Se analiza dentro de ${profile.sector_name}, con datos comparables entre Argentina, Chile y Uruguay.`
      : 'Datos comparables entre Argentina, Chile y Uruguay.',
  ].join(' ');

  return (
    <>
      <PageHero
        align="left"
        breadcrumbs={[
          { label: 'Inicio', href: '/inicio' },
          { label: 'Ocupaciones', href: '/ocupaciones' },
          { label: profile.occupation.name },
        ]}
        leading={
          <>
            {selected && (
              <Badge tone="neutral" className="border-white/25 bg-white/10 text-white">
                {countryName} ({selected.country_iso3})
              </Badge>
            )}
            <Badge tone="neutral" className="border-white/25 bg-white/10 text-white">
              CIUO {profile.occupation.occupation_code}
            </Badge>
            {profile.sector_name && (
              <Badge tone="neutral" className="border-white/25 bg-white/10 text-white">
                {profile.sector_name}
              </Badge>
            )}
            {profile.occupation.is_featured && (
              <Badge tone="neutral" className="border-white/25 bg-white/10 text-white">
                <Star className="size-3 fill-white" aria-hidden /> Destacada
              </Badge>
            )}
          </>
        }
        title={profile.occupation.name}
        description={description}
        actions={
          <Link
            href="/ocupaciones"
            className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3.5 py-2 text-[12.5px] font-semibold text-white transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Volver a Ocupaciones
          </Link>
        }
      >
        {selected && (
          <ScoreHeroCard
            score={selected.score}
            levelLabel={selected.level_label}
            coverage={{ active: activeDimensions, total: totalDimensions }}
            segments={segments}
            className="lg:w-[350px]"
          />
        )}
      </PageHero>

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <FilterPanel className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
            <div>
              <FilterLabel className="mb-2 block">Países</FilterLabel>
              <CountryFilter
                countries={countries}
                value={selected?.country_iso3 ?? ''}
                reset={['page']}
                compact
              />
            </div>

            <div className="min-w-[260px] flex-1 sm:max-w-md">
              <FilterLabel className="mb-2 block">Ocupación</FilterLabel>
              <OccupationJumpSelect
                options={occupationOptions.map((occupation) => ({
                  occupation_code: occupation.occupation_code,
                  name: occupation.name,
                  href: occupationHref(occupation),
                }))}
                value={profile.occupation.occupation_code}
              />
            </div>

            <div>
              <FilterLabel className="mb-2 block">Período</FilterLabel>
              <YearRange
                years={[...years].reverse()}
                desde={String(desde)}
                hasta={String(hasta)}
              />
            </div>
          </div>

          <div className="border-t border-card-border pt-4">
            <FilterLabel className="mb-2.5 block">Sectores</FilterLabel>
            <SectorPicker
              sectors={sectors}
              active={sectorCode}
              hrefFor={sectorHref}
            />
          </div>
        </FilterPanel>

        <OccupationChangeCards
          occupations={occupationOptions}
          activeCode={profile.occupation.occupation_code}
          hrefFor={occupationHref}
          allHref={allSectorHref}
          limit={sectorCodes ? 8 : 6}
        />

        {selected ? (
          <>
            <section
              aria-label="Indicadores de la ocupación"
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <MetricCard
                label="Demanda neta proyectada"
                value={
                  demand?.raw === null || demand?.raw === undefined
                    ? '—'
                    : formatSignedPercent(demand.raw, 1)
                }
                unit="anual"
                badge={
                  <Badge
                    tone={
                      demand?.raw === null || demand?.raw === undefined
                        ? 'neutral'
                        : demand.raw > 0
                          ? 'success'
                          : 'warning'
                    }
                  >
                    {expansionLabel(demand?.raw ?? null)}
                  </Badge>
                }
                hint="Crecimiento anual del empleo del grupo ocupacional."
                meta={detailRange(demand) ?? String(selected.year)}
              />

              <MetricCard
                label={salary?.display?.label ?? 'Salario mediano (PPA)'}
                value={
                  salary?.display
                    ? formatNumber(salary.display.value, 2)
                    : salary?.raw === null || salary?.raw === undefined
                      ? '—'
                      : formatNumber(salary.raw, 2)
                }
                unit={salary?.display ? 'USD / mes' : 'USD PPA / mes'}
                chip={
                  salary?.contribution !== null && salary?.contribution !== undefined ? (
                    <span className="inline-flex items-center rounded-md border border-card-border bg-surface-2 px-2 py-0.5 text-[10.5px] font-semibold text-body">
                      Aporte ISE: {formatNumber(salary.contribution, 1)} puntos
                    </span>
                  ) : undefined
                }
                hint={
                  salary?.display
                    ? 'Salario convertido por OIT; el ISE usa USD PPA para comparar entre países.'
                    : 'Ingreso mensual promedio en USD PPA.'
                }
                meta={salary?.display?.period ?? detailRange(salary)}
              />

              <MetricCard
                label="Exposición a la IA generativa"
                value={
                  risk?.raw === null || risk?.raw === undefined ? '—' : formatIndex01(risk.raw)
                }
                unit="índice 0-1"
                badge={<Badge tone="warning">{riskLabel(risk?.raw ?? null)}</Badge>}
                hint="Proporción de tareas que la IA generativa podría sustituir o complementar."
                meta="OIT 2025"
              />

              {insertion?.available ? (
                <MetricCard
                  label="Tasa de inserción de graduados"
                  value={componentValue(insertion)}
                  badge={<Badge tone="success">Con fuente</Badge>}
                  hint="Vinculación entre graduados y empleo formal."
                  meta={detailRange(insertion)}
                />
              ) : (
                <MetricCard
                  label="Tasa de inserción de graduados"
                  value="—"
                  badge={<Badge tone="neutral">Sin dato oficial</Badge>}
                  chip={
                    <span className="inline-flex items-center rounded-md border border-card-border bg-surface-2 px-2 py-0.5 text-[10.5px] font-semibold text-body">
                      Peso redistribuido
                    </span>
                  }
                  hint="Todavía no hay una fuente pública por ocupación."
                  meta="Proporcional"
                />
              )}
            </section>

            <section className="rounded-xl border border-card-border bg-canvas p-5 shadow-[var(--shadow-card)]">
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {selected && (
                      <Badge tone="neutral">
                        {countryName} ({selected.country_iso3})
                      </Badge>
                    )}
                    <Badge tone="neutral">CIUO {profile.occupation.occupation_code}</Badge>
                    {profile.sector_name && <Badge tone="brand">{profile.sector_name}</Badge>}
                    {profile.occupation.is_featured && (
                      <Badge tone="warning">
                        <Star className="size-3" aria-hidden /> Destacada
                      </Badge>
                    )}
                  </div>

                  <h2 className="mt-3 text-[26px] leading-tight font-bold tracking-tight text-heading">
                    {profile.occupation.name}
                  </h2>
                  <p className="mt-2 max-w-3xl text-[12.5px] leading-relaxed text-muted-text">
                    {description}
                  </p>

                  <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 border-t border-card-border pt-3 text-[11px]">
                    <div className="flex gap-1.5">
                      <dt className="font-semibold text-body">Equivalencia ESCO:</dt>
                      <dd className="text-muted-text">
                        {profile.occupation.name_en ?? 'Sin equivalencia registrada'}
                      </dd>
                    </div>
                    <div className="flex gap-1.5">
                      <dt className="font-semibold text-body">Catálogo:</dt>
                      <dd className="text-muted-text">CIUO-08 · {profile.occupation.isco08_code}</dd>
                    </div>
                    {profile.hierarchy.length > 0 && (
                      <div className="flex gap-1.5">
                        <dt className="font-semibold text-body">Grupo:</dt>
                        <dd className="text-muted-text">
                          {profile.hierarchy.at(-1)?.code} · {profile.hierarchy.at(-1)?.name}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>

                <ScoreHeroCard
                  score={selected.score}
                  levelLabel={selected.level_label}
                  coverage={{ active: activeDimensions, total: totalDimensions }}
                  segments={segments}
                  className="shadow-none"
                />
              </div>
            </section>

            <section className="space-y-4">
              <SectionHeading
                title="Desglose Factorial del Índice de Empleabilidad (ISE)"
                description={`Auditoría detallada de valores, normalización a escala 0-100, ponderaciones teóricas y fuentes del sistema · ${countryName} ${selected.year}.`}
                action={{ label: 'Ver metodología', href: '/metodologia/ise' }}
              />
              <EmployabilityBreakdownTable
                item={selected}
                terms={{
                  normalized:
                    'Valor de la dimensión llevado a una escala de 0 a 100 dentro del grupo comparado.',
                  contribution:
                    'Puntos que suma la dimensión al ISE: valor escalado por su peso efectivo.',
                }}
              />
            </section>

            {historyRows.length > 0 && (
              <ChartCard
                title="Evolución del ISE"
                subtitle={`Serie anual calculada para ${profile.occupation.name} en ${countryName}.`}
                legend={historySeries.map((item) => ({ label: item.label, color: item.color }))}
                sourceName="Observatorio · Índice de Empleabilidad Sectorial"
                updatedAt={updatedAt}
                methodologyHref="/metodologia/ise"
              >
                <TrendLineChart data={historyRows} series={historySeries} unit="index_0_1" />
              </ChartCard>
            )}
          </>
        ) : (
          <ApiErrorNote message="La ocupación no tiene registros de empleabilidad para mostrar." />
        )}

        {topSkills.length > 0 && (
          <section className="rounded-xl border border-card-border bg-canvas p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-[17px] leading-snug font-semibold text-heading">
                  Habilidades principales ({skillsTotal} en total){' '}
                  <span className="ml-1 rounded-md border border-brand/20 bg-brand/8 px-1.5 py-0.5 align-middle text-[9.5px] font-bold tracking-wide text-brand uppercase">
                    ESCO Taxonomía V1.1
                  </span>
                </h2>
                <p className="mt-1 max-w-3xl text-[12px] text-muted-text">
                  {skills?.weight_note ??
                    'Matriz de competencias esenciales y transversales indexadas con su coeficiente de relevancia específica para esta ocupación.'}
                </p>
              </div>
              <Link
                href="/habilidades?tab=gaps"
                className="inline-flex max-w-sm items-center gap-1 text-[12px] font-semibold text-link hover:text-link-hover hover:underline"
              >
                Ver análisis comparativo de brechas de estas habilidades en la sección Habilidades
                <ArrowRight className="size-3.5 shrink-0" aria-hidden />
              </Link>
            </div>

            <div className="mt-4">
              <SkillsCloud skills={topSkills} total={skillsTotal} />
            </div>
          </section>
        )}

        {profile.latest.length > 0 && (
          <section className="space-y-4">
            <SectionHeading
              title="Últimos datos de la ocupación"
              description="Observaciones más recientes informadas por la API para esta ocupación."
            />
            <div className="overflow-x-auto rounded-xl border border-card-border bg-canvas">
              <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-card-border bg-surface-2 text-[11px] tracking-wide text-muted-text uppercase">
                    <th scope="col" className="px-4 py-3 font-semibold">País</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Indicador</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Período</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Valor</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Fuente</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-card-border">
                  {profile.latest.map((point) => (
                    <tr
                      key={`${point.country_iso3}-${point.indicator_code}-${point.period}`}
                      className="hover:bg-surface"
                    >
                      <td className="px-4 py-3">
                        <Badge tone="neutral">{point.country_iso3}</Badge>
                      </td>
                      <td className="px-4 py-3 text-heading">{indicatorName(point.indicator_code)}</td>
                      <td className="px-4 py-3 text-body">{point.period}</td>
                      <td className="px-4 py-3 font-medium text-heading">
                        {formatValue(point.value, point.unit)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-text">{point.source.name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-card-border bg-rail px-4 py-3 text-[11.5px] text-muted-text">
          <span>
            <span className="font-semibold text-body">Fuente</span> ·{' '}
            {methodology?.name ?? 'Observatorio · Índice de Empleabilidad Sectorial'}
          </span>
          <Link
            href="/habilidades?tab=gaps"
            className="inline-flex items-center gap-1 font-semibold text-link hover:text-link-hover hover:underline"
          >
            Explorar brechas de habilidades
            <ArrowUpRight className="size-3.5" aria-hidden />
          </Link>
        </div>

        <DataSourceFooter
          source={
            methodology
              ? `${methodology.name ?? 'Índice de Empleabilidad Sectorial'} · v${methodology.version}`
              : 'Observatorio · Índice de Empleabilidad Sectorial'
          }
          updatedAt={updatedAt ?? 'Sin fecha informada'}
          methodologyHref="/metodologia/ise"
        />
      </div>
    </>
  );
}
