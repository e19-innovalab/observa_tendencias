'use client';

import { CloudUpload, Users } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS = [
  { href: '/admin/usuarios', label: 'Usuarios y accesos', icon: Users },
  { href: '/admin/datos', label: 'Carga de datos', icon: CloudUpload },
];

export function AdminTabs() {
  const pathname = usePathname();
  return (
    <nav aria-label="Administración" className="flex gap-2">
      {TABS.map(({ href, label, icon: Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium ${active ? 'bg-heading text-white' : 'text-body hover:bg-surface'}`}
          >
            <Icon className="size-4" aria-hidden /> {label}
          </Link>
        );
      })}
    </nav>
  );
}
