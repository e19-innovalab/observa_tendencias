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
    <div
      className={cn(
        'flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-8',
        className,
      )}
    >
      {(title || description) && (
        <div className="shrink-0 lg:max-w-[280px]">
          {title && <h3 className="text-[12.5px] font-semibold text-heading">{title}:</h3>}
          {description && <p className="mt-1 text-[10.5px] leading-relaxed text-muted-text">{description}</p>}
        </div>
      )}

      <div className="min-w-0 flex-1 space-y-2">
        <div
          className="flex h-2.5 overflow-hidden rounded-full bg-surface-2"
          role="img"
          aria-label="Ponderación del ISE"
        >
          {segments.map((segment) => (
            <div
              key={segment.label}
              style={{ width: `${(segment.value / total) * 100}%`, backgroundColor: segment.color }}
              title={`${segment.label}: ${segment.value}%`}
            />
          ))}
        </div>

        <ul className="flex flex-wrap gap-x-5 gap-y-1">
          {segments.map((segment) => (
            <li key={segment.label} className="flex items-center gap-1.5 text-[10.5px] text-muted-text">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: segment.color }}
                aria-hidden
              />
              <span className="text-body">{segment.label}:</span>
              <span className="font-semibold text-heading">{segment.value}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
