'use client';

import { AlertTriangle, ArrowUp, RotateCcw, Sparkles, Square, X } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Fragment, useCallback, useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { DIXI_OPEN_EVENT } from './dixi';
import fairyBotIcon from './fairy-bot-icon.svg';
import type {
  AssistantAnswer,
  AssistantChoice,
  AssistantContext,
  AssistantStatus,
} from '@/lib/schemas/assistant';

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

/** Nombre visible del asistente en esta aplicación. */
const NAME = 'Dixi';
const TAGLINE = 'IA de Predix';
const HOVER_LABEL = `${NAME} · ${TAGLINE}`;

/** Tamaño de la burbuja flotante y margen mínimo con los bordes de la ventana. */
const BUBBLE_SIZE = 64;
const EDGE = 12;

const OCCUPATION_PAGE = /^\/ocupaciones\/(\d{4})/;
const CODE = /^\d{4}$/;

/** Lo que la persona está mirando: país, ocupación y sector salen de la URL. */
function useAssistantContext(): AssistantContext {
  const path = usePathname();
  const sp = useSearchParams();
  const country = sp.get('country') ?? undefined;
  const sel = sp.get('sel') ?? undefined;
  const occupation =
    path.match(OCCUPATION_PAGE)?.[1] ??
    (path.startsWith('/ocupaciones') && sel && CODE.test(sel) ? sel : undefined);
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
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={i}>{part.slice(2, -2)}</strong>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}

/** El backend todavía llama «Baqueano» o «Pixi» al asistente: acá se muestra siempre como Dixi. */
function rename(text: string) {
  return text.replace(/baqueano|pixi/gi, NAME);
}

/**
 * Dixi: burbuja arrastrable que abre un panel de conversación.
 * La conversación sigue al cambiar de página y usa el mismo asistente del observatorio
 * (GET /assistant y POST /assistant/ask) que la versión Baqueano.
 */
export function DixiDock({ status }: { status: AssistantStatus }) {
  const context = useAssistantContext();
  const t: Record<string, string> = Object.fromEntries(
    Object.entries({ ...status.texts, name: NAME, title: TAGLINE, tab: NAME }).map(([key, value]) => [
      key,
      rename(value),
    ]),
  );

  const [open, setOpen] = useState(false);
  /** La burbuja se puede ocultar; el icono de las barras vuelve a abrir el panel. */
  const [hidden, setHidden] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [remaining, setRemaining] = useState(status.remaining_today);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  const input = useRef<HTMLTextAreaElement>(null);
  const pending = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const drag = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    left: number;
    top: number;
    moved: boolean;
  } | null>(null);

  const clamp = useCallback((left: number, top: number) => {
    const maxLeft = Math.max(EDGE, window.innerWidth - BUBBLE_SIZE - EDGE);
    const maxTop = Math.max(EDGE, window.innerHeight - BUBBLE_SIZE - EDGE);
    return {
      left: Math.min(Math.max(EDGE, left), maxLeft),
      top: Math.min(Math.max(EDGE, top), maxTop),
    };
  }, []);

  // Posición inicial: abajo a la derecha, por encima del botón «Ir hacia arriba».
  useEffect(() => {
    const place = () =>
      setPos((current) =>
        clamp(
          current?.left ?? window.innerWidth - BUBBLE_SIZE - 24,
          current?.top ?? window.innerHeight - BUBBLE_SIZE - 112,
        ),
      );
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [clamp]);

  useEffect(() => {
    if (open) input.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // El icono de la barra de herramientas abre el panel y restaura la burbuja.
  useEffect(() => {
    const fromToolbar = () => {
      setHidden(false);
      setOpen(true);
    };
    window.addEventListener(DIXI_OPEN_EVENT, fromToolbar);
    return () => window.removeEventListener(DIXI_OPEN_EVENT, fromToolbar);
  }, []);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [turns, busy]);

  /** shown: lo que aparece como pregunta (el texto del botón elegido); choice: lo elegido. */
  async function ask(question: string, choice?: AssistantChoice, shown?: string) {
    const q = question.trim();
    if (!q || busy) return;

    const history =
      status.history_turns > 0
        ? turns
            .filter((x) => !(x.role === 'assistant' && (x.error || x.stopped)))
            .slice(-2 * status.history_turns)
            .map(({ role, content }) => ({ role, content }))
        : [];

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
        setTurns((prev) => [
          ...prev,
          { role: 'assistant', content: rename(body?.detail || t.error), error: true },
        ]);
      } else {
        const answer = body as AssistantAnswer;
        setRemaining(answer.remaining_today);
        setTurns((prev) => [
          ...prev,
          { role: 'assistant', content: rename(answer.answer), answer, question: q, choice },
        ]);
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

  function onPointerDown(e: React.PointerEvent<HTMLButtonElement>) {
    if (e.button !== 0 || !pos) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      left: pos.left,
      top: pos.top,
      moved: false,
    };
    setDragging(true);
  }

  function onPointerMove(e: React.PointerEvent<HTMLButtonElement>) {
    const d = drag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.moved && Math.hypot(dx, dy) > 4) d.moved = true;
    if (d.moved) setPos(clamp(d.left + dx, d.top + dy));
  }

  function onPointerUp(e: React.PointerEvent<HTMLButtonElement>) {
    const d = drag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    drag.current = null;
    setDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    // Un clic sin arrastre abre el panel; arrastrar solo cambia la posición.
    if (!d.moved) setOpen(true);
  }

  function onPointerCancel(e: React.PointerEvent<HTMLButtonElement>) {
    if (drag.current?.pointerId !== e.pointerId) return;
    drag.current = null;
    setDragging(false);
  }

  return (
    <>
      {!open && !hidden && (
        <div
          style={pos ? { left: pos.left, top: pos.top } : undefined}
          className={cn('group fixed z-50 size-16 touch-none', pos ? '' : 'invisible')}
        >
          <button
            type="button"
            aria-label={`${NAME}: ${TAGLINE}`}
            title={HOVER_LABEL}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerCancel}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setOpen(true);
              }
            }}
            className={cn(
              'size-full touch-none rounded-full',
              'bg-brand shadow-[0_10px_30px_-8px_rgb(23_43_196/0.65)] ring-4 ring-white/70',
              'transition-transform hover:scale-105 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
              dragging ? 'scale-105 cursor-grabbing' : 'cursor-grab',
            )}
          >
            <Image
              src={fairyBotIcon}
              alt=""
              fill
              sizes="64px"
              draggable={false}
              unoptimized
              className="pointer-events-none rounded-full object-cover select-none"
            />

            <span className="pointer-events-none absolute right-full mr-3 hidden items-center gap-1.5 rounded-lg bg-heading px-2.5 py-1.5 text-[11.5px] font-medium whitespace-nowrap text-white opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 sm:flex">
              <Sparkles className="size-3" aria-hidden />
              {HOVER_LABEL}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setHidden(true)}
            title="Ocultar a Dixi"
            aria-label="Ocultar a Dixi"
            className="absolute -top-1.5 -right-1.5 flex size-6 items-center justify-center rounded-full border border-card-border bg-canvas text-muted-text shadow-sm transition-colors hover:bg-surface-alt hover:text-heading focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        </div>
      )}

      <aside
        aria-label={`${NAME}: ${TAGLINE}`}
        aria-hidden={!open}
        inert={!open}
        className={cn(
          'fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-card-border bg-canvas shadow-2xl',
          'transition-transform duration-200 sm:w-[420px]',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-card-border bg-surface px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
              {NAME[0]}
            </span>
            <div className="min-w-0">
              <p className="text-base font-semibold text-heading">{NAME}</p>
              <p className="truncate text-xs text-muted-text">{TAGLINE}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {turns.length > 0 && (
              <button
                type="button"
                onClick={() => setTurns([])}
                disabled={busy}
                title={t.new_chat}
                aria-label={t.new_chat}
                className="rounded-md p-1.5 text-muted-text hover:bg-surface-2 hover:text-heading disabled:opacity-40"
              >
                <RotateCcw className="size-4" aria-hidden />
              </button>
            )}
            <button
              type="button"
              onClick={() => setOpen(false)}
              title={t.close}
              aria-label={t.close}
              className="rounded-md p-1.5 text-muted-text hover:bg-surface-2 hover:text-heading"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
          {turns.length === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-body">{rename(t.intro)}</p>
              <div className="flex flex-col items-start gap-2">
                {status.examples.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => ask(ex)}
                    className="rounded-full border border-line px-3 py-1.5 text-left text-sm text-body hover:border-brand hover:text-brand"
                  >
                    {rename(ex)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn, i) =>
            turn.role === 'user' ? (
              <p
                key={i}
                className="ml-8 rounded-2xl rounded-br-sm bg-brand px-3 py-2 text-sm whitespace-pre-line text-white"
              >
                {turn.content}
              </p>
            ) : (
              <div
                key={i}
                className={cn(
                  'mr-6 space-y-2 rounded-2xl rounded-bl-sm px-3 py-2 text-sm',
                  turn.error
                    ? 'bg-danger-soft text-danger'
                    : turn.stopped
                      ? 'border border-dashed border-line text-muted-text italic'
                      : 'bg-surface-alt text-body',
                )}
              >
                <p className="whitespace-pre-line">
                  <Rich text={turn.content} />
                </p>

                {turn.answer?.warning && (
                  <p className="flex gap-1.5 rounded-lg border border-warning/40 bg-warning-soft px-2 py-1.5 text-xs text-heading">
                    <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                    {rename(turn.answer.warning)}
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
                          ask(
                            turn.question ?? '',
                            {
                              ...turn.choice,
                              ...(o.occupation ? { occupation: o.occupation } : {}),
                              ...(o.country ? { country: o.country } : {}),
                            },
                            o.label,
                          )
                        }
                        className="rounded-full border border-brand/40 bg-canvas px-3 py-1 text-left text-xs font-medium text-brand hover:border-brand hover:bg-info-soft disabled:border-line disabled:text-placeholder"
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                )}

                {!!turn.answer?.links.some((l) => !l.external) && (
                  <div className="text-xs">
                    <p className="text-muted-text">{t.links}</p>
                    <ul className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1">
                      {turn.answer.links
                        .filter((l) => !l.external)
                        .map((l) => (
                          <li key={l.href}>
                            <Link href={l.href} className="font-medium text-link hover:underline">
                              {l.label}
                            </Link>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}

                {!!turn.answer?.links.some((l) => l.external) && (
                  <div className="text-xs">
                    <p className="text-muted-text">{t.external_links}</p>
                    <ul className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1">
                      {turn.answer.links
                        .filter((l) => l.external)
                        .map((l) => (
                          <li key={l.href}>
                            <a
                              href={l.href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-link hover:underline"
                            >
                              {l.label} ↗
                            </a>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
              </div>
            ),
          )}

          {busy && (
            <p className="mr-6 animate-pulse rounded-2xl rounded-bl-sm bg-surface-alt px-3 py-2 text-sm text-muted-text">
              {t.thinking}
            </p>
          )}
          <div ref={end} />
        </div>

        <form
          className="border-t border-card-border px-4 py-3"
          onSubmit={(e) => {
            e.preventDefault();
            ask(draft);
          }}
        >
          <div className="flex items-end gap-2 rounded-xl border border-line bg-surface-alt px-3 py-2 focus-within:border-brand focus-within:bg-canvas">
            <label htmlFor="predi-q" className="sr-only">
              {t.placeholder}
            </label>
            <textarea
              id="predi-q"
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
              className="max-h-32 min-w-0 flex-1 resize-none bg-transparent text-sm text-body outline-none placeholder:text-placeholder"
            />
            {busy ? (
              <button
                type="button"
                onClick={stop}
                title={t.stop}
                aria-label={t.stop}
                className="rounded-lg bg-heading p-1.5 text-white hover:bg-brand-deep"
              >
                <Square className="size-4 fill-current" aria-hidden />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!draft.trim() || remaining === 0}
                title={t.send}
                aria-label={t.send}
                className="rounded-lg bg-brand p-1.5 text-white hover:bg-brand-hover disabled:bg-line"
              >
                <ArrowUp className="size-4" aria-hidden />
              </button>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-snug text-muted-text">
            {t.disclaimer}
            {remaining !== null && <> {t.remaining.replace('{n}', String(remaining))}</>}
          </p>
        </form>
      </aside>
    </>
  );
}
