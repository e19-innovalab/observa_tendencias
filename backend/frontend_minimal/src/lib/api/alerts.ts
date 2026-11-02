import { AlertRulesSchema, AlertsPageSchema } from '../schemas/api';
import { apiGet } from './client';

/** Con token: sin caché, para que marcar como leída se vea al instante. */
export const getAlertsPage = (
  params: { country?: string; severity?: string; alert_type?: string; unread?: boolean; limit: number; offset: number },
  token: string | null,
) => apiGet('/alerts', AlertsPageSchema, params, 60, { token });

export const getAlertRules = () => apiGet('/alerts/rules', AlertRulesSchema, {}, 3600);
