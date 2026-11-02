import { formatChange, formatValue } from '@/lib/utils/format';
import type { HighlightCard } from '@/lib/schemas/api';

type Props = { label: string; cards: HighlightCard[]; countryNames: Record<string, string> };

/** Un indicador con el último valor de cada país (cada uno con su año y su variación). */
export function RegionalKpiCard({ label, cards, countryNames }: Props) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-text">{label}</p>
      <ul className="mt-3 space-y-2">
        {cards.map((c) => {
          const change = formatChange(c.change, c.change_kind, c.indicator.unit);
          const better = c.change === null || c.change === 0 || c.indicator.higher_is_better === null
            ? null
            : (c.change > 0) === c.indicator.higher_is_better;
          return (
            <li key={c.country_iso3} className="flex items-baseline justify-between gap-2">
              <span className="w-10 text-xs font-semibold text-muted-text" title={countryNames[c.country_iso3]}>
                {c.country_iso3}
              </span>
              <span className="flex-1 text-xl font-semibold text-heading">
                {c.current ? formatValue(c.current.value, c.indicator.unit) : 'Sin dato'}
              </span>
              <span className="text-xs text-muted-text">{c.current?.period ?? ''}</span>
              {change && (
                <span
                  className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${
                    better === null ? 'bg-surface-2 text-body' : better ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'
                  }`}
                  title="Variación respecto del período anterior"
                >
                  {change}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
