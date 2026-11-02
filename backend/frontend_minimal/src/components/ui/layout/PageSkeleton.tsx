/** Mientras se cargan los datos de la página. */
export function PageSkeleton({ blocks = 3 }: { blocks?: number }) {
  return (
    <div role="status" aria-label="Cargando datos" className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      {Array.from({ length: blocks }, (_, i) => (
        <div key={i} className={`animate-pulse rounded-lg bg-surface-2 ${i === 0 ? 'h-40' : 'h-64'}`} />
      ))}
      <span className="sr-only">Cargando datos…</span>
    </div>
  );
}
