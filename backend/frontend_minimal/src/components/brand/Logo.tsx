import Image from 'next/image';
import Link from 'next/link';

/** Logo horizontal de Predix; inverted usa la versión blanca, para fondos oscuros. */
export function Logo({ href = '/', inverted = false }: { href?: string; inverted?: boolean }) {
  return (
    <Link
      href={href}
      className="flex items-center focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-focus"
    >
      <Image
        src={inverted ? '/brand/predix-horizontal-blanco.svg' : '/brand/predix-horizontal.svg'}
        alt="Predix"
        width={126}
        height={36}
        priority
        className="h-8 w-auto"
      />
    </Link>
  );
}
