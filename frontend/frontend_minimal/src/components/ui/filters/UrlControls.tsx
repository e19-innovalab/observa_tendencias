'use client';

import { Check, ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type { ReactNode } from 'react';

type Option = { value: string; label: string; count?: number };

/** href con un parámetro cambiado (vacío = se quita) y otros parámetros eliminados. */
function useHref() {
  const pathname = usePathname();
  const search = useSearchParams();
  return (key: string, value: string, remove: string[] = []) => {
    const params = new URLSearchParams(search.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    remove.forEach((k) => params.delete(k));
    const qs = params.toString();
    return qs ? `${pathname}?${qs}` : pathname;
  };
}

function Label({ children }: { children: ReactNode }) {
  return <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-muted-text">{children}</span>;
}

/** Chips de selección única con opción "Todos" (por ejemplo países). */
export function ChipGroup({ name, label, options, value, allLabel = 'Todos', reset = [], withAll = true }: {
  name: string; label: string; options: Option[]; value: string; allLabel?: string; reset?: string[]; withAll?: boolean;
}) {
  const href = useHref();
  const chips = withAll ? [{ value: '', label: `${allLabel} (${options.length})` }, ...options] : options;
  return (
    <div>
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
        {chips.map((o) => {
          const active = o.value === value;
          return (
            <Link
              key={o.value || 'all'}
              href={href(name, o.value, reset)}
              scroll={false}
              aria-pressed={active}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium focus-visible:outline-2 focus-visible:outline-focus ${
                active ? 'border-brand bg-surface-2 text-brand' : 'border-line text-muted-text hover:border-brand'
              }`}
            >
              {o.value && <span className={`size-1.5 rounded-full ${active ? 'bg-brand' : 'bg-line'}`} aria-hidden />}
              {o.label}
              {active && <Check className="size-3" aria-hidden />}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

/** Lista desplegable que cambia un parámetro de la URL. */
export function SelectParam({ name, label, options, value, placeholder, reset = [] }: {
  name: string; label: string; options: Option[]; value: string; placeholder?: string; reset?: string[];
}) {
  const router = useRouter();
  const href = useHref();
  return (
    <label className="block">
      <Label>{label}</Label>
      <span className="relative block">
        <select
          value={value}
          onChange={(e) => router.replace(href(name, e.target.value, reset), { scroll: false })}
          className="w-full appearance-none rounded-md border border-line bg-surface px-3 py-2 pr-9 text-sm text-body focus-visible:outline-2 focus-visible:outline-focus"
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-text" aria-hidden />
      </span>
    </label>
  );
}

/** Control segmentado (por ejemplo frecuencia Trimestral / Mensual / Anual). */
export function Segmented({ name, label, options, value, reset = ['page'] }: {
  name: string; label: string; options: Option[]; value: string; reset?: string[];
}) {
  const href = useHref();
  return (
    <div>
      <Label>{label}</Label>
      <div className="inline-flex rounded-md border border-line bg-surface-2 p-0.5" role="group" aria-label={label}>
        {options.map((o) => (
          <Link
            key={o.value}
            href={href(name, o.value, reset)}
            scroll={false}
            aria-pressed={o.value === value}
            className={`rounded px-3 py-1 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-focus ${
              o.value === value ? 'bg-white text-brand shadow-sm' : 'text-muted-text hover:text-heading'
            }`}
          >
            {o.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

/** Pestañas con contador (por ejemplo grupos de indicadores). */
export function CountTabs({ name, label, options, value, reset = [] }: {
  name: string; label: string; options: Option[]; value: string; reset?: string[];
}) {
  const href = useHref();
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line/70">
      <span className="py-2 pr-4 text-sm font-medium uppercase tracking-wide text-muted-text sm:border-r sm:border-line/70">{label}:</span>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Link
            key={o.value}
            href={href(name, o.value, reset)}
            scroll={false}
            aria-current={active ? 'page' : undefined}
            className={`-mb-px flex items-center gap-2 border-b-2 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus ${
              active ? 'border-brand font-semibold text-heading' : 'border-transparent text-muted-text hover:text-heading'
            }`}
          >
            {o.label}
            {o.count !== undefined && (
              <span className="rounded-full bg-surface-2 px-2 text-[11px] font-semibold text-muted-text">{o.count}</span>
            )}
          </Link>
        );
      })}
    </div>
  );
}

/** Píldoras de selección única (por ejemplo el indicador activo). */
export function PillGroup({ name, label, options, value, reset = ['page'] }: {
  name: string; label: string; options: Option[]; value: string; reset?: string[];
}) {
  const href = useHref();
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Link
            key={o.value}
            href={href(name, o.value, reset)}
            scroll={false}
            aria-pressed={active}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium focus-visible:outline-2 focus-visible:outline-focus ${
              active ? 'border-heading bg-heading text-white' : 'border-line text-body hover:border-brand'
            }`}
          >
            {active && <Check className="size-3" aria-hidden />}
            {o.label}
          </Link>
        );
      })}
    </div>
  );
}
