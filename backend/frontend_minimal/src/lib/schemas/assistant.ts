import { z } from 'zod';

/** GET /assistant: si está prendido, textos de la pantalla y preguntas que quedan hoy. */
export const AssistantStatusSchema = z.object({
  enabled: z.boolean(),
  provider: z.string(),
  model: z.string(),
  questions_per_day: z.number(),
  remaining_today: z.number().nullable(),
  max_question_chars: z.number(),
  history_turns: z.number(),
  texts: z.record(z.string(), z.string()),
  examples: z.array(z.string()).default([]),
});
export type AssistantStatus = z.infer<typeof AssistantStatusSchema>;

/** POST /assistant/ask. */
export const AssistantAnswerSchema = z.object({
  answer: z.string(),
  status: z.string(), // ok | unverified | blocked | refused
  verified: z.boolean(),
  warning: z.string().nullable().optional(),
  unverified_numbers: z.array(z.string()).default([]),
  links: z.array(z.object({ label: z.string(), href: z.string() })).default([]),
  /** Botones: repetir la pregunta con choice = {occupation, country}. */
  options: z
    .array(z.object({ label: z.string(), occupation: z.string().nullable().optional(), country: z.string().nullable().optional() }))
    .default([]),
  source: z.string().default('model'), // script (plantilla con los datos) | model
  tool_calls: z.array(z.object({ tool: z.string(), args: z.record(z.string(), z.unknown()), ok: z.boolean() })).default([]),
  remaining_today: z.number(),
  log_id: z.number(),
});
export type AssistantAnswer = z.infer<typeof AssistantAnswerSchema>;

export type AssistantContext = { page?: string; country?: string; occupation?: string; sector?: string };
export type AssistantChoice = { occupation?: string | null; country?: string | null };
