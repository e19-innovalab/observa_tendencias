import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

/** Contenedor estándar de las páginas de datos. */
export function Page({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`mx-auto max-w-[1600px] px-4 py-6 pb-12 sm:px-6 ${className}`}>{children}</div>
  );
}

/** Tarjeta base del sistema: borde suave, radio grande y sombra mínima. */
export function Card({
  children,
  className = '',
  as: Tag = 'section',
}: {
  children: ReactNode;
  className?: string;
  as?: 'section' | 'article' | 'div';
}) {
  return (
    <Tag
      className={cn(
        'rounded-xl border border-card-border bg-canvas shadow-[var(--shadow-card)]',
        className,
      )}
    >
      {children}
    </Tag>
  );
}

/** Encabezado: contexto, pregunta, bajada y controles. */
export function ChartHeader({
  eyebrow,
  title,
  subtitle,
  controls,
}: {
  eyebrow: string;
  title: ReactNode;
  subtitle?: string;
  controls?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <p className="text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">{eyebrow}</p>
        <div className="mt-1.5 text-[26px] leading-tight font-semibold tracking-tight text-heading">
          {title}
        </div>
        {subtitle && (
          <p className="mt-1.5 max-w-3xl text-[12.5px] leading-relaxed text-muted-text lg:line-clamp-2" title={subtitle}>
            {subtitle}
          </p>
        )}
      </div>
      {controls && <div className="flex flex-wrap items-center gap-2">{controls}</div>}
    </div>
  );
}

/**
 * Gráfico grande a la izquierda y columna de lectura a la derecha (abajo en el teléfono).
 * stickyRail: la columna acompaña al desplazarse, para listas largas donde se elige una fila.
 */
export function ChartLayout({
  chart,
  rail,
  className = 'items-start',
  stickyRail = false,
}: {
  chart: ReactNode;
  rail: ReactNode;
  className?: string;
  stickyRail?: boolean;
}) {
  const sticky = stickyRail
    ? 'lg:sticky lg:top-[calc(var(--header-h,57px)+1rem)] lg:max-h-[calc(100dvh-var(--header-h,57px)-2rem)] lg:overflow-y-auto'
    : '';
  return (
    <div className={`mt-4 flex flex-wrap gap-4 ${className}`}>
      <section className="min-w-0 flex-[999_1_640px] rounded-xl border border-card-border bg-canvas p-5 shadow-[var(--shadow-card)]">
        {chart}
      </section>
      <aside className={`flex w-full flex-[1_1_270px] flex-col gap-3 lg:max-w-[300px] ${sticky}`}>
        {rail}
      </aside>
    </div>
  );
}

/** Tarjeta de la columna de lectura. */
export function RailCard({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3.5 rounded-xl border border-card-border bg-rail p-5">
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">{children}</p>
  );
}

/** Pie del gráfico: fuente a la izquierda, acciones secundarias a la derecha. */
export function SourceLine({ source, children }: { source: ReactNode; children?: ReactNode }) {
  return (
    <div className="mt-3 flex flex-wrap justify-between gap-3 text-[11.5px] text-muted-text">
      <span>{source}</span>
      {children && <span className="flex flex-wrap gap-4">{children}</span>}
    </div>
  );
}

export function Stat({ label, value, sub }: { label: ReactNode; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-[11px] text-label">{label}</p>
      <p className="mt-0.5 text-[17px] font-semibold text-heading">{value}</p>
      {sub && <p className="text-[11px] text-muted-text">{sub}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="mx-auto mt-10 max-w-3xl rounded-xl border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text"
    >
      {message}
    </p>
  );
}

export const linkCls = 'text-[12.5px] font-semibold text-link hover:text-link-hover hover:underline';
export const buttonCls =
  'inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';
