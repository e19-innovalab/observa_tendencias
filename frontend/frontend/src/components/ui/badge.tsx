import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type BadgeTone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info';

const TONES: Record<BadgeTone, string> = {
  neutral: 'border-line bg-surface-2 text-body',
  brand: 'border-brand/30 bg-brand/10 text-brand',
  success: 'border-alert-positive-border bg-alert-positive-bg text-alert-positive-text',
  warning: 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text',
  danger: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text',
  info: 'border-info/30 bg-info-soft text-info',
};

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
