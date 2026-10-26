import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | undefined;
let browserStorageKey: string | undefined;

export function getSupabaseBrowserClient(): SupabaseClient {
  if (browserClient) return browserClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error(
      "Configura NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY en .env.local.",
    );
  }

  browserStorageKey = `sb-${new URL(url).hostname.split(".")[0]}-auth-token`;
  browserClient = createClient(url, anonKey, {
    auth: {
      flowType: "pkce",
      storageKey: browserStorageKey,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  });
  return browserClient;
}

export function clearSupabaseBrowserSession(): void {
  if (!browserStorageKey) {
    throw new Error("La sesión de Supabase todavía no fue inicializada.");
  }
  window.localStorage.removeItem(browserStorageKey);
}
