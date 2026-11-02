type Props = { title: string; description: string };

/** Versión mínima: título y bajada alineados a la izquierda, sin banner. */
export function PageHero({ title, description }: Props) {
  return (
    <section className="mx-auto max-w-[1360px] px-4 pt-7 sm:px-8">
      <h1 className="text-[28px] font-bold tracking-tight text-slate-900">{title}</h1>
      <p className="mt-1 max-w-3xl text-sm text-slate-600">{description}</p>
    </section>
  );
}
