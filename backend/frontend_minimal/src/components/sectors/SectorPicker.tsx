'use client';

import { CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { DEFAULT_SECTOR_STYLE, SECTOR_STYLE } from './sectorIcons';

type Props = { sectors: { sector_code: string; name: string }[]; value: string; allowAll?: boolean };

/** Tarjetas de sector (selección única, en la URL como ?sector=). */
export function SectorPicker({ sectors, value, allowAll = false }: Props) {
  const pathname = usePathname();
  const search = useSearchParams();
  const href = (code: string) => {
    const params = new URLSearchParams(search.toString());
    if (code) params.set('sector', code);
    else params.delete('sector');
    params.delete('page');
    params.delete('occupation');
    const qs = params.toString();
    return qs ? `${pathname}?${qs}` : pathname;
  };
  const options = allowAll ? [{ sector_code: '', name: 'Todos los sectores' }, ...sectors] : sectors;
  return (
    <div>
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-muted-text">Sector</span>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]" role="group" aria-label="Sector">
        {options.map((s) => {
          const style = SECTOR_STYLE[s.sector_code] ?? DEFAULT_SECTOR_STYLE;
          const Icon = style.icon;
          const active = s.sector_code === value;
          return (
            <Link
              key={s.sector_code || 'all'}
              href={href(s.sector_code)}
              scroll={false}
              aria-pressed={active}
              className={`relative flex items-center gap-3 rounded-lg border px-3 py-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus ${
                active ? 'border-heading bg-heading text-white' : 'border-line bg-white text-heading hover:border-brand'
              }`}
            >
              {s.sector_code && (
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md" style={{ background: active ? 'rgb(255 255 255 / 0.12)' : style.soft, color: active ? '#fff' : style.color }}>
                  <Icon className="size-4" aria-hidden />
                </span>
              )}
              <span className="truncate">{s.name}</span>
              {active && <CheckCircle2 className="absolute right-2 top-2 size-4" aria-hidden />}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
