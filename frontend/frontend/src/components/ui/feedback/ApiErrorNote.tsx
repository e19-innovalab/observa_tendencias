import type { ReactNode } from 'react';

type Props = { message?: string; className?: string };

/** Aviso visible cuando el backend no responde o devuelve un error. */
export function ApiErrorNote({ message, className }: Props) {
  return (
    <div
      role="alert"
      className={
        className ??
        'rounded-xl border border-alert-critical-border bg-alert-critical-bg px-4 py-3 text-[12.5px] text-alert-critical-text'
      }
    >
      <p className="font-semibold">No se pudieron cargar los datos.</p>
      <p className="mt-1">{message ?? 'Revisá que el backend esté corriendo y volvé a intentar.'}</p>
    </div>
  );
}

/** Mensaje neutro para combinaciones de filtros sin resultados. */
export function EmptyDataNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-card-border bg-rail px-4 py-10 text-center text-[12.5px] text-muted-text">
      {children}
    </div>
  );
}
