'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/**
 * Filtro "Desde / Hasta" por año (?desde=&hasta=). Elegir un año reemplaza el período rápido
 * (?periodo=); si "Desde" queda después de "Hasta", se intercambian.
 */
export function YearRange({ years, desde, hasta }: { years: number[]; desde?: string; hasta?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const set = (key: 'desde' | 'hasta', value: string) => {
    const params = new URLSearchParams(search.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    params.delete('periodo');
    const from = params.get('desde');
    const to = params.get('hasta');
    if (from && to && Number(from) > Number(to)) {
      params.set('desde', to);
      params.set('hasta', from);
    }
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  const select = 'h-9 rounded-lg border border-slate-200 bg-white pl-2.5 pr-7 text-[13px] font-medium text-slate-800 focus-visible:outline-2 focus-visible:outline-blue-700';
  return (
    <div className="flex items-center gap-2 text-[13px] text-slate-600">
      <label className="flex items-center gap-1.5">
        Desde
        <select value={desde ?? ''} onChange={(e) => set('desde', e.target.value)} className={select}>
          <option value="">—</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
      <label className="flex items-center gap-1.5">
        Hasta
        <select value={hasta ?? ''} onChange={(e) => set('hasta', e.target.value)} className={select}>
          <option value="">Último</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
    </div>
  );
}
