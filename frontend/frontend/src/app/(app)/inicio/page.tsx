import type { Metadata } from 'next';
import { io } from 'next/cache';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { QuickAccessGrid } from '@/components/ui/home/QuickAccessGrid';
import { TrendsFeed } from '@/components/ui/home/TrendsFeed';
import { KpiCard } from '@/components/ui/indicators/KpiCard';
import { SectionHeading } from '@/components/ui/layout/SectionHeading';
import { getAlerts } from '@/lib/api/alerts';
import { ApiError } from '@/lib/api/client';
import { getCountries, getDashboardSummary } from '@/lib/api/panorama';
import { QUICK_ACCESS } from '@/lib/constants';
import type { DashboardSummary, HighlightCard, Indicator } from '@/lib/schemas/api';
import type { TrendFeedItem } from '@/lib/ui-types';
import { formatChange, formatDate, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Inicio' };

type Kpi = {
  label: string;
  value: string;
  caption: string;
  changeText: string | null;
  negative: boolean;
};

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/**
 * Los destacados del backend son por país. Para el inicio se muestra el promedio
 * regional de los indicadores que aparecen en los tres resúmenes.
 */
function buildRegionalKpis(summaries: DashboardSummary[]): Kpi[] {
  const grouped = new Map<string, { indicator: Indicator; items: HighlightCard[] }>();

  for (const summary of summaries) {
    for (const highlight of summary.highlights) {
      const entry = grouped.get(highlight.indicator.code) ?? {
        indicator: highlight.indicator,
        items: [],
      };
      entry.items.push(highlight);
      grouped.set(highlight.indicator.code, entry);
    }
  }

  return [...grouped.values()].slice(0, 4).flatMap(({ indicator, items }) => {
    const value = average(
      items.flatMap((item) => (item.current ? [item.current.value] : [])),
    );
    if (value === null) return [];

    const change = average(items.flatMap((item) => (item.change === null ? [] : [item.change])));
    const countryCodes = [...new Set(items.map((item) => item.country_iso3))];
    const periods = [
      ...new Set(items.flatMap((item) => (item.current ? [item.current.period] : []))),
    ].sort();
    const periodText =
      periods.length <= 1 ? (periods[0] ?? '') : `${periods[0]}–${periods.at(-1)}`;

    return [
      {
        label: indicator.name,
        value: formatValue(value, indicator.unit),
        caption: `${countryCodes.join(', ')} · ${periodText}`,
        changeText: formatChange(change, items[0]?.change_kind ?? 'absolute', indicator.unit),
        negative: change !== null && change < 0,
      },
    ];
  });
}

function buildFeed(alertsPage: Awaited<ReturnType<typeof getAlerts>> | null): TrendFeedItem[] {
  if (!alertsPage) return [];
  return alertsPage.items.slice(0, 4).map((alert) => ({
    id: String(alert.alert_id),
    title: alert.message,
    detail: [alert.alert_type_label, alert.source?.name].filter(Boolean).join(' · '),
    date: formatDate(alert.detected_at) ?? '',
    country: alert.country_iso3 ?? 'Regional',
  }));
}

export default async function InicioPage() {
  await io(); // el inicio se calcula con datos vivos, no en el shell estático

  let kpis: Kpi[] = [];
  let feed: TrendFeedItem[] = [];
  let errorMessage = '';

  try {
    const countries = await getCountries();
    const [summaries, alerts] = await Promise.all([
      Promise.all(countries.map((country) => getDashboardSummary(country.iso3))),
      getAlerts({ limit: 4 }),
    ]);
    kpis = buildRegionalKpis(summaries);
    feed = buildFeed(alerts);
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : 'Error inesperado al cargar los datos.';
  }

  return (
    <div className="mx-auto max-w-7xl space-y-10 px-4 py-8 sm:px-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-heading">¡Hola Santiago!</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-text sm:text-base">
          Estos son los datos más destacados del observatorio. Podés explorar las secciones del
          menú o usar los accesos rápidos.
        </p>
      </header>

      {errorMessage && <ApiErrorNote message={errorMessage} />}

      {kpis.length > 0 && (
        <section aria-label="Indicadores destacados">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi) => (
              <KpiCard
                key={kpi.label}
                label={kpi.label}
                value={kpi.value}
                caption={kpi.caption}
                changeText={kpi.changeText}
                negative={kpi.negative}
              />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-4" aria-labelledby="accesos-rapidos">
        <div id="accesos-rapidos">
          <SectionHeading
            title="Accesos rápidos"
            description="Entrá directo a la sección que necesitás analizar."
          />
        </div>
        <QuickAccessGrid items={QUICK_ACCESS} />
      </section>

      <section className="space-y-4" aria-labelledby="ultimas-tendencias">
        <div id="ultimas-tendencias">
          <SectionHeading
            title="Últimas tendencias"
            action={{ label: 'Ver todas', href: '/tendencias' }}
          />
        </div>
        {feed.length > 0 ? (
          <TrendsFeed items={feed} />
        ) : (
          <p className="rounded-lg border border-line bg-surface px-4 py-6 text-center text-sm text-muted-text">
            No hay novedades recientes para mostrar.
          </p>
        )}
      </section>
    </div>
  );
}
