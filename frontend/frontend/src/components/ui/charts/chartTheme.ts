export type ChartRow = Record<string, string | number | null>;
export type ChartSeries = {
  key: string;
  label: string;
  color: string;
  /** Las proyecciones se dibujan con línea punteada. */
  dashed?: boolean;
};

/** Colores de país del Design System (--country-arg, --country-chl, --country-ury). */
export const COUNTRY_COLORS: Record<string, string> = {
  ARG: '#38bdf8',
  CHL: '#b91c1c',
  URY: '#d97706',
};
export const FALLBACK_COLOR = '#475569'; // --text-muted

/** Estructura de gráficos (--chart-grid-line). */
export const CHART_GRID = '#e2e8f0';
