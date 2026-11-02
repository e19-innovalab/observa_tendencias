import type { ReactNode } from 'react';

/**
 * Palabra con una explicación breve que aparece al pasar el mouse o al enfocarla con el teclado
 * (subrayado punteado). Sin JavaScript: sirve en componentes de servidor. side="bottom" donde
 * arriba no hay lugar (encabezados de tabla con desplazamiento, que recortan lo que sobresale).
 */
export function Term({ children, help, align = 'left', side = 'top' }: { children: ReactNode; help: string; align?: 'left' | 'right'; side?: 'top' | 'bottom' }) {
  return (
    <span className="group/term relative inline-block">
      <span tabIndex={0} className="cursor-help underline decoration-slate-400 decoration-dotted underline-offset-2 outline-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-blue-700">
        {children}
      </span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute z-20 w-64 ${side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} rounded-lg bg-slate-900 px-3 py-2 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover/term:opacity-100 group-focus-within/term:opacity-100 ${align === 'right' ? 'right-0' : 'left-0'}`}
      >
        {help}
      </span>
    </span>
  );
}
