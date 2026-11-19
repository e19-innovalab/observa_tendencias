'use client';

import { Search } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

/** Campo de búsqueda que actualiza ?<name>= después de una pausa al escribir. */
export function SearchParam({
  name = 'q',
  label,
  placeholder,
}: {
  name?: string;
  label: string;
  placeholder?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [value, setValue] = useState(search.get(name) ?? '');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

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
      <span className="mb-1.5 block text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
        {label}
      </span>
      <span className="relative block">
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-placeholder"
          aria-hidden
        />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="h-9 w-full rounded-lg border border-card-border bg-canvas py-1.5 pr-3 pl-9 text-[12.5px] text-body placeholder:text-placeholder hover:border-line focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        />
      </span>
    </label>
  );
}
