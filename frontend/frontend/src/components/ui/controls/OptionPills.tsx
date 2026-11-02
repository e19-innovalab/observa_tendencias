'use client';

import { Suspense } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

export type PillOption = { value: string; label: string; hint?: string };

type Props = {
  param: string;
  options: PillOption[];
  defaultValue: string;
  label: string;
  variant?: 'chip' | 'segment';
  className?: string;
};

const BASE = 'inline-flex items-center gap-2 rounded-full border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';

function pillClass(variant: Props['variant'], active: boolean) {
  if (variant === 'segment') {
    return cn(
      BASE,
      'border-transparent px-4 py-1.5 text-sm font-medium',
      active ? 'bg-brand text-white shadow-sm' : 'bg-transparent text-body hover:bg-surface-2',
    );
  }
  return cn(
    BASE,
    'px-4 py-2 text-sm font-medium',
    active
      ? 'border-heading bg-heading text-white'
      : 'border-line bg-canvas text-body hover:border-brand/50 hover:bg-surface-alt',
  );
}

function PillGroup({ options, current, variant, label, onSelect }: {
  options: PillOption[];
  current: string;
  variant: Props['variant'];
  label: string;
  onSelect?: (value: string) => void;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn(
        'flex flex-wrap gap-2',
        variant === 'segment' && 'inline-flex flex-nowrap rounded-full bg-surface-2 p-1',
      )}
    >
      {options.map((option) => {
        const active = option.value === current;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={onSelect ? () => onSelect(option.value) : undefined}
            className={pillClass(variant, active)}
          >
            {option.label}
            {option.hint && (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[10px] font-semibold',
                  active ? 'bg-white/20 text-white' : 'bg-surface-2 text-muted-text',
                )}
              >
                {option.hint}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Inner({ param, options, defaultValue, label, variant = 'chip', className }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const current = search.get(param) ?? defaultValue;

  function select(value: string) {
    const params = new URLSearchParams(search.toString());
    if (value === defaultValue) params.delete(param);
    else params.set(param, value);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  return (
    <div className={className}>
      <PillGroup
        options={options}
        current={current}
        variant={variant}
        label={label}
        onSelect={select}
      />
    </div>
  );
}

/**
 * Grupo de opciones que sincroniza la selección con la URL.
 * El Suspense interno permite usarlo en páginas estáticas.
 */
export function OptionPills(props: Props) {
  return (
    <Suspense
      fallback={
        <div className={props.className}>
          <PillGroup
            options={props.options}
            current={props.defaultValue}
            variant={props.variant}
            label={props.label}
          />
        </div>
      }
    >
      <Inner {...props} />
    </Suspense>
  );
}
