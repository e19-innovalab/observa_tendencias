import { z } from 'zod';
import { AlertsPageSchema } from '../schemas/api';
import { apiGet } from './client';

export const getAlerts = (params: {
  countries?: string[];
  severity?: string;
  unread?: boolean;
  limit?: number;
  offset?: number;
} = {}) =>
  apiGet(
    '/alerts',
    AlertsPageSchema,
    {
      country: params.countries,
      severity: params.severity,
      unread: params.unread,
      limit: params.limit,
      offset: params.offset,
    },
    60,
  );

/** Solo el contador de la campana. */
export const getUnreadAlerts = () =>
  apiGet(
    '/alerts',
    z.object({ unread: z.number() }).passthrough(),
    { unread: true, limit: 1 },
    60,
  );
