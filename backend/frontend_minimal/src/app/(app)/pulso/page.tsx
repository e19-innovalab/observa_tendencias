import { ExternalLink, Info } from 'lucide-react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, Page, RailCard, SourceLine, Stat } from '@/components/minimal/ui';
import { UrlSeg } from '@/components/minimal/UrlSeg';
import { SearchParam } from '@/components/ui/filters/SearchParam';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { Pager } from '@/components/ui/Pager';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/common';
import { getJobs, getJobsSummary, type JobsSummary } from '@/lib/api/jobs';
import { formatDate } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Pulso laboral' };
type SearchParams = { country?: string; provincia?: string; sector?: string; q?: string; page?: string };
const one = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 });
const pct = new Intl.NumberFormat('es-AR', { style: 'percent', maximumFractionDigits: 0 });

export default function PulsoPage({ searchParams }: PageProps<'/pulso'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PulsoContent searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** Filas del mapa: sectores en el orden de la configuración, "Otros" al final. */
function sectorRows(s: JobsSummary) {
  const present = [...new Set(s.por_provincia_sector.map((c) => c.sector))];
  return [
    ...s.view.sector_order.filter((x) => present.includes(x)),
    ...present.filter((x) => !s.view.sector_order.includes(x) && x !== s.view.other_sector),
    ...(present.includes(s.view.other_sector) ? [s.view.other_sector] : []),
  ];
}

async function PulsoContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page ?? '1') || 1);
  let countries, summary, jobs;
  let summaries: JobsSummary[];
  try {
    countries = await getCountries();
    summaries = await Promise.all(countries.map((c) => getJobsSummary(c.iso3)));
    const withData = countries.filter((_, i) => summaries[i].total > 0);
    const country = withData.find((c) => c.iso3 === sp.country)?.iso3 ?? withData[0]?.iso3;
    sp.country = country;
    summary = country ? summaries[countries.findIndex((c) => c.iso3 === country)] : summaries[0];
    jobs = country
      ? await getJobs({ country, provincia: sp.provincia, sector: sp.sector, q: sp.q, limit: summary.view.page_size, offset: (page - 1) * summary.view.page_size })
      : null;
  } catch (e) {
    return <ErrorNote message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const v = summary.view;
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const withData = countries.filter((_, i) => summaries[i].total > 0);
  const cells = summary.por_provincia_sector;
  const provinces = [...new Set(cells.map((c) => c.provincia))].sort((a, b) => a.localeCompare(b, 'es'));
  const sectors = sectorRows(summary);
  const count = (p: string, s: string) => cells.find((c) => c.provincia === p && c.sector === s)?.n ?? 0;
  const max = Math.max(1, ...cells.map((c) => c.n));
  const totals = sectors.map((s) => ({ sector: s, n: cells.filter((c) => c.sector === s).reduce((a, c) => a + c.n, 0) }));
  const top = totals.filter((t) => t.sector !== v.other_sector).sort((a, b) => b.n - a.n)[0];
  const overall = summary.competencia.find((c) => c.sector === null);
  const bySector = summary.competencia.filter((c) => c.sector !== null && c.mediana_postulantes !== null);
  const compMax = Math.max(v.applicants_cap, ...bySector.map((c) => c.mediana_postulantes!));
  const most = bySector.filter((c) => c.sector !== v.other_sector)[0];
  const least = bySector.filter((c) => c.sector !== v.other_sector).at(-1);
  const href = (params: Record<string, string | undefined>) => {
    const q = new URLSearchParams(Object.entries({ country: sp.country, ...params }).filter(([, x]) => x) as [string, string][]);
    return `/pulso?${q}#ofertas`;
  };
  const filtered = Boolean(sp.provincia || sp.sector || sp.q);

  if (!sp.country) {
    return (
      <Page>
        <ChartHeader eyebrow="LinkedIn · ofertas de empleo" title="Pulso laboral" subtitle="Todavía no hay ofertas cargadas." />
      </Page>
    );
  }

  return (
    <Page>
      <ChartHeader
        eyebrow={`Pulso laboral · ofertas de LinkedIn · ${v.period_label} · ${names[sp.country]}`}
        title="¿Dónde se busca gente esta semana y cuánta competencia hay?"
        subtitle="Ofertas publicadas en LinkedIn por provincia y sector, y cuántas personas se postulan a cada una. Tocá una celda para ver esas ofertas."
        controls={withData.length > 1 ? <UrlSeg name="country" label="País" value={sp.country} options={withData.map((c) => ({ value: c.iso3, label: c.name_es }))} reset={['provincia', 'sector', 'page']} /> : undefined}
      />
      <p className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-900">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden /> {v.notice}
      </p>
      <ChartLayout
        chart={
          <>
            <section aria-label="Ofertas por sector y provincia">
              <h2 className="text-sm font-semibold text-slate-900">Ofertas por sector y provincia</h2>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[32rem] border-separate border-spacing-1 text-sm">
                  <thead>
                    <tr>
                      <th className="text-left text-xs font-medium text-slate-500" scope="col">Sector</th>
                      {provinces.map((p) => (
                        <th key={p} scope="col" className="text-xs font-medium text-slate-500">
                          <Link href={href({ provincia: p })} scroll={false} className="hover:text-blue-700">{p}</Link>
                        </th>
                      ))}
                      <th scope="col" className="text-right text-xs font-medium text-slate-500">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sectors.map((s) => (
                      <tr key={s}>
                        <th scope="row" className="pr-2 text-left text-[13px] font-medium text-slate-900">
                          <Link href={href({ sector: s })} scroll={false} className="hover:text-blue-700">{s}</Link>
                        </th>
                        {provinces.map((p) => {
                          const n = count(p, s);
                          const share = n / max;
                          const on = sp.provincia === p && sp.sector === s;
                          return (
                            <td key={p} className="p-0">
                              {n ? (
                                <Link
                                  href={href({ provincia: p, sector: s })}
                                  scroll={false}
                                  title={`${s} · ${p}: ${n} ofertas`}
                                  className={`flex h-11 items-center justify-center rounded-md text-[13px] font-semibold ${on ? 'ring-2 ring-slate-900' : ''}`}
                                  style={{ background: `rgba(29, 78, 216, ${0.08 + share * 0.82})`, color: share > 0.45 ? '#fff' : '#1e3a8a' }}
                                >
                                  {n}
                                </Link>
                              ) : (
                                <span className="flex h-11 items-center justify-center rounded-md bg-slate-50 text-[13px] text-slate-300">0</span>
                              )}
                            </td>
                          );
                        })}
                        <td className="text-right text-[13px] font-semibold text-slate-900">{totals.find((t) => t.sector === s)?.n}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {bySector.length > 0 && (
              <section aria-label="Competencia por oferta" className="mt-8">
                <h2 className="text-sm font-semibold text-slate-900">Competencia por oferta: postulantes por oferta (mediana)</h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Pocas personas por oferta: las empresas compiten por candidatos. Muchas: las personas compiten por el puesto. {v.footnote}
                </p>
                <ul className="mt-3 space-y-1.5">
                  {bySector.map((c) => (
                    <li key={c.sector} className="grid grid-cols-[minmax(7rem,11rem)_minmax(0,1fr)_6.5rem] items-center gap-3">
                      <span className="truncate text-[13px] text-slate-900">{c.sector}</span>
                      <span className="relative block h-5 rounded bg-slate-100">
                        <span className="absolute inset-y-0 left-0 rounded bg-violet-400" style={{ width: `${(c.mediana_postulantes! / compMax) * 100}%` }} />
                        {overall?.mediana_postulantes != null && (
                          <span className="absolute -inset-y-1 w-0.5 bg-slate-900" style={{ left: `${(overall.mediana_postulantes / compMax) * 100}%` }} title={`Todas las ofertas: ${one.format(overall.mediana_postulantes)}`} />
                        )}
                      </span>
                      <span className="text-right text-[13px]">
                        <span className="font-semibold text-slate-900">{c.mediana_postulantes! >= v.applicants_cap ? `${v.applicants_cap}+` : one.format(c.mediana_postulantes!)}</span>
                        <span className="ml-1 text-[11px] text-slate-500">{c.ofertas} of.</span>
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[11px] text-slate-500">
                  Línea oscura: todas las ofertas ({overall?.mediana_postulantes != null ? one.format(overall.mediana_postulantes) : '—'} postulantes). Sectores con menos de {v.competition_min_postings} ofertas con dato no se muestran.
                </p>
              </section>
            )}
            <SourceLine source={`Fuente: ${v.source_label} · recolección ${formatDate(summary.scraped_at) ?? '—'} · sector asignado por reglas`}>
              <Link href="/metodologia/fuentes" className="text-blue-700 hover:underline">Fuentes</Link>
            </SourceLine>
          </>
        }
        rail={
          <RailCard>
            <Eyebrow>Esta semana · {names[sp.country]}</Eyebrow>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Ofertas" value={summary.total.toLocaleString('es-AR')} />
              <Stat label="Provincias" value={String(provinces.length)} />
              <Stat label="Sector con más ofertas" value={top?.sector ?? '—'} />
              <Stat label="Postulantes por oferta" value={overall?.mediana_postulantes != null ? one.format(overall.mediana_postulantes) : '—'} />
            </div>
            {most && least && most.sector !== least.sector && (
              <p className="text-[13px] leading-relaxed text-slate-700">
                <strong>{least.sector}</strong> tiene la menor competencia ({one.format(least.mediana_postulantes!)} postulantes por oferta en {least.ofertas} ofertas): más demanda que candidatos. En <strong>{most.sector}</strong> hay {one.format(most.mediana_postulantes!)} por oferta y {pct.format(most.en_tope ?? 0)} llega al tope de {v.applicants_cap}+.
              </p>
            )}
            <p className="text-[11px] leading-relaxed text-slate-500">Es una foto de {v.period_label}, no una tendencia: compará con cuidado.</p>
          </RailCard>
        }
      />

      <section id="ofertas" className="mt-10 scroll-mt-20" aria-label="Ofertas">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Ofertas{[sp.sector, sp.provincia].filter(Boolean).length ? ` · ${[sp.sector, sp.provincia].filter(Boolean).join(' · ')}` : ''}</h2>
            {filtered && <Link href={`/pulso?country=${sp.country}#ofertas`} scroll={false} className="text-xs text-blue-700 hover:underline">Quitar filtros</Link>}
          </div>
          <div className="w-72"><SearchParam label="Buscar en el título" placeholder="Ej. analista, enfermero/a" /></div>
        </div>
        <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full min-w-[52rem] text-sm">
            <thead className="bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-2.5">Puesto</th>
                <th scope="col" className="px-4 py-2.5">Empresa</th>
                <th scope="col" className="px-4 py-2.5">Provincia</th>
                <th scope="col" className="px-4 py-2.5">Sector</th>
                <th scope="col" className="px-4 py-2.5">Nivel</th>
                <th scope="col" className="px-4 py-2.5 text-right">Postulantes</th>
                <th scope="col" className="px-4 py-2.5">Publicada</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs?.items.map((j) => (
                <tr key={j.id} className="align-top hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    <a href={j.url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1 font-medium text-blue-700 hover:underline">
                      {j.titulo} <ExternalLink className="mt-0.5 size-3 shrink-0" aria-hidden />
                    </a>
                  </td>
                  <td className="px-4 py-2.5 text-slate-700">{j.empresa ?? '—'}</td>
                  <td className="px-4 py-2.5 text-slate-700">{j.provincia}</td>
                  <td className="px-4 py-2.5"><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{j.sector}</span></td>
                  <td className="px-4 py-2.5 text-slate-700">{!j.nivel_experiencia || j.nivel_experiencia === v.no_level ? '—' : j.nivel_experiencia}</td>
                  <td className="px-4 py-2.5 text-right text-slate-900">{j.postulantes == null ? '—' : j.postulantes >= v.applicants_cap ? `${v.applicants_cap}+` : j.postulantes}</td>
                  <td className="px-4 py-2.5 text-slate-500">{formatDate(j.fecha_publicacion) ?? '—'}</td>
                </tr>
              ))}
              {jobs && jobs.items.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-500">No hay ofertas con esos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="mt-3"><Pager total={jobs?.total ?? 0} pageSize={v.page_size} label="ofertas" /></div>
      </section>
    </Page>
  );
}
