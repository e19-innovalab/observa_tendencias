'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

type Option = { value: string; label: string };

/** Selector que guarda la elección en la URL (?name=value); vacío = sin parámetro. */
export function UrlSelect({ name, label, options, value, reset = [] }: { name: string; label: string; options: Option[]; value: string; reset?: string[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const change = (v: string) => {
    const params = new URLSearchParams(search.toString());
    if (v) params.set(name, v);
    else params.delete(name);
    reset.forEach((k) => params.delete(k));
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  return (
    <label className="inline-flex items-center gap-2 text-[13px] text-muted-text">
      {label}
      <select
        value={value}
        onChange={(e) => change(e.target.value)}
        className="h-9 rounded-lg border border-line bg-canvas px-2.5 text-[13px] text-heading focus-visible:outline-2 focus-visible:outline-focus"
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
