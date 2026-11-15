import Link from 'next/link';
import { ArrowUpRight, Check, Star } from 'lucide-react';
import type { Occupation } from '@/lib/schemas/api';
import { cn } from '@/lib/utils';

/** Tarjetas para saltar entre las ocupaciones del mismo sector. */
export function OccupationChangeCards({
  occupations,
  activeCode,
  hrefFor,
  allHref,
  limit = 8,
}: {
  occupations: Occupation[];
  activeCode: string;
  hrefFor: (occupation: Occupation) => string;
  allHref: string;
  limit?: number;
}) {
  const active = occupations.find((occupation) => occupation.occupation_code === activeCode);
  const rest = occupations
    .filter((occupation) => occupation.occupation_code !== activeCode)
    .sort((a, b) => {
      if (a.is_featured !== b.is_featured) return a.is_featured ? -1 : 1;
      return a.name.localeCompare(b.name, 'es');
    });
  const shown = [...(active ? [active] : []), ...rest].slice(0, limit);

  return (
    <section className="rounded-xl border border-card-border bg-canvas p-4 sm:p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
            Cambiar ocupación del sector
          </p>
          <p className="mt-0.5 text-[11.5px] text-muted-text">
            Las tarjetas y el selector de ocupación mantienen la misma selección.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 text-[10.5px] font-medium text-muted-text">
          <span className="size-1.5 rounded-full bg-brand" aria-hidden />
          Selección activa sincronizada
        </span>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
        {shown.map((occupation) => {
          const isActive = occupation.occupation_code === activeCode;
          return (
            <Link
              key={occupation.occupation_code}
              href={hrefFor(occupation)}
              title={occupation.name}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'group flex min-h-[58px] items-center gap-2.5 rounded-lg border px-3 py-2.5 transition-colors',
                'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                isActive
                  ? 'border-heading bg-heading text-white'
                  : 'border-card-border bg-canvas text-body hover:border-line hover:bg-surface',
              )}
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="truncate text-[11.5px] font-semibold">{occupation.name}</span>
                  {occupation.is_featured && (
                    <Star
                      className={cn(
                        'size-3 shrink-0',
                        isActive ? 'fill-white text-white' : 'fill-brand text-brand',
                      )}
                      aria-label="Ocupación destacada"
                    />
                  )}
                </span>
                <span
                  className={cn(
                    'mt-0.5 block text-[10.5px]',
                    isActive ? 'text-white/70' : 'text-muted-text',
                  )}
                >
                  CIUO {occupation.occupation_code}
                </span>
              </span>
              {isActive ? (
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-white text-heading">
                  <Check className="size-3" aria-hidden />
                </span>
              ) : (
                <ArrowUpRight
                  className="size-3.5 shrink-0 text-placeholder transition-colors group-hover:text-link"
                  aria-hidden
                />
              )}
            </Link>
          );
        })}
      </div>

      {occupations.length > limit && (
        <Link
          href={allHref}
          className="mt-3 inline-flex items-center gap-1 text-[11.5px] font-semibold text-link hover:text-link-hover hover:underline"
        >
          Ver las {occupations.length} ocupaciones del sector
          <ArrowUpRight className="size-3.5" aria-hidden />
        </Link>
      )}
    </section>
  );
}
