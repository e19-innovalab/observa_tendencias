import { ChevronsRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/utils/format';

type Item = { label: string; value: number; active?: boolean };

type Props = {
  items: Item[];
  average: number;
  max?: number;
  showFootnote?: boolean;
};

/** Barras horizontales comparativas con línea de promedio regional. */
export function SectorBarChart({ items, average, max = 100, showFootnote = true }: Props) {
  return (
    <div className="space-y-3.5">
      {items.map((item) => (
        <div
          key={item.label}
          className={cn(
            'rounded-lg px-3 py-2 transition-colors',
            item.active ? 'bg-brand/5' : 'hover:bg-surface',
          )}
        >
          <div className="flex items-baseline justify-between gap-3">
            <span
              className={cn(
                'flex min-w-0 items-center gap-2 text-[12.5px]',
                item.active ? 'font-semibold text-heading' : 'text-body',
              )}
            >
              {item.active ? (
                <ChevronsRight className="size-3.5 shrink-0 text-heading" aria-hidden />
              ) : (
                <span className="size-2 shrink-0 rounded-full bg-heading" aria-hidden />
              )}
              <span className="truncate">{item.label}</span>
            </span>
            <span className="shrink-0 text-[12.5px] font-semibold text-heading">
              {formatNumber(item.value, 1)}
              <span className="ml-1 text-[11px] font-normal text-muted-text">/ 100</span>
            </span>
          </div>

          <div className="relative mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2">
            <div
              className={cn('h-full rounded-full', item.active ? 'bg-heading' : 'bg-brand/55')}
              style={{ width: `${Math.min(100, (item.value / max) * 100)}%` }}
            />
            <span
              className="absolute inset-y-0 w-px border-l border-dashed border-heading/45"
              style={{ left: `${Math.min(100, (average / max) * 100)}%` }}
              aria-hidden
            />
          </div>
        </div>
      ))}

      {showFootnote && (
        <p className="flex items-center gap-2 px-3 pt-1 text-[10.5px] text-muted-text">
          <span className="inline-block h-3 border-l border-dashed border-heading/50" aria-hidden />
          Línea de referencia: promedio ponderado regional {formatNumber(average, 1)} pts.
        </p>
      )}
    </div>
  );
}
