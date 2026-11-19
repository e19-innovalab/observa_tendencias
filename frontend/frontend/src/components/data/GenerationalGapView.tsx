import Link from 'next/link';
import { LinesChart } from '@/components/data/LinesChart';
import { ErrorNote, Eyebrow, SourceLine } from '@/components/data/ui';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ApiError } from '@/lib/api/client';
import { getGenerationalGap } from '@/lib/api/generational';
import { getCountries } from '@/lib/api/panorama';
import type { GenerationalGap } from '@/lib/schemas/generational';
import { formatValue } from '@/lib/utils/format';

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Brecha generacional: desocupación joven dividida por la del total, por país y año. */
export async function GenerationalGapView() {
  let gap: GenerationalGap;
  let countries;
  try {
    [gap, countries] = await Promise.all([getGenerationalGap(), getCountries()]);
  } catch (e) {
    return (
      <ErrorNote
        message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
      />
    );
  }

  const names = Object.fromEntries(countries.map((country) => [country.iso3, country.name_es]));
  if (!gap.countries.some((country) => country.latest)) {
    return (
      <p className="rounded-xl border border-dashed border-card-border bg-rail px-4 py-24 text-center text-sm text-muted-text">
        Todavía no hay datos de la brecha generacional.
      </p>
    );
  }

  return <GenerationalGapSection gap={gap} names={names} />;
}

function GenerationalGapSection({
  gap,
  names,
}: {
  gap: GenerationalGap;
  names: Record<string, string>;
}) {
  const withData = gap.countries
    .filter((country) => country.latest)
    .sort((a, b) => b.latest!.ratio - a.latest!.ratio);
  const series = withData.map((country) => ({
    key: country.country_iso3,
    label: names[country.country_iso3] ?? country.country_iso3,
    color: COUNTRY_COLORS[country.country_iso3] ?? FALLBACK_COLOR,
    points: country.points.map((point) => ({
      period: String(point.year),
      start: `${point.year}-01-01`,
      value: point.ratio,
    })),
  }));

  return (
    <section aria-labelledby="brecha-generacional" className="flex flex-col gap-4">
      <div>
        <Eyebrow>
          {gap.youth.name} sobre {gap.total.name.toLowerCase()}
        </Eyebrow>
        <h1 id="brecha-generacional" className="mt-1 text-xl font-bold text-heading">
          {gap.title}
        </h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-body">{gap.description}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {withData.map((country) => (
          <div key={country.country_iso3} className="rounded-xl border border-card-border p-4">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-semibold text-heading">
                {names[country.country_iso3] ?? country.country_iso3}
              </span>
              <span
                className="text-3xl font-bold tabular-nums"
                style={{ color: COUNTRY_COLORS[country.country_iso3] ?? FALLBACK_COLOR }}
              >
                {one.format(country.latest!.ratio)}×
              </span>
            </div>
            <p className="mt-2 text-sm text-body">{country.headline}</p>
            <p className="mt-1.5 text-xs text-muted-text">
              Jóvenes {formatValue(country.latest!.youth, gap.youth.unit)} · todos{' '}
              {formatValue(country.latest!.total, gap.total.unit)}
              {country.points.length > 1 &&
                ` · en ${country.points[0].year} era ${one.format(country.points[0].ratio)}×`}
            </p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs text-muted-text">
          Desocupación joven dividida por la general, por año (1 = sin brecha).
        </p>
        <LinesChart series={series} unit="ratio" ariaLabel="Brecha generacional por país y año" />
        <SourceLine
          source={`Fuente: ${gap.source ?? '—'} · ${gap.youth.name} y ${gap.total.name.toLowerCase()}, de las mismas encuestas de hogares`}
        >
          <Link href="/metodologia/indicadores" className="text-link hover:underline">
            ¿Qué mide?
          </Link>
        </SourceLine>
      </div>
    </section>
  );
}
