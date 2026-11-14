'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { withParam } from '@/lib/utils/url';

type Item = { code: string; name: string };
type Props = { items: Item[]; active: string };

export function IndicatorSidebar({ items, active }: Props) {
  const pathname = usePathname();
  const search = useSearchParams();
  return (
    <nav aria-label="Indicadores" className="overflow-hidden rounded-xl border border-card-border bg-canvas">
      <h2 className="border-b border-card-border px-4 py-3 text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
        Indicadores
      </h2>
      <ul className="max-h-[32rem] overflow-y-auto py-1">
        {items.map((item) => {
          const isActive = item.code === active;
          return (
            <li key={item.code}>
              <Link
                href={`${pathname}${withParam(search, 'indicator', item.code)}`}
                aria-current={isActive ? 'true' : undefined}
                className={`block border-l-2 px-4 py-2.5 text-[12.5px] leading-snug transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus ${
                  isActive
                    ? 'border-brand bg-brand/6 font-semibold text-brand'
                    : 'border-transparent text-body hover:bg-surface-alt'
                }`}
              >
                {item.name}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
