'use client';

import { Suspense, useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  Briefcase,
  ChevronDown,
  Factory,
  Globe,
  Lightbulb,
  Settings,
  TrendingUp,
  User,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { INDEX_PATHS, INDICES, ITEMS, isActive } from './MainNav';

const ICONOS: Record<string, LucideIcon> = {
  '/panorama-regional': Globe,
  '/sectores': Factory,
  '/ocupaciones': Briefcase,
  '/habilidades': Lightbulb,
  '/genero': User,
};

const ICON =
  'flex size-9 items-center justify-center rounded-lg text-muted-text hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus';

function cerrar(e: React.MouseEvent<HTMLElement>) {
  e.currentTarget.closest('details')?.removeAttribute('open');
}

function Secciones() {
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
              'flex shrink-0 items-center gap-2 rounded-full px-3 py-2 text-[13px] font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-focus',
              active ? 'bg-brand text-white' : 'text-body hover:bg-surface-alt',
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
        <div className="absolute top-full left-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-card-border bg-canvas py-1 shadow-lg">
          {INDICES.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={cerrar}
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

export function StickyBar({ canManage }: { canManage: boolean }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const revisar = () => setVisible(window.scrollY > 140);
    revisar();
    window.addEventListener('scroll', revisar, { passive: true });
    return () => window.removeEventListener('scroll', revisar);
  }, []);

  return (
    <div
      inert={!visible}
      aria-hidden={!visible}
      className={cn(
        'fixed inset-x-0 top-0 z-50 hidden border-b border-card-border bg-canvas shadow-sm transition-transform duration-200 lg:block',
        visible ? 'translate-y-0' : '-translate-y-full',
      )}
    >
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link
          href="/inicio"
          aria-label="Ir al inicio"
          className="flex shrink-0 items-center rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <Image src="/predix-isotipo.svg" alt="Predix" width={51} height={57} className="h-9 w-auto" />
        </Link>

        <nav aria-label="Secciones" className="flex min-w-0 flex-1 items-center gap-1">
          <Suspense fallback={null}>
            <Secciones />
          </Suspense>
        </nav>

        <div className="flex shrink-0 items-center gap-1">
          <Link href="/alertas" aria-label="Alertas" title="Alertas" className={ICON}>
            <TrendingUp className="size-4" aria-hidden />
          </Link>
          <Link href="/metodologia/ise" aria-label="Metodología y fuentes" title="Metodología y fuentes" className={ICON}>
            <BookOpen className="size-4" aria-hidden />
          </Link>
          {canManage && (
            <details data-menu className="group relative">
              <summary
                aria-label="Administración"
                title="Administración"
                className="flex h-9 cursor-pointer list-none items-center gap-1 rounded-lg px-2 text-muted-text hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden"
              >
                <Settings className="size-4" aria-hidden />
                <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
              </summary>
              <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-xl border border-card-border bg-canvas py-1 shadow-lg">
                <Link href="/admin/datos" onClick={cerrar} className="block px-4 py-2.5 text-[13px] text-body hover:bg-surface-alt">
                  Carga de datos
                </Link>
                <Link href="/metodologia/fuentes" onClick={cerrar} className="block px-4 py-2.5 text-[13px] text-body hover:bg-surface-alt">
                  Fuentes y actualización
                </Link>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
