'use client';

import Image from 'next/image';
import { cn } from '@/lib/utils';
import { openDixi } from './dixi';
import fairyBotIcon from './fairy-bot-icon.svg';

/** Acceso a Dixi desde las barras de herramientas. */
export function DixiButton({ className }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={openDixi}
      aria-label="Abrir a Dixi"
      title="Dixi · IA de Predix"
      className={cn(
        'flex size-9 items-center justify-center rounded-lg text-muted-text transition-colors hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus',
        className,
      )}
    >
      <Image
        src={fairyBotIcon}
        alt=""
        width={28}
        height={28}
        unoptimized
        className="size-7 rounded-full"
      />
    </button>
  );
}
