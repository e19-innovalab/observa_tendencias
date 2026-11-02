import Link from 'next/link';
import { BarChart3, Bell, ChevronDown, User } from 'lucide-react';

type Props = {
  userName: string;
  userRole: string;
  unreadAlerts: number;
};

export function AppHeader({ userName, userRole, unreadAlerts }: Props) {
  return (
    <header className="border-b border-line bg-canvas">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/inicio"
          className="flex items-center gap-2 rounded-md py-1 text-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span className="flex size-9 items-center justify-center rounded-lg bg-brand text-white">
            <BarChart3 className="size-5" aria-hidden />
          </span>
          <span className="hidden text-lg font-bold tracking-tight text-heading sm:block">
            Observa Tendencias
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-4">
          <button
            type="button"
            className="flex items-center gap-2 rounded-md bg-surface-2 px-3 py-2 text-sm font-medium text-body hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus sm:px-4"
          >
            Administración
            <ChevronDown className="size-4" aria-hidden />
          </button>

          <button
            type="button"
            className="relative rounded-md p-2 text-brand hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-focus"
            aria-label={`Notificaciones, ${unreadAlerts} sin leer`}
          >
            <Bell className="size-5" aria-hidden />
            {unreadAlerts > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex size-4 items-center justify-center rounded-full bg-danger text-[10px] font-semibold text-white">
                {unreadAlerts > 9 ? '9+' : unreadAlerts}
              </span>
            )}
          </button>

          <div className="flex items-center gap-3 border-l border-line pl-3 sm:pl-4">
            <span className="flex size-9 items-center justify-center rounded-full bg-brand/15 text-brand">
              <User className="size-5" aria-hidden />
            </span>
            <div className="hidden leading-tight sm:block">
              <p className="text-sm font-semibold text-heading">{userName}</p>
              <p className="text-xs capitalize text-muted-text">{userRole}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
