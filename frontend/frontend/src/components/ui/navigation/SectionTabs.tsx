'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';
import { withParam } from '@/lib/utils/url';

type Tab = { id: string; label: string };
type Props = { tabs: Tab[]; active: string };

function TabList({ tabs, active, hrefFor }: { tabs: Tab[]; active: string; hrefFor?: (tab: Tab) => string }) {
  return (
    <nav aria-label="Secciones" className="grid grid-flow-col auto-cols-fr overflow-x-auto rounded-lg bg-surface-2">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        const className = cn(
          'min-w-40 px-4 py-4 text-center text-sm font-medium tracking-wide transition-colors',
          'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus',
          isActive ? 'bg-brand text-white' : 'text-body hover:bg-surface-alt',
          tab === tabs[0] && 'rounded-l-lg',
          tab === tabs[tabs.length - 1] && 'rounded-r-lg',
        );

        return hrefFor ? (
          <Link key={tab.id} href={hrefFor(tab)} aria-current={isActive ? 'page' : undefined} className={className}>
            {tab.label}
          </Link>
        ) : (
          <span key={tab.id} aria-current={isActive ? 'page' : undefined} className={className}>
            {tab.label}
          </span>
        );
      })}
    </nav>
  );
}

function Inner({ tabs, active }: Props) {
  const pathname = usePathname();
  const search = useSearchParams();

  return (
    <TabList
      tabs={tabs}
      active={active}
      hrefFor={(tab) => `${pathname}${withParam(search, 'tab', tab.id, ['indicator'])}`}
    />
  );
}

/** Pestañas de sección que escriben `?tab=` en la URL. */
export function SectionTabs({ tabs, active }: Props) {
  return (
    <Suspense fallback={<TabList tabs={tabs} active={active} />}>
      <Inner tabs={tabs} active={active} />
    </Suspense>
  );
}
