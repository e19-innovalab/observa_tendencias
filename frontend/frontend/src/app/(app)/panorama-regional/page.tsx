import type { Metadata } from 'next';
import Link from 'next/link';
import { io } from 'next/cache';
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import { CountryFilter } from '@/components/data/CountryFilter';
import { ChipGroup, CountTabs, PillGroup } from '@/components/data/UrlControls';
import { YearRange } from '@/components/data/YearRange';
import { LinesChart, type LineSeries } from '@/components/data/LinesChart';
import { ChartCard } from '@/components/ui/charts/ChartCard';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ApiErrorNote } from '@/components/ui/feedback/ApiErrorNote';
import { FilterLabel, FilterPanel } from '@/components/ui/filters/FilterPanel';
import { KpiCard, type KpiTone } from '@/components/ui/indicators/KpiCard';
import { PageHero } from '@/components/ui/layout/PageHero';
import { Eyebrow } from '@/components/data/ui';
import { ApiError } from '@/lib/api/client';
import { getGraduateTotals } from '@/lib/api/graduatesExtended';
import {
  getCompare,
  getCountries,
  getIndicators,
  getObservations,
  getProjections,
  getTrends,
} from '@/lib/api/panorama';
import type { Indicator, ObservationPoint } from '@/lib/schemas/api';
import { formatChange, formatDate, formatValue } from '@/lib/utils/format';
import { cn } from '@/lib/utils';

export const metadata: Metadata = { title: 'Panorama Regional' };

type SearchParams = {
  tab?: string;
  indicator?: string;
  country?: string;
  freq?: string;
  proy?: string;
  desde?: string;
  hasta?: string;
  /** Variante de moneda de los indicadores de ingreso: 'usd' | 'ppp'. */
  moneda?: string;
  /** Variante de género del ingreso laboral: 'f' | 'm'. */
  genero?: string;
};

const FREQ_LABELS: Record<string, string> = { A: 'Anual', Q: 'Trimestral', M: 'Mensual' };
const FREQ_ORDER = ['A', 'Q', 'M'];
const DOTS: Record<string, string> = {
  ARG: 'bg-country-arg',
  CHL: 'bg-country-chl',
  URY: 'bg-country-ury',
};
const BADGE: Record<string, string> = {
  favorable: 'border-alert-positive-border bg-alert-positive-bg text-alert-positive-text',
  unfavorable: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text',
  neutral: 'border-card-border bg-surface-2 text-muted-text',
};
const GRADUATE_SOURCES = 'Mi Futuro (Chile), Anuario DIU (Argentina) y MEC (Uruguay)';

/** Indicadores que no se listan en esta pantalla (siguen existiendo en la API). */
const HIDDEN_INDICATORS = new Set([
  // Vive en /genero.
  'employment_women',
  // Se prefiere la serie del Banco Mundial; la de encuestas no aporta otra lectura acá.
  'youth_unemployment_rate_survey',
]);

/**
 * Indicadores «por país»: se leen de a un país a la vez, aunque el filtro global diga
 * «Todos». Con «Todos» se usa el primer país de la lista para no mezclar realidades.
 */
const PER_COUNTRY_KEYS = new Set(['mean_monthly_earnings_by_country', 'earnings_tertiary']);

type CatalogOption = { value: string; code: string; label: string };
type CatalogEntry = {
  key: string;
  name: string;
  domain: string;
  domain_label: string;
  kind: 'single' | 'currency' | 'gender' | 'graduates';
  code?: string;
  options?: CatalogOption[];
  unit?: string;
  description?: string | null;
  higher_is_better?: boolean | null;
};

type MergedGroup = {
  key: string;
  name: string;
  kind: 'currency' | 'gender';
  options: CatalogOption[];
};

/**
 * Grupos de indicadores que la API publica por separado y acá se muestran como uno solo:
 * el usuario elige la variante (moneda o género) y ve una única serie.
 */
const MERGED_GROUPS: MergedGroup[] = [
  {
    key: 'mean_monthly_earnings_by_country',
    name: 'Ingreso laboral mensual promedio por país',
    kind: 'currency',
    options: [
      { value: 'ppp', code: 'mean_monthly_earnings_ppp', label: 'USD PPA' },
      { value: 'usd', code: 'mean_monthly_earnings_usd', label: 'USD' },
    ],
  },
  {
    key: 'mean_monthly_earnings_by_gender',
    name: 'Ingreso laboral mensual promedio por género (USD PPA)',
    kind: 'gender',
    options: [
      { value: 'f', code: 'mean_monthly_earnings_ppp_women', label: 'Mujeres' },
      { value: 'm', code: 'mean_monthly_earnings_ppp_men', label: 'Varones' },
    ],
  },
  {
    key: 'earnings_tertiary',
    name: 'Ingreso laboral mensual con educación superior',
    kind: 'currency',
    options: [
      { value: 'ppp', code: 'earnings_tertiary_ppp', label: 'USD PPA' },
      { value: 'usd', code: 'earnings_tertiary_usd', label: 'USD' },
    ],
  },
];

const MERGED_BY_CODE = new Map<string, MergedGroup>();
for (const group of MERGED_GROUPS) {
  for (const option of group.options) MERGED_BY_CODE.set(option.code, group);
}

function entryFromIndicator(indicator: Indicator): CatalogEntry {
  return {
    key: indicator.code,
    name: indicator.name,
    domain: indicator.domain,
    domain_label: indicator.domain_label,
    kind: 'single',
    code: indicator.code,
    unit: indicator.unit,
    description: indicator.description,
    higher_is_better: indicator.higher_is_better,
  };
}

/** Catálogo visible: oculta indicadores y reemplaza los grupos por una entrada única. */
function buildCatalog(indicators: Indicator[]): CatalogEntry[] {
  const catalog: CatalogEntry[] = [];
  const merged = new Set<string>();

  for (const indicator of indicators) {
    if (HIDDEN_INDICATORS.has(indicator.code)) continue;

    const group = MERGED_BY_CODE.get(indicator.code);
    if (group) {
      if (merged.has(group.key)) continue;
      merged.add(group.key);
      catalog.push({
        key: group.key,
        name: group.name,
        domain: indicator.domain,
        domain_label: indicator.domain_label,
        kind: group.kind,
        options: group.options,
        unit: group.kind === 'gender' ? 'ppp_usd_month' : undefined,
        higher_is_better: true,
      });
      continue;
    }

    catalog.push(entryFromIndicator(indicator));
  }

  // Totales de titulados: existe /graduates/totals en el backend, pero no como indicador.
  const education = catalog.find((entry) => entry.domain === 'education');
  if (education && !catalog.some((entry) => entry.key === 'graduate_totals')) {
    catalog.push({
      key: 'graduate_totals',
      name: 'Titulados totales por país y año',
      domain: 'education',
      domain_label: education.domain_label,
      kind: 'graduates',
      unit: 'persons',
      description:
        'Titulados observados por país y año, sumando las carreras que publica cada fuente oficial.',
      higher_is_better: true,
    });
  }

  return catalog;
}

/** Busca por la clave visible o por el código de una de sus variantes (enlaces viejos). */
function resolveEntry(catalog: CatalogEntry[], key?: string) {
  if (!key) return undefined;
  const direct = catalog.find((entry) => entry.key === key);
  if (direct) return { entry: direct, variant: undefined as string | undefined };
  for (const entry of catalog) {
    const option = entry.options?.find((item) => item.code === key);
    if (option) return { entry, variant: option.value };
  }
  return undefined;
}

function variantFor(entry: CatalogEntry, sp: SearchParams, alias?: string) {
  if (!entry.options?.length) return undefined;
  const requested = entry.kind === 'currency' ? sp.moneda : sp.genero;
  return (
    entry.options.find((option) => option.value === requested)?.value ??
    (alias && entry.options.some((option) => option.value === alias) ? alias : undefined) ??
    entry.options[0].value
  );
}

function average(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/** Verde si el cambio va en la dirección deseable; ámbar/rojo si no. */
function toneFor(change: number | null, higherIsBetter: boolean | null, unit: string): KpiTone {
  if (change === null || higherIsBetter === null || change === 0) return 'neutral';
  const good = change > 0 === higherIsBetter;
  if (good) return 'positive';
  return unit === 'percent' ? 'warning' : 'negative';
}

export default async function PanoramaRegionalPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  await io(); // KPIs y series se calculan por request, no en el shell estático
  const sp = await searchParams;
  const thisYear = new Date().getFullYear();

  let countries: Awaited<ReturnType<typeof getCountries>> = [];
  let indicators: Indicator[] = [];
  try {
    [countries, indicators] = await Promise.all([getCountries(), getIndicators()]);
  } catch (error) {
    return (
      <>
        <PageHero
          title="Panorama Regional"
          description="Analiza y compara la evolución de indicadores socioeconómicos, laborales y educativos en Argentina, Chile y Uruguay a través de datos históricos y proyecciones."
        />
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <ApiErrorNote
            message={error instanceof ApiError ? error.message : 'Error inesperado al cargar los datos.'}
          />
        </div>
      </>
    );
  }

  const byCode = new Map(indicators.map((indicator) => [indicator.code, indicator]));
  const catalog = buildCatalog(indicators);

  // Secciones = dominios que devuelve el backend.
  const domains: { id: string; label: string; count: number }[] = [];
  for (const entry of catalog) {
    const existing = domains.find((domain) => domain.id === entry.domain);
    if (existing) existing.count += 1;
    else domains.push({ id: entry.domain, label: entry.domain_label, count: 1 });
  }

  const byParam = resolveEntry(catalog, sp.indicator);
  const tab = domains.some((domain) => domain.id === sp.tab)
    ? sp.tab!
    : (byParam?.entry.domain ?? domains[0]?.id ?? '');
  const inDomain = catalog.filter((entry) => entry.domain === tab);
  const picked = byParam && byParam.entry.domain === tab ? byParam : undefined;
  const entry = picked?.entry ?? inDomain[0];

  if (!entry) {
    return (
      <>
        <PageHero
          title="Panorama Regional"
          description="Analiza y compara la evolución de indicadores socioeconómicos, laborales y educativos en Argentina, Chile y Uruguay a través de datos históricos y proyecciones."
        />
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <p className="rounded-xl border border-dashed border-card-border px-4 py-16 text-center text-[12.5px] text-muted-text">
            No hay indicadores disponibles.
          </p>
        </div>
      </>
    );
  }

  const variant = variantFor(entry, sp, picked?.variant);
  const variantOption = entry.options?.find((option) => option.value === variant);
  const variantLabel = variantOption?.label;
  const code =
    entry.kind === 'single'
      ? entry.code
      : entry.kind === 'graduates'
        ? undefined
        : variantOption?.code;
  const resolvedIndicator = code ? byCode.get(code) : undefined;
  const unit = resolvedIndicator?.unit ?? entry.unit ?? '';
  const description = resolvedIndicator?.description ?? entry.description ?? null;

  const codeFor = (item: CatalogEntry) => {
    if (item.key === entry.key) return code;
    if (item.kind === 'single') return item.code;
    const value = variantFor(item, sp);
    return item.options?.find((option) => option.value === value)?.code;
  };

  const selectedCountries =
    sp.country && sp.country !== 'all'
      ? [sp.country]
      : countries.map((country) => country.iso3);
  const fromYear = sp.desde ?? String(thisYear - 10);
  const toYear = sp.hasta;

  let observations: ObservationPoint[] = [];
  let compare: Awaited<ReturnType<typeof getCompare>> | null = null;
  let projections: Awaited<ReturnType<typeof getProjections>> | null = null;
  let trends: Awaited<ReturnType<typeof getTrends>> = [];
  let kpiCompares: (Awaited<ReturnType<typeof getCompare>> | null)[] = [];
  let graduateTotals: Awaited<ReturnType<typeof getGraduateTotals>> | null = null;
  let dataError = '';

  const kpiEntries = inDomain.filter((item) => item.kind !== 'graduates').slice(0, 4);
  const kpiCodes = kpiEntries.map(codeFor);
  const kpiCountries = kpiEntries.map(countriesFor);
  const kpiPromise = Promise.all(
    kpiCodes.map((itemCode, index) =>
      itemCode
        ? getCompare(itemCode, kpiCountries[index]).catch(() => null)
        : Promise.resolve(null),
    ),
  );

  try {
    if (entry.kind === 'graduates') {
      const [totals, kpiCmp] = await Promise.all([getGraduateTotals(), kpiPromise]);
      graduateTotals = totals;
      kpiCompares = kpiCmp;
    } else if (code) {
      const [obs, cmp, proj, tr, kpiCmp] = await Promise.all([
        getObservations({
          indicator: code,
          countries: selectedCountries,
          fromYear,
          toYear,
        }),
        getCompare(code, selectedCountries),
        getProjections(code, selectedCountries, undefined, fromYear, toYear).catch(() => null),
        getTrends(code, selectedCountries).catch(() => []),
        kpiPromise,
      ]);
      observations = obs.items;
      compare = cmp;
      projections = proj;
      trends = tr;
      kpiCompares = kpiCmp;
    }
  } catch (error) {
    dataError = error instanceof ApiError ? error.message : 'Error inesperado al cargar la serie.';
  }

  const names = Object.fromEntries(countries.map((country) => [country.iso3, country.name_es]));
  const totals = observations.filter(
    (item) => item.sector_code === null && item.occupation_code === null,
  );
  const base = totals.length ? totals : observations;

  const frequencies =
    entry.kind === 'graduates'
      ? ['A']
      : FREQ_ORDER.filter((freq) => base.some((item) => item.frequency === freq));
  const frequency =
    sp.freq && frequencies.includes(sp.freq)
      ? sp.freq
      : frequencies.includes('A')
        ? 'A'
        : (frequencies[0] ?? 'A');
  const showProjection = entry.kind !== 'graduates' && sp.proy !== 'off' && !toYear;

  const series: LineSeries[] =
    entry.kind === 'graduates'
      ? graduateTotals
        ? countries
            .filter((country) => selectedCountries.includes(country.iso3))
            .map((country) => {
              const row = graduateTotals!.paises.find((item) => item.pais === country.iso3);
              const points = row
                ? Object.entries(row.por_anio)
                    .map(([year, value]) => ({ period: year, start: `${year}-01-01`, value }))
                    .filter(
                      (point) =>
                        (!fromYear || Number(point.period) >= Number(fromYear)) &&
                        (!toYear || Number(point.period) <= Number(toYear)),
                    )
                    .sort((a, b) => a.start.localeCompare(b.start))
                : [];
              return {
                key: country.iso3,
                label: country.name_es,
                color: COUNTRY_COLORS[country.iso3] ?? FALLBACK_COLOR,
                points,
              };
            })
            .filter((item) => item.points.length > 0)
        : []
      : countries
          .filter((country) => selectedCountries.includes(country.iso3))
          .map((country) => {
            const points = base
              .filter((item) => item.country_iso3 === country.iso3 && item.frequency === frequency)
              .sort((a, b) => a.period_start.localeCompare(b.period_start))
              .map((item) => ({ period: item.period, start: item.period_start, value: item.value }));
            return {
              key: country.iso3,
              label: country.name_es,
              color: COUNTRY_COLORS[country.iso3] ?? FALLBACK_COLOR,
              points,
              projected: showProjection
                ? ((projections?.items.find((item) => item.country_iso3 === country.iso3)?.projected ??
                    [])
                    .filter((point) => point.frequency === frequency)
                    .map((point) => ({
                      period: point.period,
                      start: point.period_start,
                      value: point.value,
                      lower: point.lower_bound,
                      upper: point.upper_bound,
                    })))
                : [],
            };
          })
          .filter((item) => item.points.length > 0);

  const hasProjection = series.some((item) => item.projected?.length);

  // Tarjetas KPI: promedio regional de los indicadores del grupo activo.
  const kpiCards = kpiEntries.flatMap((item, index) => {
    const data = kpiCompares[index];
    if (!data) return [];
    const itemCode = kpiCodes[index];
    const itemUnit = (itemCode ? byCode.get(itemCode)?.unit : undefined) ?? item.unit ?? '';
    const itemHigherIsBetter =
      (itemCode ? byCode.get(itemCode)?.higher_is_better : undefined) ?? item.higher_is_better ?? null;
    const value = average(data.items.flatMap((row) => (row.current ? [row.current.value] : [])));
    if (value === null) return [];
    const change = average(data.items.flatMap((row) => (row.change === null ? [] : [row.change])));
    const periods = data.items
      .flatMap((row) => (row.current ? [row.current.period] : []))
      .sort();
    const year = periods.at(-1)?.slice(0, 4) ?? '';
    const itemVariant = item.options?.find(
      (option) => option.value === (item.key === entry.key ? variant : variantFor(item, sp)),
    )?.label;
    return [
      {
        label: itemVariant ? `${item.name} · ${itemVariant}` : item.name,
        value: formatValue(value, itemUnit),
        year,
        codes: (kpiCountries[index] ?? []).join(', '),
        changeText:
          change === null
            ? null
            : formatChange(change, data.items[0]?.change_kind ?? 'absolute', itemUnit),
        tone: toneFor(change, itemHigherIsBetter, itemUnit),
      },
    ];
  });

  // Último dato y lectura por país. Con rango de años elegido se calcula sobre la serie
  // recortada; si no, se usa /compare (que siempre trae el último dato publicado).
  const custom = Boolean(sp.desde || sp.hasta);
  const rows =
    entry.kind === 'graduates' || custom
      ? series.map((item) => {
          const last = item.points[item.points.length - 1];
          const prev = item.points[item.points.length - 2];
          const diff =
            last && prev
              ? unit === 'percent'
                ? last.value - prev.value
                : prev.value
                  ? ((last.value - prev.value) / Math.abs(prev.value)) * 100
                  : null
              : null;
          return {
            iso: item.key,
            value: last?.value ?? null,
            period: last?.period ?? null,
            prevPeriod: prev?.period ?? null,
            change: diff,
            changeText:
              diff !== null
                ? formatChange(diff, unit === 'percent' ? 'absolute' : 'relative', unit)
                : null,
          };
        })
      : (compare?.items ?? []).map((item) => ({
          iso: item.country_iso3,
          value: item.current?.value ?? null,
          period: item.current?.period ?? null,
          prevPeriod: item.previous?.period ?? null,
          change: item.change,
          changeText:
            item.change !== null && item.previous
              ? formatChange(item.change, item.change_kind, unit)
              : null,
        }));
 
  // Los «por país» con «Todos» muestran el primero: conviene decirlo para que no parezca un error.
  const fallbackCountry =
    PER_COUNTRY_KEYS.has(entry.key) && !countryFilter
      ? countries.find((country) => country.iso3 === selectedCountries[0])
      : undefined;

  const latest = rows.filter((row) => row.value !== null);
  const top = [...latest].sort((a, b) => b.value! - a.value!)[0];
  const moved = [...rows]
    .filter((row) => row.change !== null)
    .sort((a, b) => Math.abs(b.change!) - Math.abs(a.change!))[0];
  const takeaway = [
    top &&
      latest.length > 1 &&
      `${names[top.iso] ?? top.iso} tiene el valor más alto de los ${latest.length === 3 ? 'tres' : latest.length} (${formatValue(top.value!, unit)} en ${top.period}).`,
    moved &&
      moved.changeText &&
      (latest.length > 1
        ? `El mayor cambio es el de ${names[moved.iso] ?? moved.iso}: ${moved.changeText} respecto de ${moved.prevPeriod}.`
        : fallbackCountry
          ? `La serie de ${names[moved.iso] ?? moved.iso} cambió ${moved.changeText} respecto de ${moved.prevPeriod}.`
          : `Solo ${names[moved.iso] ?? moved.iso} tiene datos: ${moved.changeText}.`),
  ]
    .filter(Boolean)
    .join(' ');

  const withTrend = entry.kind === 'graduates' ? [] : trends.filter((trend) => trend.trend_state !== 'insufficient_data');
  const sourcedAt =
    entry.kind === 'graduates'
      ? null
      : formatDate(
          base.map((item) => item.source_updated_at ?? item.fetched_at).sort().at(-1) ?? null,
        );
  const sourceName =
    entry.kind === 'graduates'
      ? GRADUATE_SOURCES
      : [...new Set(base.map((item) => item.source.name))].join(', ') || null;

  // Tabla y CSV del gráfico: una fila por período.
  const periods = [
    ...new Set(
      series.flatMap((item) =>
        [...item.points, ...(item.projected ?? [])].map((point) => point.period),
      ),
    ),
  ].sort();
  const table = {
    columns: ['Período', ...series.map((item) => item.label)],
    rows: periods.map((period) => [
      period,
      ...series.map((item) => {
        const point = [...item.points, ...(item.projected ?? [])].find(
          (candidate) => candidate.period === period,
        );
        return point ? formatValue(point.value, unit) : '—';
      }),
    ]),
  };

  const chartSubtitle =
    [
      description,
      entry.kind === 'gender' && variantLabel ? `Mostrando: ${variantLabel}.` : null,
      fallbackCountry
        ? `Con «Todos» se muestra ${fallbackCountry.name_es}; elegí otro país para cambiar la serie.`
        : null,
    ]
      .filter(Boolean)
      .join(' ') || undefined;

  const controls =
    entry.kind !== 'graduates' || entry.options?.length ? (
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-card-border/70 py-2.5">
        {entry.options?.length && (
          <div className="flex flex-wrap items-center gap-2">
            <FilterLabel>{entry.kind === 'currency' ? 'Moneda' : 'Género'}</FilterLabel>
            <PillGroup
              name={entry.kind === 'currency' ? 'moneda' : 'genero'}
              label={entry.kind === 'currency' ? 'Moneda' : 'Género'}
              options={entry.options.map((option) => ({
                value: option.value,
                label: option.label,
              }))}
              value={variant ?? ''}
              reset={['page']}
            />
          </div>
        )}

        {entry.kind !== 'graduates' && (
          <>
            <span className="hidden h-4 w-px bg-card-border sm:block" aria-hidden />
            <div className="flex items-center gap-2">
              <FilterLabel>Proyección</FilterLabel>
              <div className="inline-flex rounded-lg bg-surface-2 p-0.5">
                <ProjLink href={projHref(sp, '')} active={sp.proy !== 'off'}>
                  Activa
                </ProjLink>
                <ProjLink href={projHref(sp, 'off')} active={sp.proy === 'off'}>
                  Ocultar
                </ProjLink>
              </div>
            </div>
          </>
        )}

        {frequencies.length > 1 && (
          <>
            <span className="hidden h-4 w-px bg-card-border sm:block" aria-hidden />
            <div className="flex flex-wrap items-center gap-2">
              <FilterLabel>Frecuencia</FilterLabel>
              {frequencies.map((freq) => (
                <FreqLink
                  key={freq}
                  href={freqHref(sp, freq, frequency)}
                  active={freq === frequency}
                >
                  {FREQ_LABELS[freq] ?? freq}
                </FreqLink>
              ))}
            </div>
          </>
        )}
      </div>
    ) : undefined;

  return (
    <>
      <PageHero
        title="Panorama Regional"
        description="Analiza y compara la evolución de indicadores socioeconómicos, laborales y educativos en Argentina, Chile y Uruguay a través de datos históricos y proyecciones."
      />

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <FilterPanel>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <FilterLabel>Países</FilterLabel>
              <CountryFilter countries={countries} value={sp.country ?? ''} reset={['page']} />
            </div>
            <YearRange years={Array.from({ length: 30 }, (_, i) => thisYear - i)} desde={sp.desde} hasta={sp.hasta} />
          </div>

          <div className="mt-4">
            <CountTabs
              name="tab"
              label="Grupo de indicadores"
              options={domains.map((domain) => ({
                value: domain.id,
                label: domain.label,
                count: domain.count,
              }))}
              value={tab}
              reset={['indicator', 'page']}
            />
          </div>

          <div className="mt-3.5">
            <ChipGroup
              name="indicator"
              label="Indicadores"
              hideLabel
              allLabel="Ver todos"
              options={inDomain.map((item) => ({ value: item.key, label: item.name }))}
              value={entry.key}
              reset={['page']}
              maxRows={2}
            />
          </div>
        </FilterPanel>

        {dataError && (
          <div className="mt-4">
            <ApiErrorNote message={dataError} />
          </div>
        )}

        {kpiCards.length > 0 && (
          <section aria-label="Indicadores del grupo" className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {kpiCards.map((kpi) => (
              <KpiCard
                key={kpi.label}
                label={kpi.label}
                value={kpi.value}
                year={kpi.year}
                codes={kpi.codes}
                changeText={kpi.changeText}
                tone={kpi.tone}
              />
            ))}
          </section>
        )}

        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <ChartCard
            title={entry.name}
            subtitle={chartSubtitle}
            legend={series.map((item) => ({ label: item.label, color: item.color }))}
            sourceName={sourceName}
            updatedAt={sourcedAt}
            methodologyHref="/metodologia/tendencias"
            downloadName={`${code ?? entry.key}-${frequency}.csv`}
            table={table}
            controls={controls}
          >
            {series.length ? (
              <LinesChart
                key={`${code ?? entry.key}-${frequency}-${series.length}-${variant ?? ''}`}
                series={series}
                unit={unit}
                mode={hasProjection ? 'focus' : 'toggle'}
                ariaLabel={`${entry.name} en ${series.map((item) => item.label).join(', ')}`}
              />
            ) : (
              <p className="py-16 text-center text-[12.5px] text-muted-text">
                No hay datos observados para esta combinación de filtros. Probá con otro período o
                país.
              </p>
            )}
          </ChartCard>

          <aside className="flex flex-col gap-4 rounded-xl border border-card-border bg-rail p-4">
            <section aria-labelledby="ultimo-dato">
              <div className="flex items-center justify-between gap-2">
                <Eyebrow>Último dato</Eyebrow>
                <span className="text-[10.5px] font-medium text-muted-text">
                  {latest[0]?.period?.slice(0, 4) ?? String(thisYear)}
                </span>
              </div>
              <ul id="ultimo-dato" className="mt-2.5 space-y-2.5">
                {latest.map((row) => (
                  <li key={row.iso} className="flex items-center gap-2">
                    <span className={cn('size-2.5 rounded-full', DOTS[row.iso] ?? 'bg-brand')} aria-hidden />
                    <span className="min-w-0 truncate text-[12.5px] text-body">{names[row.iso] ?? row.iso}</span>
                    <span className="ml-auto text-[13px] font-bold text-heading">
                      {formatValue(row.value!, unit)}
                    </span>
                    {row.changeText && (
                      <span
                        className={cn(
                          'inline-flex items-center gap-0.5 rounded-md border px-1 py-0.5 text-[10px] font-bold',
                          row.change !== null && row.change < 0
                            ? 'border-danger/25 bg-danger-soft text-danger'
                            : 'border-success/25 bg-success-soft text-success',
                        )}
                      >
                        {row.change !== null && row.change < 0 ? (
                          <ArrowDownRight className="size-2.5" aria-hidden />
                        ) : (
                          <ArrowUpRight className="size-2.5" aria-hidden />
                        )}
                        {row.changeText}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              {takeaway && (
                <p className="mt-3 text-[11px] leading-relaxed text-body">{takeaway}</p>
              )}
            </section>

            {withTrend.length > 0 && (
              <section aria-labelledby="tendencia-reciente" className="border-t border-card-border pt-3">
                <Eyebrow>Tendencia reciente</Eyebrow>
                <div id="tendencia-reciente" className="mt-2 space-y-2">
                  {withTrend.map((trend) => {
                    const end = series
                      .find((item) => item.key === trend.country_iso3)
                      ?.projected?.at(-1);
                    return (
                      <article
                        key={trend.country_iso3}
                        className="rounded-lg border border-card-border bg-canvas p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="flex items-center gap-2 text-[12.5px] font-semibold text-heading">
                            <span
                              className={cn('size-2 rounded-full', DOTS[trend.country_iso3] ?? 'bg-brand')}
                              aria-hidden
                            />
                            {names[trend.country_iso3] ?? trend.country_iso3}
                          </span>
                          {trend.assessment_label && (
                            <span
                              className={cn(
                                'rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                                BADGE[trend.assessment ?? 'neutral'] ?? BADGE.neutral,
                              )}
                            >
                              {trend.assessment_label}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-[11.5px] text-body">
                          {trend.trend_state_label}
                          {trend.window_start && (
                            <span className="text-muted-text">
                              {' '}
                              ({trend.window_start}–{trend.window_end})
                            </span>
                          )}
                        </p>
                        {end && (
                          <p className="mt-0.5 text-[10.5px] leading-relaxed text-muted-text">
                            Proyección {end.period}:{' '}
                            <span className="font-semibold text-body">
                              {formatValue(end.value, unit)}
                            </span>
                            {end.lower != null && end.upper != null
                              ? ` (entre ${formatValue(end.lower, unit)} y ${formatValue(end.upper, unit)})`
                              : ''}
                          </p>
                        )}
                      </article>
                    );
                  })}
                </div>
                {hasProjection && (
                  <p className="mt-3 border-t border-card-border pt-3 text-[10px] leading-relaxed text-muted-text italic">
                    La proyección prolonga la tendencia histórica: no anticipa cambios de política ni
                    shocks.
                  </p>
                )}
              </section>
            )}

            <Link
              href="/alertas"
              className="inline-flex items-center gap-1 border-t border-card-border pt-3 text-[12px] font-semibold text-link hover:text-link-hover hover:underline"
            >
              Ver alertas
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </aside>
        </div>
      </div>
    </>
  );
}

function projHref(sp: SearchParams, value: string) {
  const params = new URLSearchParams();
  for (const [key, param] of Object.entries(sp)) {
    if (key !== 'proy' && param) params.set(key, param);
  }
  if (value) params.set('proy', value);
  const query = params.toString();
  return query ? `?${query}` : '?';
}

function freqHref(sp: SearchParams, value: string, current: string) {
  const params = new URLSearchParams();
  for (const [key, param] of Object.entries(sp)) {
    if (key !== 'freq' && param) params.set(key, param);
  }
  if (value !== current) params.set('freq', value);
  const query = params.toString();
  return query ? `?${query}` : '?';
}

function ProjLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      scroll={false}
      aria-pressed={active}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11.5px] font-semibold transition-colors',
        active ? 'bg-canvas text-brand shadow-sm' : 'text-muted-text hover:text-heading',
      )}
    >
      {active && <span className="size-1.5 rounded-full bg-brand" aria-hidden />}
      {children}
    </Link>
  );
}

function FreqLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      scroll={false}
      aria-pressed={active}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11.5px] font-semibold transition-colors',
        active
          ? 'border-brand bg-canvas text-brand'
          : 'border-transparent text-muted-text hover:text-heading',
      )}
    >
      {active && <span className="size-1.5 rounded-full bg-brand" aria-hidden />}
      {children}
    </Link>
  );
}
