import { connection } from 'next/server';
import { Suspense, type ReactNode } from 'react';
import { PixiDock } from '@/components/assistant/PixiDock';
import { AppHeader } from '@/components/ui/layout/AppHeader';
import { MainNav } from '@/components/ui/layout/MainNav';
import { StickyBar } from '@/components/ui/layout/StickyBar';
import { ExperimentalTabs } from '@/components/ui/navigation/ExperimentalTabs';
import { apiGet } from '@/lib/api/client';
import { getToken, requireUser } from '@/lib/auth/session';
import { AssistantStatusSchema } from '@/lib/schemas/assistant';

/** Lee la sesión: va dentro de un Suspense para no frenar el resto del layout. */
async function Header() {
  await connection(); // depende de la sesión: se arma en cada request, no al prerenderizar
  const user = await requireUser();
  return <AppHeader userName={user.full_name} userRole={user.role_label} unreadAlerts={0} canManage={user.role !== 'viewer'} />;
}

async function Sticky() {
  await connection();
  const user = await requireUser();
  return <StickyBar canManage={user.role !== 'viewer'} />;
}

/** Pixi (antes Dixi, Predi y Baqueano): solo si el asistente está prendido y el backend responde. */
async function Assistant() {
  await connection(); // depende de la sesión: se arma en cada request, no al prerenderizar
  const status = await apiGet('/assistant', AssistantStatusSchema, {}, 0, { token: await getToken() }).catch(
    () => null,
  );
  return status?.enabled ? <PixiDock status={status} /> : null;
}

function HeaderSkeleton() {
  return (
    <header className="border-b border-card-border bg-canvas" aria-hidden>
      <div className="mx-auto flex h-[72px] max-w-7xl items-center gap-3 px-4 sm:px-6">
        <span className="size-10 rounded-[11px] bg-surface-2" />
        <span className="h-4 w-44 rounded bg-surface-2" />
      </div>
    </header>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<HeaderSkeleton />}>
        <Header />
      </Suspense>
      <MainNav />
      <Suspense fallback={null}>
        <Sticky />
      </Suspense>
      <ExperimentalTabs />
      <main className="flex-1">{children}</main>
      <Suspense fallback={null}>
        <Assistant />
      </Suspense>
    </>
  );
}
