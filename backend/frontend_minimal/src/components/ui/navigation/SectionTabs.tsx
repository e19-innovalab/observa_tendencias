'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { withParam } from '@/lib/utils/url';

type Tab = { id: string; label: string };
type Props = { tabs: Tab[]; active: string };

export function SectionTabs({ tabs, active }: Props) {
  const pathname = usePathname();
  const search = useSearchParams();
  return (
    <nav aria-label="Secciones" className="flex border-b border-gray-300 bg-gray-50">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <Link
            key={tab.id}
            // al cambiar de sección se descarta el indicador elegido
            href={`${pathname}${withParam(search, 'tab', tab.id, ['indicator'])}`}
            aria-current={isActive ? 'page' : undefined}
            className={`flex-1 px-4 py-5 text-center text-sm font-medium tracking-wide transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-blue-800 ${
              isActive
                ? 'border-b-4 border-blue-900 bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
