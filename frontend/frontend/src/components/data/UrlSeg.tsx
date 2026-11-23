'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

type Option = { value: string; label: string };

/** Control segmentado que guarda la elección en la URL (?name=value); vacío = sin parámetro. */
export function UrlSeg({
  name,
  label,
  options,
  value,
  reset = ['page', 'sel'],
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  reset?: string[];
}) {
  const pathname = usePathname();
  const search = useSearchParams();
  const href = (v: string) => {
    const params = new URLSearchParams(search.toString());
    if (v) params.set(name, v);
    else params.delete(name);
    reset.forEach((k) => params.delete(k));
    const qs = params.toString();
    return qs ? `${pathname}?${qs}` : pathname;
  };
  return (
    <div
      className="inline-flex max-w-full flex-wrap rounded-lg bg-surface-2 p-0.5"
      role="group"
      aria-label={label}
    >
      {options.map((o) => (
        <Link
          key={o.value || 'all'}
          href={href(o.value)}
          scroll={false}
          aria-pressed={o.value === value}
          className={`rounded-md px-3 py-1.5 text-[12px] font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
            o.value === value
              ? 'bg-canvas text-brand shadow-sm'
              : 'text-muted-text hover:text-heading'
          }`}
        >
          {o.label}
        </Link>
      ))}
    </div>
  );
}
