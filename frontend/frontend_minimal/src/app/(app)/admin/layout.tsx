import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { AdminTabs } from '@/components/admin/AdminTabs';

export default function AdminLayout({ children }: LayoutProps<'/admin'>) {
  return (
    <>
      <div className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <AdminTabs />
          <Link href="/inicio" className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-xs font-medium text-heading hover:border-brand">
            <ArrowLeft className="size-3.5" aria-hidden /> Volver al observatorio
          </Link>
        </div>
      </div>
      {children}
    </>
  );
}
