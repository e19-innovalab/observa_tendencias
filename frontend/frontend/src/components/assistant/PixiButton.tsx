'use client';

import Image from 'next/image';
import { cn } from '@/lib/utils';
import { openPixi } from './pixi';
import fairyBotTransparent from './fairy-bot-transparent.svg';

/** Acceso a Pixi desde las barras de herramientas. */
export function PixiButton({ className }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={openPixi}
      aria-label="Abrir a Pixi"
      title="Pixi · IA de Predix"
      className={cn(
        'flex size-9 items-center justify-center rounded-lg text-muted-text transition-colors hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus',
        className,
      )}
    >
      <Image
        src={fairyBotTransparent}
        alt=""
        width={28}
        height={28}
        unoptimized
        className="size-7"
      />
    </button>
  );
}
