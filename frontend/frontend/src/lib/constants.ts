import type { QuickAccess } from './ui-types';

/** Accesos rápidos del inicio (navegación estática, no depende del backend). */
export const QUICK_ACCESS: QuickAccess[] = [
  {
    title: 'Panorama regional',
    description: 'Compará países',
    href: '/panorama-regional',
    icon: 'globe',
  },
  {
    title: 'Sectores',
    description: 'Analizá tendencias sectoriales',
    href: '/sectores',
    icon: 'layers',
  },
  {
    title: 'Ocupaciones',
    description: 'Investigá una ocupación',
    href: '/ocupaciones',
    icon: 'briefcase',
  },
  {
    title: 'Habilidades',
    description: 'Explorá brechas de habilidades',
    href: '/habilidades',
    icon: 'graduation',
  },
  {
    title: 'Tendencias',
    description: 'Seguí la evolución de los indicadores',
    href: '/tendencias',
    icon: 'trend',
    featured: true,
  },
];

/** Colores por dimensión del ISE, alineados con el Design System. */
export const DIMENSION_COLORS: Record<string, string> = {
  net_demand: '#172bc4',
  salary_ppp: '#38bdf8',
  insertion_rate: '#8b5cf6',
  automation_risk: '#f59e0b',
};

/** Unidades de la API traducidas para las notas metodológicas. */
export const UNIT_LABELS: Record<string, string> = {
  percent: 'porcentaje',
  index_0_1: 'índice de 0 a 1',
  thousands_persons: 'miles de personas',
  ppp_usd: 'USD PPA (constantes)',
  ppp_usd_month: 'USD PPA por mes',
  usd: 'USD',
};

export function unitLabel(unit: string): string {
  return UNIT_LABELS[unit] ?? unit;
}
