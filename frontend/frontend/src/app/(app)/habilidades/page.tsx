import type { Metadata } from 'next';
import { Suspense } from 'react';
import { Badge } from '@/components/ui/badge';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { StatCard } from '@/components/ui/indicators/StatCard';
import { DataSourceFooter } from '@/components/ui/layout/DataSourceFooter';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import { GenderView } from '@/components/data/GenderView';
import { GraduatesView } from '@/components/data/GraduatesView';
import { SectorKpisView } from '@/components/data/SectorKpisView';
import { SkillGapsView } from '@/components/data/SkillGapsView';
import { ApiError } from '@/lib/api/client';
import { getGraduateProjections } from '@/lib/api/graduates';
import type { GraduateProjectionItem } from '@/lib/schemas/api';
import { formatNumber, formatSignedPercent } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Habilidades' };

type SearchParams = {
  tab?: string;
  nivel?: string;
  anio?: string;
  country?: string;
  sector?: string;
  relacion?: string;
  sel?: string;
  q?: string;
  carrera?: string;
  sector_kpi?: string;
  sector_carrera?: string;
  tema?: string;
  desde?: string;
  hasta?: string;
  proyeccion?: string;
  institucion?: string;
};

const TABS = [
  { id: 'gaps', label: 'Brechas de Habilidades' },
  { id: 'titulados', label: 'Titulados' },
  { id: 'sectores', label: 'Indicadores por sector' },
  { id: 'genero', label: 'Género' },
  { id: 'projections', label: 'Proyecciones' },
];

const TAB_IDS = new Set(TABS.map((tab) => tab.id));

export default async function HabilidadesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const tab = sp.tab && TAB_IDS.has(sp.tab) ? sp.tab : 'gaps';

  return (
    <>
      <PageHero
        title="Habilidades"
        description="Identificá las brechas entre la demanda del mercado laboral y la formación disponible, y anticipá las necesidades futuras."
      />

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <SectionTabs tabs={TABS} active={tab} />

        <Suspense fallback={<PageSkeleton />}>
          {tab === 'titulados' ? (
            <GraduatesView sp={sp} />
          ) : tab === 'sectores' ? (
            <SectorKpisView sp={sp} />
          ) : tab === 'genero' ? (
            <GenderView sp={sp} />
          ) : tab === 'projections' ? (
            <ProjectionsView />
          ) : (
            <SkillGapsView sp={sp} />
          )}
        </Suspense>
      </div>
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
        ? (last.graduados_proyectado - first.graduados_proyectado) / first.graduados_proyectado
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
                <tr className="border-b border-line bg-surface-2 text-[11px] tracking-wide text-muted-text uppercase">
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Carrera
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {firstYear ?? 'Inicio'}
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {lastYear ?? 'Fin'}
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Variación
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Rango final
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {careerRows.map((row) => (
                  <tr key={row.career} className="hover:bg-surface">
                    <td className="px-4 py-3 font-medium text-heading capitalize">{row.career}</td>
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
