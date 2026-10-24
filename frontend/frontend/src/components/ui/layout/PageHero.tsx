type Props = { title: string; description: string };

export function PageHero({ title, description }: Props) {
  return (
    <section className="bg-blue-600 px-6 py-14 text-center text-white">
      <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
      <p className="mx-auto mt-4 max-w-3xl text-base leading-relaxed text-blue-50">{description}</p>
    </section>
  );
}
