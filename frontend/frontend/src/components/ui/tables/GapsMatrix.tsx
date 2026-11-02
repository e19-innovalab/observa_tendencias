'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { GapRow } from '@/lib/ui-types';
import { formatNumber } from '@/lib/utils/format';

/** Matriz comparativa de brechas de habilidades con selección por fila. */
export function GapsMatrix({ rows }: { rows: GapRow[] }) {
  const [selected, setSelected] = useState<string[]>([]);

  function toggle(skill: string) {
    setSelected((current) =>
      current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill],
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-canvas">
      <table className="w-full min-w-[70rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-surface-2 text-[11px] uppercase tracking-wide text-muted-text">
            {[
              'Habilidad',
              'País',
              'Demanda (%/año)',
              'Formación (%/año)',
              'Brecha (pp)',
              'Ocupaciones',
              'Principales ocupaciones',
              'Acciones',
            ].map((header) => (
              <th key={header} scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => {
            const rowKey = `${row.country}-${row.skill}`;
            const isSelected = selected.includes(rowKey);
            return (
              <tr
                key={rowKey}
                className={cn('align-top hover:bg-surface', isSelected && 'bg-brand/5')}
              >
                <td className="max-w-xs px-4 py-3 font-medium text-heading">{row.skill}</td>
                <td className="px-4 py-3">
                  <Badge tone="neutral">{row.country}</Badge>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-success">{row.demand}</td>
                <td className="whitespace-nowrap px-4 py-3 text-body">{row.training}</td>
                <td
                  className={cn(
                    'whitespace-nowrap px-4 py-3 font-semibold',
                    row.gap < 0 ? 'text-danger' : 'text-success',
                  )}
                >
                  {row.gap > 0 ? '+' : ''}
                  {formatNumber(row.gap, 1)} pp
                </td>
                <td className="px-4 py-3 text-body">{row.occupations}</td>
                <td className="px-4 py-3 text-xs text-muted-text">{row.mainOccupations}</td>
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(rowKey)}
                    aria-label={`Seleccionar ${row.skill}`}
                    className="size-4 cursor-pointer accent-[var(--color-brand)]"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
