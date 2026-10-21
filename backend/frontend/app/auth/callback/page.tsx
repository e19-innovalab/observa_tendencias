"use client";

import { useEffect, useState } from "react";

type Confirmation = {
  kind: "loading" | "confirmed" | "expired" | "error" | "unknown";
  detail?: string;
};

export default function AuthCallback() {
  const [confirmation, setConfirmation] = useState<Confirmation>({ kind: "loading" });

  useEffect(() => {
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

    if (
      fragment.has("access_token") ||
      query.has("code") ||
      fragment.get("type") === "signup"
    ) {
      setConfirmation({ kind: "confirmed" });
      return;
    }

    setConfirmation({ kind: "unknown" });
  }, []);

  const content = {
    loading: {
      title: "Verificando confirmación",
      message: "Estamos revisando el resultado del enlace.",
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
