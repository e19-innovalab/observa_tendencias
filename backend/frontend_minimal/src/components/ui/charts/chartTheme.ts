export type ChartRow = Record<string, string | number | null>;
export type ChartSeries = { key: string; label: string; color: string };

/** Colores de país: tonos oscuros para que las etiquetas directas sobre el gráfico lean bien (≥4.5:1). */
export const COUNTRY_COLORS: Record<string, string> = {
  ARG: '#0369a1',
  CHL: '#b91c1c',
  URY: '#b45309',
};
export const FALLBACK_COLOR = '#475569'; // --text-muted

/** Estructura de gráficos (--chart-grid-line). */
export const CHART_GRID = '#e2e8f0';
