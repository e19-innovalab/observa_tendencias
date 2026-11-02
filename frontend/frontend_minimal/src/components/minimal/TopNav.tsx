'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SECTIONS } from './nav';

export function TopNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Secciones" className="flex flex-wrap gap-0.5">
      {SECTIONS.map((s) => {
        const active = pathname === s.href || pathname.startsWith(`${s.href}/`);
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
