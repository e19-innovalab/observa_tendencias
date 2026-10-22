import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";
import { API_URL } from "./api";

let browserClient: SupabaseClient | undefined;

export function getSupabaseBrowserClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error("Configura NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY.");
  }

  if (!browserClient) {
    const verifierSuffix = "-code-verifier";
    browserClient = createClient(url, anonKey, {
      auth: {
        flowType: "pkce",
        persistSession: true,
        autoRefreshToken: false,
        storage: {
          getItem: (key) =>
            key.endsWith(verifierSuffix) ? window.sessionStorage.getItem(key) : null,
          setItem: (key, value) => {
            if (key.endsWith(verifierSuffix)) window.sessionStorage.setItem(key, value);
          },
          removeItem: (key) => {
            if (key.endsWith(verifierSuffix)) window.sessionStorage.removeItem(key);
          },
        },
      },
    });
  }

  return browserClient;
}

export async function establishBackendSession(session: Session): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/session`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      access_token: session.access_token,
      refresh_token: session.refresh_token,
    }),
  });
  const result = (await response.json()) as { detail?: string };
  if (!response.ok) {
    throw new Error(result.detail ?? `Error ${response.status}`);
  }
}
