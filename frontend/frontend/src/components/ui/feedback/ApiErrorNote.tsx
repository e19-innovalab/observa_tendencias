import type { ReactNode } from 'react';

type Props = { message?: string; className?: string };

/** Aviso visible cuando el backend no responde o devuelve un error. */
export function ApiErrorNote({ message, className }: Props) {
  return (
    <div
      role="alert"
      className={
        className ??
        'rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900'
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
    <div className="rounded-lg border border-dashed border-line bg-surface px-4 py-10 text-center text-sm text-muted-text">
      {children}
    </div>
  );
}
