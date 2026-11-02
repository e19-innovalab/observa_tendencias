import { z } from 'zod';

/** Un eje de "Las ocupaciones en movimiento" (x, y o tamaño). */
export const MotionAxisSchema = z.object({
  key: z.string(),
  label: z.string(),
  short_label: z.string().nullable(),
  unit: z.string().nullable(),
  scale: z.enum(['linear', 'log']),
  description: z.string().nullable(),
  reference: z.number().nullable(),
  domain: z.tuple([z.number(), z.number()]).nullable(),
});
export type MotionAxis = z.infer<typeof MotionAxisSchema>;

/** Una burbuja: gran grupo de ocupaciones × país × año. carried: año de origen de x o tamaño si es anterior. */
export const MotionPointSchema = z.object({
  country_iso3: z.string(),
  group_code: z.string(),
  year: z.number(),
  x: z.number(),
  x_secondary: z.number().nullable(),
  y: z.number(),
  size: z.number(),
  carried: z.record(z.string(), z.number()),
});
export type MotionPoint = z.infer<typeof MotionPointSchema>;

export const MotionPageSchema = z.object({
  title: z.string(),
  description: z.string().nullable(),
  years: z.array(z.number()),
  x: MotionAxisSchema,
  x_secondary: MotionAxisSchema.nullable(),
  y: MotionAxisSchema,
  size: MotionAxisSchema,
  y_options: z.array(MotionAxisSchema),
  groups: z.array(z.object({ code: z.string(), name: z.string().nullable() })),
  points: z.array(MotionPointSchema),
  notes: z.array(z.string()),
});
export type MotionPage = z.infer<typeof MotionPageSchema>;
