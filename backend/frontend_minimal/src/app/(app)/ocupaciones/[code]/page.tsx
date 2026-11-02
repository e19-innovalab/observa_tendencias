import { ArrowLeft, ArrowRight, ChevronRight, Home } from 'lucide-react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { Term } from '@/components/minimal/Term';
import { ChipGroup } from '@/components/ui/filters/UrlControls';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { LevelBadge } from '@/components/ui/LevelBadge';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/common';
import { getOccupationProfile, getOccupationSkills } from '@/lib/api/employability';
import type { Component, EmployabilityTexts } from '@/lib/schemas/employability';
import { formatGrowth, formatIndex, formatScore, formatShare, formatUnit, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Detalle de ocupación' };
type Params = { code: string };
type SearchParams = { country?: string; habilidades?: string };
const SKILLS_PREVIEW = 15;
const DIM_COLORS: Record<string, string> = {
  net_demand: 'var(--color-rank-1)',
  salary_ppp: 'var(--color-rank-3)',
  insertion_rate: 'var(--color-rank-5)',
  automation_risk: 'var(--color-rank-4)',
};

export default function OccupationDetailPage({ params, searchParams }: PageProps<'/ocupaciones/[code]'>) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Detail params={params as Promise<Params>} searchParams={searchParams as Promise<SearchParams>} />
    </Suspense>
  );
}

/** Valor bruto legible de una dimensión. */
function rawText(c: Component, texts: EmployabilityTexts | null | undefined): string {
  if (c.raw === null) return '—';
  if (c.measure === 'growth') return `${formatGrowth(c.raw)} anual`;
  if (c.unit && texts?.unit_formats[c.unit]) return formatUnit(c.raw, c.unit, texts.unit_formats);
  if (c.unit === 'index_0_1') return `${formatIndex(c.raw)} (0 a 1)`;
  return formatIndex(c.raw);
}

/** De dónde sale el valor: indicador, fuente, períodos y valores usados. */
function originText(c: Component): string {
  const d = c.detail as Record<string, string | number | null | undefined>;
  if (!c.indicator) return 'Sin fuente oficial todavía; su peso se reparte entre las demás dimensiones.';
  if (!c.available) return 'Sin datos suficientes para este año.';
  const parts = [`${c.indicator}`, d.source ? `fuente ${d.source}` : null];
  if (d.from_period && d.to_period) {
    const n = (v: unknown) => (typeof v === 'number' ? formatValue(v, '') : String(v));
    const unit = c.unit === 'thousands_persons' ? ' mil personas' : '';
    parts.push(`${d.from_period} → ${d.to_period} (${n(d.from_value)} → ${n(d.to_value)}${unit})`);
  }
  else if (d.period) parts.push(`dato ${d.period}`);
  if (d.group) parts.push(`grupo ${d.group}`);
  return parts.filter(Boolean).join(' · ');
}

async function Detail({ params, searchParams }: { params: Promise<Params>; searchParams: Promise<SearchParams> }) {
  const [{ code }, sp] = await Promise.all([params, searchParams]);
  let profile, countries, skills;
  try {
    [profile, countries, skills] = await Promise.all([getOccupationProfile(code), getCountries(), getOccupationSkills(code)]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text">
          {e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
        </p>
      </div>
    );
  }
  const occ = profile.occupation;
  const scores = profile.employability;
  const current = scores.find((s) => s.country_iso3 === sp.country) ?? scores.find((s) => s.score !== null) ?? scores[0];
  const countryNames = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const comps = current?.components ?? [];
  const texts = profile.texts;
  const availableWeight = comps.filter((c) => c.available).reduce((a, c) => a + c.weight, 0);
  const effective = (c: Component) => (c.available && availableWeight ? c.weight / availableWeight : null);
  const showAll = sp.habilidades === 'todas';
  const shownSkills = showAll ? skills.items : skills.items.slice(0, SKILLS_PREVIEW);
  const hierarchy = profile.hierarchy.filter((h) => h.level < 4);

  return (
    <>
      <section className="bg-brand px-6 py-8 text-white">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_22rem]">
          <div className="space-y-4">
            <nav aria-label="Ruta" className="flex flex-wrap items-center gap-1 text-xs text-blue-100">
              <Link href="/inicio" className="inline-flex items-center gap-1 hover:underline"><Home className="size-3" aria-hidden />Inicio</Link>
              <ChevronRight className="size-3" aria-hidden />
              <Link href="/ocupaciones" className="hover:underline">Ocupaciones</Link>
              <ChevronRight className="size-3" aria-hidden />
              <span aria-current="page" className="text-white">{occ.name}</span>
            </nav>
            <div className="flex flex-wrap gap-2 text-xs font-medium">
              {current && <span className="rounded bg-white px-2 py-1 text-heading">{countryNames[current.country_iso3]} ({current.country_iso3})</span>}
              <span className="rounded bg-white px-2 py-1 text-heading">CIUO {occ.occupation_code}</span>
              {profile.sector_name && <span className="rounded bg-white/15 px-2 py-1">{profile.sector_name}</span>}
              {occ.is_featured && <span className="rounded bg-white/15 px-2 py-1">Destacada</span>}
            </div>
            <h1 className="text-3xl font-semibold leading-tight">{occ.name}</h1>
            <p className="max-w-2xl text-sm text-blue-50">
              {hierarchy.map((h) => `${h.code} ${h.name ?? ''}`).join(' › ')}
              {occ.name_en ? ` · En inglés (ISCO-08): ${occ.name_en}` : ''}
            </p>
            <Link href="/ocupaciones" className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-heading hover:bg-surface-2">
              <ArrowLeft className="size-4" aria-hidden /> Volver a Ocupaciones
            </Link>
          </div>
          {current && (
            <div className="self-start rounded-lg bg-white p-5 text-body">
              <div className="flex items-start justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-text">Puntaje ISE {current.year}</p>
                <LevelBadge level={current.level} label={current.level_label} />
              </div>
              <p className="mt-1 text-4xl font-semibold text-heading">{formatScore(current.score)} <span className="text-base font-normal text-muted-text">/ 100</span></p>
              <p className="mt-2 flex justify-between text-xs">
                <span className="text-muted-text">Cobertura de dimensiones</span>
                <strong>{formatShare(current.coverage_ratio)} ({comps.filter((c) => c.available).length} de {comps.length})</strong>
              </p>
              <div className="mt-2 flex h-2.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
                {comps.filter((c) => c.contribution !== null).map((c) => (
                  <span key={c.dimension} style={{ width: `${c.contribution}%`, background: DIM_COLORS[c.dimension] }} />
                ))}
              </div>
              <ul className="mt-3 grid grid-cols-2 gap-1 text-[11px] text-muted-text">
                {comps.map((c) => (
                  <li key={c.dimension} className="flex items-center gap-1.5">
                    <span className="size-2 rounded-sm" style={{ background: c.available ? DIM_COLORS[c.dimension] : 'var(--color-line)' }} aria-hidden />
                    {c.label.split(' (')[0]} ({c.contribution === null ? '—' : formatScore(c.contribution)})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        <ChipGroup
          name="country"
          label="País"
          value={current?.country_iso3 ?? ''}
          withAll={false}
          options={scores.map((s) => ({ value: s.country_iso3, label: `${s.country_iso3} · ${formatScore(s.score)}` }))}
        />

        {current && (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {comps.map((c) => (
              <div key={c.dimension} className={`rounded-lg border p-4 ${c.indicator ? 'border-line bg-white' : 'border-dashed border-line bg-white'}`}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-text">{c.display ? <Term help={c.display.note ?? ''}>{c.display.label}</Term> : c.label}</p>
                <p className="mt-2 text-2xl font-semibold text-heading">
                  {c.display ? formatUnit(c.display.value, c.display.unit, texts?.unit_formats) : c.indicator ? rawText(c, texts) : 'Sin dato oficial'}
                </p>
                {c.display && <p className="mt-0.5 text-xs text-muted-text">{rawText(c, texts)} · {c.display.period}</p>}
                <p className="mt-2 flex justify-between border-t border-line/60 pt-2 text-xs text-muted-text">
                  <span>
                    {c.indicator ? (
                      <>
                        <Term help={texts?.terms.contribution ?? ''}>Aporte al ISE</Term>: {c.contribution === null ? '—' : `${formatScore(c.contribution)} pts`}
                      </>
                    ) : (
                      `Peso ${formatScore(c.weight * 100)}% redistribuido`
                    )}
                  </span>
                  {c.normalized !== null && (
                    <span>
                      <Term help={texts?.terms.normalized ?? ''} align="right">Escalado</Term> {formatScore(c.normalized)}
                    </span>
                  )}
                </p>
              </div>
            ))}
          </section>
        )}

        {current && (
          <section className="overflow-hidden rounded-lg border border-line bg-white">
            <div className="border-b border-line/70 p-5">
              <h2 className="text-lg font-semibold text-heading">Desglose del Índice de Empleabilidad (ISE) · CIUO {occ.occupation_code}</h2>
              <p className="mt-1 text-sm text-muted-text">Valores de origen, escala 0-100 dentro del grupo comparado, pesos teórico y efectivo, y de dónde sale cada dato.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[56rem] text-sm">
                <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
                  <tr>
                    <th scope="col" className="px-4 py-3">Dimensión</th>
                    <th scope="col" className="px-4 py-3">Valor de origen</th>
                    <th scope="col" className="px-4 py-3 text-right"><Term help={texts?.terms.normalized ?? ''} align="right" side="bottom">Escalado (0-100)</Term></th>
                    <th scope="col" className="px-4 py-3 text-right">Peso</th>
                    <th scope="col" className="px-4 py-3 text-right"><Term help={texts?.terms.contribution ?? ''} align="right" side="bottom">Aporte al ISE</Term></th>
                    <th scope="col" className="px-4 py-3">De dónde sale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {comps.map((c) => (
                    <tr key={c.dimension} className={c.available ? '' : 'text-muted-text'}>
                      <td className="px-4 py-3 font-medium text-heading">{c.label}</td>
                      <td className="px-4 py-3">
                        {rawText(c, texts)}
                        {c.display && <span className="block text-[11px] text-muted-text">{c.display.label}: {formatUnit(c.display.value, c.display.unit, texts?.unit_formats)}</span>}
                      </td>
                      <td className="px-4 py-3 text-right">{formatScore(c.normalized)}</td>
                      <td className="px-4 py-3 text-right">
                        {formatScore(c.weight * 100)}%
                        <span className="block text-[11px] text-muted-text">{effective(c) === null ? 'redistribuido' : `efectivo ${formatScore(effective(c)! * 100)}%`}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">{c.contribution === null ? '—' : formatScore(c.contribution)}</td>
                      <td className="px-4 py-3 font-mono text-xs">{originText(c)}</td>
                    </tr>
                  ))}
                  <tr className="bg-surface font-semibold">
                    <td className="px-4 py-3 text-heading">Puntaje ISE</td>
                    <td className="px-4 py-3" />
                    <td className="px-4 py-3" />
                    <td className="px-4 py-3 text-right">100%</td>
                    <td className="px-4 py-3 text-right text-heading">{formatScore(current.score)}</td>
                    <td className="px-4 py-3 text-xs font-normal text-muted-text">Suma de los aportes de las dimensiones con datos.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            {profile.groups.length > 0 && (
              <div className="space-y-1 border-t border-line/70 p-4 text-xs text-muted-text">
                <p className="font-semibold text-body">Grupos de la CIUO usados (las fuentes publican por grupo, no por ocupación):</p>
                {profile.groups.map((g) => (
                  <p key={`${g.indicator}-${g.source}-${g.group_code}`}>
                    {g.indicator} · {g.source} · {g.countries.join(', ')} · grupo de {g.isco_digits} dígito{g.isco_digits > 1 ? 's' : ''} ({g.group_code}), compartido con {g.shared_with.length} ocupaciones.
                  </p>
                ))}
              </div>
            )}
          </section>
        )}

        <section className="rounded-lg border border-line bg-white p-5">
          <h2 className="text-lg font-semibold text-heading">ISE en cada país</h2>
          <ul className="mt-3 grid gap-3 sm:grid-cols-3">
            {scores.map((s) => (
              <li key={s.country_iso3} className="rounded-md border border-line p-3">
                <p className="text-xs text-muted-text">{countryNames[s.country_iso3]}</p>
                <p className="text-xl font-semibold text-heading">{formatScore(s.score)} <LevelBadge level={s.level} label={s.level_label} /></p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg border border-line bg-white p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-heading">Habilidades principales ({skills.total} en total)</h2>
              <p className="mt-1 text-sm text-muted-text">{skills.weight_note} Fuente: {skills.source?.name ?? 'ESCO'}.</p>
            </div>
            <Link href={`/habilidades?occupation=${occ.occupation_code}`} className="inline-flex items-center gap-1 text-sm font-medium text-link hover:underline">
              Ver brechas de estas habilidades <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
          <ul className="mt-4 flex flex-wrap gap-2">
            {shownSkills.map((s) => (
              <li key={s.skill_code} className="flex items-center gap-2 rounded-md border border-line px-2.5 py-1 text-xs text-body">
                {s.name}
                {s.weight !== null && s.weight !== undefined && <span className="rounded bg-surface-2 px-1.5 font-mono text-[10px]">{formatIndex(s.weight)}</span>}
              </li>
            ))}
          </ul>
          {skills.items.length > SKILLS_PREVIEW && (
            <Link
              href={`?${new URLSearchParams({ ...(current ? { country: current.country_iso3 } : {}), ...(showAll ? {} : { habilidades: 'todas' }) })}`}
              scroll={false}
              className="mt-4 inline-block text-sm font-medium text-link hover:underline"
            >
              {showAll ? 'Mostrar menos' : `Mostrar las ${skills.items.length} habilidades`}
            </Link>
          )}
        </section>

        <HowCalculated types={['employability_index']} title="¿Cómo se calcula el ISE?" />
      </div>
    </>
  );
}
