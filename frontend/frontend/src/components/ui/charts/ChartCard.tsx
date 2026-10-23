import type { ReactNode } from 'react';

type LegendItem = { label: string; color: string };
type Props = {
  title: string;
  subtitle?: string;
  legend: LegendItem[];
  sourceName?: string | null;
  updatedAt: string | null; // fecha ya formateada
  methodologyHref?: string;
  children: ReactNode;
};

export function ChartCard({
  title,
  subtitle,
  legend,
  sourceName,
  updatedAt,
  methodologyHref,
  children,
}: Props) {
  return (
    <section className="border border-gray-300 bg-white p-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {subtitle && <p className="mt-1 text-sm text-gray-600">{subtitle}</p>}
      <ul className="mt-3 flex flex-wrap gap-4 text-sm text-gray-600">
        {legend.map((l) => (
          <li key={l.label} className="flex items-center gap-2">
            <span className="size-3 rounded-full" style={{ backgroundColor: l.color }} aria-hidden />
            {l.label}
          </li>
        ))}
      </ul>

      <div className="mt-4">{children}</div>

      <footer className="mt-4 flex flex-wrap items-center justify-center gap-x-10 gap-y-2 border border-gray-300 px-4 py-3 text-sm">
        {sourceName && (
          <p>
            <span className="font-semibold">Fuente</span> {sourceName}
          </p>
        )}
        <p>
          <span className="font-semibold">Actualización</span> {updatedAt ?? 'Sin fecha informada'}
        </p>
        {methodologyHref && (
          <a href={methodologyHref} className="text-blue-600 hover:underline">
            Ver metodología
          </a>
        )}
      </footer>
    </section>
  );
}
