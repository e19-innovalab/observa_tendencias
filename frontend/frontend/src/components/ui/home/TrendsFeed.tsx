import { Badge } from '@/components/ui/badge';
import type { TrendFeedItem } from '@/lib/ui-types';

/** Feed de últimas novedades del observatorio. */
export function TrendsFeed({ items }: { items: TrendFeedItem[] }) {
  return (
    <ul className="divide-y divide-line rounded-lg border border-line bg-canvas">
      {items.map((item, index) => (
        <li
          key={item.id ?? `${item.title}-${item.date}-${item.country}-${index}`}
          className="flex flex-wrap items-start gap-3 p-4 sm:px-5"
        >
          <span className="mt-1.5 size-2 shrink-0 rounded-full bg-brand" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-heading">{item.title}</p>
            <p className="mt-0.5 text-xs text-muted-text">{item.detail}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge tone="neutral">{item.country}</Badge>
            <time className="text-xs text-muted-text">{item.date}</time>
          </div>
        </li>
      ))}
    </ul>
  );
}
