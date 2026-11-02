import type { ReactNode } from 'react';
import { Info } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
  title?: string;
  children: ReactNode;
  tone?: 'info' | 'warning';
  className?: string;
};

/** Aviso informativo o nota metodológica. */
export function InfoNote({ title, children, tone = 'info', className }: Props) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-4 text-sm leading-relaxed',
        tone === 'warning'
          ? 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text'
          : 'border-info/25 bg-info-soft text-info',
        className,
      )}
    >
      <Info className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div className={cn(title && 'mt-1')}>{children}</div>
      </div>
    </div>
  );
}
