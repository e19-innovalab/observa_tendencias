import Link from 'next/link';
import { BarChart3, Info, Table2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ChipGroup, SelectParam } from '@/components/data/UrlControls';
import { ErrorNote } from '@/components/data/ui';
import { getCountries } from '@/lib/api/panorama';
import { getSectorKpis } from '@/lib/api/graduatesExtended';

type SearchParams = { country?: string; anio?: string; sector_kpi?: string; vista_t?: string; vista_o?: string };
type Kpis = Awaited<ReturnType<typeof getSectorKpis>>;
type Item = Kpis['items'][number];

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const TOTAL = 'Total';
const percent = (v: number | null | undefined) => (v == null ? '—' : `${one.format(v)}%`);
const count = (v: number | null | undefined) => (v == null ? '—' : whole.format(v));
function Vacio({ text }: { text: string }) {
  return (
    <p className="flex items-center gap-2 p-5 text-sm text-muted-text">
      <Info className="size-4" aria-hidden /> {text}
    </p>
  );
}

const points = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${one.format(v)} pp`);

function Table({
  head,
  rows,
}: {
  head: string[];
  rows: { key: string; total: boolean; cells: React.ReactNode[] }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[46rem] text-sm">
        <thead className="bg-surface-2 text-left text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
          <tr>
            {head.map((h, i) => (
              <th key={h} scope="col" className={`px-3 py-3 ${i > 1 ? 'text-right' : ''}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-card-border">
          {rows.map((r) => (
            <tr key={r.key} className={r.total ? 'bg-surface-2 font-semibold' : 'hover:bg-surface'}>
              {r.cells.map((c, i) => (
                <td key={i} className={`px-3 py-2.5 ${i > 1 ? 'text-right' : ''}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({
  title,
  text,
  actions,
  children,
}: {
  title: string;
  text: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-card-border bg-canvas">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-card-border p-5">
        <div className="max-w-3xl">
          <h2 className="text-lg font-semibold text-heading">{title}</h2>
          <p className="mt-1 text-sm text-muted-text">{text}</p>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

function Vista({ sp, name }: { sp: SearchParams; name: 'vista_t' | 'vista_o' }) {
  const tabla = sp[name] === 'tabla';
  const href = (v: string) => {
    const params = new URLSearchParams();
    Object.entries(sp).forEach(([k, val]) => {
      if (val && k !== name) params.set(k, val);
    });
    if (v) params.set(name, v);
    const qs = params.toString();
    return qs ? `?${qs}` : '?';
  };
  const cls = (on: boolean) =>
    cn(
      'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12.5px] font-semibold',
      on ? 'bg-canvas text-brand shadow-sm' : 'text-muted-text hover:text-heading',
    );
  return (
    <div className="inline-flex shrink-0 rounded-lg bg-surface-2 p-0.5" role="group" aria-label="Ver como">
      <Link href={href('')} scroll={false} aria-pressed={!tabla} className={cls(!tabla)}>
        <BarChart3 className="size-4" aria-hidden /> Gráfico
      </Link>
      <Link href={href('tabla')} scroll={false} aria-pressed={tabla} className={cls(tabla)}>
        <Table2 className="size-4" aria-hidden /> Tabla
      </Link>
    </div>
  );
}

function Reparto({ rows }: { rows: { key: string; label: string; total: boolean; mujeres: number | null }[] }) {
  return (
    <div className="p-5">
      <div className="mb-4 flex flex-wrap items-center gap-4 text-[12px] text-muted-text">
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-brand" aria-hidden /> Mujeres
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-brand/25" aria-hidden /> Varones
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-0.5 bg-heading" aria-hidden /> Mitad (50 %)
        </span>
      </div>
      <ul className="space-y-4">
        {rows.map((r) => {
          const m = r.mujeres == null ? null : Math.max(0, Math.min(100, r.mujeres));
          return (
            <li key={r.key}>
              <div className="mb-1.5 flex items-baseline justify-between gap-3 text-[13px]">
                <span className={cn('min-w-0', r.total ? 'font-semibold text-heading' : 'text-body')}>{r.label}</span>
                {m != null && (
                  <span className="shrink-0 text-[12px] text-muted-text">
                    <span className="font-semibold text-heading">{percent(m)}</span> mujeres
                  </span>
                )}
              </div>
              {m == null ? (
                <p className="text-[12px] text-muted-text">Sin dato</p>
              ) : (
                <div className="relative flex h-6 overflow-hidden rounded-md">
                  <span className="h-full bg-brand" style={{ width: `${m}%` }} />
                  <span className="h-full flex-1 bg-brand/25" />
                  <span className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-heading" aria-hidden />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Indicadores de género: titulados y ocupados por sexo, sus brechas y el diagnóstico de paridad. */
export async function GenderView({ sp }: { sp: SearchParams }) {
  let kpis: Kpis, catalog;
  try {
    [kpis, catalog] = await Promise.all([getSectorKpis(), getCountries()]);
  } catch (e) {
    return (
      <ErrorNote
        message={e instanceof Error ? e.message : 'Error inesperado al cargar los datos.'}
      />
    );
  }
  const countryOptions = catalog.map((c) => ({ value: c.iso3, label: c.name_es }));
  const names = Object.fromEntries(catalog.map((c) => [c.iso3, c.name_es]));
  const country = countryOptions.some((o) => o.value === sp.country) ? sp.country : undefined;
  const countries = countryOptions.map((o) => o.value).filter((c) => !country || c === country);
  const withGender = kpis.items.filter(
    (i) => i.pct_mujeres_graduadas != null || i.pct_mujeres_ocupadas != null,
  );
  const years = [...new Set(withGender.map((i) => i.anio))].sort((a, b) => b - a);
  const year = years.includes(Number(sp.anio)) ? Number(sp.anio) : undefined;
  const sectors = [...new Set(withGender.map((i) => i.sector))]
    .filter((s) => s !== TOTAL)
    .sort((a, b) => a.localeCompare(b, 'es'));
  const allSectors = [...sectors, TOTAL];
  const sector = allSectors.includes(sp.sector_kpi ?? '') ? sp.sector_kpi! : TOTAL;

  /** Por país y sector: la fila del año elegido o, sin año, la última que tiene el dato. */
  const rowsFor = (has: (i: Item) => boolean) =>
    countries.flatMap((c) =>
      allSectors.flatMap((s) => {
        const found = kpis.items
          .filter((i) => i.pais === c && i.sector === s && has(i) && (!year || i.anio === year))
          .at(-1);
        return found ? [found] : [];
      }),
    );
  const graduates = rowsFor((i) => i.pct_mujeres_graduadas != null);
  const employed = rowsFor((i) => i.pct_mujeres_ocupadas != null);
  const place = (i: Item) => [names[i.pais] ?? i.pais, i.sector];
  const line = (field: 'pct_mujeres_graduadas' | 'pct_mujeres_ocupadas') =>
    [...years]
      .reverse()
      .map((y) => {
        const row: Record<string, string | number | null> = { label: String(y) };
        for (const c of countries) {
          row[c] =
            kpis.items.find((i) => i.pais === c && i.sector === sector && i.anio === y)?.[field] ?? null;
        }
        return row;
      })
      .filter((row) => countries.some((c) => row[c] !== null));
  const series = countries.map((c) => ({ key: c, label: c, color: COUNTRY_COLORS[c] ?? FALLBACK_COLOR }));

  return (
    <>
      <section className="rounded-xl border border-card-border bg-canvas p-4">
        <ChipGroup name="country" label="País" value={country ?? ''} options={countryOptions} />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SelectParam
            name="anio"
            label="Año de las tablas"
            value={year ? String(year) : ''}
            placeholder="Último con datos"
            options={years.map((y) => ({ value: String(y), label: String(y) }))}
          />
          <SelectParam
            name="sector_kpi"
            label="Sector de los gráficos"
            value={sector}
            options={allSectors.map((s) => ({ value: s, label: s }))}
          />
        </div>
      </section>

      <section className="rounded-xl border border-card-border bg-rail p-4 text-sm text-body">
        <p className="flex items-center gap-2 font-semibold text-heading">
          <Info className="size-4" aria-hidden /> Cómo leerlo
        </p>
        <p className="mt-1">{kpis.genero_nota}</p>
      </section>

      <Section
        actions={<Vista sp={sp} name="vista_t" />}
        title="Titulados por sexo"
        text="Cuántas personas se titulan y cómo se reparten. La brecha es el % de mujeres menos el % de varones: positiva significa más mujeres. Argentina publica el sexo solo para el total del país; la categoría no binaria solo aparece en Chile."
      >
        {graduates.length === 0 ? (
          <Vacio text="Todavía no hay datos de titulados por sexo para mostrar." />
        ) : (
          <>
            {sp.vista_t !== 'tabla' ? (
              <Reparto
                rows={graduates.map((i) => ({
                  key: `${i.pais}-${i.sector}`,
                  label: `${names[i.pais] ?? i.pais} · ${i.sector} (${i.anio})`,
                  total: i.sector === TOTAL,
                  mujeres: i.pct_mujeres_graduadas ?? null,
                }))}
              />
            ) : (
            <Table
              head={['País', 'Sector', 'Mujeres', 'Varones', 'No binario', '% mujeres', '% varones', 'Brecha', 'Diagnóstico', 'Año']}
              rows={graduates.map((i) => ({
                key: `${i.pais}-${i.sector}`,
                total: i.sector === TOTAL,
                cells: [
                  ...place(i),
                  count(i.f),
                  count(i.m),
                  i.nb ? count(i.nb) : '—',
                  percent(i.pct_mujeres_graduadas),
                  percent(i.pct_varones_graduados),
                  points(i.brecha_graduados_pct),
                  i.diagnostico_paridad ?? '—',
                  i.anio,
                ],
              }))}
            />
            )}
            <div className="grid gap-6 border-t border-card-border p-5">
              <div>
                <h3 className="mb-2 text-sm font-semibold text-heading">
                  {sector}: % de mujeres entre titulados
                </h3>
                <TrendLineChart data={line('pct_mujeres_graduadas')} series={series} unit="percent" />
              </div>
            </div>
          </>
        )}
      </Section>

      <Section
        actions={<Vista sp={sp} name="vista_o" />}
        title="Personas ocupadas y salarios"
        text="Participación de las mujeres en el empleo del sector (OIT). La brecha de empleo es el % de mujeres menos el % de varones. La brecha salarial es cuánto menos ganan las mujeres que los varones, sin ajustar por ocupación ni horas; negativa significa que ganan más."
      >
        {employed.length === 0 ? (
          <Vacio text="Todavía no hay datos de ocupados por sexo para mostrar." />
        ) : (
          <>
            {sp.vista_o !== 'tabla' ? (
              <Reparto
                rows={employed.map((i) => ({
                  key: `${i.pais}-${i.sector}`,
                  label: `${names[i.pais] ?? i.pais} · ${i.sector} (${i.anio})`,
                  total: i.sector === TOTAL,
                  mujeres: i.pct_mujeres_ocupadas ?? null,
                }))}
              />
            ) : (
            <Table
              head={['País', 'Sector', '% mujeres', 'Brecha de empleo', 'Brecha salarial', 'Diagnóstico', 'Año']}
              rows={employed.map((i) => ({
                key: `${i.pais}-${i.sector}`,
                total: i.sector === TOTAL,
                cells: [
                  ...place(i),
                  percent(i.pct_mujeres_ocupadas),
                  points(i.brecha_empleo_pct),
                  percent(i.brecha_salarial_pct),
                  i.diagnostico_empleo ?? '—',
                  i.anio,
                ],
              }))}
            />
            )}
            <div className="border-t border-card-border p-5">
              <h3 className="mb-2 text-sm font-semibold text-heading">
                {sector}: % de mujeres entre ocupados
              </h3>
              <TrendLineChart data={line('pct_mujeres_ocupadas')} series={series} unit="percent" />
            </div>
          </>
        )}
      </Section>
    </>
  );
}
