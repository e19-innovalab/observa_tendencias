'use client';

import { Suspense, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown, Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export const ITEMS = [
  { href: '/panorama-regional', label: 'Panorama regional' },
  { href: '/sectores', label: 'Sectores' },
  { href: '/ocupaciones', label: 'Ocupaciones' },
  { href: '/habilidades', label: 'Habilidades y formación' },
  { href: '/genero', label: 'Género' },
];

export const INDICES = [
  { href: '/pulso', label: 'Pulso laboral' },
  { href: '/moctezuma', label: 'Indicador Moctezuma' },
  { href: '/ludita', label: 'Indicador Ludita' },
  { href: '/reina-roja', label: 'Indicador Reina Roja' },
  { href: '/sisifo', label: 'Indicador Sísifo' },
];

export const INDEX_PATHS = ['/pulso', '/moctezuma', '/ludita', '/reina-roja', '/sisifo'];

export function isActive(href: string, pathname: string) {
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

function useCerrarMenus(pathname: string) {
  useEffect(() => {
    document.querySelectorAll('details[data-menu][open]').forEach((d) => d.removeAttribute('open'));
  }, [pathname]);

  useEffect(() => {
    const cerrar = (e: PointerEvent) => {
      document.querySelectorAll('details[data-menu][open]').forEach((d) => {
        if (!d.contains(e.target as Node)) d.removeAttribute('open');
      });
    };
    document.addEventListener('pointerdown', cerrar);
    return () => document.removeEventListener('pointerdown', cerrar);
  }, []);
}

function NavItems() {
  const pathname = usePathname();
  useCerrarMenus(pathname);
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

      <details data-menu className="group relative flex min-w-fit flex-1">
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
              onClick={(e) => e.currentTarget.closest('details')?.removeAttribute('open')}
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

const LINK_CELU =
  'block px-4 py-3 text-[14px] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus';

function MenuCelu() {
  const pathname = usePathname();
  const enIndices = INDEX_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  const actual =
    ITEMS.find((item) => isActive(item.href, pathname))?.label ?? (enIndices ? 'Experimentales' : 'Secciones');

  return (
    <details data-menu className="group relative">
      <summary
        aria-label="Abrir menú de secciones"
        className="flex h-12 cursor-pointer list-none items-center justify-between px-4 text-[14px] font-semibold text-heading focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus [&::-webkit-details-marker]:hidden"
      >
        {actual}
        <Menu className="size-5 text-muted-text group-open:hidden" aria-hidden />
        <X className="hidden size-5 text-muted-text group-open:block" aria-hidden />
      </summary>
      <div className="absolute inset-x-0 top-full z-40 border-b border-card-border bg-canvas py-1 shadow-lg">
        {ITEMS.map((item) => {
          const active = isActive(item.href, pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(LINK_CELU, active ? 'bg-surface font-semibold text-brand' : 'text-body')}
            >
              {item.label}
            </Link>
          );
        })}
        <details className="group/exp" open={enIndices}>
          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-[14px] text-body focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
            Experimentales
            <span className="rounded bg-heading px-1.5 py-0.5 text-[9.5px] font-bold tracking-wide text-white">BETA</span>
            <ChevronDown className="ml-auto size-4 text-muted-text transition-transform group-open/exp:rotate-180" aria-hidden />
          </summary>
          {INDICES.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={cn(LINK_CELU, 'pl-8', active ? 'bg-surface font-semibold text-brand' : 'text-body')}
              >
                {item.label}
              </Link>
            );
          })}
        </details>
      </div>
    </details>
  );
}

export function MainNav() {
  return (
    <nav aria-label="Principal" className="relative border-b border-white/50 bg-nav">
      <div className="hidden items-stretch lg:flex">
        <Suspense fallback={<NavFallback />}>
          <NavItems />
        </Suspense>
      </div>
      <div className="lg:hidden">
        <Suspense fallback={null}>
          <MenuCelu />
        </Suspense>
      </div>
    </nav>
  );
}
