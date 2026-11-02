import type { Metadata } from 'next';
import { ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { Suspense } from 'react';
import { RailFocus } from '@/components/minimal/RailFocus';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, RailCard, SourceLine, buttonCls } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { LevelBadge } from '@/components/ui/LevelBadge';
import { ApiError } from '@/lib/api/client';
import { getCountries, getSectors } from '@/lib/api/common';
import { getEmployability } from '@/lib/api/employability';
import type { EmployabilityItem } from '@/lib/schemas/employability';
import { formatScore } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Ocupaciones' };
type SearchParams = { sector?: string; orden?: string; sel?: string; year?: string };
const YEARS_OFFERED = 3;
const MAX_ROWS = 300; // filas país×ocupación: alcanza para el sector más grande (55 ocupaciones × 3)
const SORTS = [
  { value: '', label: 'Mayor ISE' },
  { value: 'diferencia', label: 'Mayor diferencia' },
];

export default function OcupacionesPage({ searchParams }: PageProps<'/ocupaciones'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <OcupacionesContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

type Row = { code: string; name: string; sector: string | null; items: EmployabilityItem[]; max: number; min: number };

async function OcupacionesContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  let data, countries, sectors;
  try {
    [data, countries, sectors] = await Promise.all([
      getEmployability({ featured: sp.sector ? undefined : true, sector: sp.sector, year: sp.year, view: 'all', limit: MAX_ROWS }),
      getCountries(),
      getSectors(),
    ]);
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const latestYear = data.available_years.at(-1);
  const years = data.available_years.slice(-YEARS_OFFERED).map((y) => ({ value: y === latestYear ? '' : String(y), label: String(y) }));
  const byCode = new Map<string, Row>();
  for (const it of data.items) {
    const code = it.occupation.occupation_code;
    const row = byCode.get(code) ?? { code, name: it.occupation.name, sector: it.sector_name, items: [], max: -Infinity, min: Infinity };
    row.items.push(it);
    if (it.score !== null) { row.max = Math.max(row.max, it.score); row.min = Math.min(row.min, it.score); }
    byCode.set(code, row);
  }
  const scored = [...byCode.values()].filter((r) => Number.isFinite(r.max));
  const unscored = [...byCode.values()].filter((r) => !Number.isFinite(r.max)).length;
  const rows = scored.sort((a, b) => (sp.orden === 'diferencia' ? b.max - b.min - (a.max - a.min) : b.max - a.max));
  const lo = Math.max(0, Math.floor(Math.min(...rows.map((r) => r.min)) / 10) * 10);
  const hi = Math.min(100, Math.ceil(Math.max(...rows.map((r) => r.max)) / 10) * 10);
  const ticks = Array.from({ length: Math.round((hi - lo) / 10) + 1 }, (_, i) => lo + i * 10);
  const pct = (v: number) => `${((v - lo) / (hi - lo || 1)) * 100}%`;
  const selected = rows.find((r) => r.code === sp.sel) ?? rows[0];
  const sectorName = sectors.find((s) => s.sector_code === sp.sector)?.name;
  const ficha = (code: string) => `/ocupaciones/${code}`;
  const href = (code: string) => {
    const q = new URLSearchParams({ ...(sp.sector ? { sector: sp.sector } : {}), ...(sp.orden ? { orden: sp.orden } : {}), ...(sp.year ? { year: sp.year } : {}), sel: code });
    return `/ocupaciones?${q}`;
  };

  return (
    <Page>
      <ChartHeader
        eyebrow={`Índice de empleabilidad (ISE) · ${data.year ?? ''} · ${sectorName ?? 'ocupaciones destacadas'}`}
        title="La misma ocupación, tres países"
        subtitle="Cada fila es una ocupación y cada punto, su ISE en un país (0 a 100). Cuanto más larga la línea, más difiere entre países."
        controls={
          <>
            <UrlSeg name="sector" label="Conjunto" value={sp.sector ?? ''} options={[{ value: '', label: 'Destacadas' }, ...sectors.map((s) => ({ value: s.sector_code, label: s.name }))]} />
            <UrlSeg name="orden" label="Orden" value={sp.orden ?? ''} options={SORTS} reset={[]} />
            {years.length > 1 && <UrlSeg name="year" label="Año" value={sp.year && sp.year !== String(latestYear) ? sp.year : ''} options={years} reset={[]} />}
          </>
        }
      />
      <ChartLayout
        stickyRail
        chart={
          rows.length === 0 ? (
            <p className="py-24 text-center text-sm text-slate-500">No hay ocupaciones con ISE en este conjunto.</p>
          ) : (
            <>
              <div className="mr-8 grid grid-cols-[minmax(8rem,260px)_minmax(0,1fr)] gap-4 px-2 pb-1.5 text-xs text-slate-500">
                <span className="flex flex-wrap gap-3.5">
                  {countries.map((c) => (
                    <span key={c.iso3} className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full" style={{ background: COUNTRY_COLORS[c.iso3] ?? FALLBACK_COLOR }} />{c.iso3}</span>
                  ))}
                </span>
                <span className="flex justify-between">{ticks.map((t) => <span key={t}>{t}</span>)}</span>
              </div>
              <ul>
                {rows.map((r) => {
                  const on = r.code === selected?.code;
                  return (
                    <li key={r.code} className={`group flex items-center rounded-md ${on ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
                      <Link
                        href={href(r.code)}
                        scroll={false}
                        aria-current={on ? 'true' : undefined}
                        className="grid min-h-[30px] min-w-0 flex-1 grid-cols-[minmax(8rem,260px)_minmax(0,1fr)] items-center gap-4 px-2 py-0.5"
                      >
                        <span className="truncate text-[13px] text-slate-900" title={r.name}>{r.name}</span>
                        <span className="relative block h-[22px]">
                          <span className="absolute inset-x-0 top-[10px] h-px bg-slate-100" />
                          <span className="absolute top-[9px] h-[3px] rounded bg-slate-300" style={{ left: pct(r.min), width: `calc(${pct(r.max)} - ${pct(r.min)})` }} />
                          {r.items.filter((i) => i.score !== null).map((i) => (
                            <span
                              key={i.country_iso3}
                              title={`${names[i.country_iso3]}: ${formatScore(i.score)}`}
                              className="absolute top-1 -ml-1.5 size-[13px] rounded-full border-2 border-white"
                              style={{ left: pct(i.score!), background: COUNTRY_COLORS[i.country_iso3] ?? FALLBACK_COLOR }}
                            />
                          ))}
                        </span>
                      </Link>
                      <Link
                        href={ficha(r.code)}
                        aria-label={`Abrir la ficha de ${r.name}`}
                        title="Abrir ficha"
                        className={`flex size-8 shrink-0 items-center justify-center rounded-md text-blue-700 hover:bg-blue-100 focus-visible:opacity-100 ${on ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                      >
                        <ArrowRight className="size-4" aria-hidden />
                      </Link>
                    </li>
                  );
                })}
              </ul>
              <SourceLine source={`${rows.length} ocupaciones${unscored ? ` (${unscored} sin ISE por falta de datos)` : ''} · Fuentes: ILOSTAT, SIMEL (INE Chile) y OIT (2025)`}>
                <Link href="/metodologia/ise" className="text-blue-700 hover:underline">¿Cómo se calcula el ISE?</Link>
              </SourceLine>
            </>
          )
        }
        rail={
          selected && (
            <RailFocus selection={sp.sel}>
              <RailCard>
                <Eyebrow>CIUO {selected.code}{selected.sector ? ` · ${selected.sector}` : ''}</Eyebrow>
                <h2 className="text-[22px] font-bold leading-tight text-slate-900">{selected.name}</h2>
                <Link href={ficha(selected.code)} className={buttonCls}>
                  Abrir ficha <ArrowRight className="size-4" aria-hidden />
                </Link>
                <p className="-mt-2 text-xs text-slate-500">Dimensiones del ISE, evolución y habilidades</p>
                <div>
                  {countries.map((c) => {
                    const it = selected.items.find((i) => i.country_iso3 === c.iso3);
                    return (
                      <div key={c.iso3} className="flex items-center justify-between gap-3 border-b border-slate-100 py-2">
                        <span className="text-sm text-slate-700">{c.name_es}</span>
                        <span className="flex items-center gap-2">
                          {it && it.score !== null && <LevelBadge level={it.level} label={it.level_label} />}
                          <span className="text-xl font-bold text-slate-900">{it && it.score !== null ? formatScore(it.score) : 'sin dato'}</span>
                        </span>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[13px] leading-relaxed text-slate-600">
                  Diferencia entre países: {formatScore(selected.max - selected.min)} puntos. Las ocupaciones de un mismo grupo CIUO comparten los datos de demanda y salario del grupo.
                </p>
              </RailCard>
            </RailFocus>
          )
        }
      />
    </Page>
  );
}
