import { Badge } from '@/components/ui/badge';
import type { RankingItem } from '@/lib/ui-types';
import { formatNumber } from '@/lib/utils/format';

/** Ranking vertical con barra de progreso y valor sobre 100. */
export function RankingList({ items }: { items: RankingItem[] }) {
  return (
    <ol className="divide-y divide-line rounded-lg border border-line bg-canvas">
      {items.map((item) => (
        <li key={item.rank} className="p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand/10 text-xs font-bold text-brand">
              {item.rank}
            </span>
            <h3 className="text-sm font-semibold text-heading">{item.title}</h3>
            {item.badge && <Badge tone="warning">{item.badge}</Badge>}
            <span className="ml-auto text-lg font-semibold text-heading">
              {item.score === null ? '—' : formatNumber(item.score, 1)}
              <span className="ml-1 text-xs font-normal text-muted-text">/100</span>
            </span>
          </div>

          <p className="mt-1 pl-10 text-xs text-muted-text">{item.meta}</p>

          {item.score !== null && (
            <div className="mt-2 ml-10 h-2 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full rounded-full bg-brand"
                style={{ width: `${item.score}%` }}
                aria-hidden
              />
            </div>
          )}

          {item.note && <p className="mt-2 pl-10 text-xs text-muted-text">{item.note}</p>}

          {item.delta && (
            <p className="mt-1 pl-10 text-right text-xs font-medium text-muted-text">{item.delta}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
