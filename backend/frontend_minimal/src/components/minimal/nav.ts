export type NavTab = { href: string; label: string };
/** match: la ruta que marca la sección activa, si no es la de href. */
export type NavSection = { href: string; label: string; tabs?: NavTab[]; match?: string };

/** Las secciones de la barra superior y, en las que agrupan páginas, sus pestañas. */
export const SECTIONS: NavSection[] = [
  {
    href: '/panorama',
    label: 'Panorama',
    tabs: [
      { href: '/panorama', label: 'Indicadores' },
      { href: '/panorama?tab=brecha', label: 'Brecha generacional' },
      { href: '/panorama?tab=movimiento', label: 'Ocupaciones en movimiento' },
    ],
  },
  {
    href: '/sectores',
    label: 'Empleo y habilidades',
    tabs: [
      { href: '/sectores', label: 'Sectores' },
      { href: '/ocupaciones', label: 'Ocupaciones' },
      { href: '/habilidades', label: 'Brechas de habilidades' },
      { href: '/habilidades?tab=titulados', label: 'Titulados y proyecciones' },
      { href: '/habilidades?tab=sectores', label: 'Indicadores por sector' },
      { href: '/habilidades?tab=genero', label: 'Género' },
    ],
  },
  { href: '/pulso', label: 'Pulso laboral' },
  {
    href: '/moctezuma',
    label: 'Experimental',
    tabs: [
      { href: '/moctezuma', label: 'Moctezuma' },
      { href: '/ludita', label: 'Ludita' },
      { href: '/reina-roja', label: 'Reina Roja' },
      { href: '/sisifo', label: 'Sísifo' },
    ],
  },
  { href: '/metodologia/fuentes', label: 'Metodología y fuentes', match: '/metodologia' },
];

const onPath = (pathname: string, href: string) => {
  const path = href.split('?')[0];
  return pathname === path || pathname.startsWith(`${path}/`);
};

/** La ruta pertenece a la sección o a alguna de sus pestañas. */
export const inSection = (pathname: string, section: NavSection) =>
  section.tabs ? section.tabs.some((t) => onPath(pathname, t.href)) : onPath(pathname, section.match ?? section.href);

/** La pestaña activa: misma ruta y mismo ?tab= (las sin ?tab= son la vista por defecto de su página). */
export const onTab = (pathname: string, tabParam: string | null, tab: NavTab) =>
  onPath(pathname, tab.href) && new URLSearchParams(tab.href.split('?')[1]).get('tab') === tabParam;
