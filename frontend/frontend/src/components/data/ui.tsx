import type { ReactNode } from 'react';

/** Contenedor estándar de las páginas de datos. */
export function Page({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`mx-auto max-w-7xl px-4 py-7 pb-12 sm:px-6 ${className}`}>{children}</div>
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
        <p className="text-xs font-semibold tracking-wider text-muted-text uppercase">{eyebrow}</p>
        <div className="mt-1 text-[28px] leading-tight font-bold tracking-tight text-heading">
          {title}
        </div>
        {subtitle && (
          <p className="mt-1 max-w-3xl text-sm text-muted-text lg:line-clamp-2" title={subtitle}>
            {subtitle}
          </p>
        )}
      </div>
      {controls && <div className="flex flex-wrap items-center gap-3">{controls}</div>}
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
    <div className={`mt-5 flex flex-wrap gap-8 ${className}`}>
      <section className="min-w-0 flex-[999_1_640px]">{chart}</section>
      <aside className={`flex w-full flex-[1_1_260px] flex-col gap-4 lg:max-w-[320px] ${sticky}`}>
        {rail}
      </aside>
    </div>
  );
}

export function RailCard({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3.5 rounded-lg border border-line bg-canvas p-5">
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-xs font-semibold tracking-wider text-muted-text uppercase">{children}</p>;
}

/** Pie del gráfico: fuente a la izquierda, acciones secundarias a la derecha. */
export function SourceLine({ source, children }: { source: ReactNode; children?: ReactNode }) {
  return (
    <div className="mt-3 flex flex-wrap justify-between gap-3 text-xs text-muted-text">
      <span>{source}</span>
      {children && <span className="flex flex-wrap gap-4">{children}</span>}
    </div>
  );
}

export function Stat({ label, value, sub }: { label: ReactNode; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-text">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-heading">{value}</p>
      {sub && <p className="text-[11px] text-muted-text">{sub}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="mx-auto mt-10 max-w-3xl rounded-lg border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text"
    >
      {message}
    </p>
  );
}

export const linkCls = 'text-sm font-medium text-link hover:text-link-hover hover:underline';
export const buttonCls =
  'inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';
