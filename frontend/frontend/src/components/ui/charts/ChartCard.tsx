import type { ReactNode } from 'react';

type LegendItem = { label: string; color: string };
type Props = {
  title: string;
  legend: LegendItem[];
  updatedAt: string | null; // fecha ya formateada, ej. "12/05/2021"
  methodologyHref?: string;
  children: ReactNode;
};

export function ChartCard({ title, legend, updatedAt, methodologyHref, children }: Props) {
  return (
    <section className="border border-gray-300 bg-white p-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
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
        <p>
          <span className="font-semibold">Actualización</span>{' '}
          {updatedAt ?? 'Sin fecha informada'}
        </p>
        {methodologyHref && (
          <a href={methodologyHref} className="text-blue-600 hover:underline">
            Ver fuente y metodología
          </a>
        )}
      </footer>
    </section>
  );
}
