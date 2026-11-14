import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

type Props = {
  title: string;
  description?: string;
  action?: { label: string; href: string };
  children?: ReactNode;
};

export function SectionHeading({ title, description, action, children }: Props) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="space-y-1">
        <h2 className="text-[17px] leading-snug font-semibold text-heading">{title}</h2>
        {description && <p className="max-w-3xl text-[12.5px] text-muted-text">{description}</p>}
      </div>
      {action && (
        <Link
          href={action.href}
          className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-link hover:text-link-hover hover:underline"
        >
          {action.label}
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      )}
      {children}
    </div>
  );
}
