'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

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
    <nav aria-label="Principal" className="border-b border-line bg-surface-2">
      <div className="mx-auto grid max-w-7xl auto-cols-fr grid-flow-col overflow-x-auto">
        {ITEMS.map(({ href, label }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'min-w-36 px-4 py-5 text-center text-sm transition-colors',
                'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus',
                active
                  ? 'border-b-4 border-brand bg-brand font-semibold text-white'
                  : 'border-b-4 border-transparent text-body hover:bg-surface-alt',
              )}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
