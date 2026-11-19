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
  ARG: '#22b8e6',
  CHL: '#d92d20',
  URY: '#f0a800',
};
export const FALLBACK_COLOR = '#64748b'; // --color-label

/** Estructura de gráficos (--chart-grid-line). */
export const CHART_GRID = '#eef2f9';

/** Ejes y tooltips del rediseño. */
export const CHART_AXIS = '#94a3b8';
export const CHART_TOOLTIP_BORDER = '#e6ebf5';
