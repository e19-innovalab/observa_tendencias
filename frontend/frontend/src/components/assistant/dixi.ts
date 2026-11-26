/** Evento que abre el panel de Dixi desde el icono de la barra de herramientas. */
export const DIXI_OPEN_EVENT = 'dixi:open';

export function openDixi() {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(DIXI_OPEN_EVENT));
}
