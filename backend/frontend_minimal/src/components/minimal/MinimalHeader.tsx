import { Bell, LogOut } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { Suspense } from 'react';
import { logout } from '@/lib/auth/actions';
import { PRO_PERMISSION } from '@/lib/auth/constants';
import { PERMISSIONS, type User } from '@/lib/schemas/auth';
import { Dropdown } from './Dropdown';
import { HeaderHeight } from './HeaderHeight';
import { SearchPalette } from './SearchPalette';
import { SubNav } from './SubNav';
import { TopNav } from './TopNav';

const menuItem = 'block w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-100';

function Brand() {
  return (
    <Link href="/panorama" className="flex items-center">
      <Image src="/brand/predix-horizontal.svg" alt="Predix" width={126} height={36} priority className="h-7 w-auto" />
    </Link>
  );
}

const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');

/** Barra única: marca, cinco secciones, buscador, alertas y cuenta (con lo secundario adentro). */
export function MinimalHeader({ user, unreadAlerts }: { user: User; unreadAlerts: number }) {
  const admin = [
    user.permissions.includes(PERMISSIONS.manageUsers) && { href: '/admin/usuarios', label: 'Usuarios y accesos' },
    user.permissions.includes(PERMISSIONS.manageData) && { href: '/admin/datos', label: 'Carga de datos' },
  ].filter(Boolean) as { href: string; label: string }[];
  const pro = user.permissions.includes(PRO_PERMISSION); // cuenta gratuita: sin buscador ni alertas
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <HeaderHeight />
      <div className="mx-auto flex min-h-14 max-w-[1360px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2 sm:px-8">
        <Brand />
        <TopNav free={!pro} />
        <div className="ml-auto flex flex-1 items-center justify-end gap-2">
          {pro && <SearchPalette />}
          {pro && (
            <Link href="/alertas" aria-label={`Alertas, ${unreadAlerts} sin leer`} className="relative flex size-10 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100">
              <Bell className="size-5" aria-hidden />
              {unreadAlerts > 0 && <span className="absolute right-2 top-2 size-2 rounded-full bg-red-600" aria-hidden />}
            </Link>
          )}
          <Dropdown
            summaryClassName="flex size-9 cursor-pointer items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-900"
            summary={<><span aria-hidden>{initials(user.full_name)}</span><span className="sr-only">Cuenta de {user.full_name}</span></>}
          >
            <div className="absolute right-0 z-40 mt-2 w-64 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              <div className="border-b border-slate-100 px-4 py-2">
                <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
                <p className="text-xs text-slate-500">{user.role_label} · {user.email}</p>
              </div>
              {pro ? (
                <>
                  <Link href="/alertas" className={menuItem}>Alertas</Link>
                  <Link href="/metodologia/ise" className={menuItem}>Metodología y fuentes</Link>
                </>
              ) : (
                <p className="px-4 py-2 text-xs text-slate-500">Cuenta gratuita: Inicio y Panorama. Para el acceso completo, pedíselo a un administrador.</p>
              )}
              {admin.map((l) => <Link key={l.href} href={l.href} className={menuItem}>{l.label}</Link>)}
              <form action={logout} className="border-t border-slate-100">
                <button type="submit" className={`${menuItem} flex items-center gap-2`}><LogOut className="size-4" aria-hidden /> Cerrar sesión</button>
              </form>
            </div>
          </Dropdown>
        </div>
      </div>
      <Suspense fallback={null}>
        <SubNav free={!pro} />
      </Suspense>
    </header>
  );
}

export function MinimalHeaderSkeleton() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex min-h-14 max-w-[1360px] items-center gap-6 px-4 sm:px-8">
        <Brand />
        <span className="h-8 w-96 animate-pulse rounded-md bg-slate-100" aria-hidden />
      </div>
    </header>
  );
}
