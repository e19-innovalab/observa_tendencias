/** Compartido por el proxy y el servidor (sin dependencias de request). */
export const SESSION_COOKIE = 'ot_session';
export const LOGIN_PATH = '/login';
export const HOME_PATH = '/inicio';

/** Rutas que exigen sesión (el proxy redirige al login si no hay cookie). */
export const PRIVATE_PREFIXES = [
  '/panorama',
  '/inicio',
  '/panorama-regional',
  '/sectores',
  '/ocupaciones',
  '/habilidades',
  '/genero',
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

/** Destino seguro después del login: solo rutas internas de la app. */
export function safeNext(value: unknown): string {
  const next = typeof value === 'string' ? value : '';
  return next.startsWith('/') && !next.startsWith('//') ? next : HOME_PATH;
}
