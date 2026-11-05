import { Info } from 'lucide-react';
import { ProjectionChart, type ProjectionRow } from '@/components/ui/charts/ProjectionChart';
import { TrendLineChart } from '@/components/ui/charts/TrendLineChart';
import { COUNTRY_COLORS, FALLBACK_COLOR } from '@/components/ui/charts/chartTheme';
import { ChipGroup, SelectParam } from '@/components/ui/filters/UrlControls';
import { ErrorNote } from '@/components/minimal/ui';
import { getCountries } from '@/lib/api/common';
import { getSectorKpis } from '@/lib/api/skills';

type SearchParams = { country?: string; anio?: string; sector_kpi?: string };
type Kpis = Awaited<ReturnType<typeof getSectorKpis>>;
type Item = Kpis['items'][number];
type CepItem = Kpis['cep_xxi'][number];
type CepField = 'puestos' | 'pct_mujeres' | 'salario_usd' | 'salario_usd_ppa' | 'salario_ars' | 'indice_real';
type NumericField = 'densidad' | 'ocupados' | 'pct_mujeres_graduadas' | 'pct_mujeres_ocupadas'
  | 'salario_mujeres' | 'salario_varones' | 'brecha_salarial_pct' | 'graduados';

const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const TOTAL = 'Total';

/** Filas por sector y columnas por país: el valor del año elegido o el último de cada celda. */
function SectorTable({ sectors, countries, cell, columns }: {
  sectors: string[];
  countries: string[];
  cell: (sector: string, country: string, column: string) => { text: string; year?: number } | null;
  columns: { key: string; label: string }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
          <tr>
            <th scope="col" className="sticky left-0 bg-surface-2 px-4 py-3">Sector</th>
            {countries.flatMap((c) => columns.map((col) => (
              <th key={`${c}-${col.key}`} scope="col" className="px-3 py-3 text-right">{c}{col.label ? ` · ${col.label}` : ''}</th>
            )))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/60">
          {sectors.map((s) => (
            <tr key={s} className={s === TOTAL ? 'bg-surface-2 font-semibold' : 'hover:bg-surface'}>
              <th scope="row" className={`sticky left-0 px-4 py-3 text-left font-medium text-heading ${s === TOTAL ? 'bg-surface-2' : 'bg-white'}`}>{s}</th>
              {countries.flatMap((c) => columns.map((col) => {
                const v = cell(s, c, col.key);
                return (
                  <td key={`${c}-${col.key}`} className="px-3 py-3 text-right">
                    {v ? v.text : '—'}
                    {v?.year && <span className="block text-[11px] font-normal text-muted-text">{v.year}</span>}
                  </td>
                );
              }))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, text, children }: { title: string; text: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-white">
      <div className="border-b border-line/70 p-5">
        <h2 className="text-lg font-semibold text-heading">{title}</h2>
        <p className="mt-1 text-sm text-muted-text">{text}</p>
      </div>
      {children}
    </section>
  );
}

export async function SectorKpisView({ sp }: { sp: SearchParams }) {
  let kpis: Kpis, catalog;
  try {
    [kpis, catalog] = await Promise.all([getSectorKpis(), getCountries()]);
  } catch (e) {
    return <ErrorNote message={e instanceof Error ? e.message : 'Error inesperado al cargar los datos.'} />;
  }
  const countryOptions = catalog.map((c) => ({ value: c.iso3, label: c.name_es }));
  const country = countryOptions.some((o) => o.value === sp.country) ? sp.country : undefined;
  const countries = countryOptions.map((o) => o.value).filter((c) => !country || c === country);
  const years = [...new Set(kpis.items.map((i) => i.anio))].sort((a, b) => b - a);
  const year = years.includes(Number(sp.anio)) ? Number(sp.anio) : undefined;
  const sectors = [...new Set(kpis.items.map((i) => i.sector))].filter((s) => s !== TOTAL).sort((a, b) => a.localeCompare(b, 'es'));
  const allSectors = [...sectors, TOTAL];
  const sector = allSectors.includes(sp.sector_kpi ?? '') ? sp.sector_kpi! : TOTAL;

  const byKey = new Map<string, Item>(kpis.items.map((i) => [`${i.pais}|${i.sector}|${i.anio}`, i]));
  /** La fila del año elegido o, sin año, la última con dato en ese campo. */
  const pick = (c: string, s: string, field: NumericField): Item | null => {
    if (year) {
      const row = byKey.get(`${c}|${s}|${year}`);
      return row && row[field] != null ? row : null;
    }
    return kpis.items.filter((i) => i.pais === c && i.sector === s && i[field] != null).at(-1) ?? null;
  };
  const cellFor = (field: NumericField, format: (v: number) => string) => (s: string, c: string) => {
    const row = pick(c, s, field);
    return row ? { text: format(row[field] as number), year: year ? undefined : row.anio } : null;
  };
  /** Una línea por país para el sector elegido. */
  const lineRows = (field: NumericField) => [...years].reverse().map((y) => {
    const row: Record<string, string | number | null> = { label: String(y) };
    for (const c of countries) {
      const value = byKey.get(`${c}|${sector}|${y}`)?.[field];
      row[c] = value ?? null;
    }
    return row;
  }).filter((row) => countries.some((c) => row[c] !== null));
  const lineSeries = countries.map((c) => ({ key: c, label: c, color: COUNTRY_COLORS[c] ?? FALLBACK_COLOR }));
  const percent = (v: number) => `${one.format(v)}%`;
  const number = (v: number) => whole.format(v);

  // Proyección: titulados observados y proyectados del sector, en los países que la tienen.
  const projectionCountries = [...new Set(kpis.proyecciones.filter((p) => p.sector === sector).map((p) => p.pais))]
    .filter((c) => countries.includes(c));
  const projectionCharts = projectionCountries.map((c) => {
    const observed = kpis.items.filter((i) => i.pais === c && i.sector === sector && i.graduados != null);
    const projected = kpis.proyecciones.filter((p) => p.pais === c && p.sector === sector);
    const rows: ProjectionRow[] = [
      ...observed.map((o, i) => ({
        anio: o.anio,
        observado: o.graduados as number,
        ...(i === observed.length - 1 ? { union: o.graduados as number } : {}),
      })),
      ...projected.map((p, i) => ({
        anio: p.anio,
        valor: p.valor,
        banda: [p.limite_inferior ?? p.valor, p.limite_superior ?? p.valor] as [number, number],
        ...(i === 0 ? { union: p.valor } : {}),
      })),
    ];
    return { country: c, rows };
  });

  // CEP-XXI: las filas vienen ordenadas por sector y año.
  const cepCell = (field: CepField, format: (v: number) => string) => (s: string) => {
    const rows = kpis.cep_xxi.filter((i) => i.sector === s && i[field] != null && (!year || i.anio === year));
    const row: CepItem | undefined = rows.at(-1);
    return row ? { text: format(row[field] as number), year: year ? undefined : row.anio } : null;
  };
  const cepColumns: { key: CepField; label: string; format: (v: number) => string }[] = [
    { key: 'puestos', label: 'Puestos', format: number },
    { key: 'pct_mujeres', label: '% mujeres', format: percent },
    { key: 'salario_usd', label: 'USD', format: (v) => `USD ${whole.format(v)}` },
    { key: 'salario_usd_ppa', label: 'USD PPA', format: (v) => `USD PPA ${whole.format(v)}` },
    { key: 'salario_ars', label: 'Pesos', format: (v) => `$ ${whole.format(v)}` },
    { key: 'indice_real', label: `Salario real (${kpis.cep_base} = 100)`, format: (v) => one.format(v) },
  ];
  const cepLine = (field: CepField) => kpis.cep_xxi
    .filter((i) => i.sector === sector && i[field] != null)
    .map((i) => ({ label: String(i.anio), ARG: i[field] as number }));
  const cepSeries = (label: string) => [{ key: 'ARG', label, color: COUNTRY_COLORS.ARG ?? FALLBACK_COLOR }];

  return (
    <>
      <section className="rounded-lg border border-line bg-white p-4">
        <ChipGroup name="country" label="País" value={country ?? ''} options={countryOptions} />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SelectParam name="anio" label="Año de las tablas" value={year ? String(year) : ''} placeholder="Último con datos" options={years.map((y) => ({ value: String(y), label: String(y) }))} />
          <SelectParam name="sector_kpi" label="Sector de los gráficos" value={sector} options={allSectors.map((s) => ({ value: s, label: s }))} />
        </div>
      </section>

      <section className="rounded-lg border border-line bg-surface p-4 text-sm text-body">
        <p className="flex items-center gap-2 font-semibold text-heading"><Info className="size-4" aria-hidden /> Alcance</p>
        <p className="mt-1">{kpis.nota}</p>
      </section>

      <Section
        title="Densidad profesional"
        text="Titulados del año por cada 1.000 personas ocupadas en el sector. Alto significa que se forma mucha gente en relación con el empleo actual. Es aproximada: en Energía compara carreras que incluyen electricidad y minería con el empleo de electricidad y gas, así que no se lee como valor absoluto."
      >
        <SectorTable sectors={allSectors} countries={countries} columns={[{ key: 'v', label: '' }]} cell={cellFor('densidad', (v) => one.format(v))} />
        <div className="border-t border-line/70 p-5">
          <h3 className="mb-2 text-sm font-semibold text-heading">{sector}: titulados por cada 1.000 ocupados</h3>
          <TrendLineChart data={lineRows('densidad')} series={lineSeries} unit="number" />
        </div>
      </Section>

      <Section
        title="Salarios y brecha salarial"
        text="Ingreso mensual promedio de las personas asalariadas en dólares a paridad de poder adquisitivo (OIT). La brecha es cuánto menos ganan las mujeres que los varones; negativa significa que ganan más. Compara promedios sin ajustar por ocupación ni horas, y en sectores chicos puede variar mucho."
      >
        <SectorTable
          sectors={allSectors}
          countries={countries}
          columns={[{ key: 'f', label: 'Mujeres' }, { key: 'm', label: 'Varones' }, { key: 'b', label: 'Brecha' }]}
          cell={(s, c, col) => (col === 'f'
            ? cellFor('salario_mujeres', number)(s, c)
            : col === 'm'
              ? cellFor('salario_varones', number)(s, c)
              : cellFor('brecha_salarial_pct', percent)(s, c))}
        />
        <div className="border-t border-line/70 p-5">
          <h3 className="mb-2 text-sm font-semibold text-heading">{sector}: brecha salarial por año</h3>
          <TrendLineChart data={lineRows('brecha_salarial_pct')} series={lineSeries} unit="percent" />
        </div>
      </Section>

      <Section title="Personas ocupadas" text="Personas ocupadas por sector según la OIT. Un sector de Economía del conocimiento incluye Información y comunicación, que también es Tecnología, así que los sectores no se suman.">
        <SectorTable sectors={allSectors} countries={countries} columns={[{ key: 'v', label: '' }]} cell={cellFor('ocupados', number)} />
      </Section>

      {(!country || country === 'ARG') && kpis.cep_xxi.length > 0 && (
        <Section title="Argentina: empleo privado registrado y salarios (CEP-XXI)" text={kpis.cep_nota}>
          {kpis.dolar_oficial && (
            <p className="border-b border-line/70 px-5 py-3 text-sm text-body">
              {kpis.dolar_oficial.nombre}: <strong>$ {new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2 }).format(kpis.dolar_oficial.valor)}</strong> del <strong>{kpis.dolar_oficial.fecha.split('-').reverse().join('/')}</strong>.
            </p>
          )}
          <SectorTable
            sectors={allSectors}
            countries={['ARG']}
            columns={cepColumns.map(({ key, label }) => ({ key, label }))}
            cell={(s, _c, col) => {
              const column = cepColumns.find((c) => c.key === col);
              return column ? cepCell(column.key, column.format)(s) : null;
            }}
          />
          <div className="grid gap-6 border-t border-line/70 p-5 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-semibold text-heading">{sector}: puestos de trabajo</h3>
              <TrendLineChart data={cepLine('puestos')} series={cepSeries('Puestos')} unit="number" />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-heading">{sector}: salario real ({kpis.cep_base} = 100)</h3>
              <TrendLineChart data={cepLine('indice_real')} series={cepSeries('Salario real')} unit="number" />
            </div>
          </div>
        </Section>
      )}

      <Section
        title="Titulados por sector, con proyección"
        text="Serie de titulados del sector y proyección orientativa. Solo hay proyección con al menos 12 años de historia sin huecos, por eso hoy es solo para Chile. Elegí el sector arriba."
      >
        {projectionCharts.length === 0 ? (
          <p className="p-5 text-sm text-muted-text">No hay proyección para {sector} con estos filtros. Probá con un sector y Chile.</p>
        ) : projectionCharts.map((chart) => (
          <div key={chart.country} className="p-5">
            <h3 className="mb-2 text-sm font-semibold text-heading">{sector} · {chart.country}</h3>
            <ProjectionChart data={chart.rows} color={COUNTRY_COLORS[chart.country] ?? FALLBACK_COLOR} />
          </div>
        ))}
      </Section>
    </>
  );
}
