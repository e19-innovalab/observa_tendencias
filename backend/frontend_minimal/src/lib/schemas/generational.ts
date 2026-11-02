import { z } from 'zod';
import { IndicatorSchema } from './api';

const GapPointSchema = z.object({ year: z.number(), youth: z.number(), total: z.number(), ratio: z.number() });

/** Desocupación de 15 a 24 años sobre la general, por país y año (misma fuente para las dos). */
export const GenerationalGapSchema = z.object({
  title: z.string(),
  description: z.string(),
  youth: IndicatorSchema,
  total: IndicatorSchema,
  source: z.string().nullable(),
  countries: z.array(z.object({
    country_iso3: z.string(),
    points: z.array(GapPointSchema),
    latest: GapPointSchema.nullable(),
    headline: z.string().nullable(),
  })),
});
export type GenerationalGap = z.infer<typeof GenerationalGapSchema>;
