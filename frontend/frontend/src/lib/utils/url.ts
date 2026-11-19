/** Devuelve "?a=1&b=2" con una clave cambiada y otras claves eliminadas. */
export function withParam(
  current: { toString(): string },
  key: string,
  value: string,
  remove: string[] = [],
): string {
  const params = new URLSearchParams(current.toString());
  params.set(key, value);
  remove.forEach((k) => params.delete(k));
  return `?${params.toString()}`;
}
