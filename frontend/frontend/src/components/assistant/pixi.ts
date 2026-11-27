/** Evento que abre el panel de Pixi desde el icono de la barra de herramientas. */
export const PIXI_OPEN_EVENT = 'pixi:open';

export function openPixi() {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(PIXI_OPEN_EVENT));
}
