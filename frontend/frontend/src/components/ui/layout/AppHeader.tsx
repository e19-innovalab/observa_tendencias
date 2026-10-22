import { Bell, ChevronDown, User } from 'lucide-react';

type Props = {
  userName: string;
  userRole: string;
  unreadAlerts: number;
};

export function AppHeader({ userName, userRole, unreadAlerts }: Props) {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <span className="text-2xl font-bold text-gray-700">LOGO</span>

        <div className="flex items-center gap-4">
          <button
            type="button"
            className="flex items-center gap-2 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-slate-200 focus-visible:outline-2 focus-visible:outline-blue-600"
          >
            Administración
            <ChevronDown className="size-4" aria-hidden />
          </button>

          <button
            type="button"
            className="relative rounded-md p-2 text-blue-700 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600"
            aria-label={`Notificaciones, ${unreadAlerts} sin leer`}
          >
            <Bell className="size-5" aria-hidden />
            {unreadAlerts > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex size-4 items-center justify-center rounded-full bg-red-600 text-[10px] font-semibold text-white">
                {unreadAlerts > 9 ? '9+' : unreadAlerts}
              </span>
            )}
          </button>

          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-full bg-blue-400 text-white">
              <User className="size-5" aria-hidden />
            </span>
            <div className="hidden leading-tight sm:block">
              <p className="text-sm font-semibold text-gray-900">{userName}</p>
              <p className="text-xs text-gray-500">{userRole}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
