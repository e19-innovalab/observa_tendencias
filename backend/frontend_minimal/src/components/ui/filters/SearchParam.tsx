'use client';

import { Search } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

/** Campo de búsqueda que actualiza ?<name>= después de una pausa al escribir. */
export function SearchParam({ name = 'q', label, placeholder }: { name?: string; label: string; placeholder?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [value, setValue] = useState(search.get(name) ?? '');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  function onChange(next: string) {
    setValue(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const params = new URLSearchParams(search.toString());
      if (next.trim()) params.set(name, next.trim());
      else params.delete(name);
      params.delete('page');
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    }, 350);
  }

  return (
    <label className="block">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-muted-text">{label}</span>
      <span className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-text" aria-hidden />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-md border border-line bg-surface py-2 pl-9 pr-3 text-sm text-body placeholder:text-placeholder focus-visible:outline-2 focus-visible:outline-focus"
        />
      </span>
    </label>
  );
}
