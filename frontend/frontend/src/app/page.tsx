import { ChartCard } from '@/components/ui/charts/ChartCard';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { SERIES_COLORS, type TrendDatum } from '@/components/ui/charts/chartTheme';
import { FilterBar, type FilterConfig } from './../components/ui/filters/FilterBar';
import { IndicatorSidebar } from '@/components/ui/indicators/IndicatorSidebar';
import { KpiCard } from '@/components/ui/indicators/KpiCard';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';

/* ---- Datos de ejemplo: se reemplazan por la capa de servicios + API ---- */
const TABS = [
  { id: 'economic', label: 'Indicadores socioeconómicos' },
  { id: 'labor', label: 'Laborales' },
  { id: 'education', label: 'Educativos' },
];

const FILTERS: FilterConfig[] = [
  {
    name: 'country',
    label: 'País',
    options: [
      { value: 'ARG', label: 'Argentina' },
      { value: 'URY', label: 'Uruguay' },
      { value: 'CHL', label: 'Chile' },
    ],
  },
  { name: 'sector', label: 'Sector', options: [{ value: 'tech', label: 'Tecnología' }] },
  { name: 'period', label: 'Período', options: [{ value: '2024', label: '2024' }] },
];

const KPIS = [
  { label: 'Indicador de ejemplo 1', value: '11,8 M', change: 2.5 },
  { label: 'Indicador de ejemplo 2', value: '8.236 K', change: -1.2 },
  { label: 'Indicador de ejemplo 3', value: '2.352 M', change: 11 },
  { label: 'Indicador de ejemplo 4', value: '8 K', change: 5.2 },
];

const INDICATORS = [
  { code: 'pbi', name: 'PBI' },
  { code: 'inflacion', name: 'Inflación' },
  { code: 'actividad', name: 'Actividad económica' },
];

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const DATA: TrendDatum[] = MONTHS.map((label, i) => ({
  label,
  current: 240 + i * 38 + (i % 3) * 25,
  previous: 200 + i * 30 + (i % 4) * 35,
}));

type Props = { searchParams: Promise<{ tab?: string; indicator?: string }> };

export default async function PanoramaRegionalPage({ searchParams }: Props) {
  const { tab = 'economic', indicator = 'pbi' } = await searchParams;
  const current = INDICATORS.find((i) => i.code === indicator) ?? INDICATORS[0];

  return (
    <>
      <PageHero
        title="Panorama regional"
        description="Compará indicadores de Argentina, Uruguay y Chile con datos de fuentes oficiales."
      />

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-6">
        <div className="space-y-6">
          <SectionTabs tabs={TABS} active={tab} />
          <FilterBar filters={FILTERS} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {KPIS.map((k) => (
            <KpiCard key={k.label} {...k} />
          ))}
        </div>

        <div className="grid gap-8 lg:grid-cols-[14rem_1fr]">
          <IndicatorSidebar items={INDICATORS} active={current.code} />
          <ChartCard
            title={current.name}
            legend={[
              { label: 'Año actual', color: SERIES_COLORS.current },
              { label: 'Año pasado', color: SERIES_COLORS.previous },
            ]}
            updatedAt="12/05/2021"
            methodologyHref="#"
          >
            <TrendLineChart data={DATA} />
          </ChartCard>
        </div>
      </div>
    </>
  );
}
