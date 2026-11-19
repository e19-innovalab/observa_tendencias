import { z } from 'zod';
import { AlertsPageSchema } from '../schemas/api';
import { apiGet } from './client';

export const AlertRulesSchema = z.object({
  rules: z.array(
    z.object({
      alert_type: z.string(),
      label: z.string(),
      definition: z.string().nullable(),
      params: z.record(z.string(), z.unknown()),
      severity_rule: z.string(),
      active: z.boolean(),
    }),
  ),
  severities: z.array(
    z.object({ code: z.string(), label: z.string(), definition: z.string().nullable() }),
  ),
});
export type AlertRules = z.infer<typeof AlertRulesSchema>;

/** Con token: sin caché, para que marcar como leída se vea al instante. */
export const getAlertsPage = (
  params: {
    country?: string;
    severity?: string;
    alert_type?: string;
    unread?: boolean;
    limit: number;
    offset: number;
  },
  token?: string | null,
) => apiGet('/alerts', AlertsPageSchema, params, token ? 0 : 60);

export const getAlertRules = () => apiGet('/alerts/rules', AlertRulesSchema, {}, 3600);
