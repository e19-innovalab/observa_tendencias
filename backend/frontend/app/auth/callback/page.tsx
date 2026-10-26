"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { API_URL } from "../../../lib/api";
import {
  clearSupabaseBrowserSession,
  getSupabaseBrowserClient,
} from "../../../lib/supabase";

export default function AuthCallbackPage() {
  const started = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    async function finishSignIn() {
      try {
        const params = new URLSearchParams(window.location.search);
        const providerError = params.get("error_description") ?? params.get("error");
        if (providerError) throw new Error(providerError);

        const supabase = getSupabaseBrowserClient();
        const code = params.get("code");
        const tokenHash = params.get("token_hash");
        if (code) {
          const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
          if (exchangeError) throw exchangeError;
        } else if (tokenHash && (params.get("type") === "signup" || params.get("type") === "email")) {
          const { error: verifyError } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: params.get("type") as "signup" | "email",
          });
          if (verifyError) throw verifyError;
        }

        const { data, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) throw sessionError;
        if (!data.session) {
          throw new Error("No se encontró una sesión válida. Inicia sesión nuevamente.");
        }

        const response = await fetch(`${API_URL}/api/v1/auth/session`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
          }),
        });
        if (!response.ok) {
          const result = (await response.json().catch(() => ({}))) as { detail?: string };
          throw new Error(result.detail ?? `No se pudo establecer la sesión (HTTP ${response.status}).`);
        }

        const sessionResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
          credentials: "include",
        });
        if (!sessionResponse.ok) {
          throw new Error(
            "Google validó la cuenta, pero el navegador no conservó la sesión. " +
              "Comprueba que frontend y API usan el mismo host (localhost) y vuelve a intentarlo.",
          );
        }

        clearSupabaseBrowserSession();
        window.location.assign(`${API_URL}/explorer`);
      } catch (callbackError) {
        setError(callbackError instanceof Error ? callbackError.message : "No se pudo completar el inicio de sesión.");
      }
    }

    void finishSignIn();
  }, []);

  return (
    <main className="auth-shell">
      <section className="auth-card auth-callback-card" aria-live="polite">
        <div className="auth-brand">
          <span className="auth-mark" aria-hidden="true">OT</span>
          <span>Observa Tendencias</span>
        </div>
        {error ? (
          <>
            <h1>No se pudo validar la cuenta</h1>
            <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>
            <Link className="auth-submit auth-submit-link" href="/auth">Volver al inicio de sesión</Link>
          </>
        ) : (
          <>
            <h1>Validando tu cuenta</h1>
            <p className="auth-intro">Estamos completando el inicio de sesión de forma segura…</p>
            <span className="auth-spinner" aria-label="Cargando" />
          </>
        )}
      </section>
    </main>
  );
}
