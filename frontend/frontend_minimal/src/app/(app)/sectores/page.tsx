import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, RailCard, SourceLine, Stat, buttonCls } from '@/components/minimal/ui';
import { Term } from '@/components/minimal/Term';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { DEFAULT_SECTOR_STYLE, SECTOR_STYLE } from '@/components/sectors/sectorIcons';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/common';
import { getSectorSummaries } from '@/lib/api/employability';
import { formatIndex, formatPoints, formatScore, formatUnit, formatUsd } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Sectores' };
type SearchParams = { country?: string; year?: string; sector?: string };
const YEARS_OFFERED = 3;

export default function SectoresPage({ searchParams }: PageProps<'/sectores'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SectoresContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

async function SectoresContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  let data, countries;
  try {
    [data, countries] = await Promise.all([getSectorSummaries({ country: sp.country, year: sp.year }), getCountries()]);
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const items = [...data.items].sort((a, b) => (b.average_score ?? -1) - (a.average_score ?? -1));
  const selected = items.find((s) => s.sector_code === sp.sector) ?? items[0];
  const avg = data.regional_average;
  const scope = sp.country ? names[sp.country] ?? sp.country : 'los 3 países';
  const years = data.available_years.slice(-YEARS_OFFERED).map((y) => ({ value: String(y), label: String(y) }));
  const href = (code: string) => {
    const q = new URLSearchParams({ ...(sp.country ? { country: sp.country } : {}), ...(sp.year ? { year: sp.year } : {}), sector: code });
    return `/sectores?${q}`;
  };

  return (
    <Page>
      <ChartHeader
        eyebrow={`Índice de empleabilidad (ISE) · ${data.year ?? ''} · ${scope}`}
        title="¿Qué sector ofrece mejor empleabilidad?"
        subtitle={`Promedio del ISE (0 a 100) de las ocupaciones de cada sector. La marca gris es ${data.year ? data.year - 1 : 'el año anterior'}.`}
        controls={
          <>
            <UrlSeg name="country" label="País" value={sp.country ?? ''} options={[{ value: '', label: 'Región' }, ...countries.map((c) => ({ value: c.iso3, label: c.iso3 }))]} />
            {years.length > 1 && <UrlSeg name="year" label="Año" value={sp.year ?? String(data.year ?? '')} options={years} />}
          </>
        }
      />
      <ChartLayout
        stickyRail
        chart={
          <>
            <div className="grid grid-cols-[minmax(8rem,220px)_minmax(0,1fr)_7rem] gap-4 px-3 pb-2 text-xs text-slate-500">
              <span>Sector</span>
              <span className="flex justify-between"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></span>
              <span className="text-right">ISE · cambio</span>
            </div>
            <ul className="flex flex-col gap-1">
              {items.map((s) => {
                const on = s.sector_code === selected?.sector_code;
                const style = SECTOR_STYLE[s.sector_code] ?? DEFAULT_SECTOR_STYLE;
                const Icon = style.icon;
                return (
                  <li key={s.sector_code}>
                    <Link
                      href={href(s.sector_code)}
                      scroll={false}
                      aria-current={on ? 'true' : undefined}
                      className={`grid grid-cols-[minmax(8rem,220px)_minmax(0,1fr)_7rem] items-center gap-4 rounded-xl px-3 py-3.5 ${on ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                    >
                      <span className="flex items-center gap-2.5 text-[15px] font-semibold text-slate-900">
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md" style={{ background: style.soft, color: style.color }}><Icon className="size-4" aria-hidden /></span>
                        {s.name}
                      </span>
                      <span className="relative block h-7 rounded-md bg-slate-100">
                        {s.average_score !== null && <span className={`absolute inset-y-0 left-0 rounded-md ${on ? 'bg-blue-700' : 'bg-blue-300'}`} style={{ width: `${s.average_score}%` }} />}
                        {s.previous_average !== null && <span className="absolute -inset-y-1 w-[3px] rounded bg-slate-500" style={{ left: `calc(${s.previous_average}% - 1px)` }} title={`Año anterior: ${formatScore(s.previous_average)}`} />}
                        {avg !== null && <span className="absolute -inset-y-1.5 w-0.5 bg-slate-900" style={{ left: `${avg}%` }} />}
                      </span>
                      <span className="text-right">
                        <span className="text-xl font-bold text-slate-900">{formatScore(s.average_score)}</span>
                        {s.change !== null && <span className={`ml-1.5 text-xs ${s.change >= 0 ? 'text-green-800' : 'text-red-800'}`}>{formatPoints(s.change)?.replace(' pts', '')}</span>}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
            <p className="mx-3 mt-3 text-xs text-slate-500">
              Línea vertical oscura: promedio de todas las ocupaciones ({formatScore(avg)}). {data.no_source_note ? 'La tasa de inserción todavía no tiene fuente: su peso se reparte entre las otras dimensiones.' : ''}
            </p>
            <SourceLine source="Fuentes: ILOSTAT, SIMEL (INE Chile) y OIT (2025)">
              <Link href="/metodologia/ise" className="text-blue-700 hover:underline">¿Cómo se calcula el ISE?</Link>
            </SourceLine>
          </>
        }
        rail={
          selected && (
            <RailCard>
              <Eyebrow>Sector elegido</Eyebrow>
              <h2 className="text-[22px] font-bold text-slate-900">{selected.name}</h2>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Ocupaciones" value={String(selected.occupations)} />
                <Stat label="Nivel" value={selected.level_label ?? '—'} />
                {selected.salary_usd_average != null ? (
                  <Stat
                    label={<Term help={data.texts?.display.salary_ppp?.note ?? ''}>Salario medio</Term>}
                    value={formatUnit(selected.salary_usd_average, 'usd_month', data.texts?.unit_formats)}
                    sub={formatUnit(selected.salary_ppp_average, 'ppp_usd_month', data.texts?.unit_formats)}
                  />
                ) : (
                  <Stat label="Salario medio (PPA)" value={formatUsd(selected.salary_ppp_average)} />
                )}
                <Stat label="Exposición a la IA" value={`${formatIndex(selected.automation_average)} de 1`} />
              </div>
              {selected.top_occupation && (
                <div className="border-t border-slate-100 pt-3">
                  <p className="text-xs text-slate-500">Ocupación con mayor ISE</p>
                  <Link href={`/ocupaciones/${selected.top_occupation.occupation_code}?country=${selected.top_occupation.country_iso3}`} className="mt-1 block text-sm font-semibold leading-snug text-slate-900 hover:text-blue-800">
                    {selected.top_occupation.name}
                  </Link>
                  <p className="mt-0.5 text-[13px] text-slate-600">{names[selected.top_occupation.country_iso3]} · ISE {formatScore(selected.top_occupation.score)}</p>
                </div>
              )}
              <Link href={`/ocupaciones?${new URLSearchParams({ sector: selected.sector_code, ...(sp.year ? { year: sp.year } : {}) })}`} className={buttonCls}>
                Ver las ocupaciones del sector{data.year ? ` en ${data.year}` : ''} →
              </Link>
            </RailCard>
          )
        }
      />
      <div className="mt-10">
        <HowCalculated types={['employability_index']} title="¿Cómo se calcula el ISE?" />
      </div>
    </Page>
  );
}
