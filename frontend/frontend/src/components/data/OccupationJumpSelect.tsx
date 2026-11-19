'use client';

import { ChevronDown } from 'lucide-react';
import { useRouter } from 'next/navigation';

type Option = { occupation_code: string; name: string; href: string };

/** Selector de ocupación que navega a la ficha elegida conservando país y período. */
export function OccupationJumpSelect({
  options,
  value,
}: {
  options: Option[];
  value: string;
}) {
  const router = useRouter();

  return (
    <span className="relative block">
      <select
        value={value}
        aria-label="Ocupación"
        onChange={(event) => {
          const next = options.find((option) => option.occupation_code === event.target.value);
          if (next) router.push(next.href, { scroll: false });
        }}
        className="h-9 w-full appearance-none rounded-lg border border-card-border bg-canvas px-2.5 pr-8 text-[12.5px] font-semibold text-heading focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        {options.map((option) => (
          <option key={option.occupation_code} value={option.occupation_code}>
            {option.name} · CIUO {option.occupation_code}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-text"
        aria-hidden
      />
    </span>
  );
}
