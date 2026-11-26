'use client';

import { useActionState, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
} from 'lucide-react';
import { Badge, type BadgeTone } from '@/components/ui/badge';
import {
  commitDatasetAction,
  uploadDatasetAction,
  type CommitState,
  type UploadState,
} from '@/lib/api/admin-actions';
import type { DatasetProfile, DatasetUploadResult } from '@/lib/schemas/datasets';
import { DATASET_STATUS_LABELS } from '@/lib/utils/datasets';
import { formatDate } from '@/lib/utils/format';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8010';
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

const INITIAL_UPLOAD: UploadState = { status: 'idle' };
const INITIAL_COMMIT: CommitState = { status: 'idle' };

const STATUS_TONES: Record<string, BadgeTone> = {
  validated: 'brand',
  loaded: 'success',
  unchanged: 'neutral',
  replaced: 'neutral',
  rejected: 'danger',
  format_changed: 'warning',
};

const LABEL = 'mb-1.5 block text-[10.5px] font-bold tracking-[0.08em] text-label uppercase';
const FIELD =
  'h-10 w-full rounded-lg border border-card-border bg-canvas px-3 text-[13px] text-body transition-colors placeholder:text-placeholder hover:border-line focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';

function templateUrl(code: string, format: 'xlsx' | 'csv') {
  return `${API_URL}/api/v1/datasets/profiles/${encodeURIComponent(code)}/template?format=${format}`;
}

function exampleUrl(code: string, name: string) {
  return `${API_URL}/api/v1/datasets/profiles/${encodeURIComponent(code)}/examples/${encodeURIComponent(name)}`;
}

function cell(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

export function DatasetUpload({ profiles }: { profiles: DatasetProfile[] }) {
  const [profileCode, setProfileCode] = useState(profiles[0]?.dataset_code ?? '');
  const profile = profiles.find((p) => p.dataset_code === profileCode);
  const [upload, uploadAction, uploading] = useActionState(uploadDatasetAction, INITIAL_UPLOAD);

  return (
    <section className="overflow-hidden rounded-xl border border-card-border bg-rail">
      <div className="border-b border-card-border p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-heading">
          Subir un archivo
        </h2>
        <p className="mt-1 text-xs text-muted-text">
          Elegí el formato, subí el archivo y revisá el reporte. Nada se carga hasta que lo
          confirmes.
        </p>
      </div>

      <form action={uploadAction} className="space-y-5 p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className={LABEL}>Formato</span>
            <select
              name="profile"
              value={profileCode}
              onChange={(e) => setProfileCode(e.target.value)}
              required
              className={FIELD}
            >
              {profiles.map((p) => (
                <option key={p.dataset_code} value={p.dataset_code}>
                  {p.title}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className={LABEL}>Archivo (.xlsx o .csv)</span>
            <input
              name="file"
              type="file"
              accept=".xlsx,.csv"
              required
              className="block w-full rounded-lg border border-card-border bg-canvas px-3 py-2 text-[12.5px] text-body file:mr-3 file:rounded-md file:border-0 file:bg-brand file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-brand-hover focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            />
          </label>
        </div>

        {profile && (
          <div className="rounded-lg border border-card-border bg-canvas p-3 text-xs leading-relaxed text-muted-text">
            <p>
              <span className="font-semibold text-heading">Formato esperado:</span>{' '}
              {profile.file_format}
              {profile.automatic ? ' · También se descarga automáticamente' : ' · Solo carga manual'}
            </p>
            {!!profile.required_columns?.length && (
              <p className="mt-1">
                <span className="font-semibold text-heading">Columnas obligatorias:</span>{' '}
                {profile.required_columns.join(', ')}
              </p>
            )}
            {(profile.has_template || profile.example_files.length > 0) && (
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
                {profile.has_template && (
                  <>
                    <a
                      href={templateUrl(profile.dataset_code, 'xlsx')}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-link hover:underline"
                    >
                      <Download className="size-3.5" aria-hidden />
                      Plantilla Excel
                    </a>
                    <a
                      href={templateUrl(profile.dataset_code, 'csv')}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-link hover:underline"
                    >
                      <Download className="size-3.5" aria-hidden />
                      Plantilla CSV
                    </a>
                  </>
                )}
                {profile.example_files.map((name) => (
                  <a
                    key={name}
                    href={exampleUrl(profile.dataset_code, name)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-link hover:underline"
                  >
                    <Download className="size-3.5" aria-hidden />
                    Ejemplo «{name}»
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {profile?.requires_declared_source && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className={LABEL}>Fuente declarada · nombre</span>
              <input
                name="declared_source_name"
                type="text"
                required
                placeholder="Por ejemplo, ILOSTAT"
                className={FIELD}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Fuente declarada · URL</span>
              <input
                name="declared_source_url"
                type="url"
                required
                placeholder="https://..."
                className={FIELD}
              />
            </label>
          </div>
        )}

        <label className="block max-w-xs">
          <span className={LABEL}>Fecha de referencia (opcional)</span>
          <input name="reference_date" type="date" className={FIELD} />
        </label>

        {upload.status === 'error' && (
          <p
            role="alert"
            className="rounded-lg border border-alert-critical-border bg-alert-critical-bg px-3 py-2 text-sm text-alert-critical-text"
          >
            {upload.error}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={uploading || !profileCode}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:opacity-60"
          >
            {uploading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Upload className="size-4" aria-hidden />
            )}
            {uploading ? 'Validando…' : 'Validar archivo'}
          </button>
          <p className="text-[11.5px] text-muted-text">
            Se revisa que el archivo sea lo que dice y que los datos sean válidos. El archivo queda
            en el historial aunque no pase la revisión.
          </p>
        </div>
      </form>

      {upload.status === 'ok' && upload.result && (
        <div className="border-t border-card-border p-4">
          <UploadResult key={upload.result.dataset_id} result={upload.result} />
        </div>
      )}
    </section>
  );
}

function UploadResult({ result }: { result: DatasetUploadResult }) {
  const report = result.report;
  const groups = report.groups ?? [];
  const errors = report.errors ?? [];
  const warnings = report.warnings ?? [];
  const overlaps = report.overlaps ?? null;
  const columns = result.preview[0] ? Object.keys(result.preview[0]) : [];

  const [confirmOverlap, setConfirmOverlap] = useState(false);
  const [commit, commitAction, committing] = useActionState(commitDatasetAction, INITIAL_COMMIT);
  const needsConfirmation = (overlaps?.count ?? 0) > 0;
  const loaded = commit.status === 'ok';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <FileSpreadsheet className="mt-0.5 size-5 shrink-0 text-muted-text" aria-hidden />
          <div className="min-w-0">
            <p className="break-all font-mono text-xs font-medium text-heading">{result.file_name}</p>
            <p className="mt-0.5 text-xs text-muted-text">
              {whole.format(result.records)} registros · {formatDate(result.created_at) ?? '—'}
            </p>
          </div>
        </div>
        <Badge tone={STATUS_TONES[result.status] ?? 'neutral'}>
          {DATASET_STATUS_LABELS[result.status] ?? result.status}
        </Badge>
      </div>

      {groups.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-heading">Problemas agrupados</p>
          {groups.map((group, i) => (
            <details
              key={`${group.kind}-${i}`}
              className="rounded-lg border border-alert-critical-border bg-alert-critical-bg/40"
            >
              <summary className="cursor-pointer list-none px-3 py-2 text-xs font-semibold text-alert-critical-text [&::-webkit-details-marker]:hidden">
                {group.title}{' '}
                <span className="font-normal">
                  · {group.count} {group.count === 1 ? 'fila' : 'filas'}
                </span>
              </summary>
              <div className="space-y-1 border-t border-alert-critical-border/50 px-3 py-2 text-xs text-body">
                {group.column && (
                  <p>
                    <span className="font-semibold text-heading">Columna:</span> {group.column}
                  </p>
                )}
                {group.rows.length > 0 && (
                  <p>
                    <span className="font-semibold text-heading">Filas:</span>{' '}
                    {group.rows.join(', ')}
                  </p>
                )}
                {group.values.length > 0 && (
                  <p>
                    <span className="font-semibold text-heading">Valores:</span>{' '}
                    {group.values.join(', ')}
                  </p>
                )}
                {group.hint && <p className="text-muted-text">{group.hint}</p>}
              </div>
            </details>
          ))}
        </div>
      )}

      {errors.length > 0 && (
        <details className="rounded-lg border border-card-border bg-canvas">
          <summary className="cursor-pointer list-none px-3 py-2 text-xs font-semibold text-heading [&::-webkit-details-marker]:hidden">
            Errores fila por fila · {errors.length}
          </summary>
          <ul className="space-y-1 border-t border-card-border px-3 py-2 text-xs text-body">
            {errors.map((error, i) => (
              <li key={i}>
                {error.row !== null && error.row !== undefined ? `Fila ${error.row}: ` : ''}
                {error.column ? `«${error.column}»: ` : ''}
                {error.message}
              </li>
            ))}
          </ul>
        </details>
      )}

      {warnings.length > 0 && (
        <details className="rounded-lg border border-alert-warning-border bg-alert-warning-bg">
          <summary className="cursor-pointer list-none px-3 py-2 text-xs font-semibold text-alert-warning-text [&::-webkit-details-marker]:hidden">
            Avisos · {warnings.length}
          </summary>
          <ul className="space-y-1 border-t border-alert-warning-border px-3 py-2 text-xs text-body">
            {warnings.map((warning, i) => (
              <li key={i}>
                {warning.row !== null && warning.row !== undefined ? `Fila ${warning.row}: ` : ''}
                {warning.message}
              </li>
            ))}
          </ul>
        </details>
      )}

      {overlaps && overlaps.count > 0 && (
        <div className="rounded-lg border border-alert-warning-border bg-alert-warning-bg px-3 py-2 text-xs text-alert-warning-text">
          <p className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="size-4 shrink-0" aria-hidden />
            Coincidencias con fuentes oficiales
          </p>
          <p className="mt-1">{overlaps.message}</p>
          {overlaps.examples.length > 0 && (
            <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
              {overlaps.examples.map((example, i) => (
                <li key={i}>{example}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {columns.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-heading">
            Vista previa · {result.preview.length} filas
          </p>
          <div className="mt-1.5 overflow-x-auto rounded-lg border border-card-border">
            <table className="w-full min-w-max text-left text-xs">
              <thead className="bg-surface-2 text-[10.5px] font-bold tracking-[0.08em] text-label uppercase">
                <tr>
                  {columns.map((column) => (
                    <th key={column} scope="col" className="px-3 py-2 whitespace-nowrap">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-card-border">
                {result.preview.map((row, i) => (
                  <tr key={i}>
                    {columns.map((column) => (
                      <td key={column} className="px-3 py-1.5 whitespace-nowrap text-body">
                        {cell(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result.status === 'validated' ? (
        <form action={commitAction} className="space-y-3 rounded-lg border border-card-border bg-canvas p-3">
          <input type="hidden" name="dataset_id" value={result.dataset_id} />

          {needsConfirmation && (
            <label className="flex items-start gap-2 text-xs text-body">
              <input
                name="confirm_overlap"
                type="checkbox"
                checked={confirmOverlap}
                onChange={(e) => setConfirmOverlap(e.target.checked)}
                className="mt-0.5 size-4 shrink-0 rounded border-card-border text-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              />
              <span>
                Confirmo que quiero cargar estos valores como fuente aparte. No reemplazan los
                datos oficiales.
              </span>
            </label>
          )}

          {commit.status === 'error' && (
            <p
              role="alert"
              className="rounded-lg border border-alert-critical-border bg-alert-critical-bg px-3 py-2 text-sm text-alert-critical-text"
            >
              {commit.error}
            </p>
          )}

          {commit.status === 'ok' && commit.dataset && (
            <p className="flex items-start gap-1.5 rounded-lg border border-alert-positive-border bg-alert-positive-bg px-3 py-2 text-sm text-alert-positive-text">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden />
              Se cargaron {whole.format(commit.dataset.records)} registros al observatorio.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={committing || loaded || (needsConfirmation && !confirmOverlap)}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:opacity-60"
            >
              {committing ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <CheckCircle2 className="size-4" aria-hidden />
              )}
              {committing ? 'Cargando…' : loaded ? 'Cargado' : 'Cargar datos al observatorio'}
            </button>
            <p className="text-[11.5px] text-muted-text">
              Se vuelve a validar el archivo. Si ya había una carga de este formato y fuente, se
              reemplaza.
            </p>
          </div>
        </form>
      ) : (
        <p className="rounded-lg border border-dashed border-line px-3 py-2 text-xs text-muted-text">
          El archivo no pasó la validación. Corregí los problemas y volvé a subirlo.
        </p>
      )}
    </div>
  );
}
