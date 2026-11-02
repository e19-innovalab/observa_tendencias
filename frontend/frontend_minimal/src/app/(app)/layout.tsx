import { connection } from 'next/server';
import { Suspense, type ReactNode } from 'react';
import { z } from 'zod';
import { AssistantDock } from '@/components/minimal/AssistantDock';
import { MinimalHeader, MinimalHeaderSkeleton } from '@/components/minimal/MinimalHeader';
import { apiGet } from '@/lib/api/client';
import { getToken, requireUser } from '@/lib/auth/session';
import { AssistantStatusSchema } from '@/lib/schemas/assistant';

const AlertCountSchema = z.object({ unread: z.number() });

/** Lee la sesión: va dentro de un Suspense para no frenar el resto del layout. */
async function Header() {
  await connection(); // depende de la sesión: se arma en cada request, no al prerenderizar
  const user = await requireUser();
  const alerts = await apiGet('/alerts', AlertCountSchema, { limit: 1 }, 60).catch(() => ({ unread: 0 }));
  return <MinimalHeader user={user} unreadAlerts={alerts.unread} />;
}

/** Asistente (pestaña a la derecha): solo si está prendido y el backend responde. */
async function Assistant() {
  await connection(); // depende de la sesión: se arma en cada request, no al prerenderizar
  const status = await apiGet('/assistant', AssistantStatusSchema, {}, 0, { token: await getToken() }).catch(() => null);
  return status?.enabled ? <AssistantDock status={status} /> : null;
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<MinimalHeaderSkeleton />}>
        <Header />
      </Suspense>
      <main className="flex-1 bg-white">{children}</main>
      <Suspense fallback={null}>
        <Assistant />
      </Suspense>
    </>
  );
}
