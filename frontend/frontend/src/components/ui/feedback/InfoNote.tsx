import type { ReactNode } from 'react';
import { Info, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
  title?: string;
  children: ReactNode;
  tone?: 'info' | 'warning';
  className?: string;
};

/** Aviso informativo o nota metodológica. */
export function InfoNote({ title, children, tone = 'info', className }: Props) {
  const Icon = tone === 'warning' ? TriangleAlert : Info;
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border px-4 py-3.5 text-[12.5px] leading-relaxed',
        tone === 'warning'
          ? 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text'
          : 'border-brand/15 bg-brand/4 text-body',
        className,
      )}
    >
      <Icon
        className={cn(
          'mt-0.5 size-4 shrink-0',
          tone === 'warning' ? 'text-alert-warning-icon' : 'text-brand',
        )}
        aria-hidden
      />
      <div>
        {title && <p className="font-semibold text-heading">{title}</p>}
        <div className={cn(title && 'mt-0.5', 'text-muted-text')}>{children}</div>
      </div>
    </div>
  );
}
