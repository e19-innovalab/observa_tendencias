import { ChevronDown, Info } from 'lucide-react';
import Link from 'next/link';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { ChartHeader, ChartLayout, ErrorNote, Eyebrow, RailCard, SourceLine, Stat } from '@/components/data/ui';
import { UrlSeg } from '@/components/data/UrlSeg';
import { ApiError } from '@/lib/api/client';
import { getCountries, getSectors } from '@/lib/api/panorama';
import { getSkillGaps, getSkillGroupGaps } from '@/lib/api/skills';
import type { SectorUse } from '@/lib/schemas/api';
import { formatGrowth } from '@/lib/utils/format';

type SearchParams = {
  tab?: string;
  nivel?: string;
  anio?: string;
  country?: string;
  sector?: string;
  relacion?: string;
  sel?: string;
  q?: string;
  carrera?: string;
  sector_kpi?: string;
};

const PER_SIDE = 8;
const BAR_ROOM = 82; // % del medio ancho que ocupa la barra más larga
const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const RELATIONS = [
  { value: '', label: 'Esenciales del sector' },
  { value: 'any', label: 'También opcionales' },
];
const LEVELS = [
  { value: '', label: 'Grupos de habilidades' },
  { value: 'detalle', label: 'Habilidades detalladas' },
];

/** Brecha (diferencia de fracciones) en puntos porcentuales con signo. */
const gapText = (v: number) =>
  `${v > 0 ? '+' : v < 0 ? '−' : ''}${one.format(Math.abs(v * 100))} pp`;
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

type Through = {
  country_iso3: string;
  demand: number | null;
  supply: number | null;
  supplemented_years: number[];
  supply_note: string | null;
};

/** Una fila del gráfico, igual para un grupo de ESCO o una habilidad detallada. */
type Row = {
  code: string;
  name: string;
  kicker: string; // tipo de habilidad o grupo superior
  description: string | null;
  descriptionEn: string | null; // original de ESCO en inglés
  descriptionOrigin: string | null; // esco | translation | null
  gap: number;
  demand: number | null;
  supply: number | null;
  occupations: number;
  skills: { name: string; description: string | null }[] | null; // habilidades del grupo (las de más peso)
  skillsTotal: number | null; // cuántas habilidades de ESCO junta el grupo
  sectors: SectorUse[];
  cross: boolean;
  emerging: boolean;
  unstable: { occupation: string; name: string }[]; // fuera de la oferta: serie de titulados inestable
};

export async function SkillGapsView({ sp: params }: { sp: SearchParams }) {
  const groups = params.nivel !== 'detalle';
  let countries, sectors, rows: Row[], total: number, year: number | null, years: number[], through: Through | undefined, reviewed: boolean, scope: { total: number; full: number } | null = null;
  const sp = { ...params };
  try {
    [countries, sectors] = await Promise.all([getCountries(), getSectors()]);
    sp.country = sp.country ?? countries[0]?.iso3;
    const base = { country: sp.country, sector: sp.sector, relation: sp.relacion, year: sp.anio };
    if (groups) {
      const pages = sp.q
        ? [await getSkillGroupGaps({ ...base, q: sp.q, view: 'all', limit: PER_SIDE * 2 })]
        : await Promise.all([
            getSkillGroupGaps({ ...base, view: 'top', limit: PER_SIDE }),
            getSkillGroupGaps({ ...base, view: 'bottom', limit: PER_SIDE }),
          ]);
      rows = pages
        .flatMap((pg) => pg.items)
        .filter((i) => i.gap !== null)
        .map((i) => ({
          code: i.group.group_code,
          name: i.group.name,
          kicker: i.group.parent ?? 'Grupo de ESCO',
          description: i.group.description,
          descriptionEn: i.group.description_en,
          descriptionOrigin: i.group.description_origin,
          gap: i.gap!,
          demand: i.demand_growth,
          supply: i.supply_growth,
          occupations: i.occupations,
          skills: i.top_skills.map((k) => ({ name: k.name, description: k.description ?? null })),
          skillsTotal: i.skills,
          sectors: i.sectors,
          cross: i.is_cross_sector,
          emerging: i.is_emerging,
          unstable: i.unstable_supply.flatMap((u) =>
            typeof u.name === 'string' && typeof u.occupation === 'string'
              ? [{ occupation: u.occupation, name: u.name }]
              : [],
          ),
        }));
      total = pages[0].full_total;
      year = pages[0].year;
      years = pages[0].available_years;
      through = pages[0].data_through.find((d) => d.country_iso3 === sp.country);
      reviewed = Object.values(pages[0].crosswalk_reviewed).every(Boolean);
      if (sp.sector && !sp.q) {
        const all = await getSkillGroupGaps({ ...base, view: 'all', limit: 1 });
        scope = { total: all.total, full: all.full_total };
      }
    } else {
      const pages = sp.q
        ? [await getSkillGaps({ ...base, q: sp.q, view: 'all', limit: PER_SIDE * 2 })]
        : await Promise.all([
            getSkillGaps({ ...base, view: 'top', limit: PER_SIDE }),
            getSkillGaps({ ...base, view: 'bottom', limit: PER_SIDE }),
          ]);
      rows = pages
        .flatMap((pg) => pg.items)
        .filter((i) => i.gap !== null)
        .map((i) => ({
          code: i.skill.skill_code,
          name: i.skill.name,
          kicker: i.skill.skill_type_label ?? 'Habilidad',
          description: i.skill.description ?? null,
          descriptionEn: i.skill.description_en ?? null,
          descriptionOrigin: i.skill.description_origin ?? null,
          gap: i.gap!,
          demand: i.demand_growth,
          supply: i.supply_growth,
          occupations: i.occupations,
          skills: null,
          skillsTotal: null,
          sectors: i.sectors,
          cross: i.is_cross_sector,
          emerging: i.is_emerging,
          unstable: i.unstable_supply.flatMap((u) =>
            typeof u.name === 'string' && typeof u.occupation === 'string'
              ? [{ occupation: u.occupation, name: u.name }]
              : [],
          ),
        }));
      total = pages[0].full_total;
      year = pages[0].year;
      years = pages[0].available_years;
      through = pages[0].data_through.find((d) => d.country_iso3 === sp.country);
      reviewed = Object.values(pages[0].crosswalk_reviewed).every(Boolean);
      if (sp.sector && !sp.q) {
        const all = await getSkillGaps({ ...base, view: 'all', limit: 1 });
        scope = { total: all.total, full: all.full_total };
      }
    }
  } catch (e) {
    return (
      <ErrorNote
        message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
      />
    );
  }
  const names = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const items = rows
    .filter((r, k, all) => all.findIndex((x) => x.code === r.code) === k)
    .sort((a, b) => b.gap - a.gap);
  const maxAbs = Math.max(0.05, ...items.map((i) => Math.abs(i.gap)));
  const selIndex = Math.min(Math.max(0, Number(sp.sel ?? '0') || 0), Math.max(0, items.length - 1));
  const selected = items[selIndex];
  const unit = groups ? 'grupos' : 'habilidades';
  const href = (k: number) => {
    const q = new URLSearchParams({
      country: sp.country!,
      ...(sp.nivel ? { nivel: sp.nivel } : {}),
      ...(sp.anio ? { anio: sp.anio } : {}),
      ...(sp.sector ? { sector: sp.sector } : {}),
      ...(sp.relacion ? { relacion: sp.relacion } : {}),
      ...(sp.q ? { q: sp.q } : {}),
      sel: String(k),
    });
    return `/habilidades?${q}`;
  };
  const sectorName = sectors.find((s) => s.sector_code === sp.sector)?.name;

  return (
    <>
      <ChartHeader
        eyebrow={`Demanda vs formación · crecimiento anual${year ? ` · ${year}` : ''}`}
        title={
          sp.q
            ? `${groups ? 'Grupos' : 'Habilidades'} que coinciden con “${sp.q}”`
            : groups
              ? '¿Qué grupos de habilidades faltan y cuáles sobran?'
              : '¿Qué habilidades faltan y cuáles sobran?'
        }
        subtitle={
          groups
            ? 'Cada grupo de ESCO junta habilidades muy parecidas (por ejemplo, las distintas formas de preparar informes financieros). Brecha = crecimiento del empleo que las usa − crecimiento de los titulados que las aprenden.'
            : 'Brecha = crecimiento del empleo que usa la habilidad − crecimiento de los titulados que la aprenden, en puntos porcentuales.'
        }
        controls={
          <>
            <UrlSeg name="nivel" label="Nivel" value={sp.nivel ?? ''} options={LEVELS} />
            <UrlSeg
              name="country"
              label="País"
              value={sp.country ?? ''}
              options={countries.map((c) => ({ value: c.iso3, label: c.name_es }))}
              reset={['sel', 'anio']}
            />
            {years.length > 1 && (
              <UrlSeg
                name="anio"
                label="Año"
                value={sp.anio ?? ''}
                options={years.map((y) => ({
                  value: y === years.at(-1) ? '' : String(y),
                  label: String(y),
                }))}
              />
            )}
            <UrlSeg
              name="sector"
              label="Sector"
              value={sp.sector ?? ''}
              options={[
                { value: '', label: 'Todos' },
                ...sectors.map((s) => ({ value: s.sector_code, label: s.name })),
              ]}
              reset={['sel', 'relacion']}
            />
            {sp.sector && (
              <UrlSeg name="relacion" label="Del sector" value={sp.relacion ?? ''} options={RELATIONS} />
            )}
          </>
        }
      />
      {through?.demand && through.supply && through.supply < through.demand && (
        <p className="mt-3 text-[13px] text-muted-text">
          Los titulados de {names[sp.country!]} llegan hasta {through.supply} y el empleo hasta{' '}
          {through.demand}: la brecha necesita los dos, así que el último año es {through.supply}.{' '}
          Los años siguientes aparecerán cuando la fuente oficial publique los titulados y se carguen.
        </p>
      )}
      {through?.supply_note && year !== null && through.supplemented_years.includes(year) && (
        <p className="mt-2 flex items-start gap-2 rounded-lg border border-alert-warning-border bg-alert-warning-bg px-3 py-2 text-[13px] text-alert-warning-text">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden /> {through.supply_note}
        </p>
      )}
      <ChartLayout
        stickyRail
        chart={
          items.length === 0 ? (
            <div className="mx-auto max-w-xl py-20 text-center text-sm text-muted-text">
              {scope && scope.total > 0 ? (
                <>
                  <p className="font-semibold text-heading">
                    {whole.format(scope.total)} {unit}{' '}
                    {sp.relacion === 'any' ? 'usados' : 'esenciales'} en {sectorName},{' '}
                    {scope.full
                      ? `solo ${scope.full} con brecha y en menos de 3 ocupaciones`
                      : 'ninguno con brecha calculada'}
                    .
                  </p>
                  <p className="mt-2">
                    Falta el dato de formación: las fuentes de titulados de {names[sp.country!]} no
                    incluyen las carreras que forman para estas ocupaciones (por ejemplo, si se forman
                    en institutos terciarios o formación profesional). Ver las fuentes en Metodología.
                  </p>
                </>
              ) : (
                <p>No hay brechas calculadas con estos filtros.</p>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 border-b border-line pb-2 text-xs font-semibold">
                <span className="pr-3 text-right text-brand">
                  ← La formación crece más rápido (posible excedente)
                </span>
                <span className="pl-3 text-warning">
                  La demanda crece más rápido (posible déficit) →
                </span>
              </div>
              <ul className="relative pt-1.5">
                <span className="absolute inset-y-0 left-1/2 w-px bg-line" aria-hidden />
                {items.map((it, k) => {
                  const on = k === selIndex;
                  const pos = it.gap > 0;
                  const width = `${(BAR_ROOM * Math.abs(it.gap)) / maxAbs}%`; // deja lugar a la etiqueta del valor
                  const name = cap(it.name);
                  const tag = it.cross && (
                    <span className="shrink-0 rounded-full bg-sector-knowledge-soft px-1.5 text-[10px] font-semibold tracking-wide text-sector-knowledge uppercase">
                      Transversal
                    </span>
                  );
                  return (
                    <li key={it.code}>
                      <Link
                        href={href(k)}
                        scroll={false}
                        aria-current={on ? 'true' : undefined}
                        className={`grid min-h-[34px] grid-cols-2 items-center rounded-md py-0.5 ${on ? 'bg-info-soft' : 'hover:bg-surface'}`}
                      >
                        <span className="relative block h-[26px]">
                          {pos ? (
                            <span
                              className="absolute top-1 right-3 flex max-w-[95%] items-center justify-end gap-1.5 text-[13px] text-heading"
                              title={it.description ?? name}
                            >
                              {tag}
                              <span className="truncate">{name}</span>
                            </span>
                          ) : (
                            <>
                              <span
                                className={`absolute top-[5px] right-0 h-4 rounded-l ${on ? 'bg-brand' : 'bg-brand/40'}`}
                                style={{ width }}
                              />
                              <span
                                className="absolute top-1 text-xs font-semibold whitespace-nowrap text-brand"
                                style={{ right: `calc(${width} + 8px)` }}
                              >
                                {gapText(it.gap)}
                              </span>
                            </>
                          )}
                        </span>
                        <span className="relative block h-[26px]">
                          {pos ? (
                            <>
                              <span
                                className={`absolute top-[5px] left-0 h-4 rounded-r ${on ? 'bg-warning' : 'bg-warning/40'}`}
                                style={{ width }}
                              />
                              <span
                                className="absolute top-1 text-xs font-semibold whitespace-nowrap text-warning"
                                style={{ left: `calc(${width} + 8px)` }}
                              >
                                {gapText(it.gap)}
                              </span>
                            </>
                          ) : (
                            <span
                              className="absolute top-1 left-3 flex max-w-[95%] items-center gap-1.5 text-[13px] text-heading"
                              title={it.description ?? name}
                            >
                              <span className="truncate">{name}</span>
                              {tag}
                            </span>
                          )}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
              <SourceLine
                source={`${sp.q ? 'Coincidencias' : `Los ${PER_SIDE} mayores de cada lado`} entre ${whole.format(total)} ${unit} con brecha en ${names[sp.country!]}${reviewed ? '' : ' · correspondencia carrera → ocupación sin revisar'}`}
              >
                <Link href="/metodologia/brechas" className="text-link hover:underline">
                  ¿Cómo se calcula la brecha?
                </Link>
              </SourceLine>
            </>
          )
        }
        rail={selected && <RowPanel row={selected} country={names[sp.country!] ?? ''} groups={groups} />}
      />
      {selected?.skills && selected.skills.length > 0 && <GroupSkills row={selected} />}
      {selected && selected.sectors.length > 0 && (
        <OccupationsBySector row={selected} iso3={sp.country!} groups={groups} />
      )}
      <div className="mt-10">
        <HowCalculated types={['skill_gap']} title="¿Cómo se calcula la brecha?" />
      </div>
    </>
  );
}

function RowPanel({ row, country, groups }: { row: Row; country: string; groups: boolean }) {
  const count = row.sectors.reduce((n, u) => n + u.occupations.length, 0);
  return (
    <RailCard>
      <Eyebrow>
        {groups ? 'Grupo elegido' : 'Habilidad elegida'} · {country}
      </Eyebrow>
      <div>
        <h2 className="text-xl leading-snug font-bold text-heading">{cap(row.name)}</h2>
        <p className="mt-0.5 text-xs text-muted-text">
          {[row.kicker, row.emerging ? 'Emergente' : null].filter(Boolean).join(' · ')}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Demanda / año" value={formatGrowth(row.demand)} />
        <Stat label="Formación / año" value={formatGrowth(row.supply)} />
        <Stat label="Brecha" value={gapText(row.gap)} />
        <Stat label="Ocupaciones" value={String(row.occupations)} />
      </div>
      {row.demand !== null && row.supply !== null && (
        <p className="-mt-1 text-[13px] leading-relaxed text-muted-text">
          La brecha viene sobre todo del lado de{' '}
          {Math.abs(row.supply) > Math.abs(row.demand) ? 'la formación' : 'la demanda'}.
        </p>
      )}
      {row.unstable.length > 0 && (
        <details className="group rounded-lg border border-alert-warning-border bg-alert-warning-bg px-3 py-2 text-[12px] leading-relaxed text-alert-warning-text">
          <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            {row.unstable.length === 1
              ? '1 ocupación quedó'
              : `${row.unstable.length} ocupaciones quedaron`}{' '}
            fuera de la formación{' '}
            <span className="underline group-open:hidden">por qué</span>
            <ChevronDown
              className="ml-0.5 inline size-3.5 align-[-2px] transition-transform group-open:rotate-180"
              aria-hidden
            />
          </summary>
          <p className="mt-1">
            {row.unstable.map((u) => u.name).join(', ')}: su serie de titulados tiene saltos bruscos
            de un año al otro (dato poco confiable).{' '}
            <Link href="/metodologia/brechas" className="font-medium underline hover:text-heading">
              ¿Cómo se calcula?
            </Link>
          </p>
        </details>
      )}
      {row.description && (
        <div className="border-t border-line/60 pt-3">
          <details className="group">
            <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
              <EscoText
                text={row.description}
                className="max-h-[3.75rem] overflow-hidden text-[13px] leading-5 text-body [mask-image:linear-gradient(to_bottom,black_55%,transparent)] group-open:max-h-none group-open:[mask-image:none]"
              />
              <span className="mt-0.5 inline-block text-[12px] font-medium text-brand">
                <span className="group-open:hidden">Leer más</span>
                <span className="hidden group-open:inline">Ver menos</span>
                <ChevronDown
                  className="ml-0.5 inline size-3.5 align-[-2px] transition-transform group-open:rotate-180"
                  aria-hidden
                />
              </span>
            </summary>
          </details>
          {row.descriptionOrigin === 'translation' && row.descriptionEn && (
            <details className="group/orig mt-1.5 text-[11px] text-muted-text">
              <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                Traducción no oficial del original de ESCO (en inglés) ·{' '}
                <span className="text-brand">
                  ver original
                  <ChevronDown
                    className="ml-0.5 inline size-3 align-[-2px] transition-transform group-open/orig:rotate-180"
                    aria-hidden
                  />
                </span>
              </summary>
              <EscoText text={row.descriptionEn} lang="en" className="mt-1 leading-relaxed" />
            </details>
          )}
          {!row.descriptionOrigin && (
            <p className="mt-1.5 text-[11px] text-muted-text">
              ESCO publica esta descripción solo en inglés; traducción pendiente.
            </p>
          )}
        </div>
      )}
      {row.skillsTotal ? (
        <a
          href="#habilidades-del-grupo"
          className="border-t border-line/60 pt-3 text-sm font-medium text-brand hover:underline"
        >
          Ver las {row.skillsTotal} habilidades que incluye ↓
        </a>
      ) : null}
      {count > 0 && (
        <a
          href="#ocupaciones"
          className={`${row.skillsTotal ? '-mt-1.5' : 'border-t border-line/60 pt-3'} text-sm font-medium text-brand hover:underline`}
        >
          Ver las {count} ocupaciones que {groups ? 'lo usan' : 'la usan'} ↓
        </a>
      )}
    </RailCard>
  );
}

const OCCUPATIONS_SHOWN = 8;
const essentials = (n: number) => `${n} ${n === 1 ? 'esencial' : 'esenciales'}`;
const optionals = (n: number) => `${n} ${n === 1 ? 'opcional' : 'opcionales'}`;

/** Bloque a lo ancho bajo el gráfico: qué ocupaciones usan la habilidad o el grupo, por sector. */
function OccupationsBySector({ row, iso3, groups }: { row: Row; iso3: string; groups: boolean }) {
  const count = row.sectors.reduce((n, u) => n + u.occupations.length, 0);
  const tally = (u: SectorUse) => ({
    essential: u.occupations.filter((o) => o.relation === 'essential').length,
    optional: u.occupations.filter((o) => o.relation !== 'essential').length,
  });
  return (
    <section id="ocupaciones" className="mt-10 scroll-mt-20" aria-label="Ocupaciones que la usan">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-xl font-bold text-heading">
          ¿Qué ocupaciones usan «{cap(row.name)}»?{' '}
          <span className="font-normal text-muted-text">({count})</span>
        </h2>
        {row.cross && (
          <span className="rounded-full bg-sector-knowledge-soft px-2.5 py-0.5 text-xs font-semibold text-sector-knowledge">
            Transversal: esencial en más de un sector
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-text">
        Según ESCO, {groups ? 'alguna habilidad del grupo es' : 'la habilidad es'} <strong>esencial</strong>{' '}
        u <strong>opcional</strong> para cada ocupación. La brecha se calcula con todas ellas.
      </p>
      <ul className="mt-4 flex flex-wrap gap-2" aria-label="Resumen por sector">
        {row.sectors.map((u) => {
          const t = tally(u);
          return (
            <li key={u.sector_code ?? 'otras'}>
              <a
                href={`#sector-${u.sector_code ?? 'otras'}`}
                className="inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-[13px] hover:border-brand"
              >
                <span className="font-semibold text-heading">{u.name}</span>
                <span className="text-muted-text">
                  {essentials(t.essential)}
                  {t.optional ? ` · ${optionals(t.optional)}` : ''}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
      <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {row.sectors.map((u) => {
          const t = tally(u);
          const first = u.occupations.slice(0, OCCUPATIONS_SHOWN);
          const rest = u.occupations.slice(OCCUPATIONS_SHOWN);
          const item = (o: SectorUse['occupations'][number]) => (
            <li key={o.occupation_code} className="flex items-start gap-2 text-[13px] leading-snug">
              <span
                className={`mt-0.5 shrink-0 rounded px-1.5 py-px text-[10px] font-semibold tracking-wide uppercase ${o.relation === 'essential' ? 'bg-heading text-white' : 'bg-surface-2 text-muted-text'}`}
              >
                {o.relation_label}
              </span>
              <span>
                <Link
                  href={`/ocupaciones/${o.occupation_code}?country=${iso3}`}
                  className="text-link hover:underline"
                >
                  {o.name}
                </Link>
                {o.via.length > 0 && (
                  <span className="block text-[11px] text-muted-text">vía {o.via.join(', ')}</span>
                )}
              </span>
            </li>
          );
          return (
            <div
              key={u.sector_code ?? 'otras'}
              id={`sector-${u.sector_code ?? 'otras'}`}
              className="scroll-mt-20 rounded-xl border border-line p-4"
            >
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-semibold text-heading">{u.name}</h3>
                <span className="text-xs text-muted-text">
                  {u.occupations.length} · {essentials(t.essential)}
                </span>
              </div>
              <ul className="mt-3 space-y-1.5">{first.map(item)}</ul>
              {rest.length > 0 && (
                <details className="group mt-2">
                  <summary className="cursor-pointer list-none text-[13px] font-medium text-brand hover:underline [&::-webkit-details-marker]:hidden">
                    <span className="group-open:hidden">+{rest.length} más</span>
                    <span className="hidden group-open:inline">Mostrar menos</span>
                  </summary>
                  <ul className="mt-1.5 space-y-1.5">{rest.map(item)}</ul>
                </details>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** Bloque a lo ancho bajo el gráfico: las habilidades de ESCO que junta el grupo, con su definición. */
function GroupSkills({ row }: { row: Row }) {
  const skills = row.skills ?? [];
  const total = row.skillsTotal ?? skills.length;
  return (
    <section id="habilidades-del-grupo" className="mt-10 scroll-mt-20" aria-label="Habilidades del grupo">
      <h2 className="text-xl font-bold text-heading">
        ¿Qué habilidades incluye «{cap(row.name)}»?{' '}
        <span className="font-normal text-muted-text">({total})</span>
      </h2>
      <p className="mt-1 text-sm text-muted-text">
        {total > skills.length
          ? `Las ${skills.length} con más peso en las ocupaciones, de las ${total} habilidades de ESCO que junta el grupo.`
          : `Las ${total} habilidades de ESCO que junta el grupo.`}{' '}
        Definiciones de ESCO.
      </p>
      <ul className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {skills.map((k) => (
          <li key={k.name} className="rounded-xl border border-line p-4">
            <p className="text-[14px] leading-snug font-semibold text-heading">{cap(k.name)}</p>
            {k.description && (
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted-text">{k.description}</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Texto de ESCO: respeta los saltos de línea y muestra sus subtítulos ("=== Inclusiones") como tales. */
function EscoText({ text, className, lang }: { text: string; className: string; lang?: string }) {
  return (
    <div lang={lang} className={className}>
      {text.split('\n').map((line, i) => {
        const heading = /^=+\s*(.+?)\s*=*$/.exec(line.trim());
        return heading ? (
          <p key={i} className="mt-2 font-semibold text-heading">
            {heading[1]}
          </p>
        ) : (
          <p key={i}>{line}</p>
        );
      })}
    </div>
  );
}
