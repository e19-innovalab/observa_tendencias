import { z } from 'zod';
import { apiGet } from './client';

export const SourceItemSchema = z.object({
  code: z.string(),
  name: z.string(),
  kind: z.string(),
  base_url: z.string().nullable(),
  expected_frequency: z.string().nullable(),
  has_connector: z.boolean(),
  status: z.string(),
  last_success_at: z.string().nullable(),
  last_run: z
    .object({ status: z.string(), finished_at: z.string().nullable(), records_normalized: z.number().nullable(), error_message: z.string().nullable() })
    .loose()
    .nullable(),
});
export type SourceItem = z.infer<typeof SourceItemSchema>;

export const getSources = () => apiGet('/sources', z.array(SourceItemSchema), {}, 300);
