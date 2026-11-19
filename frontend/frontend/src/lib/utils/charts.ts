import {
  COUNTRY_COLORS,
  FALLBACK_COLOR,
  type ChartRow,
  type ChartSeries,
} from '@/components/ui/charts/chartTheme';
import type { Country, ObservationPoint, ProjectionResult } from '@/lib/schemas/api';

/** Una fila por período y una columna por país, lista para Recharts. */
export function buildCountryChart(items: ObservationPoint[], countries: Country[]) {
  const sorted = [...items].sort((a, b) => a.period_start.localeCompare(b.period_start));
  const rows = new Map<string, ChartRow>();
  const present = new Set<string>();

  for (const item of sorted) {
    const row = rows.get(item.period) ?? { label: item.period };
    row[item.country_iso3] = item.value;
    rows.set(item.period, row);
    present.add(item.country_iso3);
  }

  const series: ChartSeries[] = countries
    .filter((country) => present.has(country.iso3))
    .map((country) => ({
      key: country.iso3,
      label: country.name_es,
      color: COUNTRY_COLORS[country.iso3] ?? FALLBACK_COLOR,
    }));

  return { data: [...rows.values()], series };
}

/**
 * Serie observada + proyectada por país. La proyección arranca en el último punto
 * observado para que la línea punteada se lea como continuación de la serie.
 */
export function buildProjectionChart(result: ProjectionResult, countries: Country[]) {
  const rows = new Map<string, { row: ChartRow; start: string }>();
  const series: ChartSeries[] = [];

  const ensure = (label: string, start: string) => {
    const entry = rows.get(label) ?? { row: { label }, start };
    rows.set(label, entry);
    return entry;
  };

  for (const item of result.items) {
    const country = countries.find((c) => c.iso3 === item.country_iso3);
    const color = COUNTRY_COLORS[item.country_iso3] ?? FALLBACK_COLOR;
    const name = country?.name_es ?? item.country_iso3;

    series.push({ key: item.country_iso3, label: name, color });
    for (const point of item.observed) {
      ensure(point.period, point.period_start).row[item.country_iso3] = point.value;
    }

    if (item.projected.length === 0) continue;

    const projectedKey = `${item.country_iso3}__projected`;
    series.push({ key: projectedKey, label: `${name} · proyección`, color, dashed: true });

    const lastObserved = item.observed.at(-1);
    if (lastObserved) {
      ensure(lastObserved.period, lastObserved.period_start).row[projectedKey] =
        lastObserved.value;
    }
    for (const point of item.projected) {
      ensure(point.period, point.period_start).row[projectedKey] = point.value;
    }
  }

  const data = [...rows.values()]
    .sort((a, b) => a.start.localeCompare(b.start))
    .map((entry) => entry.row);

  return { data, series };
}
