import { ExternalLink, FileSpreadsheet } from 'lucide-react';
import type { Metadata } from 'next';
import { Suspense } from 'react';
import { DatasetUpload } from '@/components/admin/DatasetUpload';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import { SelectParam, Segmented } from '@/components/data/UrlControls';
import { ErrorNote } from '@/components/data/ui';
import { InfoNote } from '@/components/ui/feedback/InfoNote';
import { PageHero } from '@/components/ui/layout/PageHero';
import { getDatasetProfiles, getDatasets } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { getCurrentUser } from '@/lib/auth/session';
import { PERMISSIONS } from '@/lib/schemas/auth';
import { DATASET_STATUS_CLASSES, DATASET_STATUS_LABELS } from '@/lib/utils/datasets';
import { formatDate } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Carga de datos' };

type SearchParams = { formato?: string; origen?: string };

const HISTORY_LIMIT = 100;
const ORIGINS = [
  { value: 'todos', label: 'Todos' },
  { value: 'download', label: 'Descargas automáticas' },
  { value: 'upload', label: 'Cargas manuales' },
];
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

export default function DatosPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return (
    <>
      <PageHero
        title="Carga de datos"
        description="Subí un archivo para revisarlo antes de cargarlo y consultá el historial de todo lo que se leyó, descargó o cargó a mano en el observatorio."
      />
      <Suspense fallback={<PageSkeleton />}>
        <DatosContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function DatosContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const origin =
    ORIGINS.some((o) => o.value === sp.origen) && sp.origen !== 'todos' ? sp.origen : undefined;

  let profiles: Awaited<ReturnType<typeof getDatasetProfiles>>;
  let files: Awaited<ReturnType<typeof getDatasets>>;
  try {
    [profiles, files] = await Promise.all([
      getDatasetProfiles(),
      getDatasets({ profile: sp.formato, origin, limit: HISTORY_LIMIT }),
    ]);
  } catch (e) {
    return (
      <div className="mx-auto max-w-[1600px] px-4 py-8 sm:px-6">
        <ErrorNote
          message={e instanceof ApiError ? e.message : 'Error inesperado al cargar los datos.'}
        />
      </div>
    );
  }

  const titles = Object.fromEntries(profiles.map((p) => [p.dataset_code, p.title]));
  const user = await getCurrentUser();
  const canManage = !!user?.permissions.includes(PERMISSIONS.manageData);

  return (
    <div className="mx-auto max-w-[1600px] space-y-6 px-4 py-8 sm:px-6">
      {canManage ? (
        <DatasetUpload profiles={profiles} />
      ) : (
        <InfoNote title="Subir archivos">
          Tu rol no tiene permiso para cargar archivos. Podés consultar el historial en modo
          lectura. Si necesitás cargar datos, pedile a quien administra tu institución que te
          asigne el permiso de gestión de datos.
        </InfoNote>
      )}

      <section className="overflow-hidden rounded-xl border border-card-border bg-rail">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-card-border p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-heading">
            Historial de archivos{' '}
            <span className="ml-2 rounded-full border border-card-border px-2 py-0.5 text-xs font-medium normal-case text-muted-text">
              {files.length}
            </span>
          </h2>
          <div className="flex flex-wrap items-end gap-4">
            <div className="w-72">
              <SelectParam
                name="formato"
                label="Formato"
                value={sp.formato ?? ''}
                placeholder="Todos los formatos"
                options={profiles.map((p) => ({ value: p.dataset_code, label: p.title }))}
              />
            </div>
            <Segmented
              name="origen"
              label="Origen"
              value={origin ?? 'todos'}
              options={ORIGINS}
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[60rem] text-sm">
            <thead className="bg-surface-2 text-left text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
              <tr>
                <th scope="col" className="px-4 py-3">
                  ID
                </th>
                <th scope="col" className="px-4 py-3">
                  Archivo
                </th>
                <th scope="col" className="px-4 py-3">
                  Origen
                </th>
                <th scope="col" className="px-4 py-3">
                  Edición
                </th>
                <th scope="col" className="px-4 py-3">
                  Recibido
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Registros
                </th>
                <th scope="col" className="px-4 py-3">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border">
              {files.map((f) => {
                const warnings = f.report.warnings?.length ?? 0;
                const errors = f.report.errors?.length ?? 0;
                return (
                  <tr key={f.dataset_id} className="align-top">
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-muted-text">
                      DS-{String(f.dataset_id).padStart(5, '0')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <FileSpreadsheet
                          className="mt-0.5 size-4 shrink-0 text-muted-text"
                          aria-hidden
                        />
                        <div className="min-w-0">
                          <p className="break-all font-mono text-xs font-medium text-heading">
                            {f.file_name}
                          </p>
                          <p className="text-xs text-muted-text">
                            {titles[f.profile_code] ?? f.profile_code}
                            {f.declared_source_name
                              ? ` · Fuente: ${f.declared_source_name}`
                              : ''}
                          </p>
                          {f.url && (
                            <a
                              href={f.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-link hover:underline"
                            >
                              Archivo original{' '}
                              <ExternalLink className="size-3" aria-hidden />
                            </a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {f.origin === 'upload' ? 'Carga manual' : 'Descarga automática'}
                    </td>
                    <td className="px-4 py-3 text-xs">{f.release ?? f.reference_date ?? '—'}</td>
                    <td className="px-4 py-3 text-xs">{formatDate(f.created_at)}</td>
                    <td className="px-4 py-3 text-right">{whole.format(f.records)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${DATASET_STATUS_CLASSES[f.status] ?? 'border-card-border bg-surface text-body'}`}
                      >
                        {DATASET_STATUS_LABELS[f.status] ?? f.status}
                      </span>
                      {(warnings > 0 || errors > 0) && (
                        <p className="mt-1 text-[11px] text-muted-text">
                          {[
                            errors && `${errors} ${errors === 1 ? 'error' : 'errores'}`,
                            warnings && `${warnings} ${warnings === 1 ? 'aviso' : 'avisos'}`,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </p>
                      )}
                    </td>
                  </tr>
                );
              })}
              {files.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-muted-text">
                    No hay archivos con estos filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
