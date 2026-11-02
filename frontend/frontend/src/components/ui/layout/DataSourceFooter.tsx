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
        'flex flex-wrap items-center justify-center gap-x-10 gap-y-2 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-body',
        className,
      )}
    >
      <p>
        <span className="font-semibold">Fuente</span> {source}
      </p>
      <p>
        <span className="font-semibold">Actualización</span> {updatedAt}
      </p>
      <Link href={methodologyHref} className="font-medium text-link hover:text-link-hover hover:underline">
        Ver fuente y metodología
      </Link>
    </footer>
  );
}
