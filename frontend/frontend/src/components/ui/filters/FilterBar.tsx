'use client';

import { ChevronDown } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

export type FilterConfig = {
  name: string; // nombre del query param: country, sector, occupation...
  label: string; // texto cuando no hay selección
  options: { value: string; label: string }[];
};

export function FilterBar({ filters }: { filters: FilterConfig[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();

  function onChange(name: string, value: string) {
    const params = new URLSearchParams(search.toString());
    if (value) params.set(name, value);
    else params.delete(name);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  return (
    <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(14rem,1fr))]">
      {filters.map((f) => (
        <div key={f.name} className="relative">
          <select
            aria-label={f.label}
            value={search.get(f.name) ?? ''}
            onChange={(e) => onChange(f.name, e.target.value)}
            className="w-full appearance-none border-b border-gray-400 bg-slate-50 px-4 py-3 pr-10 text-sm text-gray-900 focus-visible:outline-2 focus-visible:outline-blue-600"
          >
            <option value="">{f.label}</option>
            {f.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <ChevronDown
            className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-gray-600"
            aria-hidden
          />
        </div>
      ))}
    </div>
  );
}
