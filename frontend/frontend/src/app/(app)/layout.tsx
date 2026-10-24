import type { ReactNode } from 'react';
import { AppHeader } from '@/components/ui/layout/AppHeader';
import { MainNav } from '@/components/ui/layout/MainNav';

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {/* Usuario y alertas son datos de ejemplo hasta definir autenticación */}
      <AppHeader userName="Eduardo González" userRole="consultas" unreadAlerts={9} />
      <MainNav />
      <main>{children}</main>
    </>
  );
}
