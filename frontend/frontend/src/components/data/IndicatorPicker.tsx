'use client';

import { ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

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
    <details className="group relative inline-block">
      <summary className="inline-flex cursor-pointer list-none items-center gap-2 rounded-md hover:text-brand [&::-webkit-details-marker]:hidden">
        {current.name}
        <ChevronDown className="size-5 text-muted-text transition-transform group-open:rotate-180" aria-hidden />
        <span className="sr-only">Cambiar indicador</span>
      </summary>
      <div className="absolute left-0 z-30 mt-2 max-h-[28rem] w-[min(36rem,90vw)] overflow-auto rounded-lg border border-line bg-canvas p-2 text-sm font-normal shadow-lg">
        {groups.map((g) => (
          <div key={g} className="py-1">
            <p className="px-3 py-1 text-[11px] font-semibold tracking-wider text-muted-text uppercase">
              {g}
            </p>
            {indicators
              .filter((i) => i.domain_label === g)
              .map((i) => (
                <Link
                  key={i.code}
                  href={href(i.code)}
                  scroll={false}
                  aria-current={i.code === current.code ? 'true' : undefined}
                  className={`block rounded-md px-3 py-1.5 tracking-normal ${
                    i.code === current.code
                      ? 'bg-brand/10 font-semibold text-brand'
                      : 'text-body hover:bg-surface'
                  }`}
                >
                  {i.name}
                </Link>
              ))}
          </div>
        ))}
      </div>
    </details>
  );
}
