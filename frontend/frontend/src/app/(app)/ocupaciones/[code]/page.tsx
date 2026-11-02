import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { OptionPills } from '@/components/ui/controls/OptionPills';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { RankingList } from '@/components/ui/indicators/RankingList';
import { StatCard } from '@/components/ui/indicators/StatCard';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { ApiError } from '@/lib/api/client';
import { getEmployabilityHistory, getOccupationProfile } from '@/lib/api/employability';
import { getIndicators } from '@/lib/api/panorama';
import type {
  EmployabilityHistory,
  EmployabilityItem,
  Indicator,
  OccupationProfile,
} from '@/lib/schemas/api';
import type { RankingItem } from '@/lib/ui-types';
import { findComponent } from '@/lib/utils/employability';
import {
  formatComponentValue,
  formatDate,
  formatIndex01,
  formatNumber,
  formatSignedPercent,
  formatUsd,
  formatValue,
  riskLabel,
} from '@/lib/utils/format';

type Props = {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ country?: string }>;
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

function buildBreakdown(item: EmployabilityItem): RankingItem[] {
  const availableWeight = item.components
    .filter((component) => component.available && component.weight > 0)
    .reduce((sum, component) => sum + component.weight, 0);

  return item.components.map((component, index) => {
    const effective =
      component.available && availableWeight > 0 ? component.weight / availableWeight : 0;
    const delta =
      component.raw === null
        ? undefined
        : `${formatComponentValue(component.dimension, component.raw, component.unit)}${
            component.dimension === 'automation_risk' ? ` · ${riskLabel(component.raw)}` : ''
          }`;

    return {
      rank: index + 1,
      title: component.label,
      meta: `Peso efectivo: ${formatNumber(effective * 100, 1)}%${
        component.unit ? ` · ${component.unit}` : ''
      }`,
      score: component.normalized,
      delta,
      badge: component.available ? undefined : 'En calibración',
      note: component.available
        ? undefined
        : 'Componente a la espera de una fuente oficial de datos.',
    };
  });
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

  const employabilityByCountry = profile.employability;
  const selected =
    employabilityByCountry.find((item) => item.country_iso3 === sp.country) ??
    employabilityByCountry.find((item) => item.country_iso3 === 'ARG') ??
    employabilityByCountry[0] ??
    null;

  let history: EmployabilityHistory[] = [];
  let indicators: Indicator[] = [];
  if (selected) {
    const [historyResult, indicatorsResult] = await Promise.allSettled([
      getEmployabilityHistory(code, [selected.country_iso3]),
      getIndicators(),
    ]);
    if (historyResult.status === 'fulfilled') history = historyResult.value;
    if (indicatorsResult.status === 'fulfilled') indicators = indicatorsResult.value;
  }

  const breakdown = selected ? buildBreakdown(selected) : [];
  const demand = selected ? findComponent(selected, 'net_demand') : undefined;
  const salary = selected ? findComponent(selected, 'salary_ppp') : undefined;
  const risk = selected ? findComponent(selected, 'automation_risk') : undefined;
  const insertion = selected ? findComponent(selected, 'insertion_rate') : undefined;

  const countryNames: Record<string, string> = { ARG: 'Argentina', CHL: 'Chile', URY: 'Uruguay' };
  const countryName = selected ? (countryNames[selected.country_iso3] ?? selected.country_iso3) : '';

  const historyRows =
    history[0]?.points.map((point) => ({ label: String(point.year), score: point.score })) ?? [];
  const historySeries = [
    { key: 'score', label: `ISE · ${countryName}`, color: '#172bc4' },
  ];

  const indicatorName = (code: string) =>
    indicators.find((indicator) => indicator.code === code)?.name ?? code;

  const updatedAt = formatDate(selected?.computed_at ?? null);
  const methodology = selected?.methodology;

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <Link
        href="/ocupaciones"
        className="inline-flex items-center gap-2 text-sm font-medium text-link hover:text-link-hover hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Volver al ranking de ocupaciones
      </Link>

      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-heading sm:text-3xl">
            {profile.occupation.name}
          </h1>
          {profile.sector_name && <Badge tone="brand">{profile.sector_name}</Badge>}
          <Badge tone="neutral">CIUO {profile.occupation.occupation_code}</Badge>
        </div>
        <p className="text-sm text-muted-text">
          {profile.occupation.name_en ?? 'Ocupación del catálogo CIUO-08'} · ISCO{' '}
          {profile.occupation.isco08_code}
        </p>

        {profile.hierarchy.length > 0 && (
          <nav aria-label="Jerarquía CIUO" className="flex flex-wrap items-center gap-1 text-xs text-muted-text">
            {profile.hierarchy.map((level, index) => (
              <span key={`${level.level}-${level.code}`} className="flex items-center gap-1">
                {index > 0 && <span aria-hidden>›</span>}
                <span title={level.level_label} className="text-body">
                  {level.code} · {level.name}
                </span>
              </span>
            ))}
          </nav>
        )}
      </header>

      {employabilityByCountry.length > 1 && (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-text">
            País del desglose
          </p>
          <OptionPills
            param="country"
            label="País del desglose"
            options={employabilityByCountry.map((item) => ({
              value: item.country_iso3,
              label: item.country_iso3,
            }))}
            defaultValue={selected?.country_iso3 ?? employabilityByCountry[0].country_iso3}
          />
        </div>
      )}

      {selected ? (
        <>
          <section aria-label="Indicadores de la ocupación" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Puntaje ISE"
              value={selected.score === null ? '—' : formatNumber(selected.score, 1)}
              unit="/100 pts"
              hint={`${selected.level_label} · Cobertura ${Math.round(selected.coverage_ratio * 100)}%`}
              badge={<Badge tone={selected.score === null ? 'neutral' : 'info'}>{selected.level_label}</Badge>}
            />
            <StatCard
              label="Demanda neta"
              value={demand?.raw === null || demand?.raw === undefined ? '—' : formatSignedPercent(demand.raw)}
              hint="Crecimiento anual del empleo del grupo ocupacional"
            />
            <StatCard
              label="Salario PPA"
              value={salary?.raw === null || salary?.raw === undefined ? '—' : formatUsd(salary.raw)}
              unit="/ mes"
              hint="Ingreso laboral mensual promedio en USD PPA"
            />
            <StatCard
              label="Riesgo de automatización"
              value={risk?.raw === null || risk?.raw === undefined ? '—' : formatIndex01(risk.raw)}
              unit="/1"
              hint={riskLabel(risk?.raw ?? null)}
              badge={<Badge tone="warning">IA</Badge>}
            />
          </section>

          {insertion && !insertion.available && (
            <InfoNote title="Componente sin fuente oficial">
              La tasa de inserción de graduados todavía no tiene una fuente pública por ocupación,
              por lo que su peso se redistribuye entre los demás componentes disponibles.
            </InfoNote>
          )}

          <section className="space-y-4">
            <SectionHeading
              title="Desglose del puntaje ISE"
              description={`Aporte de cada componente al coeficiente final · ${countryName} ${selected.year}.`}
            />
            <RankingList items={breakdown} />
          </section>

          {historyRows.length > 0 && (
            <ChartCard
              title="Evolución del ISE"
              subtitle={`Serie anual calculada para ${profile.occupation.name} en ${countryName}.`}
              legend={historySeries.map((item) => ({ label: item.label, color: item.color }))}
              sourceName="Observatorio · Índice de Empleabilidad Sectorial"
              updatedAt={updatedAt}
              methodologyHref="/panorama-regional"
            >
              <TrendLineChart data={historyRows} series={historySeries} unit="index_0_1" />
            </ChartCard>
          )}
        </>
      ) : (
        <ApiErrorNote message="La ocupación no tiene registros de empleabilidad para mostrar." />
      )}

      {profile.top_skills.length > 0 && (
        <section className="space-y-4">
          <SectionHeading
            title="Habilidades principales"
            description="Habilidades y conocimientos ESCO asociados con mayor peso a esta ocupación."
          />
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {profile.top_skills.map((skill) => (
              <li
                key={skill.skill_code}
                className="rounded-lg border border-line bg-canvas p-4 text-sm"
              >
                <p className="font-medium text-heading">{skill.name}</p>
                <p className="mt-1 text-xs text-muted-text">
                  {skill.skill_type_label ?? 'Habilidad'}
                  {skill.weight !== null && skill.weight !== undefined
                    ? ` · Peso ${formatNumber(skill.weight, 2)}`
                    : ''}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {profile.latest.length > 0 && (
        <section className="space-y-4">
          <SectionHeading
            title="Últimos datos de la ocupación"
            description="Observaciones más recientes informadas por la API para esta ocupación."
          />
          <div className="overflow-x-auto rounded-lg border border-line bg-canvas">
            <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-surface-2 text-[11px] uppercase tracking-wide text-muted-text">
                  <th scope="col" className="px-4 py-3 font-semibold">País</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Indicador</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Período</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Valor</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Fuente</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {profile.latest.map((point) => (
                  <tr key={`${point.country_iso3}-${point.indicator_code}-${point.period}`} className="hover:bg-surface">
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

      <DataSourceFooter
        source={
          methodology
            ? `${methodology.name ?? 'Índice de Empleabilidad Sectorial'} · v${methodology.version}`
            : 'Observatorio · Índice de Empleabilidad Sectorial'
        }
        updatedAt={updatedAt ?? 'Sin fecha informada'}
        methodologyHref="/panorama-regional"
      />
    </div>
  );
}
