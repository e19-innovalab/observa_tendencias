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
type Options = {
  /** Token de sesión: se envía como Authorization: Bearer y la respuesta no se cachea. */
  token?: string | null;
  /** Para cortar el pedido (por ejemplo, cuando la persona cancela). */
  signal?: AbortSignal;
};

function buildUrl(path: string, params: Record<string, ParamValue> = {}): URL {
  const url = new URL(`/api/v1${path}`, BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    url.searchParams.set(key, Array.isArray(value) ? value.join(',') : String(value));
  }
  return url;
}

/** El backend responde los errores como {"detail": "mensaje en español"} (o una lista de errores). */
async function errorFrom(res: Response, path: string): Promise<ApiError> {
  let detail: unknown = null;
  try {
    detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
  } catch {
    // respuesta sin JSON
  }
  const message =
    typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? 'Hay datos inválidos en el formulario.'
        : `El backend respondió ${res.status} en ${path}`;
  return new ApiError(message, res.status, detail);
}

async function send(url: URL, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    if (init.signal?.aborted) throw e; // cancelado a propósito, no es un backend caído
    throw new ApiError(`No se pudo conectar con el backend (${BASE_URL}). ¿Está corriendo?`);
  }
}

function parse<T>(json: unknown, schema: ZodType<T>, path: string): T {
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    console.error(`[api] Respuesta inesperada en ${path}`, parsed.error.issues);
    throw new ApiError(`La respuesta de ${path} no tiene la forma esperada`, undefined, parsed.error.issues);
  }
  return parsed.data;
}

function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * GET al backend (prefijo /api/v1) y validación de la respuesta con Zod.
 * Pensado para llamarse desde componentes de servidor: así no hay problemas de CORS.
 */
export async function apiGet<T>(
  path: string,
  schema: ZodType<T>,
  params: Record<string, ParamValue> = {},
  revalidateSeconds = 300,
  options: Options = {},
): Promise<T> {
  const res = await send(buildUrl(path, params), {
    headers: authHeaders(options.token),
    ...(options.token ? { cache: 'no-store' as const } : { next: { revalidate: revalidateSeconds } }),
  });
  if (!res.ok) throw await errorFrom(res, path);
  return parse(await res.json(), schema, path);
}

/** POST / PATCH con cuerpo JSON (acciones del servidor). Sin respuesta (204) devuelve null. */
export async function apiSend<T>(
  method: 'POST' | 'PATCH',
  path: string,
  schema: ZodType<T> | null,
  body: unknown,
  options: Options = {},
): Promise<T | null> {
  const res = await send(buildUrl(path), {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders(options.token) },
    body: JSON.stringify(body),
    cache: 'no-store',
    signal: options.signal,
  });
  if (!res.ok) throw await errorFrom(res, path);
  if (res.status === 204 || !schema) return null;
  return parse(await res.json(), schema, path);
}

/** POST multipart (carga de archivos). */
export async function apiUpload<T>(
  path: string,
  schema: ZodType<T>,
  form: FormData,
  options: Options = {},
): Promise<T> {
  const res = await send(buildUrl(path), {
    method: 'POST',
    headers: authHeaders(options.token),
    body: form,
    cache: 'no-store',
  });
  if (!res.ok) throw await errorFrom(res, path);
  return parse(await res.json(), schema, path);
}
