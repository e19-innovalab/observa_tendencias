import type { ReactNode } from 'react';

type Props = {
  title: string;
  description: string;
  children?: ReactNode;
};

/** Héroe de sección: degradado de marca, título alineado a la izquierda. */
export function PageHero({ title, description, children }: Props) {
  return (
    <section className="text-white" style={{ backgroundImage: 'var(--gradient-hero)' }}>
      <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 py-6 sm:px-6">
        <div>
          <h1 className="text-[25px] leading-tight font-semibold tracking-tight">{title}</h1>
          <p className="mt-1.5 max-w-[620px] text-[12.5px] leading-relaxed text-blue-100/85">
            {description}
          </p>
        </div>
        {children}
      </div>
    </section>
  );
}
