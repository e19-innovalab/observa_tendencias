'use client';

import { Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { highlight } from '@/lib/utils/search';

type Result = { label: string; detail?: string; href: string };
type Group = { label: string; items: Result[] };
type Answer = { query: string; country: string | null; code: string | null; groups: Group[] };

const DEBOUNCE_MS = 200;

/**
 * Buscador global (⌘K / Ctrl+K). No es un menú: no muestra nada hasta que se escribe. Entiende
 * palabras en cualquier orden y sin tildes, códigos CIUO ("2221") y nombres de país ("chile").
 */
export function SearchPalette() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState('');
  const [focused, setFocused] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        input.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    const term = q.trim();
    if (!term) return;
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(term)}`, { signal: ctrl.signal });
        if (res.ok) {
          setAnswer((await res.json()) as Answer);
          setActive(0);
        }
      } catch {
        // búsqueda cancelada o backend caído: se mantiene la respuesta anterior
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [q]);

  const term = q.trim();
  // la respuesta corresponde a lo escrito (mientras llega la nueva, no se muestra la vieja como si fuera de esta)
  const current = answer && term && answer.query === term ? answer : null;
  const flat = current?.groups.flatMap((g) => g.items) ?? [];
  const open = focused && term.length > 0 && (current !== null || answer !== null);

  const go = (r: Result) => {
    setQ('');
    setAnswer(null);
    input.current?.blur();
    router.push(r.href);
  };

  let k = -1;
  return (
    <div className="relative w-full max-w-xs">
      <label className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 focus-within:border-blue-700 focus-within:bg-white">
        <Search className="size-4 shrink-0 text-slate-500" aria-hidden />
        <span className="sr-only">Buscar</span>
        <input
          ref={input}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, flat.length - 1)); }
            if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            if (e.key === 'Enter' && flat[active]) go(flat[active]);
            if (e.key === 'Escape') { setQ(''); input.current?.blur(); }
          }}
          placeholder="Buscar indicador, ocupación o habilidad"
          role="combobox"
          aria-expanded={open}
          aria-controls="search-results"
          aria-autocomplete="list"
          aria-activedescendant={open && flat[active] ? `search-opt-${active}` : undefined}
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-500"
        />
        <kbd className="hidden rounded border border-slate-200 bg-white px-1.5 text-[11px] font-medium text-slate-500 sm:block">⌘K</kbd>
      </label>
      {open && (
        <div id="search-results" role="listbox" className="absolute right-0 z-40 mt-2 max-h-[28rem] w-[28rem] max-w-[90vw] overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          {current && (current.country || current.code) && (
            <p className="px-3 pb-1 pt-2 text-xs text-slate-500">
              {current.code && <>Código CIUO <span className="font-semibold text-slate-700">{current.code}</span></>}
              {current.code && current.country && ' · '}
              {current.country && <>País: <span className="font-semibold text-slate-700">{current.country}</span></>}
            </p>
          )}
          {current && flat.length === 0 && (
            <p className="px-3 py-3 text-sm text-slate-600">
              Sin resultados para «{term}». Probá con menos palabras, otra forma de la palabra o un código CIUO (por ejemplo, 2221).
            </p>
          )}
          {!current && <p className="px-3 py-3 text-sm text-slate-500">Buscando…</p>}
          {current?.groups.map((g) => (
            <div key={g.label} role="group" aria-label={g.label}>
              <p className="px-3 pb-1 pt-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{g.label}</p>
              {g.items.map((r) => {
                k += 1;
                const i = k;
                return (
                  <button
                    key={r.href}
                    id={`search-opt-${i}`}
                    type="button"
                    role="option"
                    aria-selected={i === active}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => go(r)}
                    onMouseEnter={() => setActive(i)}
                    className={`flex w-full items-baseline justify-between gap-3 px-3 py-1.5 text-left text-sm ${i === active ? 'bg-slate-100' : ''}`}
                  >
                    <span className="min-w-0 truncate text-slate-800">
                      {highlight(r.label, term).map((p, j) => (p.hit ? <mark key={j} className="bg-transparent font-semibold text-slate-950">{p.text}</mark> : <span key={j}>{p.text}</span>))}
                    </span>
                    {r.detail && <span className="shrink-0 text-xs text-slate-500">{r.detail}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
