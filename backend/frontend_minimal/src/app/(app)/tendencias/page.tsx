import { redirect } from 'next/navigation';

/** La tendencia y la proyección se muestran en Panorama; los enlaces viejos siguen funcionando. */
export default async function Tendencias({ searchParams }: PageProps<'/tendencias'>) {
  const params = Object.entries(await searchParams).filter((e): e is [string, string] => typeof e[1] === 'string');
  const query = new URLSearchParams(params);
  if (query.has('burbujas')) query.set('tab', 'movimiento');
  redirect(query.size ? `/panorama?${query}` : '/panorama');
}
