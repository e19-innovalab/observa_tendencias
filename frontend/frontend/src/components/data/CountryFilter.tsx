'use client';

import { Check } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

type Country = { iso3: string; name_es: string };

const DOTS: Record<string, string> = {
  ARG: 'bg-country-arg',
  CHL: 'bg-country-chl',
  URY: 'bg-country-ury',
};

/** Píldoras de país: "Todos (3)" o un país a la vez, sincronizadas con ?country=. */
export function CountryFilter({
  countries,
  value,
  name = 'country',
  reset = [],
  compact = false,
}: {
  countries: Country[];
  value: string;
  name?: string;
  reset?: string[];
  /** Muestra solo el código ISO3 (para paneles compactos). */
  compact?: boolean;
}) {
  const pathname = usePathname();
  const search = useSearchParams();
  const href = (next: string) => {
    const params = new URLSearchParams(search.toString());
    if (next) params.set(name, next);
    else params.delete(name);
    reset.forEach((key) => params.delete(key));
    const query = params.toString();
    return query ? `${pathname}?${query}` : pathname;
  };

  const pill =
    'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[12.5px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Países">
      <Link
        href={href('')}
        scroll={false}
        aria-pressed={!value}
        className={cn(
          pill,
          !value
            ? 'border-brand bg-brand/8 font-semibold text-brand'
            : 'border-card-border bg-canvas text-body hover:border-line',
        )}
      >
        {!value && <Check className="size-3.5" aria-hidden />}
        Todos ({countries.length})
      </Link>
      {countries.map((country) => {
        const active = value === country.iso3;
        return (
          <Link
            key={country.iso3}
            href={href(country.iso3)}
            scroll={false}
            aria-pressed={active}
            className={cn(
              pill,
              active
                ? 'border-brand bg-brand/8 font-semibold text-brand'
                : 'border-card-border bg-canvas text-body hover:border-line',
            )}
          >
            <span
              className={cn('size-2.5 rounded-full', DOTS[country.iso3] ?? 'bg-brand')}
              aria-hidden
            />
            {compact ? country.iso3 : `${country.name_es} (${country.iso3})`}
            {active && <Check className="size-3.5" aria-hidden />}
          </Link>
        );
      })}
    </div>
  );
}
