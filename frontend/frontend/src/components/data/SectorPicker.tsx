import Link from 'next/link';
import {
  Activity,
  BrainCircuit,
  Check,
  MonitorPlay,
  Plane,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type SectorOption = { sector_code: string; name: string };

const ICONS: Record<string, LucideIcon> = {
  technology: MonitorPlay,
  energy: Zap,
  health: Activity,
  knowledge_economy: BrainCircuit,
  tourism: Plane,
};

const ORDER = ['technology', 'energy', 'health', 'knowledge_economy', 'tourism'];

/** Tarjetas de sector con icono. Cada tarjeta navega al sector elegido. */
export function SectorPicker({
  sectors,
  active,
  hrefFor,
  className,
}: {
  sectors: SectorOption[];
  active?: string;
  hrefFor: (sectorCode: string) => string;
  className?: string;
}) {
  const ordered = [...sectors].sort((a, b) => {
    const ai = ORDER.indexOf(a.sector_code);
    const bi = ORDER.indexOf(b.sector_code);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div className={cn('grid gap-3 sm:grid-cols-2 lg:grid-cols-5', className)}>
      {ordered.map((sector) => {
        const Icon = ICONS[sector.sector_code] ?? Activity;
        const isActive = sector.sector_code === active;

        return (
          <Link
            key={sector.sector_code}
            href={hrefFor(sector.sector_code)}
            aria-current={isActive ? 'page' : undefined}
            title={sector.name}
            className={cn(
              'group flex min-w-0 items-center gap-3 rounded-xl border px-4 py-3 transition-colors',
              'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
              isActive
                ? 'border-heading bg-heading text-white shadow-sm'
                : 'border-card-border bg-canvas text-body hover:border-line hover:bg-surface',
            )}
          >
            <span
              className={cn(
                'flex size-9 shrink-0 items-center justify-center rounded-lg',
                isActive ? 'bg-white/12 text-white' : 'bg-surface-2 text-brand',
              )}
            >
              <Icon className="size-[18px]" aria-hidden />
            </span>
            <span className="min-w-0 truncate text-[13px] font-medium">{sector.name}</span>
            {isActive && (
              <span className="ml-auto flex size-5 shrink-0 items-center justify-center rounded-full bg-white text-heading">
                <Check className="size-3" aria-hidden />
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}
