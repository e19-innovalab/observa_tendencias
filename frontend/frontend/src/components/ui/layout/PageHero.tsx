import type { ReactNode } from 'react';
import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export type Crumb = { label: string; href?: string };

type Props = {
  title: string;
  description?: ReactNode;
  /** Migas de pan que se muestran sobre el título (solo en páginas de detalle). */
  breadcrumbs?: Crumb[];
  /** `center` para las portadas de sección; `left` para fichas y detalles. */
  align?: 'center' | 'left';
  /** Chips o etiquetas que acompañan al título (país, sector, código CIUO). */
  leading?: ReactNode;
  /** Acciones bajo la descripción (por ejemplo, volver al listado). */
  actions?: ReactNode;
  /** Panel lateral derecho, como la tarjeta de puntaje del detalle de ocupación. */
  children?: ReactNode;
};

/** Héroe de sección: fondo de marca, título protagonista y contenido contextual. */
export function PageHero({
  title,
  description,
  breadcrumbs,
  align = 'center',
  leading,
  actions,
  children,
}: Props) {
  const centered = align === 'center';

  return (
    <section className="text-white" style={{ backgroundImage: 'var(--gradient-hero)' }}>
      <div
        className={cn(
          'mx-auto max-w-[1600px] px-4 sm:px-6',
          centered ? 'py-9 text-center sm:py-11' : 'py-8',
        )}
      >
        <div
          className={cn(
            'flex flex-col gap-6',
            !centered && children && 'lg:flex-row lg:items-start lg:justify-between',
          )}
        >
          <div className={cn('min-w-0', centered && 'mx-auto max-w-4xl')}>
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav aria-label="Migas de pan" className="mb-4 flex flex-wrap items-center gap-1 text-[12px]">
                {breadcrumbs.map((crumb, index) => (
                  <span key={`${crumb.label}-${index}`} className="flex items-center gap-1">
                    {index > 0 && <ChevronRight className="size-3.5 text-white/50" aria-hidden />}
                    {crumb.href ? (
                      <Link
                        href={crumb.href}
                        className="rounded-sm text-white/75 transition-colors hover:text-white hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                      >
                        {crumb.label}
                      </Link>
                    ) : (
                      <span className="text-white/90" aria-current="page">
                        {crumb.label}
                      </span>
                    )}
                  </span>
                ))}
              </nav>
            )}

            {leading && <div className={cn('mb-3 flex flex-wrap gap-2', centered && 'justify-center')}>{leading}</div>}

            <h1
              className={cn(
                'font-bold tracking-tight text-white',
                centered
                  ? 'text-[32px] leading-tight sm:text-[40px]'
                  : 'text-[29px] leading-tight sm:text-[36px]',
              )}
            >
              {title}
            </h1>

            {description && (
              <p
                className={cn(
                  'mt-3 text-[13.5px] leading-relaxed text-blue-50/90',
                  centered ? 'mx-auto max-w-[860px] sm:text-[14px]' : 'max-w-[680px]',
                )}
              >
                {description}
              </p>
            )}

            {actions && <div className={cn('mt-5 flex flex-wrap gap-2', centered && 'justify-center')}>{actions}</div>}
          </div>

          {children && <div className="w-full shrink-0 lg:w-auto">{children}</div>}
        </div>
      </div>
    </section>
  );
}
