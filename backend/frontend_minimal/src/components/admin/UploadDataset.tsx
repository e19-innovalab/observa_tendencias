'use client';

import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, Upload } from 'lucide-react';
import { useActionState, useState } from 'react';
import { commitDataset, uploadDataset, type UploadState } from '@/lib/admin/actions';
import type { DatasetProfile } from '@/lib/schemas/datasets';

const input = 'w-full rounded-md border border-line bg-white px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus';
const labelCls = 'mb-1 block text-xs font-semibold text-muted-text';
const whole = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const linkCls = 'inline-flex items-center gap-1 font-medium text-link hover:underline';
const download = (profile: string, extra: string) => `/api/datasets/download?profile=${profile}&${extra}`;

/**
 * Paso 1: se sube y se revisa el archivo (nada se carga). Paso 2: con el informe a la vista,
 * se confirma la carga; el backend recalcula tendencias, proyecciones, ISE y alertas.
 */
export function UploadDataset({ profiles, statusLabels }: { profiles: DatasetProfile[]; statusLabels: Record<string, string> }) {
  const [state, uploadAction, uploading] = useActionState<UploadState, FormData>(uploadDataset, {});
  const [committed, commitAction, committing] = useActionState<UploadState, FormData>(
    async (_prev, form) => commitDataset(state, form.get('confirm_overlap') === 'on'),
    {},
  );
  // confirmación del choque con datos oficiales, solo para el archivo revisado (no pasa al siguiente)
  const [confirmedFor, setConfirmedFor] = useState<number | null>(null);
  const [profileCode, setProfileCode] = useState(profiles.find((p) => !p.automatic)?.dataset_code ?? profiles[0]?.dataset_code ?? '');
  const profile = profiles.find((p) => p.dataset_code === profileCode);
  const result = state.result;
  const confirmOverlap = result !== undefined && confirmedFor === result.dataset_id;
  const done = committed.committed && committed.result?.dataset_id === result?.dataset_id ? committed.committed : null;
  const errors = result?.report.errors ?? [];
  const groups = result?.report.groups ?? [];
  const overlaps = result?.report.overlaps;
  const warnings = (result?.report.warnings ?? []).filter((w) => w.kind !== 'overlap');
  const columns = result?.preview[0] ? Object.keys(result.preview[0]) : [];

  return (
    <div className="space-y-5">
      <form action={uploadAction} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="lg:col-span-2">
          <span className={labelCls}>Formato del archivo</span>
          <select name="profile" value={profileCode} onChange={(e) => setProfileCode(e.target.value)} className={input}>
            {profiles.map((p) => (
              <option key={p.dataset_code} value={p.dataset_code}>
                {p.title}{p.automatic ? ' (también se descarga solo)' : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className={labelCls}>Archivo (.csv o .xlsx)</span>
          <input name="file" type="file" accept=".csv,.xlsx" required className="block w-full text-sm file:mr-3 file:rounded-md file:border file:border-line file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-medium" />
        </label>
        <label>
          <span className={labelCls}>Fuente declarada{profile?.requires_declared_source ? ' (obligatoria)' : ''}</span>
          <input name="declared_source_name" required={profile?.requires_declared_source} placeholder="Ej. INE Uruguay" className={input} />
        </label>
        <label>
          <span className={labelCls}>URL de la fuente oficial{profile?.requires_declared_source ? ' (obligatoria)' : ''}</span>
          <input name="declared_source_url" type="url" required={profile?.requires_declared_source} placeholder="https://" className={input} />
        </label>
        <label>
          <span className={labelCls}>Fecha de referencia</span>
          <input name="reference_date" type="date" className={input} />
        </label>
        {profile && (
          <p className="rounded-md border border-line bg-surface p-3 text-xs text-body md:col-span-2 lg:col-span-3">
            {profile.required_columns
              ? `Columnas obligatorias: ${profile.required_columns.join(', ')}${profile.template_columns ? ` (opcionales: ${Object.values(profile.template_columns).filter((c) => !profile.required_columns?.includes(c)).join(', ')})` : ''}.`
              : `Mismo archivo que publica la fuente oficial, sin modificar (${profile.file_format.toUpperCase()}).`}
            {profile.landing_page && (
              <> Página oficial: <a href={profile.landing_page} target="_blank" rel="noreferrer" className="text-link hover:underline">{profile.landing_page}</a></>
            )}
            {profile.has_template && (
              <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-semibold text-heading">Plantilla:</span>
                <a href={download(profile.dataset_code, 'format=xlsx')} className={linkCls}><Download className="size-3.5" aria-hidden />Excel (.xlsx) con los códigos válidos</a>
                <a href={download(profile.dataset_code, 'format=csv')} className={linkCls}><Download className="size-3.5" aria-hidden />CSV</a>
                {profile.example_files.length > 0 && <span className="font-semibold text-heading">Para probar:</span>}
                {profile.example_files.map((name) => (
                  <a key={name} href={download(profile.dataset_code, `example=${name}`)} className={linkCls}>
                    <Download className="size-3.5" aria-hidden />ejemplo {name.replace(/_/g, ' ')}
                  </a>
                ))}
              </span>
            )}
          </p>
        )}
        <div className="flex items-center gap-3 md:col-span-2 lg:col-span-3">
          <button type="submit" disabled={uploading} className="inline-flex items-center gap-2 rounded-md bg-heading px-4 py-2 text-sm font-medium text-white hover:bg-brand disabled:opacity-60">
            <Upload className="size-4" aria-hidden /> {uploading ? 'Revisando…' : 'Subir y revisar'}
          </button>
          <span className="text-xs text-muted-text">Primero se revisa el archivo; nada se carga hasta que lo confirmes.</span>
          {state.error && <p role="alert" className="text-sm text-alert-critical-text">{state.error}</p>}
        </div>
      </form>

      {result && (
        <section aria-label="Resultado de la revisión" className="space-y-4 rounded-lg border border-line p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="size-5 text-muted-text" aria-hidden />
              <div>
                <p className="font-mono text-sm font-medium text-heading">{result.file_name}</p>
                <p className="text-xs text-muted-text">
                  {(result.size_bytes / 1e6).toFixed(1)} MB · sha256 {result.sha256.slice(0, 12)}… · {whole.format(result.records)} registros
                  {result.report.first_period ? ` · ${result.report.first_period} a ${result.report.last_period}` : ''}
                </p>
              </div>
            </div>
            <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${result.status === 'validated' ? 'border-success/40 bg-success-soft text-success' : 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text'}`}>
              {statusLabels[result.status] ?? result.status}
            </span>
          </div>
          {groups.length > 0 && (
            <ul className="space-y-2 rounded-md border border-alert-critical-border bg-alert-critical-bg p-3 text-xs text-alert-critical-text">
              {groups.map((g) => (
                <li key={`${g.kind}-${g.column}`}>
                  <p>
                    <span className="font-semibold">{g.title}</span>: {g.count} {g.count === 1 ? 'fila' : 'filas'}
                    {g.rows.length > 0 && ` (${g.count > g.rows.length ? 'entre otras, ' : ''}${g.rows.length === 1 ? 'fila' : 'filas'} ${g.rows.join(', ')})`}
                    {g.values.length > 0 && <> · {g.values.map((v) => `«${v}»`).join(', ')}</>}
                  </p>
                  {g.hint && <p className="text-alert-critical-text/80">{g.hint}</p>}
                </li>
              ))}
            </ul>
          )}
          {errors.length > 0 && (groups.length > 0 ? (
            <details className="text-xs text-muted-text">
              <summary className="cursor-pointer">Ver cada error ({errors.length}{errors.length < groups.reduce((n, g) => n + g.count, 0) ? ', los primeros' : ''})</summary>
              <ul className="mt-2 space-y-1">
                {errors.map((e, i) => <li key={i}>{e.row ? `Fila ${e.row}: ` : ''}{e.column ? `${e.column}: ` : ''}{e.message}</li>)}
              </ul>
            </details>
          ) : (
            <ul className="space-y-1 rounded-md border border-alert-critical-border bg-alert-critical-bg p-3 text-xs text-alert-critical-text">
              {errors.map((e, i) => <li key={i}>{e.row ? `Fila ${e.row}: ` : ''}{e.column ? `${e.column}: ` : ''}{e.message}</li>)}
            </ul>
          ))}
          {overlaps && overlaps.count > 0 && (
            <div className="flex gap-2 rounded-md border border-alert-warning-border bg-alert-warning-bg p-3 text-xs text-alert-warning-text">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <p>{overlaps.message}</p>
            </div>
          )}
          {warnings.length > 0 && (
            <ul className="space-y-1 rounded-md border border-alert-warning-border bg-alert-warning-bg p-3 text-xs text-alert-warning-text">
              {warnings.map((w, i) => <li key={i}>{w.message}</li>)}
            </ul>
          )}
          {columns.length > 0 && (
            <div className="overflow-x-auto">
              <p className="mb-2 text-xs font-semibold text-muted-text">Vista previa (primeras {result.preview.length} filas leídas)</p>
              <table className="w-full text-xs">
                <thead className="bg-surface-2 text-left text-muted-text"><tr>{columns.map((c) => <th key={c} className="px-2 py-1.5 font-semibold">{c}</th>)}</tr></thead>
                <tbody className="divide-y divide-line/60">
                  {result.preview.map((row, i) => <tr key={i}>{columns.map((c) => <td key={c} className="px-2 py-1">{row[c] === null || row[c] === undefined ? '—' : String(row[c])}</td>)}</tr>)}
                </tbody>
              </table>
            </div>
          )}
          {result.status === 'validated' && !done && (
            <form action={commitAction} className="flex flex-wrap items-center gap-3">
              {overlaps && overlaps.count > 0 && (
                <label className="flex w-full items-center gap-2 text-sm text-body">
                  <input type="checkbox" name="confirm_overlap" checked={confirmOverlap} onChange={(e) => setConfirmedFor(e.target.checked ? result.dataset_id : null)} />
                  Entiendo que {overlaps.count} valores ya están publicados por fuentes oficiales; cargarlos igual como fuente aparte.
                </label>
              )}
              <button type="submit" disabled={committing || (!!overlaps?.count && !confirmOverlap)} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                {committing ? 'Cargando y recalculando…' : 'Cargar al observatorio'}
              </button>
              <span className="text-xs text-muted-text">Si ya había una carga de este formato, se reemplaza; los valores anteriores quedan en el historial de revisiones.</span>
              {committed.error && <p role="alert" className="text-sm text-alert-critical-text">{committed.error}</p>}
            </form>
          )}
          {done && (
            <p role="status" className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="size-4" aria-hidden /> Cargado: {whole.format(done.records)} registros. Se recalcularon tendencias, proyecciones, ISE y alertas.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
