import { cn } from '@/lib/utils';

type Segment = { label: string; value: number; color: string };

type Props = {
  segments: Segment[];
  title?: string;
  description?: string;
  className?: string;
};

/** Barra segmentada con la ponderación de cada componente del ISE. */
export function WeightBar({ segments, title, description, className }: Props) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className={cn('space-y-3', className)}>
      {(title || description) && (
        <div>
          {title && <h3 className="text-sm font-semibold text-heading">{title}</h3>}
          {description && <p className="mt-1 text-xs text-muted-text">{description}</p>}
        </div>
      )}

      <div className="flex h-3 overflow-hidden rounded-full bg-surface-2" role="img" aria-label="Ponderación del ISE">
        {segments.map((segment) => (
          <div
            key={segment.label}
            style={{ width: `${(segment.value / total) * 100}%`, backgroundColor: segment.color }}
            title={`${segment.label}: ${segment.value}%`}
          />
        ))}
      </div>

      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {segments.map((segment) => (
          <li key={segment.label} className="flex items-center gap-2 text-xs text-muted-text">
            <span
              className="size-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: segment.color }}
              aria-hidden
            />
            <span className="text-body">{segment.label}</span>
            <span className="ml-auto font-semibold text-heading">{segment.value}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
