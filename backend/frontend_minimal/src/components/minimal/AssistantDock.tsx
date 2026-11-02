'use client';

import { AlertTriangle, ArrowUp, MessageCircle, RotateCcw, Square, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Fragment, useEffect, useRef, useState } from 'react';
import type { AssistantAnswer, AssistantChoice, AssistantContext, AssistantStatus } from '@/lib/schemas/assistant';

type Turn =
  | { role: 'user'; content: string }
  | {
      role: 'assistant';
      content: string;
      answer?: AssistantAnswer;
      error?: boolean;
      stopped?: boolean;
      /** La pregunta que respondió (las opciones la repiten con lo elegido). */
      question?: string;
      choice?: AssistantChoice;
    };

const OCCUPATION_PAGE = /^\/ocupaciones\/(\d{4})/;
const CODE = /^\d{4}$/;

/** Lo que la persona está mirando: país, ocupación y sector salen de la URL. */
function useContext(): AssistantContext {
  const path = usePathname();
  const sp = useSearchParams();
  const country = sp.get('country') ?? undefined;
  const sel = sp.get('sel') ?? undefined;
  const occupation =
    path.match(OCCUPATION_PAGE)?.[1] ?? (path.startsWith('/ocupaciones') && sel && CODE.test(sel) ? sel : undefined);
  const sector = sp.get('sector') ?? (path.startsWith('/sectores') && sel && !CODE.test(sel) ? sel : undefined);
  return {
    page: path,
    country: country && !country.includes(',') ? country : undefined,
    occupation,
    sector: sector || undefined,
  };
}

/** **negrita** del modelo → <strong>; el resto, texto tal cual (con saltos de línea). */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
      )}
    </>
  );
}

/**
 * Asistente: pestaña fija en el borde derecho que abre un panel de conversación. Todos los textos
 * vienen de GET /assistant (app.yaml → assistant.texts). La conversación sigue al cambiar de página.
 */
export function AssistantDock({ status }: { status: AssistantStatus }) {
  const t = status.texts;
  const context = useContext();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [remaining, setRemaining] = useState(status.remaining_today);
  const input = useRef<HTMLTextAreaElement>(null);
  const pending = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) input.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [turns, busy]);

  /** shown: lo que aparece como pregunta (el texto del botón elegido); choice: lo elegido. */
  async function ask(question: string, choice?: AssistantChoice, shown?: string) {
    const q = question.trim();
    if (!q || busy) return;
    const history = turns
      .filter((x) => !(x.role === 'assistant' && (x.error || x.stopped)))
      .slice(-2 * status.history_turns)
      .map(({ role, content }) => ({ role, content }));
    setTurns((prev) => [...prev, { role: 'user', content: shown ?? q }]);
    setDraft('');
    setBusy(true);
    const ctrl = new AbortController();
    pending.current = ctrl;
    try {
      const res = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, context, history, choice }),
        signal: ctrl.signal,
      });
      const body = await res.json();
      if (!res.ok) {
        setTurns((prev) => [...prev, { role: 'assistant', content: body?.detail || t.error, error: true }]);
      } else {
        const answer = body as AssistantAnswer;
        setRemaining(answer.remaining_today);
        setTurns((prev) => [...prev, { role: 'assistant', content: answer.answer, answer, question: q, choice }]);
      }
    } catch {
      setTurns((prev) => [
        ...prev,
        ctrl.signal.aborted
          ? { role: 'assistant', content: t.stopped, stopped: true }
          : { role: 'assistant', content: t.error, error: true },
      ]);
    } finally {
      pending.current = null;
      setBusy(false);
      input.current?.focus();
    }
  }

  /** Corta la pregunta en curso: el backend detiene el modelo y no la cuenta para el límite. */
  const stop = () => pending.current?.abort();

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed right-0 top-1/2 z-30 flex -translate-y-1/2 items-center gap-2 rounded-l-lg bg-blue-700 px-2 py-4 text-sm font-semibold text-white shadow-lg hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 [writing-mode:vertical-rl]"
          aria-label={t.title}
        >
          <MessageCircle className="size-4 rotate-90" aria-hidden />
          {t.tab}
        </button>
      )}

      <aside
        aria-label={t.title}
        aria-hidden={!open}
        inert={!open}
        className={`fixed bottom-0 right-0 top-[var(--header-h,57px)] z-40 flex w-full flex-col border-l border-slate-200 bg-white shadow-2xl transition-transform duration-200 sm:w-[420px] ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div className="min-w-0">
            <p className="text-base font-semibold text-slate-900">{t.name}</p>
            <p className="truncate text-xs text-slate-500">{t.title}</p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {turns.length > 0 && (
              <button type="button" onClick={() => setTurns([])} disabled={busy} title={t.new_chat} aria-label={t.new_chat}
                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-40">
                <RotateCcw className="size-4" aria-hidden />
              </button>
            )}
            <button type="button" onClick={() => setOpen(false)} title={t.close} aria-label={t.close}
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800">
              <X className="size-4" aria-hidden />
            </button>
          </div>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
          {turns.length === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-slate-700">{t.intro}</p>
              <div className="flex flex-col items-start gap-2">
                {status.examples.map((ex) => (
                  <button key={ex} type="button" onClick={() => ask(ex)}
                    className="rounded-full border border-slate-200 px-3 py-1.5 text-left text-sm text-slate-700 hover:border-blue-700 hover:text-blue-700">
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn, i) =>
            turn.role === 'user' ? (
              <p key={i} className="ml-8 whitespace-pre-line rounded-2xl rounded-br-sm bg-blue-700 px-3 py-2 text-sm text-white">
                {turn.content}
              </p>
            ) : (
              <div key={i} className={`mr-6 space-y-2 rounded-2xl rounded-bl-sm px-3 py-2 text-sm ${turn.error ? 'bg-red-50 text-red-800' : turn.stopped ? 'border border-dashed border-slate-300 italic text-slate-500' : 'bg-slate-100 text-slate-800'}`}>
                <p className="whitespace-pre-line"><Rich text={turn.content} /></p>
                {turn.answer?.warning && (
                  <p className="flex gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-2 py-1.5 text-xs text-amber-900">
                    <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                    {turn.answer.warning}
                  </p>
                )}
                {!!turn.answer?.options.length && (
                  <div className="flex flex-col items-start gap-1.5">
                    {turn.answer.options.map((o) => (
                      <button
                        key={o.label}
                        type="button"
                        disabled={busy || i !== turns.length - 1}
                        onClick={() =>
                          ask(turn.question ?? '', {
                            ...turn.choice,
                            ...(o.occupation ? { occupation: o.occupation } : {}),
                            ...(o.country ? { country: o.country } : {}),
                          }, o.label)
                        }
                        className="rounded-full border border-blue-700/40 bg-white px-3 py-1 text-left text-xs font-medium text-blue-700 hover:border-blue-700 hover:bg-blue-50 disabled:border-slate-200 disabled:text-slate-400"
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                )}
                {!!turn.answer?.links.length && (
                  <div className="text-xs">
                    <p className="text-slate-500">{t.links}</p>
                    <ul className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1">
                      {turn.answer.links.map((l) => (
                        <li key={l.href}>
                          <Link href={l.href} className="font-medium text-blue-700 hover:underline">{l.label}</Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ),
          )}

          {busy && (
            <p className="mr-6 animate-pulse rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 text-sm text-slate-500">{t.thinking}</p>
          )}
          <div ref={end} />
        </div>

        <form
          className="border-t border-slate-200 px-4 py-3"
          onSubmit={(e) => {
            e.preventDefault();
            ask(draft);
          }}
        >
          <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 focus-within:border-blue-700 focus-within:bg-white">
            <label htmlFor="assistant-q" className="sr-only">{t.placeholder}</label>
            <textarea
              id="assistant-q"
              ref={input}
              rows={2}
              value={draft}
              maxLength={status.max_question_chars}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  ask(draft);
                }
              }}
              placeholder={t.placeholder}
              className="max-h-32 min-w-0 flex-1 resize-none bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-500"
            />
            {busy ? (
              <button type="button" onClick={stop} title={t.stop} aria-label={t.stop}
                className="rounded-lg bg-slate-800 p-1.5 text-white hover:bg-slate-950">
                <Square className="size-4 fill-current" aria-hidden />
              </button>
            ) : (
              <button type="submit" disabled={!draft.trim() || remaining === 0} title={t.send} aria-label={t.send}
                className="rounded-lg bg-blue-700 p-1.5 text-white hover:bg-blue-800 disabled:bg-slate-300">
                <ArrowUp className="size-4" aria-hidden />
              </button>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-snug text-slate-500">
            {t.disclaimer}
            {remaining !== null && <> {t.remaining.replace('{n}', String(remaining))}</>}
          </p>
        </form>
      </aside>
    </>
  );
}
