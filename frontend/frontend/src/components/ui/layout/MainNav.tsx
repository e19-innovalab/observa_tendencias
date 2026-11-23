'use client';

import { Suspense, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, Briefcase, ChevronDown, Factory, Globe, Lightbulb, Menu, User, X, type LucideIcon } from 'lucide-react';
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

const ICONOS: Record<string, LucideIcon> = {
  '/panorama-regional': Globe,
  '/sectores': Factory,
  '/ocupaciones': Briefcase,
  '/habilidades': Lightbulb,
  '/genero': User,
};

const DETALLE: Record<string, string> = {
  '/pulso': 'Demanda y competencia en tiempo real',
  '/moctezuma': 'Brecha tecnológica y social',
  '/ludita': 'Riesgo de desplazamiento',
  '/reina-roja': 'Obsolescencia de habilidades',
  '/sisifo': 'Sobreeducación y subempleo',
};

export function cerrar(e: React.MouseEvent<HTMLElement>) {
  e.currentTarget.closest('details')?.removeAttribute('open');
}

export function Secciones() {
  const pathname = usePathname();
  const enIndices = INDEX_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));

  return (
    <>
      {ITEMS.map((item) => {
        const active = isActive(item.href, pathname);
        const Icono = ICONOS[item.href];
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-focus',
              active ? 'border-brand bg-brand text-white' : 'border-card-border bg-canvas text-body hover:border-transparent hover:bg-surface-alt',
            )}
          >
            {Icono && <Icono className={cn('hidden size-4 xl:block', active ? 'text-white' : 'text-muted-text')} aria-hidden />}
            {item.label}
            {active && <span className="size-1.5 rounded-full bg-white" aria-hidden />}
          </Link>
        );
      })}

      <details data-menu className="group relative shrink-0">
        <summary
          className={cn(
            'flex cursor-pointer list-none items-center gap-2 rounded-lg border px-3 py-1.5 text-[13px] font-medium whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden',
            enIndices ? 'border-brand bg-brand text-white' : 'border-card-border text-body hover:bg-surface-alt',
          )}
        >
          <BarChart3 className={cn('size-4', enIndices ? 'text-white' : 'text-muted-text')} aria-hidden />
          Experimentales
          <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
          <span className={cn('rounded px-1.5 py-0.5 text-[9.5px] font-bold', enIndices ? 'bg-white/20 text-white' : 'bg-brand text-white')}>
            BETA
          </span>
        </summary>
        <div className="absolute top-full right-0 z-50 mt-2 w-[600px] max-w-[calc(100vw-2rem)] rounded-xl border border-card-border bg-canvas p-5 shadow-lg">
          <p className="border-b border-card-border pb-3 text-[13px] text-muted-text">
            Modelos analíticos y fuentes alternativas para el monitoreo regional
          </p>
          <div className="mt-4 grid grid-cols-2 gap-6">
            <div>
              <p className="border-b border-card-border pb-2 text-[11px] font-semibold tracking-[0.1em] text-muted-text uppercase">
                Tiempo real
              </p>
              <Link
                href="/pulso"
                onClick={cerrar}
                className="mt-3 block rounded-lg bg-surface-alt px-3 py-2.5 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-focus"
              >
                <span className="block text-[13px] font-medium text-heading">Pulso laboral (LinkedIn)</span>
                <span className="block text-[12.5px] text-muted-text">{DETALLE['/pulso']}</span>
              </Link>
            </div>
            <div className="border-l border-card-border pl-6">
              <p className="border-b border-card-border pb-2 text-[11px] font-semibold tracking-[0.1em] text-muted-text uppercase">
                Indicadores
              </p>
              {INDICES.filter((item) => item.href !== '/pulso').map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={cerrar}
                  className="mt-1 block rounded-lg px-3 py-2 hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
                >
                  <span className="block text-[13px] font-medium text-heading">{item.label.replace('Indicador ', '')}</span>
                  <span className="block text-[12.5px] text-muted-text">{DETALLE[item.href]}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </details>
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
  return <Secciones />;
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
    <nav aria-label="Principal" className="relative border-b border-card-border bg-nav lg:bg-surface">
      <div className="mx-auto hidden max-w-7xl items-center gap-1 px-4 py-2.5 sm:px-6 lg:flex">
        <Suspense fallback={null}>
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
