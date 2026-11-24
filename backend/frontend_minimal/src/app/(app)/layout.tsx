import { headers } from 'next/headers';
import { connection } from 'next/server';
import { Suspense, type ReactNode } from 'react';
import { z } from 'zod';
import { AssistantDock } from '@/components/minimal/AssistantDock';
import { MinimalHeader, MinimalHeaderSkeleton } from '@/components/minimal/MinimalHeader';
import { ProOnly } from '@/components/minimal/ProOnly';
import { apiGet } from '@/lib/api/client';
import { isFreePath, PATH_HEADER, PRO_PERMISSION } from '@/lib/auth/constants';
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
  return status?.enabled && status.can_ask ? <AssistantDock status={status} /> : null;
}

/** Cuenta gratuita: fuera de sus rutas, el aviso del acceso completo en lugar de la página. */
async function Gate({ children }: { children: ReactNode }) {
  await connection(); // depende de la sesión: se arma en cada request, no al prerenderizar
  const user = await requireUser();
  const path = (await headers()).get(PATH_HEADER) ?? '';
  return user.permissions.includes(PRO_PERMISSION) || isFreePath(path) ? children : <ProOnly />;
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<MinimalHeaderSkeleton />}>
        <Header />
      </Suspense>
      <main className="flex-1 bg-white">
        <Suspense fallback={null}>
          <Gate>{children}</Gate>
        </Suspense>
      </main>
      <Suspense fallback={null}>
        <Assistant />
      </Suspense>
    </>
  );
}
