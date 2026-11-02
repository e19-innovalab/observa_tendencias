import { ExternalLink, FileSpreadsheet } from 'lucide-react';
import type { Metadata } from 'next';
import { Suspense } from 'react';
import { UploadDataset } from '@/components/admin/UploadDataset';
import { SelectParam, Segmented } from '@/components/ui/filters/UrlControls';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { getDatasetProfiles, getDatasets } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { requirePermission } from '@/lib/auth/session';
import { PERMISSIONS } from '@/lib/schemas/auth';
import { formatDate } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Carga de datos' };
type SearchParams = { formato?: string; origen?: string };
const HISTORY_LIMIT = 100;
/** Estados del archivo en el backend (datasets). */
const STATUS_LABELS: Record<string, string> = {
  validated: 'Revisado, listo para cargar',
  loaded: 'Cargado',
  unchanged: 'Sin cambios',
  replaced: 'Reemplazado',
  rejected: 'Rechazado',
  format_changed: 'Cambió el formato',
};
const STATUS_STYLES: Record<string, string> = {
  loaded: 'border-success/40 bg-success-soft text-success',
  validated: 'border-brand/40 bg-surface text-brand',
  rejected: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text',
  format_changed: 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text',
};
const ORIGINS = [
  { value: 'todos', label: 'Todos' },
  { value: 'download', label: 'Descargas automáticas' },
  { value: 'upload', label: 'Cargas manuales' },
];
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

export default function DatosPage({ searchParams }: PageProps<'/admin/datos'>) {
  return (
    <>
      <div className="border-b border-line bg-white">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <h1 className="text-2xl font-semibold text-heading">Carga de datos</h1>
          <p className="mt-1 text-sm text-muted-text">Subí archivos de fuentes oficiales y revisá el historial de todo lo que se leyó, descargado o cargado a mano.</p>
        </div>
      </div>
      <Suspense fallback={<PageSkeleton />}>
        <DatosContent searchParams={searchParams as Promise<SearchParams>} />
      </Suspense>
    </>
  );
}

async function DatosContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  await requirePermission(PERMISSIONS.manageData);
  const sp = await searchParams;
  const origin = ORIGINS.some((o) => o.value === sp.origen) && sp.origen !== 'todos' ? sp.origen : undefined;
  let profiles, files;
  try {
    [profiles, files] = await Promise.all([getDatasetProfiles(), getDatasets({ profile: sp.formato, origin, limit: HISTORY_LIMIT })]);
  } catch (e) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text">
          {e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
        </p>
      </div>
    );
  }
  const titles = Object.fromEntries(profiles.map((p) => [p.dataset_code, p.title]));

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      <section className="rounded-lg border border-line bg-white p-5">
        <h2 className="text-lg font-semibold text-heading">Cargar un archivo de datos</h2>
        <p className="mb-5 mt-1 text-sm text-muted-text">
          Para series que no tienen descarga automática usá la plantilla genérica (una fila por valor). Los archivos oficiales se aceptan tal como los publica la fuente: si cambió el formato, se rechazan y se mantienen los datos anteriores.
        </p>
        <UploadDataset profiles={profiles} statusLabels={STATUS_LABELS} />
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-white">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line/70 p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-heading">Historial de archivos <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-xs font-medium normal-case text-muted-text">{files.length}</span></h2>
          <div className="flex flex-wrap items-end gap-4">
            <div className="w-72"><SelectParam name="formato" label="Formato" value={sp.formato ?? ''} placeholder="Todos los formatos" options={profiles.map((p) => ({ value: p.dataset_code, label: p.title }))} /></div>
            <Segmented name="origen" label="Origen" value={origin ?? 'todos'} options={ORIGINS} />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[60rem] text-sm">
            <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              <tr>
                <th scope="col" className="px-4 py-3">ID</th>
                <th scope="col" className="px-4 py-3">Archivo</th>
                <th scope="col" className="px-4 py-3">Origen</th>
                <th scope="col" className="px-4 py-3">Edición</th>
                <th scope="col" className="px-4 py-3">Recibido</th>
                <th scope="col" className="px-4 py-3 text-right">Registros</th>
                <th scope="col" className="px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {files.map((f) => {
                const warnings = f.report.warnings?.length ?? 0;
                const errors = f.report.errors?.length ?? 0;
                return (
                  <tr key={f.dataset_id} className="align-top">
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-muted-text">DS-{String(f.dataset_id).padStart(5, '0')}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <FileSpreadsheet className="mt-0.5 size-4 shrink-0 text-muted-text" aria-hidden />
                        <div className="min-w-0">
                          <p className="break-all font-mono text-xs font-medium text-heading">{decodeURIComponent(f.file_name)}</p>
                          <p className="text-xs text-muted-text">{titles[f.profile_code] ?? f.profile_code}{f.declared_source_name ? ` · Fuente: ${f.declared_source_name}` : ''}</p>
                          {f.url && (
                            <a href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-link hover:underline">Archivo original <ExternalLink className="size-3" aria-hidden /></a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">{f.origin === 'upload' ? 'Carga manual' : 'Descarga automática'}</td>
                    <td className="px-4 py-3 text-xs">{f.release ?? f.reference_date ?? '—'}</td>
                    <td className="px-4 py-3 text-xs">{formatDate(f.created_at)}</td>
                    <td className="px-4 py-3 text-right">{whole.format(f.records)}</td>
                    <td className="px-4 py-3">
                      <span className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[f.status] ?? 'border-line bg-surface text-body'}`}>{STATUS_LABELS[f.status] ?? f.status}</span>
                      {(warnings > 0 || errors > 0) && (
                        <p className="mt-1 text-[11px] text-muted-text">{[errors && `${errors} ${errors === 1 ? 'error' : 'errores'}`, warnings && `${warnings} ${warnings === 1 ? 'aviso' : 'avisos'}`].filter(Boolean).join(' · ')}</p>
                      )}
                    </td>
                  </tr>
                );
              })}
              {files.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-text">No hay archivos con estos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
