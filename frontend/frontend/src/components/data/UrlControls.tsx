'use client';

import { Check, ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type { ReactNode } from 'react';

export type Option = { value: string; label: string; count?: number };

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
  return (
    <span className="mb-1.5 block text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
      {children}
    </span>
  );
}

/** Chips de selección única con opción "Todos". */
export function ChipGroup({
  name,
  label,
  options,
  value,
  allLabel = 'Todos',
  reset = [],
  withAll = true,
  hideLabel = false,
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  allLabel?: string;
  reset?: string[];
  withAll?: boolean;
  hideLabel?: boolean;
}) {
  const href = useHref();
  const chips = withAll ? [{ value: '', label: `${allLabel} (${options.length})` }, ...options] : options;
  return (
    <div>
      {!hideLabel && <Label>{label}</Label>}
      <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
        {chips.map((o) => {
          const active = o.value === value;
          return (
            <Link
              key={o.value || 'all'}
              href={href(name, o.value, reset)}
              scroll={false}
              aria-pressed={active}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
                active
                  ? 'border-brand bg-brand text-white'
                  : 'border-card-border bg-canvas text-body hover:border-line'
              }`}
            >
              {o.value && (
                <span
                  className={`size-1.5 rounded-full ${active ? 'bg-brand' : 'bg-line'}`}
                  aria-hidden
                />
              )}
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
export function SelectParam({
  name,
  label,
  options,
  value,
  placeholder,
  reset = [],
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  placeholder?: string;
  reset?: string[];
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
          className="h-9 w-full appearance-none rounded-lg border border-card-border bg-canvas px-2.5 pr-8 text-[12.5px] font-semibold text-heading focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-text"
          aria-hidden
        />
      </span>
    </label>
  );
}

/** Control segmentado. */
export function Segmented({
  name,
  label,
  options,
  value,
  reset = ['page'],
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  reset?: string[];
}) {
  const href = useHref();
  return (
    <div>
      <Label>{label}</Label>
      <div
        className="inline-flex rounded-lg bg-surface-2 p-0.5"
        role="group"
        aria-label={label}
      >
        {options.map((o) => (
          <Link
            key={o.value}
            href={href(name, o.value, reset)}
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
    </div>
  );
}

/** Pestañas con contador. */
export function CountTabs({
  name,
  label,
  options,
  value,
  reset = [],
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  reset?: string[];
}) {
  const href = useHref();
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-card-border">
      <span className="py-2.5 pr-5 text-[10.5px] font-bold tracking-[0.08em] text-label uppercase sm:border-r sm:border-card-border">
        {label}
      </span>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Link
            key={o.value}
            href={href(name, o.value, reset)}
            scroll={false}
            aria-current={active ? 'page' : undefined}
            className={`-mb-px flex items-center gap-2 border-b-2 py-2.5 text-[12.5px] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
              active
                ? 'border-brand font-semibold text-heading'
                : 'border-transparent text-muted-text hover:text-heading'
            }`}
          >
            {o.label}
            {o.count !== undefined && (
              <span
                className={`rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold ${
                  active ? 'bg-brand/10 text-brand' : 'bg-surface-2 text-muted-text'
                }`}
              >
                {o.count}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}

/** Píldoras de selección única. */
export function PillGroup({
  name,
  label,
  options,
  value,
  reset = ['page'],
}: {
  name: string;
  label: string;
  options: Option[];
  value: string;
  reset?: string[];
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
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
              active
                ? 'border-brand bg-brand/8 font-semibold text-brand'
                : 'border-card-border bg-canvas text-body hover:border-line'
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
