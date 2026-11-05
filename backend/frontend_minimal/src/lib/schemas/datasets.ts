import { z } from 'zod';

export const DatasetProfileSchema = z.object({
  dataset_code: z.string(),
  title: z.string(),
  source: z.string(),
  landing_page: z.string().nullable(),
  automatic: z.boolean(),
  requires_declared_source: z.boolean(),
  file_format: z.string(),
  required_columns: z.array(z.string()).nullable(),
  template_columns: z.record(z.string(), z.string()).nullable(),
  has_template: z.boolean().default(false),
  example_files: z.array(z.string()).default([]),
});
export type DatasetProfile = z.infer<typeof DatasetProfileSchema>;

const IssueSchema = z.object({
  row: z.number().nullable().optional(),
  column: z.string().nullable().optional(),
  message: z.string(),
  kind: z.string().nullable().optional(), // tipo de problema (agrupa filas); overlap = choca con datos oficiales
});

export const DatasetFileSchema = z.object({
  dataset_id: z.number(),
  profile_code: z.string(),
  origin: z.string(), // download | upload
  file_name: z.string(),
  url: z.string().nullable(),
  release: z.string().nullable(),
  sha256: z.string(),
  size_bytes: z.number(),
  status: z.string(),
  records: z.number(),
  declared_source_name: z.string().nullable(),
  declared_source_url: z.string().nullable(),
  reference_date: z.string().nullable(),
  replaces_dataset_id: z.number().nullable(),
  created_at: z.string(),
  loaded_at: z.string().nullable(),
  report: z
    .object({
      ok: z.boolean().optional(),
      errors: z.array(IssueSchema).optional(),
      warnings: z.array(IssueSchema).optional(),
      first_period: z.string().nullable().optional(),
      last_period: z.string().nullable().optional(),
      /** El mismo problema en muchas filas, una vez: cuántas, cuáles, qué valores y qué hacer. */
      groups: z
        .array(
          z.object({
            kind: z.string(),
            title: z.string(),
            column: z.string().nullable(),
            count: z.number(),
            rows: z.array(z.number()),
            values: z.array(z.string()),
            hint: z.string().nullable(),
          }),
        )
        .optional(),
      /** Valores que ya existen en fuentes oficiales: la carga pide confirmación. */
      overlaps: z
        .object({ count: z.number(), by_source: z.record(z.string(), z.number()), examples: z.array(z.string()), message: z.string() })
        .nullable()
        .optional(),
    })
    .loose(),
});
export type DatasetFile = z.infer<typeof DatasetFileSchema>;

export const DatasetUploadResultSchema = DatasetFileSchema.extend({ preview: z.array(z.record(z.string(), z.unknown())) });
export type DatasetUploadResult = z.infer<typeof DatasetUploadResultSchema>;
