import Link from 'next/link';
import { cn } from '@/lib/utils';

type Props = {
  source: string;
  updatedAt: string;
  methodologyHref?: string;
  className?: string;
};

/** Pie de trazabilidad que acompaña a los gráficos y tablas. */
export function DataSourceFooter({
  source,
  updatedAt,
  methodologyHref = '/panorama-regional',
  className,
}: Props) {
  return (
    <footer
      className={cn(
        'flex flex-wrap items-center justify-between gap-x-6 gap-y-2 rounded-xl border border-card-border bg-rail px-4 py-3 text-[11.5px] text-muted-text',
        className,
      )}
    >
      <p>
        <span className="font-semibold text-body">Fuente</span> · {source}
      </p>
      <p>
        <span className="font-semibold text-body">Actualización</span> · {updatedAt}
      </p>
      <Link href={methodologyHref} className="font-semibold text-link hover:text-link-hover hover:underline">
        Ver fuente y metodología
      </Link>
    </footer>
  );
}
