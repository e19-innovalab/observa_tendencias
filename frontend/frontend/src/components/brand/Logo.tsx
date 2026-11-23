import Image from 'next/image';
import Link from 'next/link';

export function Logo({ href = '/', inverted = false }: { href?: string; inverted?: boolean }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-focus ${
        inverted ? 'text-white' : 'text-heading'
      }`}
    >
      <Image
        src={inverted ? '/predix-horizontal-blanco.svg' : '/predix-horizontal.svg'}
        alt="Predix"
        width={126}
        height={36}
        priority
        className="h-9 w-auto"
      />
    </Link>
  );
}
