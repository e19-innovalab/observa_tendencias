import Link from 'next/link';

/** Marca provisoria hasta tener el logo definitivo (el diseño usa un marcador "LOGO"). */
export function Logo({ href = '/', inverted = false }: { href?: string; inverted?: boolean }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-focus ${
        inverted ? 'text-white' : 'text-heading'
      }`}
    >
      <span
        aria-hidden
        className={`flex size-8 items-center justify-center rounded-md text-sm font-bold ${
          inverted ? 'bg-white text-brand' : 'bg-brand text-white'
        }`}
      >
        OT
      </span>
      <span className="text-lg">Observa Tendencias</span>
    </Link>
  );
}
