import Link from 'next/link';
import { BarChart3 } from 'lucide-react';

const links = [
  { label: 'El observatorio', href: '/landing#observatorio' },
  { label: 'Qué podés encontrar', href: '/landing#encontrar' },
  { label: 'Cómo funciona', href: '/landing#funciona' },
  { label: 'Alcance', href: '/landing#alcance' },
];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/landing"
          className="flex items-center gap-2 rounded-md py-1 text-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span className="flex size-9 items-center justify-center rounded-lg bg-brand text-white">
            <BarChart3 className="size-5" aria-hidden />
          </span>
          <span className="hidden text-lg font-bold tracking-tight text-heading sm:block">Observa Tendencias</span>
        </Link>
        <nav aria-label="Principal" className="hidden gap-6 text-sm font-medium text-body lg:flex">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-link">
              {l.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/login"
          className="rounded-md bg-brand px-5 py-2 text-sm font-medium text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          Ingresar
        </Link>
      </div>
    </header>
  );
}
