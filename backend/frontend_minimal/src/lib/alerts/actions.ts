'use server';

import { revalidatePath } from 'next/cache';
import { apiSend } from '@/lib/api/client';
import { getToken } from '@/lib/auth/session';

export async function markAlertRead(alertId: number): Promise<void> {
  await apiSend('PATCH', `/alerts/${alertId}`, null, { is_read: true }, { token: await getToken() });
  revalidatePath('/', 'layout'); // también el contador de la campana
}

export async function markAllAlertsRead(): Promise<void> {
  await apiSend('POST', '/alerts/read-all', null, {}, { token: await getToken() });
  revalidatePath('/', 'layout');
}
