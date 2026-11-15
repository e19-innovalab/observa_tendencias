'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Download, LineChart as LineChartIcon, Table2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type LegendItem = { label: string; color: string };

type TableData = {
  columns: string[];
  rows: (string | number)[][];
};

type Props = {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  meta?: React.ReactNode;
  legend?: LegendItem[];
  sourceName?: string | null;
  updatedAt: string | null; // fecha ya formateada
  methodologyHref?: string;
  controls?: React.ReactNode;
  table?: TableData;
  downloadName?: string;
  children: React.ReactNode;
};

function toCsv({ columns, rows }: TableData) {
  const escape = (value: string | number) => {
    const text = String(value ?? '');
    return /[",;\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [columns, ...rows].map((row) => row.map(escape).join(';')).join('\r\n');
}

export function ChartCard({
  title,
  subtitle,
  icon,
  meta,
  legend = [],
  sourceName,
  updatedAt,
  methodologyHref,
  controls,
  table,
  downloadName = 'datos.csv',
  children,
}: Props) {
  const [view, setView] = useState<'chart' | 'table'>('chart');

  function download() {
    if (!table) return;
    const blob = new Blob([`\ufeff${toCsv(table)}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = downloadName;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="overflow-hidden rounded-xl border border-card-border bg-canvas shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
        <div className="flex min-w-0 items-start gap-2.5">
          {icon && <span className="mt-0.5 shrink-0 text-brand">{icon}</span>}
          <div className="min-w-0">
            <h3 className="text-[19px] leading-tight font-semibold text-heading">{title}</h3>
            {subtitle && <p className="mt-1 text-[12.5px] leading-relaxed text-muted-text">{subtitle}</p>}
          </div>
        </div>

        {(meta || table) && (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            {meta}
            {table && (
              <>
                <div
                  className="inline-flex rounded-lg bg-surface-2 p-0.5"
                  role="group"
                  aria-label="Vista del gráfico"
                >
                  <button
                    type="button"
                    aria-pressed={view === 'chart'}
                    onClick={() => setView('chart')}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12.5px] font-semibold transition-colors',
                      view === 'chart' ? 'bg-canvas text-brand shadow-sm' : 'text-muted-text hover:text-heading',
                    )}
                  >
                    <LineChartIcon className="size-4" aria-hidden />
                    Gráfico
                  </button>
                  <button
                    type="button"
                    aria-pressed={view === 'table'}
                    onClick={() => setView('table')}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12.5px] font-semibold transition-colors',
                      view === 'table' ? 'bg-canvas text-brand shadow-sm' : 'text-muted-text hover:text-heading',
                    )}
                  >
                    <Table2 className="size-4" aria-hidden />
                    Tabla
                  </button>
                </div>
                <button
                  type="button"
                  onClick={download}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-card-border bg-canvas px-3 text-[12.5px] font-semibold text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
                >
                  <Download className="size-4 text-muted-text" aria-hidden />
                  Descargar CSV
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {controls && <div className="px-5 pt-4">{controls}</div>}

      <div className="px-5 pt-2 pb-4">
        {view === 'table' && table ? (
          <div className="max-h-[28rem] overflow-auto rounded-lg border border-card-border">
            <table className="w-full min-w-[36rem] border-collapse text-left text-[12.5px]">
              <thead className="sticky top-0 bg-surface-2 text-[10.5px] tracking-wide text-muted-text uppercase">
                <tr>
                  {table.columns.map((column) => (
                    <th key={column} scope="col" className="px-3 py-2 font-semibold whitespace-nowrap">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-card-border">
                {table.rows.map((row, index) => (
                  <tr key={index} className="hover:bg-surface">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className={cn('px-3 py-2', cellIndex === 0 ? 'font-medium text-heading' : 'text-body')}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          children
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-t border-card-border px-5 py-3">
        {legend.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {legend.map((item) => (
              <span
                key={item.label}
                className="inline-flex items-center gap-1.5 rounded-md border border-card-border px-2 py-1 text-[10.5px] text-muted-text"
              >
                <span
                  className="h-0.5 w-3.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                  aria-hidden
                />
                {item.label}
              </span>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10.5px] text-muted-text">
          {sourceName && (
            <span>
              <span className="text-placeholder">·</span> Fuente: {sourceName}
            </span>
          )}
          <span>
            <span className="text-placeholder">·</span> Actualizado: {updatedAt ?? 'sin fecha'}
          </span>
          {methodologyHref && (
            <Link
              href={methodologyHref}
              className="font-semibold text-link hover:text-link-hover hover:underline"
            >
              Ver metodología
            </Link>
          )}
        </div>
      </footer>
    </section>
  );
}
