export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export type AuthUser = { id: string; email: string | null; username: string | null };
export type AuthResult = { user: AuthUser; authenticated: boolean };

export async function postAuth<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}/api/v1/auth/${path}`, {
    method: "POST",
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const result = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(result.detail ?? `Error de autenticación (HTTP ${response.status}).`);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export type SummaryCell = { provincia: string; sector: string; n: number };
export type Summary = {
  total: number;
  scraped_at: string | null;
  por_provincia_sector: SummaryCell[];
  source: string;
};
export type Job = {
  id: string;
  provincia: string;
  sector: string;
  titulo: string;
  empresa: string | null;
  fecha_publicacion: string | null;
  nivel_experiencia: string | null;
  tipo_empleo: string | null;
  url: string;
};
export type JobsPage = { total: number; limit: number; offset: number; items: Job[]; source: string };
export type Coverage = {
  pais: string;
  sector: string;
  n_anios_observados: number;
  anio_min: number | null;
  anio_max: number | null;
  elegible_proyeccion: boolean;
  estado: string;
};

export type GraduateTrend = {
  pais: string;
  nombre: string;
  anio_desde: number;
  anio_hasta: number;
  n_anios_serie: number;
  ventana_anios: number;
  graduados_inicio_ventana: number;
  graduados_ultimo: number;
  variacion_ventana_pct: number | null;
  tendencia: "growing" | "stable" | "declining" | "insufficient_data";
  tiene_huecos: boolean;
  proyeccion: string;
};
export type GraduateTrends = { items: GraduateTrend[]; source: string };
export type GraduateProjection = {
  pais: string;
  nombre: string;
  anio: number;
  graduados_proyectado: number;
  limite_inferior: number;
  limite_superior: number;
};

export async function getJson<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T> {
  const url = new URL(API_URL + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Error ${res.status}`);
  }
  return (await res.json()) as T;
}
