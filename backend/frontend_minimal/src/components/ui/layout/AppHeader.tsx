import { Bell, ChevronDown, LogOut, User as UserIcon } from 'lucide-react';
import Link from 'next/link';
import { Logo } from '@/components/brand/Logo';
import { logout } from '@/lib/auth/actions';
import { PERMISSIONS, type User } from '@/lib/schemas/auth';

type Props = { user: User; unreadAlerts: number };

const menuItem =
  'block px-4 py-2 text-sm text-body hover:bg-surface-2 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus';

export function AppHeader({ user, unreadAlerts }: Props) {
  const adminLinks = [
    user.permissions.includes(PERMISSIONS.manageUsers) && { href: '/admin/usuarios', label: 'Usuarios y accesos' },
    user.permissions.includes(PERMISSIONS.manageData) && { href: '/admin/datos', label: 'Carga de datos' },
  ].filter(Boolean) as { href: string; label: string }[];

  return (
    <header className="border-b border-line/60 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <Logo href="/inicio" />

        <div className="flex items-center gap-3">
          {adminLinks.length > 0 && (
            <details className="relative">
              <summary className="flex cursor-pointer list-none items-center gap-2 rounded-md bg-surface-2 px-4 py-2 text-sm font-medium text-heading hover:bg-selection focus-visible:outline-2 focus-visible:outline-focus">
                Administración
                <ChevronDown className="size-4" aria-hidden />
              </summary>
              <div className="absolute right-0 z-20 mt-2 w-56 overflow-hidden rounded-md border border-line bg-white py-1 shadow-lg">
                {adminLinks.map((l) => (
                  <Link key={l.href} href={l.href} className={menuItem}>
                    {l.label}
                  </Link>
                ))}
              </div>
            </details>
          )}

          <Link
            href="/alertas"
            className="relative rounded-md p-2 text-brand hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-focus"
            aria-label={`Alertas, ${unreadAlerts} sin leer`}
          >
            <Bell className="size-5" aria-hidden />
            {unreadAlerts > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
                {unreadAlerts > 99 ? '99+' : unreadAlerts}
              </span>
            )}
          </Link>

          <details className="relative">
            <summary className="flex cursor-pointer list-none items-center gap-3 rounded-md px-2 py-1 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-focus">
              <span className="flex size-10 items-center justify-center rounded-full bg-info text-white">
                <UserIcon className="size-5" aria-hidden />
              </span>
              <span className="hidden text-left leading-tight sm:block">
                <span className="block text-sm font-semibold text-heading">{user.full_name}</span>
                <span className="block text-xs text-muted-text">{user.role_label}</span>
              </span>
            </summary>
            <div className="absolute right-0 z-20 mt-2 w-60 overflow-hidden rounded-md border border-line bg-white py-1 shadow-lg">
              <p className="border-b border-line/60 px-4 py-2 text-xs text-muted-text">{user.email}</p>
              <form action={logout}>
                <button type="submit" className={`${menuItem} flex w-full items-center gap-2 text-left`}>
                  <LogOut className="size-4" aria-hidden />
                  Cerrar sesión
                </button>
              </form>
            </div>
          </details>
        </div>
      </div>
    </header>
  );
}

/** Mientras se verifica la sesión. */
export function AppHeaderSkeleton() {
  return (
    <header className="border-b border-line/60 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <Logo href="/inicio" />
        <span className="h-10 w-48 animate-pulse rounded-md bg-surface-2" aria-hidden />
      </div>
    </header>
  );
}
