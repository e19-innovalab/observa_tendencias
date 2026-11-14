'use client';

import { Suspense } from 'react';
import { ChevronDown } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

export type FilterConfig = {
  name: string; // nombre del query param: country, sector, occupation...
  label: string; // texto cuando no hay selección
  options: { value: string; label: string }[];
  defaultValue?: string;
};

function Selects({
  filters,
  values,
  onChange,
  disabled = false,
}: {
  filters: FilterConfig[];
  values: Record<string, string>;
  onChange?: (name: string, value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {filters.map((f) => (
        <label key={f.name} className="flex items-center gap-2">
          <span className="text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
            {f.label}
          </span>
          <span className="relative">
            <select
              aria-label={f.label}
              value={values[f.name] ?? ''}
              disabled={disabled}
              onChange={onChange ? (e) => onChange(f.name, e.target.value) : undefined}
              className={cn(
                'h-9 appearance-none rounded-lg border border-card-border bg-canvas pr-8 pl-2.5 text-[12.5px] font-semibold text-heading',
                'hover:border-line focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                disabled && 'opacity-70',
              )}
            >
              <option value="">{f.label}</option>
              {f.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <ChevronDown
              className="pointer-events-none absolute top-1/2 right-2.5 size-3.5 -translate-y-1/2 text-muted-text"
              aria-hidden
            />
          </span>
        </label>
      ))}
    </div>
  );
}

function Inner({ filters }: { filters: FilterConfig[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();

  const values = Object.fromEntries(
    filters.map((f) => [f.name, search.get(f.name) ?? f.defaultValue ?? '']),
  );

  function onChange(name: string, value: string) {
    const params = new URLSearchParams(search.toString());
    if (value) params.set(name, value);
    else params.delete(name);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  return <Selects filters={filters} values={values} onChange={onChange} />;
}

/** Filtros de la barra superior, sincronizados con la URL. */
export function FilterBar({ filters }: { filters: FilterConfig[] }) {
  const values = Object.fromEntries(filters.map((f) => [f.name, f.defaultValue ?? '']));

  return (
    <Suspense fallback={<Selects filters={filters} values={values} disabled />}>
      <Inner filters={filters} />
    </Suspense>
  );
}
