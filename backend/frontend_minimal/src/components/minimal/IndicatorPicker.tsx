'use client';

import { ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Dropdown } from './Dropdown';

type Item = { code: string; name: string; domain_label: string };

/** El título del gráfico es el selector de indicador (agrupados por dominio). */
export function IndicatorPicker({ current, indicators }: { current: Item; indicators: Item[] }) {
  const pathname = usePathname();
  const search = useSearchParams();
  const href = (code: string) => {
    const params = new URLSearchParams(search.toString());
    params.set('indicator', code);
    params.delete('sector');
    return `${pathname}?${params}`;
  };
  const groups = [...new Set(indicators.map((i) => i.domain_label))];
  return (
    <Dropdown
      className="relative inline-block"
      summaryClassName="inline-flex cursor-pointer items-center gap-2 rounded-md hover:text-blue-800"
      summary={
        <>
          {current.name}
          <ChevronDown className="size-5 text-slate-500 transition-transform group-open:rotate-180" aria-hidden />
          <span className="sr-only">Cambiar indicador</span>
        </>
      }
    >
      <div className="absolute left-0 z-30 mt-2 max-h-[28rem] w-[min(36rem,90vw)] overflow-auto rounded-xl border border-slate-200 bg-white p-2 text-sm font-normal shadow-lg">
        {groups.map((g) => (
          <div key={g} className="py-1">
            <p className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{g}</p>
            {indicators.filter((i) => i.domain_label === g).map((i) => (
              <Link
                key={i.code}
                href={href(i.code)}
                scroll={false}
                aria-current={i.code === current.code ? 'true' : undefined}
                className={`block rounded-md px-3 py-1.5 tracking-normal ${i.code === current.code ? 'bg-blue-50 font-semibold text-blue-800' : 'text-slate-700 hover:bg-slate-100'}`}
              >
                {i.name}
              </Link>
            ))}
          </div>
        ))}
      </div>
    </Dropdown>
  );
}
