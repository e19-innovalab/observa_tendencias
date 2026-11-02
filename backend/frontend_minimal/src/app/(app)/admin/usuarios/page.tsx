import { UserPlus } from 'lucide-react';
import type { Metadata } from 'next';
import { Suspense } from 'react';
import { UserForm } from '@/components/admin/UserForm';
import { SearchParam } from '@/components/ui/filters/SearchParam';
import { SelectParam } from '@/components/ui/filters/UrlControls';
import { PageSkeleton } from '@/components/ui/layout/PageSkeleton';
import { Pager } from '@/components/ui/Pager';
import { setUserStatus } from '@/lib/admin/actions';
import { getUserOptions, getUsers } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { getCountries, getSectors } from '@/lib/api/common';
import { requirePermission } from '@/lib/auth/session';
import { PERMISSIONS } from '@/lib/schemas/auth';
import { formatDate } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Usuarios y accesos' };
type SearchParams = { q?: string; role?: string; sector?: string; status?: string; page?: string };
const PAGE_SIZE = 20;
const ACTIVE = 'active';
const SUSPENDED = 'suspended';

export default function UsuariosPage({ searchParams }: PageProps<'/admin/usuarios'>) {
  return (
    <>
      <div className="border-b border-line bg-white">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <h1 className="text-2xl font-semibold text-heading">Usuarios y accesos</h1>
          <p className="mt-1 text-sm text-muted-text">Cuentas del observatorio, su rol (qué pueden hacer) y su sector y países de interés.</p>
        </div>
      </div>
      <Suspense fallback={<PageSkeleton />}>
        <UsuariosContent searchParams={searchParams as Promise<SearchParams>} />
      </Suspense>
    </>
  );
}

const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');

async function UsuariosContent({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const me = await requirePermission(PERMISSIONS.manageUsers);
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page ?? '1') || 1);
  let data, options, sectors, countries;
  try {
    [data, options, sectors, countries] = await Promise.all([
      getUsers({ q: sp.q, role: sp.role, sector: sp.sector, status: sp.status, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
      getUserOptions(),
      getSectors(),
      getCountries(),
    ]);
  } catch (e) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p role="alert" className="rounded-md border border-alert-critical-border bg-alert-critical-bg p-4 text-sm text-alert-critical-text">
          {e instanceof ApiError ? e.message : 'Error inesperado al cargar las cuentas.'}
        </p>
      </div>
    );
  }
  const roleOptions = options.roles.map((r) => ({ value: r.role, label: r.label }));
  const statusOptions = Object.entries(options.statuses).map(([value, label]) => ({ value, label }));
  const sectorOptions = sectors.map((s) => ({ value: s.sector_code, label: s.name }));
  const countryOptions = countries.map((c) => ({ value: c.iso3, label: c.iso3 }));
  const formProps = { roles: roleOptions, statuses: statusOptions, sectors: sectorOptions, countries: countryOptions, passwordMin: options.password_min_length, defaultRole: options.default_role };

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      <details className="group rounded-lg border border-line bg-white">
        <summary className="flex cursor-pointer list-none items-center gap-2 p-4 text-sm font-semibold text-heading [&::-webkit-details-marker]:hidden">
          <UserPlus className="size-4" aria-hidden /> Crear una cuenta
        </summary>
        <div className="border-t border-line/70 p-5">
          <UserForm {...formProps} />
          <p className="mt-3 text-xs text-muted-text">
            Roles: {options.roles.map((r) => `${r.label} (${r.permissions.join(', ')})`).join(' · ')}. Compartí la contraseña inicial por un canal seguro; la persona puede cambiarla después.
          </p>
        </div>
      </details>

      <section aria-label="Filtros" className="flex flex-wrap items-end gap-4 rounded-lg border border-line bg-white p-4">
        <div className="w-72"><SearchParam label="Buscar" placeholder="Nombre o correo" /></div>
        <div className="w-44"><SelectParam name="role" label="Rol" value={sp.role ?? ''} placeholder="Todos los roles" reset={['page']} options={roleOptions} /></div>
        <div className="w-52"><SelectParam name="sector" label="Sector" value={sp.sector ?? ''} placeholder="Todos los sectores" reset={['page']} options={sectorOptions} /></div>
        <div className="w-44"><SelectParam name="status" label="Estado" value={sp.status ?? ''} placeholder="Cualquier estado" reset={['page']} options={statusOptions} /></div>
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-white">
        <div className="border-b border-line/70 p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-heading">Cuentas registradas <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-xs font-medium normal-case text-muted-text">{data.total}</span></h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[60rem] text-sm">
            <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-text">
              <tr>
                <th scope="col" className="px-4 py-3">Usuario</th>
                <th scope="col" className="px-4 py-3">Rol</th>
                <th scope="col" className="px-4 py-3">Sector de interés</th>
                <th scope="col" className="px-4 py-3">Ámbito</th>
                <th scope="col" className="px-4 py-3">Último acceso</th>
                <th scope="col" className="px-4 py-3">Estado</th>
                <th scope="col" className="px-4 py-3"><span className="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              {data.items.map((u) => {
                const suspended = u.status !== ACTIVE;
                const isMe = u.user_id === me.user_id;
                return (
                  <tr key={u.user_id} className={`align-top ${suspended ? 'text-muted-text' : ''}`}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-heading">{initials(u.full_name)}</span>
                        <div>
                          <p className={`font-medium ${suspended ? 'line-through' : 'text-heading'}`}>
                            {u.full_name} {isMe && <span className="ml-1 rounded border border-line px-1 text-[10px] font-semibold no-underline">VOS</span>}
                          </p>
                          <p className="text-xs text-muted-text">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><span className="rounded-full border border-line px-2 py-0.5 text-xs font-medium">{u.role_label}</span></td>
                    <td className="px-4 py-3">{u.sector_name ?? 'Transversal'}</td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-line px-1.5 py-0.5 text-xs font-medium">{u.countries.length ? u.countries.join(', ') : 'Regional'}</span>
                    </td>
                    <td className="px-4 py-3 text-xs">{formatDate(u.last_login_at) ?? 'Nunca'}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${suspended ? 'border-line bg-surface' : 'border-success/40 bg-success-soft text-success'}`}>{u.status_label}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <details className="group relative">
                          <summary className="cursor-pointer list-none text-xs font-medium text-link hover:underline [&::-webkit-details-marker]:hidden">Editar</summary>
                          <div className="absolute right-0 z-20 mt-2 w-[min(56rem,90vw)] rounded-lg border border-line bg-white p-5 text-left shadow-lg">
                            <p className="mb-3 text-sm font-semibold text-heading">{u.full_name} · {u.email}</p>
                            <UserForm user={u} {...formProps} />
                          </div>
                        </details>
                        {!isMe && (
                          <form action={setUserStatus.bind(null, u.user_id, suspended ? ACTIVE : SUSPENDED)}>
                            <button type="submit" className="text-xs font-medium text-link hover:underline">{suspended ? 'Reactivar' : 'Suspender'}</button>
                          </form>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {data.items.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-text">No hay cuentas con estos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="border-t border-line/70 p-4">
          <Pager total={data.total} pageSize={PAGE_SIZE} label="cuentas" />
        </div>
      </section>
    </div>
  );
}
