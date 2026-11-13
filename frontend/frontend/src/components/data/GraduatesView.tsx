import { Info } from 'lucide-react';
import Link from 'next/link';
import { ProjectionChart, type ProjectionRow } from '@/components/ui/charts/ProjectionChart';
import { COUNTRY_COLORS } from '@/components/ui/charts/chartTheme';
import { ChipGroup, Segmented, SelectParam } from '@/components/data/UrlControls';
import { ErrorNote } from '@/components/data/ui';
import { getCountries, getSectors } from '@/lib/api/panorama';
import {
  getGraduateInstitutions,
  getGraduateSeries,
  getGraduateTrendsExtended,
  getGraduateTotals,
  getGraduatesByYear,
  getInstitutionCareers,
  getInstitutionList,
  getProjectionsRaw,
} from '@/lib/api/graduatesExtended';

type SearchParams = {
  carrera?: string;
  anio?: string;
  sector_carrera?: string;
  tema?: string;
  desde?: string;
  hasta?: string;
  proyeccion?: string;
  country?: string;
  institucion?: string;
};
const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

function ErrorBox({ error }: { error: unknown }) {
  return (
    <ErrorNote
      message={error instanceof Error ? error.message : 'Error inesperado al cargar los datos.'}
    />
  );
}

const TREND_LABELS: Record<string, string> = {
  growing: 'Creciente',
  declining: 'Decreciente',
  stable: 'Estable',
  insufficient_data: 'Datos insuficientes',
};
const COUNTRY_ISO: Record<string, string> = { argentina: 'ARG', chile: 'CHL', uruguay: 'URY' };
const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const TOP_PER_COUNTRY = 15;
const OTHER_SECTOR = { value: 'otros', label: 'Otros' };
const TOP_INSTITUTIONS = 15;

export async function GraduatesView({ sp }: { sp: SearchParams }) {
  const askedYear = /^\d{4}$/.test(sp.anio ?? '') ? sp.anio : undefined;
  let trends, projections, byYear, sectors, totals, catalogCountries, institutionNames;
  try {
    [trends, projections, byYear, sectors, totals, catalogCountries, institutionNames] =
      await Promise.all([
        getGraduateTrendsExtended(),
        getProjectionsRaw(),
        getGraduatesByYear(askedYear),
        getSectors(),
        getGraduateTotals({ sector: sp.sector_carrera, tema: sp.tema }),
        getCountries(),
        getInstitutionList(),
      ]);
  } catch (e) {
    return <ErrorBox error={e} />;
  }
  const countryOptions = catalogCountries.map((c) => ({ value: c.iso3, label: c.name_es }));
  const country = countryOptions.some((o) => o.value === sp.country) ? sp.country : undefined;
  const listed = institutionNames.filter((i) => !country || COUNTRY_ISO[i.pais] === country);
  const institution = listed.find((i) => i.institucion === sp.institucion);
  // An institution's own graduates per career and year: every figure of the tab comes from here.
  let institutionData: Awaited<ReturnType<typeof getInstitutionCareers>>['carreras'] = [];
  if (institution) {
    try {
      institutionData = (await getInstitutionCareers(institution.institucion)).carreras.filter(
        (c) => c.pais === institution.pais,
      );
    } catch (e) {
      return <ErrorBox error={e} />;
    }
  }
  const institutionYears = [...new Set(institutionData.flatMap((c) => Object.keys(c.por_anio)))].sort();
  // a year the institution has no data for would only empty the tab
  const year = !institution || institutionYears.includes(askedYear ?? '') ? askedYear : undefined;
  const institutionYear = year ?? institutionYears.at(-1);
  const ownValues = new Map(institutionData.map((c) => [`${c.pais}|${c.nombre}`, c]));
  const inCountry = (t: { pais: string }) =>
    institution ? t.pais === institution.pais : !country || COUNTRY_ISO[t.pais] === country;
  const sectorOptions = [...sectors.map((s) => ({ value: s.sector_code, label: s.name })), OTHER_SECTOR];
  const sectorLabel = (code: string | null) =>
    sectorOptions.find((o) => o.value === code)?.label ?? OTHER_SECTOR.label;
  const topicOptions = [...new Set(trends.items.map((t) => t.tema).filter((t): t is string => !!t))]
    .sort((a, b) => a.localeCompare(b, 'es'))
    .map((t) => ({ value: t, label: t }));
  const inSector = (t: { sector: string | null }) =>
    !sp.sector_carrera || (t.sector ?? OTHER_SECTOR.value) === sp.sector_carrera;
  const yearValues = new Map(byYear.items.map((i) => [`${i.pais}|${i.nombre}`, i]));
  const keyOf = (t: { pais: string; nombre: string }) => `${t.pais}|${t.nombre}`;
  const ownAmount = (t: { pais: string; nombre: string }) =>
    ownValues.get(keyOf(t))?.por_anio[institutionYear ?? ''] ?? 0;
  const amount = (t: { pais: string; nombre: string; graduados_ultimo: number }) =>
    institution ? ownAmount(t) : year ? (yearValues.get(keyOf(t))?.graduados ?? 0) : t.graduados_ultimo;
  const hasData = (t: { pais: string; nombre: string }) =>
    institution ? ownAmount(t) > 0 : !year || yearValues.has(keyOf(t));
  const allItems = [...trends.items]
    .filter((t) => inCountry(t) && hasData(t) && inSector(t) && (!sp.tema || t.tema === sp.tema))
    .sort((a, b) => a.pais.localeCompare(b.pais) || amount(b) - amount(a));
  const shownCount: Record<string, number> = {};
  const items = allItems.filter((t) => {
    if (sp.tema || institution) return true; // few rows: all of them are shown
    shownCount[t.pais] = (shownCount[t.pais] ?? 0) + 1;
    return shownCount[t.pais] <= TOP_PER_COUNTRY;
  });
  // Graduates per sector and country: only careers of the source, since programs found by topic
  // also count diplomas and are already part of them. Partial for a projected year, so not shown.
  const projectedYear = !!year && byYear.anios_proyectados.includes(Number(year));
  const countries = [...new Set(trends.items.filter(inCountry).map((t) => t.pais))].sort();
  // Same rule as the country totals: programs found by topic count only when a topic is chosen.
  const ownTotal: Record<string, number> = {};
  for (const c of institutionData) {
    if ((c.es_seguimiento && !sp.tema) || !inSector(c) || (sp.tema && c.tema !== sp.tema)) continue;
    for (const [y, v] of Object.entries(c.por_anio)) ownTotal[y] = (ownTotal[y] ?? 0) + v;
  }
  const countryTotals = institution
    ? [{ pais: institution.pais, por_anio: ownTotal }]
    : totals.paises.filter(inCountry);
  const totalYears = institution
    ? Object.keys(ownTotal).sort().map(Number)
    : totals.anios.filter((y) => countryTotals.some((c) => c.por_anio[String(y)] !== undefined));
  const careers = trends.items.filter((t) => !t.es_seguimiento && hasData(t));
  const latestYear = (pais: string) =>
    (institution ? institutionYear : year) ??
    Math.max(
      ...trends.items.filter((t) => t.pais === pais).map((t) => t.anio_hasta),
    );
  const sectorTotal = (pais: string, code?: string) =>
    careers
      .filter((t) => t.pais === pais && (code === undefined || (t.sector ?? OTHER_SECTOR.value) === code))
      .reduce((sum, t) => sum + amount(t), 0);
  const withProjection = new Set(projections.map(keyOf));
  // every career with a projection can be opened in the chart, not only those in the table
  const chartCareers = [...trends.items]
    .filter(
      (t) =>
        inCountry(t) &&
        inSector(t) &&
        (!sp.tema || t.tema === sp.tema) &&
        (!institution || ownValues.has(keyOf(t))),
    )
    .sort((a, b) =>
      institution ? ownAmount(b) - ownAmount(a) : b.graduados_ultimo - a.graduados_ultimo,
    )
    .map(keyOf);
  const selected = chartCareers.includes(sp.carrera ?? '')
    ? sp.carrera!
    : (chartCareers.find((k) => withProjection.has(k)) ?? chartCareers[0]);
  const yearOptions = institution
    ? [...institutionYears].reverse().map((y) => ({ value: y, label: y }))
    : [
        ...[...byYear.anios_proyectados]
          .reverse()
          .map((y) => ({ value: String(y), label: `${y} (proyección)` })),
        ...[...byYear.anios_observados].reverse().map((y) => ({ value: String(y), label: String(y) })),
      ];
  const institutionOptions = listed.map((i) => ({
    value: i.institucion,
    label: country ? i.institucion : `${i.institucion} (${COUNTRY_ISO[i.pais] ?? i.pais})`,
  }));
  const filters = (
    <section className="rounded-lg border border-line bg-canvas p-4">
      <ChipGroup
        name="country"
        label="País"
        value={country ?? ''}
        options={countryOptions}
        reset={['carrera', 'desde', 'hasta', 'institucion']}
      />
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SelectParam
          name="anio"
          label="Año"
          value={year ?? ''}
          placeholder={institution ? 'Último con datos' : 'Último de cada país'}
          options={yearOptions}
        />
        <SelectParam
          name="institucion"
          label="Institución"
          value={institution?.institucion ?? ''}
          placeholder="Todas"
          options={institutionOptions}
          reset={['carrera', 'desde', 'hasta']}
        />
        <SelectParam
          name="sector_carrera"
          label="Sector"
          value={sp.sector_carrera ?? ''}
          placeholder="Todos"
          options={sectorOptions}
        />
        <SelectParam
          name="tema"
          label="Tema"
          value={sp.tema ?? ''}
          placeholder="Todos"
          options={topicOptions}
        />
      </div>
    </section>
  );
  if (countries.length === 0) {
    return (
      <>
        {filters}
        <section className="rounded-lg border border-line bg-surface p-4 text-sm text-body">
          <p className="flex items-center gap-2 font-semibold text-heading">
            <Info className="size-4" aria-hidden /> Sin series por carrera para este país
          </p>
        </section>
      </>
    );
  }
  const [pais, nombre] = (selected ?? '|').split('|');
  let observed: { anio: number; graduados: number }[] = [];
  let institutions: Awaited<ReturnType<typeof getGraduateInstitutions>> | null = null;
  if (selected && institution) {
    observed = Object.entries(ownValues.get(selected)?.por_anio ?? {})
      .map(([y, v]) => ({ anio: Number(y), graduados: v }))
      .sort((a, b) => a.anio - b.anio);
  } else if (selected) {
    try {
      const [series, byInstitution] = await Promise.all([
        getGraduateSeries(pais, nombre),
        getGraduateInstitutions(pais, nombre),
      ]);
      observed = series.puntos;
      institutions = byInstitution;
    } catch (e) {
      return <ErrorBox error={e} />;
    }
  }
  // projections are per career in the whole country: there are none for one institution
  const projectedRows = institution
    ? []
    : projections.filter((p) => p.pais === pais && p.nombre === nombre).sort((a, b) => a.anio - b.anio);
  const showProjection = sp.proyeccion !== 'sin' && projectedRows.length > 0;
  const lastObserved = observed.at(-1);
  const chartRows: ProjectionRow[] = [
    ...observed.map((o) => ({
      anio: o.anio,
      observado: o.graduados,
      ...(showProjection && o === lastObserved ? { union: o.graduados } : {}),
    })),
    ...(showProjection ? projectedRows : []).map((p, i) => ({
      anio: p.anio,
      valor: p.graduados_proyectado,
      banda: [p.limite_inferior, p.limite_superior] as [number, number],
      ...(i === 0 ? { union: p.graduados_proyectado } : {}),
    })),
  ];
  const chartYears = chartRows.map((r) => r.anio);
  const pickYear = (value: string | undefined, fallback: number | undefined) =>
    chartYears.includes(Number(value)) ? Number(value) : fallback;
  const fromYear = pickYear(sp.desde, chartYears[0]) ?? 0;
  const toYear = pickYear(sp.hasta, chartYears.at(-1)) ?? 0;
  const [start, end] = fromYear <= toYear ? [fromYear, toYear] : [toYear, fromYear];
  const rows = chartRows.filter((r) => r.anio >= start && r.anio <= end);
  const detailYears = (institutions?.anios ?? []).filter((y) => y >= start && y <= end);
  const topicLabel = sp.tema ? `del tema ${sp.tema}` : '';
  const sectorScope = sp.sector_carrera ? `del sector ${sectorLabel(sp.sector_carrera)}` : '';
  const rangeOptions = chartYears.map((y) => ({
    value: String(y),
    label: lastObserved && y > lastObserved.anio ? `${y} (proyección)` : String(y),
  }));
  const trend = trends.items.find((t) => t.pais === pais && t.nombre === nombre);
  // links to the chart keep the table's filters, so the selected career stays available
  const chartHref = (key: string) => {
    const params = new URLSearchParams({ tab: 'titulados', carrera: key });
    if (country) params.set('country', country);
    if (year) params.set('anio', year);
    if (institution) params.set('institucion', institution.institucion);
    if (sp.sector_carrera) params.set('sector_carrera', sp.sector_carrera);
    if (sp.tema) params.set('tema', sp.tema);
    return `/habilidades?${params}`;
  };

  return (
    <>
      {filters}

      <section className="rounded-lg border border-line bg-surface p-4 text-sm text-body">
        <p className="flex items-center gap-2 font-semibold text-heading">
          <Info className="size-4" aria-hidden /> Alcance
        </p>
        <p className="mt-1">
          Cada fila usa el nombre que publica la fuente: las carreras genéricas de Mi Futuro, las
          disciplinas del Anuario argentino y, cuando hay un tema, el programa tal como figura en el
          archivo de titulados. En Uruguay los nombres cambian entre anuarios, así que se unifican
          con una tabla propia; hay datos desde 2020, por lo que todavía no hay proyección. El sector
          sale del campo CINE-F de la carrera; los programas con tema toman el sector de su tema. El
          tema es un filtro propio, no un título: esos programas incluyen diplomados y posgrados, así
          que no se comparan con las carreras genéricas. La proyección solo se genera con al menos 12
          años de historia sin huecos. {trends.source}
        </p>
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-canvas">
        <div className="border-b border-line/70 p-5">
          <h2 className="text-lg font-semibold text-heading">
            Titulados por sector{institution ? ` · ${institution.institucion}` : ''}
          </h2>
          <p className="mt-1 text-sm text-muted-text">
            {institution
              ? `Titulados de esta institución en ${institutionYear}. Solo carreras genéricas y disciplinas, para no contar dos veces.`
              : projectedYear
                ? `La proyección de ${year} no existe para todas las carreras: elegí un año observado para ver el total por sector.`
                : 'Solo carreras genéricas y disciplinas, para no contar dos veces. Los países no cuentan el mismo nivel (Argentina: pregrado y grado; Chile: pregrado; Uruguay: grado): compará la participación de cada sector, no el total. Argentina publica disciplinas amplias, sin Energía ni Turismo aparte: ese 0 significa que la fuente no las separa, no que no haya titulados; sus titulados están en otras filas, como Otros.'}
          </p>
        </div>
        {(institution || !projectedYear) && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-sm">
              <thead className="bg-surface-2 text-left text-[11px] font-semibold tracking-wide text-muted-text uppercase">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Sector
                  </th>
                  {countries.map((p) => (
                    <th key={p} scope="col" className="px-4 py-3 text-right">
                      {COUNTRY_ISO[p] ?? p} ({latestYear(p)})
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {sectorOptions.map((s) => (
                  <tr key={s.value} className="hover:bg-surface">
                    <th scope="row" className="px-4 py-3 text-left font-medium text-heading">
                      {s.label}
                    </th>
                    {countries.map((p) => {
                      const total = sectorTotal(p);
                      const value = sectorTotal(p, s.value);
                      return (
                        <td key={p} className="px-4 py-3 text-right">
                          {whole.format(value)}
                          <span className="ml-2 text-xs text-muted-text">
                            {total ? one.format((value / total) * 100) : '0,0'}%
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr className="bg-surface-2 font-semibold">
                  <th scope="row" className="px-4 py-3 text-left text-heading">
                    Total
                  </th>
                  {countries.map((p) => (
                    <td key={p} className="px-4 py-3 text-right">
                      {whole.format(sectorTotal(p))}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-canvas">
        <div className="border-b border-line/70 p-5">
          <h2 className="text-lg font-semibold text-heading">
            {institution
              ? `Totales por año · ${institution.institucion}`
              : 'Totales por país y año'}
          </h2>
          <p className="mt-1 text-sm text-muted-text">
            Titulados observados {[sectorScope, topicLabel].filter(Boolean).join(' ') || 'de todas las carreras'}.
            {institution &&
              COUNTRY_ISO[institution.pais] === 'ARG' &&
              ' En Argentina, el detalle por institución sale de los anuarios del DIU, salvo 2019, que no tiene anuario publicado con estos cuadros.'}
            {institution &&
              COUNTRY_ISO[institution.pais] === 'URY' &&
              ' Según los anuarios del MEC: la cifra de Udelar es preliminar.'}
            {institution
              ? ''
              : sp.tema
                ? ' Con un tema se suman sus programas, con todos los niveles, incluidos diplomados y posgrados.'
                : ' Solo carreras genéricas y disciplinas. En Argentina, 2019 sale del archivo de Indicadores CTI, que ese año queda por debajo del Anuario del DIU: no leas ese escalón como una caída real.'}
          </p>
        </div>
        {countryTotals.length === 0 || totalYears.length === 0 ? (
          <p className="p-5 text-sm text-muted-text">No hay titulados con estos filtros.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-[11px] font-semibold tracking-wide text-muted-text uppercase">
                <tr>
                  <th scope="col" className="sticky left-0 bg-surface-2 px-4 py-3">
                    País
                  </th>
                  {totalYears.map((y) => (
                    <th key={y} scope="col" className="px-3 py-3 text-right">
                      {y}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {countryTotals.map((c) => (
                  <tr key={c.pais}>
                    <th
                      scope="row"
                      className="sticky left-0 bg-canvas px-4 py-3 text-left font-medium text-heading"
                    >
                      {COUNTRY_ISO[c.pais] ?? c.pais}
                    </th>
                    {totalYears.map((y) => (
                      <td
                        key={y}
                        className={`px-3 py-3 text-right ${String(y) === year ? 'font-semibold text-heading' : ''}`}
                      >
                        {c.por_anio[String(y)] === undefined ? '—' : whole.format(c.por_anio[String(y)])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && (
        <section className="rounded-lg border border-line bg-canvas p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-heading">
                {titleCase(nombre)} · {institution ? institution.institucion : titleCase(pais)}
              </h2>
              <p className="mt-1 text-sm text-muted-text">
                Titulados por año, {start}–{end}.
                {institution
                  ? ' Solo esta institución. La proyección es de la carrera en todo el país: no hay por institución.'
                  : trend &&
                    ` Último dato observado: ${whole.format(trend.graduados_ultimo)} titulados en ${trend.anio_hasta}.`}
                {!institution &&
                  projectedRows.length === 0 &&
                  ' Esta carrera no tiene proyección: necesita al menos 12 años de historia sin huecos.'}
              </p>
            </div>
            <div className="w-80">
              <SelectParam
                name="carrera"
                label="Carrera"
                value={selected}
                reset={['desde', 'hasta']}
                options={chartCareers.map((k) => {
                  const [p, n] = k.split('|');
                  return { value: k, label: `${titleCase(n)} (${COUNTRY_ISO[p] ?? p})` };
                })}
              />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <div className="w-44">
              <SelectParam name="desde" label="Desde" value={String(fromYear)} options={rangeOptions} />
            </div>
            <div className="w-44">
              <SelectParam name="hasta" label="Hasta" value={String(toYear)} options={rangeOptions} />
            </div>
            {projectedRows.length > 0 && (
              <Segmented
                name="proyeccion"
                label="Proyección"
                value={showProjection ? 'con' : 'sin'}
                reset={['desde', 'hasta']}
                options={[
                  { value: 'con', label: 'Con proyección' },
                  { value: 'sin', label: 'Sin proyección' },
                ]}
              />
            )}
          </div>
          <div className="mt-4">
            <ProjectionChart data={rows} color={COUNTRY_COLORS[COUNTRY_ISO[pais]] ?? '#475569'} />
          </div>
          {!institution && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-heading">Por institución</h3>
              {!institutions || institutions.instituciones.length === 0 ? (
                <p className="mt-1 text-sm text-muted-text">
                  La fuente no publica esta carrera por institución.
                </p>
              ) : detailYears.length === 0 ? (
                <p className="mt-1 text-sm text-muted-text">
                  No hay datos observados por institución en los años elegidos.
                </p>
              ) : (
                <>
                  <p className="mt-1 text-sm text-muted-text">
                    {institutions.instituciones.length > TOP_INSTITUTIONS
                      ? `Las ${TOP_INSTITUTIONS} con más titulados, de ${whole.format(institutions.instituciones.length)} instituciones. El total incluye a todas.`
                      : `${whole.format(institutions.instituciones.length)} ${institutions.instituciones.length === 1 ? 'institución' : 'instituciones'}.`}
                    {COUNTRY_ISO[pais] === 'ARG'
                      ? ' En Argentina, este detalle sale de los anuarios del DIU. 2019 no tiene anuario publicado con estos cuadros, y en 2015 faltan algunas disciplinas: el gráfico usa Indicadores CTI en esos dos años.'
                      : COUNTRY_ISO[pais] === 'URY'
                        ? ' Según los anuarios del MEC: la cifra de Udelar es preliminar y la suma de una carrera puede diferir un poco de su serie.'
                        : ' Universidades, institutos profesionales y centros de formación técnica.'}
                  </p>
                  <div className="mt-2 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-surface-2 text-left text-[11px] font-semibold tracking-wide text-muted-text uppercase">
                        <tr>
                          <th scope="col" className="sticky left-0 bg-surface-2 px-4 py-2">
                            Institución
                          </th>
                          {detailYears.map((y) => (
                            <th key={y} scope="col" className="px-3 py-2 text-right">
                              {y}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line/60">
                        {institutions.instituciones.slice(0, TOP_INSTITUTIONS).map((i) => (
                          <tr key={i.institucion}>
                            <th
                              scope="row"
                              className="sticky left-0 bg-canvas px-4 py-2 text-left font-medium text-heading"
                            >
                              {i.institucion}
                            </th>
                            {detailYears.map((y) => (
                              <td key={y} className="px-3 py-2 text-right">
                                {i.por_anio[String(y)] === undefined
                                  ? '—'
                                  : whole.format(i.por_anio[String(y)])}
                              </td>
                            ))}
                          </tr>
                        ))}
                        <tr className="bg-surface-2 font-semibold">
                          <th
                            scope="row"
                            className="sticky left-0 bg-surface-2 px-4 py-2 text-left text-heading"
                          >
                            Total {COUNTRY_ISO[pais] ?? pais}
                          </th>
                          {detailYears.map((y) => (
                            <td key={y} className="px-3 py-2 text-right">
                              {whole.format(institutions.totales[String(y)] ?? 0)}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </section>
      )}

      <section className="overflow-hidden rounded-lg border border-line bg-canvas">
        <div className="border-b border-line/70 p-5">
          <h2 className="text-lg font-semibold text-heading">Tendencia de titulados por carrera</h2>
          <p className="mt-1 text-sm text-muted-text">
            {whole.format(items.length)} de {whole.format(allItems.length)} carreras
            {sp.tema || institution ? '' : `: las ${TOP_PER_COUNTRY} con más titulados de cada país`}.{' '}
            Variación entre el inicio de la ventana y el último año con datos.
            {institution
              ? ` La columna de titulados es de esta institución en ${institutionYear}; serie, variación, tendencia y proyección son de la carrera en todo el país.`
              : year && ` Se muestran las carreras con dato en ${year}.`}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[64rem] text-sm">
            <thead className="bg-surface-2 text-left text-[11px] font-semibold tracking-wide text-muted-text uppercase">
              <tr>
                <th scope="col" className="px-4 py-3">
                  Carrera
                </th>
                <th scope="col" className="px-4 py-3">
                  Institución
                </th>
                <th scope="col" className="px-4 py-3">
                  Sector
                </th>
                <th scope="col" className="px-4 py-3">
                  País
                </th>
                <th scope="col" className="px-4 py-3">
                  Serie
                </th>
                {(year || institution) && (
                  <th scope="col" className="px-4 py-3 text-right">
                    Titulados {institutionYear ?? year}
                  </th>
                )}
                <th scope="col" className="px-4 py-3 text-right">
                  Inicio de ventana
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Último año
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Variación
                </th>
                <th scope="col" className="px-4 py-3">
                  Tendencia
                </th>
                <th scope="col" className="px-4 py-3">
                  Proyección
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={year || institution ? 11 : 10}
                    className="px-4 py-6 text-center text-sm text-muted-text"
                  >
                    No hay carreras con estos filtros.
                  </td>
                </tr>
              )}
              {items.map((t) => {
                const key = keyOf(t);
                const value = yearValues.get(key);
                return (
                  <tr key={key} className="hover:bg-surface">
                    <td className="px-4 py-3 font-medium text-heading">
                      {t.nombre}
                      {t.tema && (
                        <span className="ml-2 rounded border border-line px-1.5 py-0.5 text-xs font-normal text-muted-text">
                          Tema: {t.tema}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-body">
                      {institution ? (
                        institution.institucion
                      ) : t.institucion_principal ? (
                        <>
                          {t.institucion_principal}
                          {t.n_instituciones !== null && t.n_instituciones > 1 && (
                            <Link href={chartHref(key)} className="block text-xs text-link hover:underline">
                              y {whole.format(t.n_instituciones - 1)} más
                            </Link>
                          )}
                        </>
                      ) : (
                        <span className="text-xs text-muted-text">Sin detalle cargado</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-text">{sectorLabel(t.sector)}</td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-line px-1.5 py-0.5 text-xs font-medium">
                        {COUNTRY_ISO[t.pais] ?? t.pais}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-text">
                      {t.anio_desde}–{t.anio_hasta}
                    </td>
                    {institution && (
                      <td className="px-4 py-3 text-right">{whole.format(ownAmount(t))}</td>
                    )}
                    {!institution && year && (
                      <td className="px-4 py-3 text-right">
                        {value &&
                          (value.tipo === 'proyectado'
                            ? `≈ ${whole.format(value.graduados)}`
                            : whole.format(value.graduados))}
                        {value?.tipo === 'proyectado' && (
                          <span className="block text-xs text-muted-text">proyección</span>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-3 text-right">
                      {whole.format(t.graduados_inicio_ventana)}
                    </td>
                    <td className="px-4 py-3 text-right">{whole.format(t.graduados_ultimo)}</td>
                    <td className="px-4 py-3 text-right">
                      {t.variacion_ventana_pct === null
                        ? '—'
                        : `${t.variacion_ventana_pct > 0 ? '+' : ''}${one.format(t.variacion_ventana_pct)}%`}
                    </td>
                    <td className="px-4 py-3">{TREND_LABELS[t.tendencia] ?? t.tendencia}</td>
                    <td className="px-4 py-3">
                      {withProjection.has(key) ? (
                        <Link href={chartHref(key)} className="text-link hover:underline">
                          Ver proyección
                        </Link>
                      ) : (
                        <>
                          <span className="block text-xs text-muted-text">
                            {t.proyeccion.startsWith('historia')
                              ? 'Historia insuficiente'
                              : 'Serie con huecos'}
                          </span>
                          <Link href={chartHref(key)} className="text-xs text-link hover:underline">
                            Ver serie
                          </Link>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
