'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const ITEMS = [
  { href: '/inicio', label: 'Inicio' },
  { href: '/panorama-regional', label: 'Panorama regional' },
  { href: '/panorama', label: 'Panorama' },
  { href: '/sectores', label: 'Sectores' },
  { href: '/ocupaciones', label: 'Ocupaciones' },
  { href: '/habilidades', label: 'Habilidades' },
  { href: '/pulso', label: 'Pulso laboral' },
  { href: '/moctezuma', label: 'Experimental' },
  { href: '/metodologia/ise', label: 'Metodología' },
];

export function MainNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Principal" className="border-b border-line bg-surface-2">
      <div className="mx-auto flex max-w-7xl flex-wrap gap-px overflow-x-auto bg-surface-2">
        {ITEMS.map(({ href, label }) => {
          const active =
            pathname === href ||
            pathname.startsWith(`${href}/`) ||
            (href === '/metodologia/ise' && pathname.startsWith('/metodologia'));
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'min-w-32 flex-1 px-3 py-5 text-center text-sm transition-colors',
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
