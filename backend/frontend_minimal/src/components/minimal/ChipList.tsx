'use client';

import { useId, useState } from 'react';

/** Lista de etiquetas que muestra las primeras `shown` y despliega el resto con un triángulo. */
export function ChipList({ items, shown, tone }: { items: string[]; shown: number; tone: 'in' | 'out' }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (!items.length) return <p className="text-sm text-slate-500">Ninguna.</p>;
  const hidden = items.length - shown;
  const visible = open || hidden <= 0 ? items : items.slice(0, shown);
  const chip = tone === 'in' ? 'bg-teal-50 text-teal-900' : 'bg-slate-100 text-slate-600 line-through decoration-slate-400';
  return (
    <div id={id} className="flex flex-wrap items-center gap-1.5">
      {visible.map((x) => <span key={x} className={`rounded-md px-2 py-0.5 text-xs ${chip}`}>{x}</span>)}
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={id}
          className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-700"
        >
          <span aria-hidden>{open ? '▲' : '▼'}</span>
          {open ? 'ver menos' : `y ${hidden} más`}
        </button>
      )}
    </div>
  );
}
