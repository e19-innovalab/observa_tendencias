'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ITEMS = [
  { href: '/inicio', label: 'Inicio' },
  { href: '/panorama-regional', label: 'Panorama regional' },
  { href: '/tendencias', label: 'Tendencias' },
  { href: '/ocupaciones', label: 'Ocupaciones' },
  { href: '/formacion', label: 'Formación' },
];

export function MainNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Principal" className="grid auto-cols-fr grid-flow-col overflow-x-auto bg-gray-200">
      {ITEMS.map(({ href, label }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`min-w-36 px-4 py-6 text-center text-sm transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-blue-800 ${
              active ? 'bg-blue-600 font-medium text-white' : 'text-gray-900 hover:bg-gray-300'
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
