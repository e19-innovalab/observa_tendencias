"use client";

import { FormEvent, useState } from "react";
import { API_URL } from "../../lib/api";

type AuthResponse = {
  auth_url?: string;
  user?: { email?: string | null; username?: string | null };
  session?: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    expires_at?: number | null;
  } | null;
  message?: string;
  detail?: string;
};

type AuthSession = NonNullable<AuthResponse["session"]>;

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [canResend, setCanResend] = useState(false);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [showTokens, setShowTokens] = useState(false);

  async function request(path: string, body?: Record<string, string>): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/api/v1/auth/${path}`, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = (await response.json()) as AuthResponse;
    if (!response.ok) {
      throw new Error(data.detail ?? `Error ${response.status}`);
    }
    return data;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setCanResend(false);
    setSession(null);
    setShowTokens(false);

    try {
      if (mode === "signup") {
        const data = await request("signup", { username, email, password });
        if (data.session) {
          setSession(data.session);
          setMessage("Cuenta creada e iniciada. El panel de datos sigue disponible sin iniciar sesión.");
        } else {
          setMessage("Cuenta creada. Revisa tu correo y confirma la dirección antes de iniciar sesión.");
          setCanResend(true);
        }
      } else {
        const data = await request("login", { email, password });
        setSession(data.session ?? null);
        setMessage("Inicio de sesión correcto. La sesión es opcional y el panel sigue siendo público.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo completar la solicitud.");
      setSession(null);
      if (mode === "login") setCanResend(true);
    } finally {
      setBusy(false);
    }
  }

  async function resendConfirmation() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await request("resend-confirmation", { email });
      setMessage(data.message ?? "Si la cuenta necesita confirmación, recibirás un nuevo correo.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo solicitar otro correo.");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithGoogle() {
    setBusy(true);
    setError("");
    try {
      const data = await request("google");
      if (!data.auth_url) throw new Error("La API no devolvió la URL de Google.");
      window.location.assign(data.auth_url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo iniciar con Google.");
      setBusy(false);
    }
  }

  return (
    <main className="wrap">
      <header className="top">
        <h1>{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h1>
        <p>La autenticación es opcional; puedes usar el observatorio sin iniciar sesión.</p>
      </header>

      <section className="card auth-card" aria-labelledby="auth-title">
        <h2 id="auth-title">Acceso opcional</h2>
        <p className="desc">
          {mode === "login"
            ? "Ingresa con el email y la contraseña de tu cuenta."
            : "Regístrate con un nombre de usuario, email y contraseña."}
        </p>

        <form className="auth-form" onSubmit={submit}>
          {mode === "signup" && (
            <label>
              Nombre de usuario
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Procesando…" : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
          </button>
        </form>

        <div className="auth-actions">
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setMessage("");
              setError("");
              setCanResend(false);
              setSession(null);
              setShowTokens(false);
            }}
          >
            {mode === "login" ? "Crear una cuenta" : "Ya tengo una cuenta"}
          </button>
          <button className="btn" type="button" disabled={busy} onClick={signInWithGoogle}>
            Continuar con Google
          </button>
        </div>

        {canResend && email && (
          <p>
            <button className="link-btn" type="button" disabled={busy} onClick={resendConfirmation}>
              Reenviar correo de confirmación
            </button>
          </p>
        )}
        {message && <p role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {session && (
          <section className="token-panel" aria-labelledby="session-tokens-title">
            <h3 id="session-tokens-title">Tokens de Supabase recibidos</h3>
            <p className="notice" role="note">
              Son credenciales privadas: cualquier persona que las obtenga podría acceder a tu
              sesión. No las compartas ni captures esta pantalla. Se muestran solo aquí y no se
              guardan en el navegador.
            </p>
            <button
              className="btn"
              type="button"
              onClick={() => setShowTokens((visible) => !visible)}
              aria-expanded={showTokens}
            >
              {showTokens ? "Ocultar tokens" : "Mostrar tokens"}
            </button>
            {showTokens && (
              <dl className="token-list">
                <dt>Access token (JWT)</dt>
                <dd><code>{session.access_token}</code></dd>
                <dt>Refresh token</dt>
                <dd><code>{session.refresh_token}</code></dd>
                <dt>Tipo</dt>
                <dd>{session.token_type}</dd>
                <dt>Expira en</dt>
                <dd>{session.expires_in} segundos</dd>
                {session.expires_at && (
                  <>
                    <dt>Expira en fecha</dt>
                    <dd>{new Date(session.expires_at * 1000).toLocaleString()}</dd>
                  </>
                )}
              </dl>
            )}
          </section>
        )}
      </section>

      <p>
        <a href="/">Volver al observatorio</a>
      </p>
    </main>
  );
}
