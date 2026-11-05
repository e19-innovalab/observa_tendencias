'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { inSection, onTab, SECTIONS } from './nav';

/** Pestañas de la sección actual, debajo de la barra superior. */
export function SubNav() {
  const pathname = usePathname();
  const tabParam = useSearchParams().get('tab');
  const section = SECTIONS.find((s) => s.tabs && inSection(pathname, s));
  if (!section?.tabs) return null;
  return (
    <nav aria-label={section.label} className="mx-auto flex max-w-[1360px] gap-6 overflow-x-auto px-4 sm:px-8">
      {section.tabs.map((t) => {
        const on = onTab(pathname, tabParam, t);
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={on ? 'page' : undefined}
            className={`-mb-px whitespace-nowrap border-b-2 pb-2.5 text-sm ${on ? 'border-slate-900 font-semibold text-slate-900' : 'border-transparent font-medium text-slate-600 hover:text-slate-900'}`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
