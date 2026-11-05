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
    <nav aria-label="Indicadores">
      <h2 className="bg-gray-300 px-4 py-3 text-center text-sm font-semibold text-gray-900">
        Indicadores
      </h2>
      <ul>
        {items.map((item) => {
          const isActive = item.code === active;
          return (
            <li key={item.code}>
              <Link
                href={`${pathname}${withParam(search, 'indicator', item.code)}`}
                aria-current={isActive ? 'true' : undefined}
                className={`block border-l-4 px-4 py-3 text-sm transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-blue-600 ${
                  isActive
                    ? 'border-blue-600 bg-indigo-50 font-medium text-blue-700'
                    : 'border-transparent text-gray-700 hover:bg-gray-50'
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
