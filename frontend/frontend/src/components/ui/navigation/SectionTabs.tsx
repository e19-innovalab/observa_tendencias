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
    <nav
      aria-label="Secciones"
      className="flex flex-wrap items-center gap-x-7 gap-y-1 border-b border-card-border"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        const className = cn(
          '-mb-px flex min-w-fit items-center gap-2 border-b-2 py-2.5 text-[12.5px] transition-colors',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          isActive
            ? 'border-brand font-semibold text-heading'
            : 'border-transparent text-muted-text hover:text-heading',
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
