import { formatDate, formatValue } from '@/lib/utils/format';
import type { AlertItem } from '@/lib/schemas/api';

const SEVERITY: Record<string, string> = {
  high: 'bg-alert-critical-icon',
  medium: 'bg-alert-warning-icon',
  low: 'bg-alert-positive-icon',
};

export function AlertList({ items, countryNames }: { items: AlertItem[]; countryNames: Record<string, string> }) {
  if (items.length === 0) return <p className="text-sm text-muted-text">No hay alertas para mostrar.</p>;
  return (
    <ul className="space-y-4">
      {items.map((a) => {
        const subject = [a.alert_type_label, a.indicator?.name, a.occupation?.name, a.source?.name]
          .filter(Boolean)
          .join(' · ');
        const values =
          a.previous_value !== null && a.current_value !== null
            ? `${formatValue(a.previous_value, a.unit ?? '')} → ${formatValue(a.current_value, a.unit ?? '')}`
            : null;
        return (
          <li key={a.alert_id} className="flex gap-3">
            <span
              className={`mt-1.5 size-2 shrink-0 rounded-full ${SEVERITY[a.severity] ?? 'bg-info'}`}
              aria-label={`Severidad ${a.severity_label}`}
            />
            <div className="min-w-0 text-sm">
              <p className="font-medium text-heading">{subject}</p>
              <p className="text-body">{a.message}</p>
              {values && <p className="text-body">{values}</p>}
              <p className="mt-0.5 text-xs text-muted-text">
                {[a.country_iso3 ? countryNames[a.country_iso3] ?? a.country_iso3 : null, formatDate(a.detected_at)]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
