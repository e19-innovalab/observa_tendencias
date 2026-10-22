"use client";

import { FormEvent, useState } from "react";
import { API_URL } from "../../lib/api";
import { establishBackendSession, getSupabaseBrowserClient } from "../../lib/supabase";

type AuthResponse = {
  user?: { email?: string | null; username?: string | null };
  authenticated?: boolean;
  message?: string;
  detail?: string;
};

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [requestSucceeded, setRequestSucceeded] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [canResend, setCanResend] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function request(path: string, body?: Record<string, string>): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/api/v1/auth/${path}`, {
      method: body ? "POST" : "GET",
      credentials: "include",
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
    setRequestSucceeded(false);
    setCanResend(false);

    try {
      if (mode === "signup") {
        const data = await request("signup", { username, email, password });
        if (data.authenticated) {
          setRequestSucceeded(true);
          setMessage("Cuenta creada. El panel de datos sigue disponible sin iniciar sesión.");
        } else {
          setRequestSucceeded(true);
          setMessage("Cuenta creada. Revisa tu correo y confirma la dirección antes de iniciar sesión.");
          setCanResend(true);
        }
      } else {
        const { data, error: authError } =
          await getSupabaseBrowserClient().auth.signInWithPassword({ email, password });
        if (authError) throw authError;
        if (!data.session) {
          throw new Error("Supabase no confirmó el inicio de sesión.");
        }
        await establishBackendSession(data.session);
        setRequestSucceeded(true);
        setMessage("Inicio de sesión exitoso. Redirigiendo al observatorio…");
        window.setTimeout(() => window.location.assign(`${API_URL}/explorer`), 700);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo completar la solicitud.");
      setRequestSucceeded(false);
      if (mode === "login") setCanResend(true);
    } finally {
      setBusy(false);
    }
  }

  async function resendConfirmation() {
    setBusy(true);
    setError("");
    setMessage("");
    setRequestSucceeded(false);
    try {
      const data = await request("resend-confirmation", { email });
      setMessage(data.message ?? "Si la cuenta necesita confirmación, recibirás un nuevo correo.");
      setRequestSucceeded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo solicitar otro correo.");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithGoogle() {
    setBusy(true);
    setError("");
    setMessage("");
    setRequestSucceeded(false);
    try {
      const { error: authError } = await getSupabaseBrowserClient().auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          queryParams: { prompt: "select_account" },
        },
      });
      if (authError) throw authError;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo iniciar con Google.");
      setBusy(false);
    }
  }

  function showPasswordRecoveryMessage() {
    setError("");
    setRequestSucceeded(false);
    setMessage("La recuperación de contraseña todavía no está disponible.");
  }

  return (
    <main className="auth-layout">
      <section className="auth-main" aria-labelledby="auth-title">
        <div className="auth-content">
          <a className="auth-brand" href="/" aria-label="Observa Tendencias, volver al inicio">
            <span className="auth-brand-mark" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </a>

          <h1 id="auth-title">{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h1>
          <p className="auth-intro">
            {mode === "login"
              ? "Ingresa tus datos para continuar."
              : "Completa tus datos para crear una cuenta."}
          </p>

          <form className="auth-form" onSubmit={submit}>
            {mode === "signup" && (
              <label>
                Nombre de usuario
                <input
                  autoComplete="username"
                  required
                  placeholder="Tu nombre"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>
            )}
            <label>
              Correo electrónico
              <input
                type="email"
                autoComplete="email"
                required
                placeholder="nombre@ejemplo.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Contraseña
              <span className="auth-password-field">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  placeholder="Ingresa tu contraseña"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  className="auth-password-toggle"
                  type="button"
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((visible) => !visible)}
                >
                  {showPassword ? "Ocultar" : "Ver"}
                </button>
              </span>
              {mode === "login" && (
                <span className="auth-password-hint">
                  Ingresa la contraseña asociada a tu cuenta.
                </span>
              )}
            </label>

            {mode === "login" && (
              <div className="auth-form-options">
                <label className="auth-checkbox">
                  <input type="checkbox" />
                  <span>Recordar contraseña</span>
                </label>
                <button
                  className="auth-text-button"
                  type="button"
                  onClick={showPasswordRecoveryMessage}
                >
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
            )}

            <button className="auth-submit" type="submit" disabled={busy}>
              {busy ? "Procesando…" : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
            </button>
          </form>

          <button
            className="auth-google"
            type="button"
            disabled={busy}
            onClick={signInWithGoogle}
          >
            <span className="auth-google-mark" aria-hidden="true">G</span>
            <span>Iniciar sesión con Google</span>
            <span className="auth-google-arrow" aria-hidden="true">→</span>
          </button>

          {canResend && email && (
            <p className="auth-feedback">
              <button className="auth-text-button" type="button" disabled={busy} onClick={resendConfirmation}>
                Reenviar correo de confirmación
              </button>
            </p>
          )}
          {message && (
            <p
              className={requestSucceeded ? "auth-feedback auth-success" : "auth-feedback"}
              role="status"
            >
              {message}
            </p>
          )}
          {error && <p className="auth-error" role="alert">{error}</p>}

          <div className="auth-account-switch">
            <span>
              {mode === "login" ? "¿No tienes una cuenta?" : "¿Ya tienes una cuenta?"}
            </span>
            <button
              className="auth-text-button"
              type="button"
              disabled={busy}
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setMessage("");
                setRequestSucceeded(false);
                setError("");
                setCanResend(false);
              }}
            >
              {mode === "login" ? "Crear cuenta" : "Iniciar sesión"}
            </button>
          </div>
        </div>
      </section>

      <aside className="auth-aside">
        <section className="auth-promo">
          <h2>{mode === "login" ? "¿Aún no estás registrado?" : "Tu próximo paso empieza aquí"}</h2>
          <p>
            {mode === "login"
              ? "Crea una cuenta para explorar las tendencias laborales y educativas de la región."
              : "Regístrate para continuar. El acceso al observatorio sigue disponible sin iniciar sesión."}
          </p>
          <ul>
            <li>Consulta información laboral y educativa del Cono Sur.</li>
            <li>Explora indicadores, ocupaciones y tendencias por país.</li>
            <li>La cuenta es opcional y no condiciona el uso del observatorio.</li>
          </ul>
          <a className="auth-promo-link" href="/">
            Explorar el observatorio <span aria-hidden="true">→</span>
          </a>
        </section>
      </aside>
    </main>
  );
}
