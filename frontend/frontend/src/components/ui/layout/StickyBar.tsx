'use client';

import { Suspense, useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
  BookOpen,
  ChevronDown,
  Settings,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Secciones, cerrar } from './MainNav';

const ICON =
  'flex size-9 items-center justify-center rounded-lg text-muted-text hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus';

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
