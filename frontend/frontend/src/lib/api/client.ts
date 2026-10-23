import type { ZodType } from 'zod';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8010';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type ParamValue = string | number | boolean | null | undefined | (string | number)[];

/**
 * GET al backend (prefijo /api/v1) y validación de la respuesta con Zod.
 * Pensado para llamarse desde componentes de servidor: así no hay problemas de CORS.
 */
export async function apiGet<T>(
  path: string,
  schema: ZodType<T>,
  params: Record<string, ParamValue> = {},
  revalidateSeconds = 300,
): Promise<T> {
  const url = new URL(`/api/v1${path}`, BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    url.searchParams.set(key, Array.isArray(value) ? value.join(',') : String(value));
  }

  let res: Response;
  try {
    res = await fetch(url, { next: { revalidate: revalidateSeconds } });
  } catch {
    throw new ApiError(`No se pudo conectar con el backend (${BASE_URL}). ¿Está corriendo?`);
  }

  if (!res.ok) {
    throw new ApiError(`El backend respondió ${res.status} en ${path}`, res.status);
  }

  const json: unknown = await res.json();
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    console.error(`[api] Respuesta inesperada en ${path}`, parsed.error.issues);
    throw new ApiError(`La respuesta de ${path} no tiene la forma esperada`, undefined, parsed.error.issues);
  }
  return parsed.data;
}
