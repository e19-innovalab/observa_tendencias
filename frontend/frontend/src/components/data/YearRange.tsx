'use client';

import { RotateCcw } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/**
 * Filtro "Desde / Hasta" por año (?desde=&hasta=). Elegir un año reemplaza el período rápido
 * (?periodo=); si "Desde" queda después de "Hasta", se intercambian.
 */
export function YearRange({
  years,
  desde,
  hasta,
}: {
  years: number[];
  desde?: string;
  hasta?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();

  const go = (params: URLSearchParams) => {
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

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
    go(params);
  };

  const reset = () => {
    const params = new URLSearchParams(search.toString());
    ['desde', 'hasta', 'periodo'].forEach((key) => params.delete(key));
    go(params);
  };

  const select =
    'h-9 appearance-none rounded-lg border border-card-border bg-canvas pr-7 pl-2.5 text-[12.5px] font-semibold text-heading hover:border-line focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';
  const label = 'text-[10.5px] font-bold tracking-[0.08em] text-label uppercase';

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1.5">
        <span className={label}>Desde</span>
        <select value={desde ?? ''} onChange={(e) => set('desde', e.target.value)} className={select}>
          <option value="">—</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1.5">
        <span className={label}>Hasta</span>
        <select value={hasta ?? ''} onChange={(e) => set('hasta', e.target.value)} className={select}>
          <option value="">Último</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={reset}
        className="inline-flex size-9 items-center justify-center rounded-lg border border-card-border text-muted-text hover:border-line hover:text-heading focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        aria-label="Restablecer período"
        title="Restablecer período"
      >
        <RotateCcw className="size-3.5" aria-hidden />
      </button>
    </div>
  );
}
