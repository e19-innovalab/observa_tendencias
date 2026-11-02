import { Info } from 'lucide-react';
import Link from 'next/link';
import { ProjectionChart } from '@/components/ui/charts/ProjectionChart';
import { COUNTRY_COLORS } from '@/components/ui/charts/chartTheme';
import { SelectParam } from '@/components/ui/filters/UrlControls';
import { ErrorNote } from '@/components/minimal/ui';
import { getGraduateProjections, getGraduateTrends } from '@/lib/api/skills';

type SearchParams = { carrera?: string };
const one = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

function ErrorBox({ error }: { error: unknown }) {
  return <ErrorNote message={error instanceof Error ? error.message : 'Error inesperado al cargar los datos.'} />;
}

const TREND_LABELS: Record<string, string> = {
  growing: 'Creciente',
  declining: 'Decreciente',
  stable: 'Estable',
  insufficient_data: 'Datos insuficientes',
};
const COUNTRY_ISO: Record<string, string> = { argentina: 'ARG', chile: 'CHL', uruguay: 'URY' };
const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export async function GraduatesView({ sp }: { sp: SearchParams }) {
  let trends, projections;
  try {
    [trends, projections] = await Promise.all([getGraduateTrends(), getGraduateProjections()]);
  } catch (e) {
    return <ErrorBox error={e} />;
  }
  const projected = [...new Set(projections.map((p) => `${p.pais}|${p.nombre}`))];
  const selected = projected.includes(sp.carrera ?? '') ? sp.carrera! : projected[0];
  const [pais, nombre] = (selected ?? '|').split('|');
  const rows = projections
    .filter((p) => p.pais === pais && p.nombre === nombre)
    .sort((a, b) => a.anio - b.anio)
    .map((p) => ({ anio: p.anio, valor: p.graduados_proyectado, banda: [p.limite_inferior, p.limite_superior] as [number, number] }));
  const trend = trends.items.find((t) => t.pais === pais && t.nombre === nombre);
  const items = [...trends.items].sort((a, b) => a.pais.localeCompare(b.pais) || b.graduados_ultimo - a.graduados_ultimo);

  return (
    <>
      <section className="rounded-lg border border-line bg-surface p-4 text-sm text-body">
        <p className="flex items-center gap-2 font-semibold text-heading"><Info className="size-4" aria-hidden /> Alcance de las proyecciones</p>
        <p className="mt-1">
          Selección de {trends.items.length} carreras estratégicas preparada por el equipo de datos. La proyección solo se genera cuando la carrera
          tiene al menos 12 años de historia sin huecos; hoy eso ocurre para {projected.length} carreras de Chile. Las variaciones porcentuales grandes
          suelen venir de carreras nuevas con pocos titulados al inicio: mirá también los valores absolutos. {trends.source}
        </p>
      </section>

      {selected && (
        <section className="rounded-lg border border-line bg-white p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-heading">{titleCase(nombre)} · {titleCase(pais)}</h2>
              <p className="mt-1 text-sm text-muted-text">
                Titulados proyectados {rows[0]?.anio}–{rows.at(-1)?.anio} con su intervalo.
                {trend && ` Último dato observado: ${whole.format(trend.graduados_ultimo)} titulados en ${trend.anio_hasta}.`}
              </p>
            </div>
            <div className="w-80">
              <SelectParam
                name="carrera"
                label="Carrera"
                value={selected}
                options={projected.map((k) => {
                  const [p, n] = k.split('|');
                  return { value: k, label: `${titleCase(n)} (${COUNTRY_ISO[p] ?? p})` };
                })}
              />
            </div>
          </div>
          <div className="mt-4">
            <ProjectionChart data={rows} color={COUNTRY_COLORS[COUNTRY_ISO[pais]] ?? '#475569'} />
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-lg border border-line bg-white">
        <div className="border-b border-line/70 p-5">
          <h2 className="text-lg font-semibold text-heading">Tendencia de titulados por carrera</h2>
          <p className="mt-1 text-sm text-muted-text">Variación entre el inicio de la ventana y el último año con datos.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[50rem] text-sm">
            <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              <tr>
                <th scope="col" className="px-4 py-3">Carrera</th>
                <th scope="col" className="px-4 py-3">País</th>
                <th scope="col" className="px-4 py-3">Serie</th>
                <th scope="col" className="px-4 py-3 text-right">Inicio de ventana</th>
                <th scope="col" className="px-4 py-3 text-right">Último año</th>
                <th scope="col" className="px-4 py-3 text-right">Variación</th>
                <th scope="col" className="px-4 py-3">Tendencia</th>
                <th scope="col" className="px-4 py-3">Proyección</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {items.map((t) => {
                const key = `${t.pais}|${t.nombre}`;
                return (
                  <tr key={key} className="hover:bg-surface">
                    <td className="px-4 py-3 font-medium text-heading">{titleCase(t.nombre)}</td>
                    <td className="px-4 py-3"><span className="rounded border border-line px-1.5 py-0.5 text-xs font-medium">{COUNTRY_ISO[t.pais] ?? t.pais}</span></td>
                    <td className="px-4 py-3 text-muted-text">{t.anio_desde}–{t.anio_hasta}</td>
                    <td className="px-4 py-3 text-right">{whole.format(t.graduados_inicio_ventana)}</td>
                    <td className="px-4 py-3 text-right">{whole.format(t.graduados_ultimo)}</td>
                    <td className="px-4 py-3 text-right">{t.variacion_ventana_pct === null ? '—' : `${t.variacion_ventana_pct > 0 ? '+' : ''}${one.format(t.variacion_ventana_pct)}%`}</td>
                    <td className="px-4 py-3">{TREND_LABELS[t.tendencia] ?? t.tendencia}</td>
                    <td className="px-4 py-3">
                      {projected.includes(key) ? (
                        <Link href={`/habilidades?tab=titulados&carrera=${encodeURIComponent(key)}`} className="text-link hover:underline">Ver proyección</Link>
                      ) : (
                        <span className="text-xs text-muted-text">{t.proyeccion.startsWith('historia') ? 'Historia insuficiente' : 'Serie con huecos'}</span>
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
