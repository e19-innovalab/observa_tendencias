'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import {
  BarChart3,
  Briefcase,
  ChevronDown,
  Globe2,
  GraduationCap,
  Home,
  Layers,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const ITEMS = [
  { href: '/inicio', label: 'Inicio', icon: Home },
  { href: '/panorama-regional', label: 'Panorama regional', icon: Globe2 },
  { href: '/sectores', label: 'Sectores', icon: Layers },
  { href: '/ocupaciones', label: 'Ocupaciones', icon: Briefcase },
  { href: '/habilidades', label: 'Habilidades y formación', icon: GraduationCap },
  { href: '/habilidades?tab=genero', label: 'Género', icon: Users },
];

const INDICES = [
  { href: '/pulso', label: 'Pulso laboral' },
  { href: '/moctezuma', label: 'Indicador Moctezuma' },
  { href: '/ludita', label: 'Indicador Ludita' },
  { href: '/reina-roja', label: 'Indicador Reina Roja' },
  { href: '/sisifo', label: 'Indicador Sísifo' },
  { href: '/panorama?tab=brecha', label: 'Brecha generacional' },
  { href: '/panorama?tab=movimiento', label: 'Ocupaciones en movimiento' },
];

const INDEX_PATHS = ['/pulso', '/moctezuma', '/ludita', '/reina-roja', '/sisifo'];

function isActive(href: string, pathname: string, tab: string | null) {
  if (href === '/habilidades?tab=genero') return pathname.startsWith('/habilidades') && tab === 'genero';
  if (href === '/habilidades') return pathname.startsWith('/habilidades') && tab !== 'genero';
  if (href === '/panorama-regional') return pathname.startsWith('/panorama-regional');
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Item({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof Home;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        active ? 'bg-brand text-white shadow-sm' : 'text-body hover:bg-surface-alt',
      )}
    >
      <Icon
        className={cn('size-4', active ? 'text-white/85' : 'text-placeholder')}
        aria-hidden
      />
      {label}
      {active && <span className="ml-1 size-1.5 rounded-full bg-white/70" aria-hidden />}
    </Link>
  );
}

function NavItems() {
  const pathname = usePathname();
  const search = useSearchParams();
  const tab = search.get('tab');
  const indicesActive = INDEX_PATHS.some((path) => pathname.startsWith(path));

  return (
    <>
      <div className="flex items-center gap-0.5">
        {ITEMS.map(({ href, label, icon }) => (
          <Item
            key={href}
            href={href}
            label={label}
            icon={icon}
            active={isActive(href, pathname, tab)}
          />
        ))}
      </div>

      <div className="ml-auto shrink-0 pl-3">
        <details className="group relative">
          <summary
            className={cn(
              'flex cursor-pointer list-none items-center gap-2 rounded-lg border px-3 py-1.5 text-[13px] font-medium transition-colors',
              'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden',
              indicesActive
                ? 'border-brand bg-brand text-white'
                : 'border-card-border text-body hover:bg-surface-alt',
            )}
          >
            <BarChart3
              className={cn('size-4', indicesActive ? 'text-white/85' : 'text-placeholder')}
              aria-hidden
            />
            Índices &amp; Pulso
            <span className="rounded-md bg-brand px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-white">
              BETA
            </span>
            <ChevronDown
              className={cn(
                'size-3.5 transition-transform group-open:rotate-180',
                indicesActive ? 'text-white/80' : 'text-muted-text',
              )}
              aria-hidden
            />
          </summary>
          <div className="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-xl border border-card-border bg-canvas py-1 shadow-lg">
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
      </div>
    </>
  );
}

function NavFallback() {
  const pathname = '/';
  return (
    <>
      <div className="flex items-center gap-0.5">
        {ITEMS.map(({ href, label, icon }) => (
          <Item key={href} href={href} label={label} icon={icon} active={pathname === href} />
        ))}
      </div>
      <span className="ml-auto shrink-0" />
    </>
  );
}

export function MainNav() {
  return (
    <nav aria-label="Principal" className="border-b border-card-border bg-canvas">
      <div className="mx-auto flex h-12 max-w-7xl items-center gap-1 overflow-x-auto px-4 sm:px-6">
        <Suspense fallback={<NavFallback />}>
          <NavItems />
        </Suspense>
      </div>
    </nav>
  );
}
