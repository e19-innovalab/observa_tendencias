'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

type Option = { value: string; label: string };

/** País y carrera en la URL (?pais=&carrera=): al cambiar el país se borra la carrera. */
export function CareerFilter({ countries, careers, pais, carrera }: { countries: Option[]; careers: Option[]; pais: string; carrera: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const go = (changes: Record<string, string>) => {
    const params = new URLSearchParams(search.toString());
    for (const [k, v] of Object.entries(changes)) {
      if (v) params.set(k, v);
      else params.delete(k);
    }
    params.delete('ocupacion');
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  const select = 'h-9 min-w-0 rounded-lg border border-slate-200 bg-white px-2.5 text-[13px] text-slate-900 focus-visible:outline-2 focus-visible:outline-blue-700';
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtrar por carrera">
      <select aria-label="País de la carrera" className={select} value={pais} onChange={(e) => go({ pais: e.target.value, carrera: '' })}>
        <option value="">Carrera: elegí un país</option>
        {countries.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      {pais && (
        <select aria-label="Carrera" className={`${select} max-w-72`} value={carrera} onChange={(e) => go({ carrera: e.target.value })}>
          <option value="">Todas las carreras</option>
          {careers.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      )}
      {(pais || carrera) && (
        <button type="button" onClick={() => go({ pais: '', carrera: '' })} className="text-[13px] font-medium text-blue-700 hover:underline">
          Quitar filtro
        </button>
      )}
    </div>
  );
}
