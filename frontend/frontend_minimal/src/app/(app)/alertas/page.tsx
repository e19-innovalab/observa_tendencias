import { ArrowRight, CheckCheck } from 'lucide-react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { HowCalculated } from '@/components/methodology/HowCalculated';
import { ChipGroup, SelectParam, Segmented } from '@/components/ui/filters/UrlControls';
import { PageHero } from '@/components/ui/layout/PageHero';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { Pager } from '@/components/ui/Pager';
import { markAlertRead, markAllAlertsRead } from '@/lib/alerts/actions';
import { getAlertRules, getAlertsPage } from '@/lib/api/alerts';
import { ApiError } from '@/lib/api/client';
import { getCountries } from '@/lib/api/common';
import { getToken, requireUser } from '@/lib/auth/session';
import type { AlertItem } from '@/lib/schemas/api';
import { formatDate, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Alertas' };
type SearchParams = { country?: string; severity?: string; tipo?: string; estado?: string; page?: string };
const PAGE_SIZE = 20;
const STATES = [
  { value: 'todas', label: 'Todas' },
  { value: 'no_leidas', label: 'No leídas' },
];
const SEVERITY_STYLES: Record<string, { dot: string; badge: string }> = {
  high: { dot: 'bg-alert-critical-icon', badge: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text' },
  medium: { dot: 'bg-alert-warning-icon', badge: 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text' },
  low: { dot: 'bg-alert-positive-icon', badge: 'border-line bg-surface text-body' },
};

export default function AlertasPage({ searchParams }: PageProps<'/alertas'>) {
  return (
    <>
      <PageHero
        title="Alertas"
        description="Cambios que el observatorio detecta solo después de cada actualización de datos: variaciones fuera de lo habitual, cambios de tendencia, ocupaciones que cambian de nivel en el ISE y fuentes que dejaron de actualizarse."
      />
      <Suspense fallback={<PageSkeleton />}>
        <AlertasContent searchParams={searchParams as Promise<SearchParams>} />
      </Suspense>
    </>
  );
}

/** Adónde ir para ver el dato que disparó la alerta. */
function targetOf(a: AlertItem): { href: string; label: string } | null {
  if (a.occupation) return { href: `/ocupaciones/${a.occupation.code}${a.country_iso3 ? `?country=${a.country_iso3}` : ''}`, label: 'Ver ocupación' };
  if (a.indicator) {
    const q = new URLSearchParams({ indicator: a.indicator.code });
    if (a.country_iso3) q.set('country', a.country_iso3);
    return { href: `/tendencias?${q}`, label: 'Ver tendencia' };
  }
  return null;
}

async function AlertasContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const user = await requireUser();
  const canManage = user.permissions.includes('manage_data');
  const page = Math.max(1, Number(sp.page ?? '1') || 1);
  const onlyUnread = sp.estado === 'no_leidas';
  let data, all, rules, countries;
  try {
    const token = await getToken();
    [data, all, rules, countries] = await Promise.all([
      getAlertsPage({ country: sp.country, severity: sp.severity, alert_type: sp.tipo, unread: onlyUnread || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }, token),
      getAlertsPage({ limit: 1, offset: 0 }, token),
      getAlertRules(),
      getCountries(),
    ]);
  } catch (e) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text">
          {e instanceof ApiError ? e.message : 'Error inesperado al cargar las alertas.'}
        </p>
      </div>
    );
  }
  const countryNames = Object.fromEntries(countries.map((c) => [c.iso3, c.name_es]));
  const severityLabel = Object.fromEntries(rules.severities.map((s) => [s.code, s.label]));

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
      <section aria-label="Resumen" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-lg border border-line bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-text">Alertas</p>
          <p className="mt-2 text-2xl font-semibold text-heading">{all.total}</p>
        </div>
        <div className="rounded-lg border border-line bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-text">No leídas</p>
          <p className="mt-2 text-2xl font-semibold text-heading">{all.unread}</p>
        </div>
        {rules.severities.map((s) => (
          <div key={s.code} className="rounded-lg border border-line bg-white p-4" title={s.definition ?? undefined}>
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-text">
              <span className={`size-2 rounded-full ${SEVERITY_STYLES[s.code]?.dot ?? 'bg-info'}`} aria-hidden /> Severidad {s.label.toLowerCase()}
            </p>
            <p className="mt-2 text-2xl font-semibold text-heading">{all.by_severity[s.code] ?? 0}</p>
          </div>
        ))}
      </section>

      <section aria-label="Filtros" className="flex flex-wrap items-end gap-6 rounded-lg border border-line bg-white p-5">
        <ChipGroup name="country" label="Países" value={sp.country ?? ''} reset={['page']} options={countries.map((c) => ({ value: c.iso3, label: c.iso3 }))} />
        <ChipGroup name="severity" label="Severidad" value={sp.severity ?? ''} allLabel="Todas" reset={['page']} options={rules.severities.map((s) => ({ value: s.code, label: s.label }))} />
        <div className="w-56">
          <SelectParam name="tipo" label="Tipo de alerta" value={sp.tipo ?? ''} placeholder="Todos los tipos" reset={['page']} options={rules.rules.map((r) => ({ value: r.alert_type, label: r.label }))} />
        </div>
        <Segmented name="estado" label="Estado" value={onlyUnread ? 'no_leidas' : 'todas'} options={STATES} />
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line/70 p-5">
          <div>
            <h2 className="text-lg font-semibold text-heading">Alertas detectadas</h2>
            <p className="mt-1 text-sm text-muted-text">Las más recientes y más severas primero. {data.total} con estos filtros.</p>
          </div>
          {canManage && all.unread > 0 && (
            <form action={markAllAlertsRead}>
              <button type="submit" className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-xs font-medium text-heading hover:border-brand">
                <CheckCheck className="size-3.5" aria-hidden /> Marcar todas como leídas
              </button>
            </form>
          )}
        </div>
        <ul className="divide-y divide-line/60">
          {data.items.map((a) => {
            const style = SEVERITY_STYLES[a.severity];
            const target = targetOf(a);
            const values =
              a.previous_value !== null && a.current_value !== null
                ? `${formatValue(a.previous_value, a.unit ?? '')} → ${formatValue(a.current_value, a.unit ?? '')}`
                : null;
            return (
              <li key={a.alert_id} className={`flex flex-wrap items-start gap-4 p-5 ${a.is_read ? '' : 'bg-surface/60'}`}>
                <span className={`mt-1.5 size-2.5 shrink-0 rounded-full ${style?.dot ?? 'bg-info'}`} aria-hidden />
                <div className="min-w-0 flex-1 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded border px-1.5 py-0.5 text-[11px] font-semibold ${style?.badge ?? 'border-line'}`}>{severityLabel[a.severity] ?? a.severity_label}</span>
                    <span className="text-xs font-medium uppercase tracking-wide text-muted-text">{a.alert_type_label}</span>
                    {!a.is_read && <span className="rounded bg-brand px-1.5 py-0.5 text-[10px] font-semibold text-white">Nueva</span>}
                  </div>
                  <p className="mt-1.5 font-medium text-heading">
                    {[a.indicator?.name, a.occupation?.name, a.source?.name].filter(Boolean).join(' · ')}
                    {a.country_iso3 ? ` · ${countryNames[a.country_iso3] ?? a.country_iso3}` : ''}
                  </p>
                  <p className="text-body">{a.message}{values ? ` (${values}${a.period ? `, ${a.period}` : ''})` : ''}</p>
                  <p className="mt-1 text-xs text-muted-text">Detectada el {formatDate(a.detected_at)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {target && (
                    <Link href={target.href} className="inline-flex items-center gap-1 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-heading hover:border-brand">
                      {target.label} <ArrowRight className="size-3" aria-hidden />
                    </Link>
                  )}
                  {canManage && !a.is_read && (
                    <form action={markAlertRead.bind(null, a.alert_id)}>
                      <button type="submit" className="rounded-md px-2.5 py-1.5 text-xs font-medium text-link hover:underline">Marcar leída</button>
                    </form>
                  )}
                </div>
              </li>
            );
          })}
          {data.items.length === 0 && <li className="p-10 text-center text-sm text-muted-text">No hay alertas con estos filtros.</li>}
        </ul>
        <div className="border-t border-line/70 p-4">
          <Pager total={data.total} pageSize={PAGE_SIZE} label="alertas" />
        </div>
      </section>

      <HowCalculated types={['alert']} title="¿Cómo se generan las alertas?" />

      <section className="rounded-lg border border-line bg-white p-5">
        <h2 className="text-lg font-semibold text-heading">Tipos de alerta y umbrales</h2>
        <p className="mt-1 text-sm text-muted-text">
          Las reglas y sus umbrales están en la configuración del backend (analytics.yaml) y se aplican después de cada actualización.
          {!canManage && ' Marcar alertas como leídas requiere el permiso de gestión de datos.'}
        </p>
        <dl className="mt-4 grid gap-4 md:grid-cols-2">
          {rules.rules.map((r) => (
            <div key={r.alert_type} className="rounded-md border border-line p-4">
              <dt className="flex items-center justify-between gap-2 font-medium text-heading">
                {r.label}
                {!r.active && <span className="rounded border border-dashed border-line px-1.5 py-0.5 text-[11px] font-normal text-muted-text">Inactiva</span>}
              </dt>
              <dd className="mt-1 text-sm text-body">{r.definition ?? '—'}</dd>
              <dd className="mt-2 text-xs text-muted-text">Severidad: {r.severity_rule}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
