import Link from 'next/link';
import { ArrowRight, Briefcase, Globe2, GraduationCap, Layers, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { QuickAccess } from '@/lib/ui-types';

const ICONS = {
  globe: Globe2,
  layers: Layers,
  briefcase: Briefcase,
  graduation: GraduationCap,
  trend: TrendingUp,
};

/** Accesos rápidos del inicio: 4 tarjetas y una destacada de ancho completo. */
export function QuickAccessGrid({ items }: { items: QuickAccess[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((item) => {
        const Icon = ICONS[item.icon];
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'group flex items-center gap-4 rounded-lg border border-line bg-surface p-5 transition-colors',
              'hover:border-brand/50 hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
              item.featured && 'sm:col-span-2',
            )}
          >
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
              <Icon className="size-6" aria-hidden />
            </span>
            <span className="min-w-0">
              <span className="block font-semibold text-heading">{item.title}</span>
              <span className="block text-sm text-muted-text">{item.description}</span>
            </span>
            <ArrowRight
              className="ml-auto size-5 shrink-0 text-muted-text transition-transform group-hover:translate-x-0.5 group-hover:text-brand"
              aria-hidden
            />
          </Link>
        );
      })}
    </div>
  );
}
