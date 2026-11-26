/** Estados del archivo en el backend (datasets). */
export const DATASET_STATUS_LABELS: Record<string, string> = {
  validated: 'Revisado, listo para cargar',
  loaded: 'Cargado',
  unchanged: 'Sin cambios',
  replaced: 'Reemplazado',
  rejected: 'Rechazado',
  format_changed: 'Cambió el formato',
};

export const DATASET_STATUS_CLASSES: Record<string, string> = {
  loaded: 'border-success/40 bg-success-soft text-success',
  validated: 'border-brand/40 bg-surface text-brand',
  rejected: 'border-alert-critical-border bg-alert-critical-bg text-alert-critical-text',
  format_changed: 'border-alert-warning-border bg-alert-warning-bg text-alert-warning-text',
};
