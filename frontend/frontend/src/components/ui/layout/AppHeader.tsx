import Link from 'next/link';
import { Bell, BookOpen, ChevronDown, LogOut, Search } from 'lucide-react';
import { logout } from '@/lib/auth/actions';

type Props = {
  userName: string;
  userRole: string;
  unreadAlerts: number;
  canManage: boolean;
};

/** Isotipo del observatorio: barras ascendentes dentro del cuadrado de marca. */
export function LogoMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden fill="none">
      <rect x="3.2" y="12.4" width="3.4" height="8.2" rx="1.5" fill="currentColor" />
      <rect x="10.3" y="7.4" width="3.4" height="13.2" rx="1.5" fill="currentColor" opacity="0.85" />
      <rect x="17.4" y="3.4" width="3.4" height="17.2" rx="1.5" fill="currentColor" opacity="0.7" />
    </svg>
  );
}

function initials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export function AppHeader({ userName, userRole, unreadAlerts, canManage }: Props) {
  return (
    <header className="border-b border-card-border bg-canvas">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center gap-3 px-4 sm:px-6 lg:gap-6">
        <Link
          href="/inicio"
          className="flex shrink-0 items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span className="flex size-10 items-center justify-center rounded-[11px] bg-brand text-white shadow-sm">
            <LogoMark />
          </span>
          <span className="hidden leading-none sm:block">
            <span className="block text-[12.5px] font-bold tracking-[0.13em] text-heading">
              OBSERVATORIO
            </span>
            <span className="mt-1 block text-[10px] font-semibold tracking-[0.22em] text-brand">
              CONO SUR
            </span>
          </span>
        </Link>

        <form action="/panorama" role="search" className="hidden min-w-0 flex-1 justify-center lg:flex">
          <div className="relative w-full max-w-[420px]">
            <Search
              className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-placeholder"
              aria-hidden
            />
            <input
              type="search"
              name="q"
              aria-label="Buscar indicador, ocupación o habilidad"
              placeholder="Buscar indicador, ocupación o habilidad..."
              className="h-10 w-full rounded-lg border border-card-border bg-canvas pr-3 pl-10 text-[13px] text-body transition-colors placeholder:text-placeholder hover:border-line focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            />
          </div>
        </form>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <Link
            href="/alertas"
            className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] font-medium text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
          >
            <Bell className="size-4 text-muted-text" aria-hidden />
            <span className="hidden sm:inline">Alertas</span>
            {unreadAlerts > 0 && (
              <span className="rounded-full bg-brand px-1.5 py-0.5 text-[10px] leading-none font-bold text-white">
                {unreadAlerts > 99 ? '99+' : unreadAlerts}
              </span>
            )}
            <span className="sr-only">{unreadAlerts} sin leer</span>
          </Link>

          <Link
            href="/metodologia/ise"
            className="hidden items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] font-medium text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus xl:flex"
          >
            <BookOpen className="size-4 text-muted-text" aria-hidden />
            Metodología y fuentes
          </Link>

          {canManage && (
          <details data-menu className="group relative">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-lg px-2.5 py-2 text-[13px] font-medium text-body transition-colors hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
              Administración
              <ChevronDown
                className="size-3.5 text-muted-text transition-transform group-open:rotate-180"
                aria-hidden
              />
            </summary>
            <div className="absolute right-0 z-30 mt-2 w-56 overflow-hidden rounded-xl border border-card-border bg-canvas py-1 shadow-lg">
              <Link
                href="/admin/datos"
                className="block px-4 py-2.5 text-[13px] text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
              >
                Carga de datos
              </Link>
              <Link
                href="/metodologia/fuentes"
                className="block px-4 py-2.5 text-[13px] text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
              >
                Fuentes y actualización
              </Link>
            </div>
          </details>
          )}

          <div className="ml-1 flex items-center gap-2.5 border-l border-card-border pl-2.5 sm:pl-3">
            <span className="flex size-10 items-center justify-center rounded-full bg-brand text-[12px] font-bold tracking-wide text-white">
              {initials(userName)}
            </span>
            <span className="hidden leading-tight md:block">
              <span className="block text-[13px] font-semibold text-heading">{userName}</span>
              <span className="block text-[11px] font-medium text-brand">{userRole}</span>
            </span>
            <form action={logout}>
              <button
                type="submit"
                aria-label="Cerrar sesión"
                title="Cerrar sesión"
                className="flex items-center rounded-lg p-2 text-muted-text hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
              >
                <LogOut className="size-4" aria-hidden />
              </button>
            </form>
          </div>
        </div>
      </div>
    </header>
  );
}
