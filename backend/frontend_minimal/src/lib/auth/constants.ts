/** Compartido por el proxy y el servidor (sin dependencias de request). */
export const SESSION_COOKIE = 'ot_session';
export const LOGIN_PATH = '/login';
export const HOME_PATH = '/panorama';

/** Rutas que exigen sesión (el proxy redirige al login si no hay cookie). */
export const PRIVATE_PREFIXES = [
  '/panorama',
  '/inicio',
  '/panorama-regional',
  '/sectores',
  '/ocupaciones',
  '/habilidades',
  '/tendencias',
  '/pulso',
  '/moctezuma',
  '/ludita',
  '/reina-roja',
  '/sisifo',
  '/metodologia',
  '/alertas',
  '/admin',
];

/**
 * Cuenta gratuita (ingreso con Google): solo estas rutas. El resto pide el permiso de acceso
 * completo, que da un administrador al cambiar el rol (app.yaml -> auth.roles).
 */
export const FREE_PREFIXES = ['/inicio', '/panorama'];
export const PRO_PERMISSION = 'view';
/** El proxy pasa la ruta pedida en este header, para que el layout sepa qué página se abre. */
export const PATH_HEADER = 'x-pathname';

export const isFreePath = (pathname: string) =>
  FREE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));

/** Destino seguro después del login: solo rutas internas de la app. */
export function safeNext(value: unknown): string {
  const next = typeof value === 'string' ? value : '';
  return next.startsWith('/') && !next.startsWith('//') ? next : HOME_PATH;
}
