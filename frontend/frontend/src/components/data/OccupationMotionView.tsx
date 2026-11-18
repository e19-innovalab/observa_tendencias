import Link from 'next/link';
import { MotionChart } from '@/components/data/MotionChart';
import { ErrorNote, Eyebrow, SourceLine } from '@/components/data/ui';
import { UrlSeg } from '@/components/data/UrlSeg';
import { ApiError } from '@/lib/api/client';
import { getMotion } from '@/lib/api/motion';
import { getCountries } from '@/lib/api/panorama';

type SearchParams = { burbujas?: string };

/** Burbujas animadas por gran grupo de ocupaciones y país. */
export async function OccupationMotionView({ sp }: { sp: SearchParams }) {
  let motion, countries;
  try {
    [motion, countries] = await Promise.all([getMotion(sp.burbujas), getCountries()]);
  } catch (e) {
    return (
      <ErrorNote
        message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
      />
    );
  }

  const names = Object.fromEntries(countries.map((country) => [country.iso3, country.name_es]));
  if (motion.points.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-card-border bg-rail px-4 py-24 text-center text-sm text-muted-text">
        Todavía no hay datos de las ocupaciones en movimiento.
      </p>
    );
  }

  return (
    <section className="flex flex-col gap-4" aria-labelledby="motion-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex max-w-3xl flex-col gap-1">
          <Eyebrow>
            Por grandes grupos de ocupaciones · {motion.years[0]}–{motion.years.at(-1)}
          </Eyebrow>
          <h1 id="motion-title" className="text-xl font-semibold text-heading">
            {motion.title}
          </h1>
          <p className="text-sm leading-relaxed text-body">
            {[motion.description, motion.y.description].filter(Boolean).join(' ')}
          </p>
        </div>
        <UrlSeg
          name="burbujas"
          label="Eje vertical"
          value={motion.y.key === motion.y_options[0]?.key ? '' : motion.y.key}
          options={motion.y_options.map((option, index) => ({
            value: index === 0 ? '' : option.key,
            label: option.short_label ?? option.label,
          }))}
          reset={[]}
        />
      </div>

      <MotionChart key={motion.y.key} data={motion} names={names} />

      <SourceLine source="Fuentes: ILOSTAT, SIMEL (INE Chile) y OIT (2025)">
        <Link href="/metodologia/ise" className="text-link hover:underline">
          ¿Cómo se calcula el ISE?
        </Link>
      </SourceLine>

      <ul className="flex flex-col gap-1 text-xs leading-relaxed text-muted-text">
        {motion.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
