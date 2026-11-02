'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ITEMS = [
  { href: '/inicio', label: 'Inicio' },
  { href: '/panorama-regional', label: 'Panorama regional' },
  { href: '/sectores', label: 'Sectores' },
  { href: '/ocupaciones', label: 'Ocupaciones' },
  { href: '/habilidades', label: 'Habilidades' },
  { href: '/tendencias', label: 'Tendencias' },
];

export function MainNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Principal" className="grid auto-cols-fr grid-flow-col overflow-x-auto bg-surface-2">
      {ITEMS.map(({ href, label }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`min-w-36 border-r border-white px-4 py-5 text-center text-sm transition-colors last:border-r-0 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-deep ${
              active ? 'bg-brand font-medium text-white' : 'text-heading hover:bg-selection'
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
