"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL } from "../../../lib/api";
import { establishBackendSession, getSupabaseBrowserClient } from "../../../lib/supabase";

type Confirmation = {
  kind: "loading" | "redirecting" | "confirmed" | "expired" | "error" | "unknown";
  detail?: string;
};

export default function AuthCallback() {
  const [confirmation, setConfirmation] = useState<Confirmation>({ kind: "loading" });
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    async function handleCallback() {
      const query = new URLSearchParams(window.location.search);
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const errorCode = query.get("error_code") ?? fragment.get("error_code");
      const errorDescription =
        query.get("error_description") ?? fragment.get("error_description");

      if (errorCode === "otp_expired") {
        setConfirmation({ kind: "expired" });
        return;
      }

      if (errorCode || query.get("error") || fragment.get("error")) {
        setConfirmation({ kind: "error", detail: errorDescription ?? errorCode ?? undefined });
        return;
      }

      const code = query.get("code");
      if (code) {
        window.history.replaceState({}, document.title, window.location.pathname);
        setConfirmation({ kind: "redirecting" });
        try {
          const { data, error } = await getSupabaseBrowserClient().auth.exchangeCodeForSession(
            code
          );
          if (error) throw error;
          if (!data.session) throw new Error("Supabase no devolvió una sesión.");
          await establishBackendSession(data.session);
          window.location.replace(`${API_URL}/explorer`);
        } catch (cause) {
          setConfirmation({
            kind: "error",
            detail: cause instanceof Error ? cause.message : "No se pudo validar la sesión.",
          });
        }
        return;
      }

      if (fragment.has("access_token") || fragment.get("type") === "signup") {
        setConfirmation({ kind: "confirmed" });
        return;
      }

      setConfirmation({ kind: "unknown" });
    }

    void handleCallback();
  }, []);

  const content = {
    loading: {
      title: "Verificando confirmación",
      message: "Estamos revisando el resultado del enlace.",
    },
    redirecting: {
      title: "Inicio de sesión exitoso",
      message: "Redirigiendo al observatorio…",
    },
    confirmed: {
      title: "Correo confirmado",
      message: "Tu cuenta quedó confirmada. Ya puedes volver a la aplicación e iniciar sesión.",
    },
    expired: {
      title: "El enlace venció o ya fue utilizado",
      message:
        "Solicita un nuevo correo de confirmación y abre el enlace más reciente. Cada enlace puede usarse una sola vez.",
    },
    error: {
      title: "No se pudo confirmar el correo",
      message: confirmation.detail ?? "Solicita un nuevo enlace e inténtalo otra vez.",
    },
    unknown: {
      title: "No se pudo verificar la confirmación",
      message: "Vuelve a abrir el enlace del correo o solicita uno nuevo.",
    },
  }[confirmation.kind];

  return (
    <main className="wrap">
      <header className="top">
        <h1>{content.title}</h1>
        <p>{content.message}</p>
      </header>
      <p>
        <a href="/">Volver a Observa Tendencias</a>
      </p>
    </main>
  );
}
