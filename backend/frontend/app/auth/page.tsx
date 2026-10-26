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

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="auth-title">
        <Link className="auth-back" href="/">← Volver al observatorio</Link>
        <div className="auth-brand">
          <span className="auth-mark" aria-hidden="true">OT</span>
          <span>Observa Tendencias</span>
        </div>
        <h1 id="auth-title">{mode === "login" ? "Te damos la bienvenida" : "Crea tu cuenta"}</h1>
        <p className="auth-intro">
          {mode === "login"
            ? "Inicia sesión para continuar. El observatorio también está disponible sin cuenta."
            : "Regístrate para acceder a tu cuenta de Observa Tendencias."}
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

        <button
          className="auth-google"
          type="button"
          onClick={signInWithGoogle}
          disabled={busy || checkingSession || Boolean(sessionCheckError)}
        >
          <span className="google-g" aria-hidden="true">G</span>
          Continuar con Google
        </button>
        <div className="auth-divider"><span>o con tu correo</span></div>

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
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={1}
              maxLength={128}
              required
            />
          </label>
          <button className="auth-submit" type="submit" disabled={busy || checkingSession || Boolean(sessionCheckError)}>
            {busy ? "Un momento..." : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
          </button>
        </form>

        {mode === "login" && (
          <button className="auth-text-button" type="button" onClick={resendConfirmation} disabled={busy || checkingSession || Boolean(sessionCheckError) || !email}>
            Reenviar correo de confirmación
          </button>
        )}
        {error && <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>}
        {message && <p className="auth-feedback" role="status">{message}</p>}

        <p className="auth-switch">
          {mode === "login" ? "¿No tienes una cuenta?" : "¿Ya tienes una cuenta?"}{" "}
          <button
            type="button"
            disabled={busy || checkingSession || Boolean(sessionCheckError)}
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
              setMessage("");
            }}
          >
            {mode === "login" ? "Regístrate" : "Inicia sesión"}
          </button>
        </p>
        <p className="auth-optional">El inicio de sesión es opcional; puedes volver al observatorio cuando quieras.</p>
      </section>
    </main>
  );
}
