type Props = { title: string; description: string };

export function PageHero({ title, description }: Props) {
  return (
    <section className="bg-brand px-4 py-12 text-center text-white sm:px-6 sm:py-14">
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
      <p className="mx-auto mt-4 max-w-3xl text-sm leading-relaxed text-blue-50 sm:text-base">
        {description}
      </p>
    </section>
  );
}
