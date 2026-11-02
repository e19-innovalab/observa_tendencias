import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/utils/format';

type Item = { label: string; value: number; active?: boolean };

type Props = {
  items: Item[];
  average: number;
  max?: number;
};

/** Barras horizontales comparativas con línea de promedio regional. */
export function SectorBarChart({ items, average, max = 100 }: Props) {
  return (
    <div className="space-y-5">
      {items.map((item) => (
        <div key={item.label} className="grid grid-cols-[minmax(0,13rem)_1fr_3.5rem] items-center gap-3">
          <span className={cn('text-sm', item.active ? 'font-semibold text-brand' : 'text-body')}>
            {item.label}
            {item.active && <span className="ml-1 text-xs text-muted-text">(activa)</span>}
          </span>

          <div className="relative h-6 rounded-sm bg-surface-2">
            <div
              className={cn('h-full rounded-sm', item.active ? 'bg-brand' : 'bg-brand/35')}
              style={{ width: `${(item.value / max) * 100}%` }}
            />
            <span
              className="absolute inset-y-0 w-px border-l border-dashed border-heading/50"
              style={{ left: `${(average / max) * 100}%` }}
              aria-hidden
            />
          </div>

          <span className="text-right text-xs font-semibold text-heading">
            {formatNumber(item.value, 1)}
          </span>
        </div>
      ))}

      <p className="flex items-center gap-2 text-xs text-muted-text">
        <span className="inline-block h-3 border-l border-dashed border-heading/50" aria-hidden />
        Línea de referencia: promedio ponderado regional {average.toFixed(1)} pts.
      </p>
    </div>
  );
}
