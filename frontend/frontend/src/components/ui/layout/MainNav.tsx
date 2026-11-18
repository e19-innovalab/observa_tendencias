'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const ITEMS = [
  { href: '/panorama-regional', label: 'Panorama regional' },
  { href: '/sectores', label: 'Sectores' },
  { href: '/ocupaciones', label: 'Ocupaciones' },
  { href: '/habilidades', label: 'Habilidades y formación' },
];

const INDICES = [
  { href: '/pulso', label: 'Pulso laboral' },
  { href: '/moctezuma', label: 'Indicador Moctezuma' },
  { href: '/ludita', label: 'Indicador Ludita' },
  { href: '/reina-roja', label: 'Indicador Reina Roja' },
  { href: '/sisifo', label: 'Indicador Sísifo' },
];

const INDEX_PATHS = ['/pulso', '/moctezuma', '/ludita', '/reina-roja', '/sisifo'];

function isActive(href: string, pathname: string) {
  if (href === '/ocupaciones') return pathname.startsWith('/ocupaciones');
  if (href === '/sectores') return pathname.startsWith('/sectores');
  if (href === '/panorama-regional') return pathname.startsWith('/panorama-regional');
  if (href === '/habilidades') return pathname.startsWith('/habilidades');
  return pathname === href || pathname.startsWith(`${href}/`);
}

const CELL =
  'flex h-16 min-w-fit flex-1 items-center justify-center gap-2 border-r border-white/30 px-4 text-center text-[13.5px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-white sm:text-[14px]';

function NavFallback() {
  return (
    <>
      {ITEMS.map((item) => (
        <span key={item.href} className={cn(CELL, 'bg-nav text-body')}>
          {item.label}
        </span>
      ))}
      <span className={cn(CELL, 'bg-nav text-body')}>Experimentales</span>
    </>
  );
}

function NavItems() {
  const pathname = usePathname();
  const indicesActive = INDEX_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  return (
    <>
      {ITEMS.map((item) => {
        const active = isActive(item.href, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              CELL,
              active ? 'bg-nav-active text-white' : 'bg-nav text-body hover:bg-nav-hover',
            )}
          >
            {item.label}
          </Link>
        );
      })}

      <details className="group relative flex min-w-fit flex-1">
        <summary
          className={cn(
            CELL,
            'w-full cursor-pointer list-none [&::-webkit-details-marker]:hidden',
            indicesActive ? 'bg-nav-active text-white' : 'bg-nav text-body hover:bg-nav-hover',
          )}
        >
          Experimentales
          <ChevronDown
            className={cn(
              'size-4 transition-transform group-open:rotate-180',
              indicesActive ? 'text-white/80' : 'text-muted-text',
            )}
            aria-hidden
          />
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-[9.5px] font-bold tracking-wide',
              indicesActive ? 'bg-white/20 text-white' : 'bg-heading text-white',
            )}
          >
            BETA
          </span>
        </summary>
        <div className="absolute top-full right-0 z-40 mt-1 w-72 overflow-hidden rounded-xl border border-card-border bg-canvas py-1 shadow-lg">
          {INDICES.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-4 py-2.5 text-[13px] text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </details>
    </>
  );
}

export function MainNav() {
  return (
    <nav aria-label="Principal" className="border-b border-white/50 bg-nav">
      <div className="flex items-stretch overflow-x-auto lg:overflow-visible">
        <Suspense fallback={<NavFallback />}>
          <NavItems />
        </Suspense>
      </div>
    </nav>
  );
}
