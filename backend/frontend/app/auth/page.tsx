"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { API_URL, postAuth, type AuthResult } from "../../lib/api";
import { getSupabaseBrowserClient } from "../../lib/supabase";

type Mode = "login" | "signup";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [sessionCheckError, setSessionCheckError] = useState("");

  async function checkSession() {
    setCheckingSession(true);
    setSessionCheckError("");
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/me`, { credentials: "include" });
      if (response.status === 401) return;
      if (!response.ok) {
        throw new Error(`No se pudo consultar la sesión (HTTP ${response.status}).`);
      }
      window.location.replace(`${API_URL}/explorer`);
    } catch (sessionError) {
      setSessionCheckError(
        sessionError instanceof Error
          ? sessionError.message
          : "No se pudo consultar la sesión.",
      );
    } finally {
      setCheckingSession(false);
    }
  }

  useEffect(() => {
    void checkSession();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (checkingSession || sessionCheckError) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      if (mode === "login") {
        await postAuth<AuthResult>("login", { email, password });
        window.location.assign(`${API_URL}/explorer`);
      } else {
        const result = await postAuth<AuthResult>("signup", { username, email, password });
        if (result.authenticated) {
          window.location.assign(`${API_URL}/explorer`);
        } else {
          setMessage("Revisa tu correo para confirmar la cuenta antes de iniciar sesión.");
        }
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo completar la solicitud.");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithGoogle() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          queryParams: { prompt: "select_account" },
        },
      });
      if (oauthError) throw oauthError;
    } catch (oauthError) {
      setError(oauthError instanceof Error ? oauthError.message : "No se pudo iniciar con Google.");
      setBusy(false);
    }
  }

  async function resendConfirmation() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const result = await postAuth<{ message: string }>("resend-confirmation", { email });
      setMessage(result.message);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo reenviar el correo.");
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
    setMessage("");
  }

  return (
    <main className="auth-shell auth-login-shell">
      <section className="auth-login-main" aria-labelledby="auth-title">
        <div className="auth-login-content">
          <Link className="auth-back" href="/">← Volver al observatorio</Link>
          <div className="auth-brand">
            <span className="auth-mark" aria-hidden="true">OT</span>
            <span>Observa Tendencias</span>
          </div>
          <h1 id="auth-title">{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h1>
          <p className="auth-intro">
            {mode === "login"
              ? "Ingresa tus datos para continuar."
              : "Completa tus datos para crear tu cuenta."}
          </p>

          {checkingSession && <p className="auth-feedback" role="status">Comprobando si ya tienes una sesión activa…</p>}
          {sessionCheckError && (
            <p className="auth-feedback auth-feedback-error" role="alert">
              {sessionCheckError}{" "}
              <button className="auth-text-button" type="button" onClick={checkSession}>
                Reintentar
              </button>
            </p>
          )}

          <form className="auth-form" onSubmit={submit}>
            {mode === "signup" && (
              <label>
                Nombre
                <input
                  autoComplete="name"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  maxLength={80}
                  required
                />
              </label>
            )}
            <label>
              Correo electrónico
              <input
                type="email"
                autoComplete="email"
                placeholder="nombre@correo.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label>
              Contraseña
              <span className="auth-password-control">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="Ingresa tu contraseña"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={1}
                  maxLength={128}
                  required
                />
                <button
                  className="auth-password-toggle"
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
                      <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8" />
                      <path d="M9.9 5.2A10.7 10.7 0 0112 5c5.5 0 9 7 9 7a15.7 15.7 0 01-3 3.8M6.2 6.2C3.9 7.7 3 12 3 12s3.5 7 9 7c1.2 0 2.3-.3 3.3-.8" />
                    </svg>
                  ) : (
                    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
                      <path d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </span>
            </label>
            {mode === "login" && (
              <div className="auth-form-meta">
                <span>Usa la contraseña de tu cuenta.</span>
                <button
                  className="auth-text-button"
                  type="button"
                  onClick={resendConfirmation}
                  disabled={busy || checkingSession || Boolean(sessionCheckError) || !email}
                >
                  Reenviar confirmación
                </button>
              </div>
            )}
            <button className="auth-submit" type="submit" disabled={busy || checkingSession || Boolean(sessionCheckError)}>
              {busy ? "Un momento..." : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
            </button>
          </form>

          <button
            className="auth-google"
            type="button"
            onClick={signInWithGoogle}
            disabled={busy || checkingSession || Boolean(sessionCheckError)}
          >
            <span className="google-g" aria-hidden="true">G</span>
            Iniciar sesión con Google
            <span className="auth-google-arrow" aria-hidden="true">→</span>
          </button>

          {error && <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>}
          {message && <p className="auth-feedback" role="status">{message}</p>}

          <p className="auth-switch">
            {mode === "login" ? "¿No tienes una cuenta?" : "¿Ya tienes una cuenta?"}{" "}
            <button
              type="button"
              disabled={busy || checkingSession || Boolean(sessionCheckError)}
              onClick={switchMode}
            >
              {mode === "login" ? "Crear cuenta" : "Iniciar sesión"}
            </button>
          </p>
          <p className="auth-optional">El acceso es opcional; puedes consultar el observatorio sin una cuenta.</p>
        </div>
      </section>

      <aside className="auth-aside">
        <div className="auth-aside-panel">
          <span className="auth-aside-eyebrow">OBSERVATORIO LABORAL Y EDUCATIVO</span>
          <h2>{mode === "login" ? "¿Aún no tienes una cuenta?" : "¿Ya tienes una cuenta?"}</h2>
          <p>
            {mode === "login"
              ? "Crea tu cuenta para acceder de forma sencilla a Observa Tendencias."
              : "Vuelve a iniciar sesión y continúa en Observa Tendencias."}
          </p>
          <ul>
            <li>Accede con tu correo electrónico y contraseña.</li>
            <li>También puedes iniciar sesión con Google.</li>
            <li>Explora tendencias laborales y educativas del Cono Sur.</li>
          </ul>
          <button
            className="auth-aside-action"
            type="button"
            onClick={switchMode}
            disabled={busy || checkingSession || Boolean(sessionCheckError)}
          >
            {mode === "login" ? "Crear cuenta" : "Iniciar sesión"}
            <span aria-hidden="true">→</span>
          </button>
        </div>
        <p className="auth-aside-footer">Observa Tendencias</p>
      </aside>
    </main>
  );
}
