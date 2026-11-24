'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { isFreePath } from '@/lib/auth/constants';
import { inSection, SECTIONS } from './nav';

/** free: cuenta gratuita, solo las secciones que puede abrir. */
export function TopNav({ free = false }: { free?: boolean }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Secciones" className="flex flex-wrap gap-0.5">
      {SECTIONS.filter((s) => !free || isFreePath(s.href.split('?')[0])).map((s) => {
        const active = inSection(pathname, s);
        return (
          <Link
            key={s.href}
            href={s.href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-md px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-blue-700 ${
              active ? 'bg-slate-100 font-semibold text-slate-900' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {s.label}
          </Link>
        );
      })}
    </nav>
  );
}
