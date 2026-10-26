"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  type Coverage,
  type GraduateProjection,
  type GraduateTrend,
  type GraduateTrends,
  type JobsPage,
  type Summary,
  type AuthUser,
  API_URL,
  getJson,
} from "../lib/api";

const SECTORS = ["Tecnología", "Economía del conocimiento", "Salud", "Energía", "Turismo", "Otros"];
const COUNTRIES = ["ARG", "URY", "CHL"];
const PAGE_SIZE = 25;

const STATE_LABEL: Record<string, { icon: string; text: string }> = {
  proyectable: { icon: "●", text: "Proyectable" },
  solo_mostrar: { icon: "◐", text: "Solo mostrar" },
  sin_datos_observados: { icon: "○", text: "Sin datos" },
};

const TREND_LABEL: Record<GraduateTrend["tendencia"], { icon: string; text: string }> = {
  growing: { icon: "▲", text: "Creciendo" },
  stable: { icon: "▬", text: "Estable" },
  declining: { icon: "▼", text: "Cayendo" },
  insufficient_data: { icon: "○", text: "Datos insuficientes" },
};
const COUNTRY_NAME: Record<string, string> = { argentina: "Argentina", chile: "Chile", uruguay: "Uruguay" };

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function fmtNum(n: number) {
  return n.toLocaleString("es-AR");
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-AR", { dateStyle: "medium", timeStyle: "short" });
}

function cellStyle(n: number, max: number) {
  if (n === 0 || max === 0) return {};
  const pct = Math.max(8, Math.round((n / max) * 100));
  return {
    background: `color-mix(in srgb, var(--seq) ${pct}%, var(--surface-1))`,
    color: pct >= 55 ? "#ffffff" : undefined,
  };
}

export default function Home() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [jobs, setJobs] = useState<JobsPage | null>(null);
  const [grads, setGrads] = useState<GraduateTrends | null>(null);
  const [projections, setProjections] = useState<GraduateProjection[]>([]);
  const [gradCountry, setGradCountry] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);

  const [provincia, setProvincia] = useState("");
  const [sector, setSector] = useState("");
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/auth/me`, { credentials: "include" })
      .then(async (response) => {
        if (response.ok) {
          const result = (await response.json()) as { user: AuthUser };
          setUser(result.user);
        } else if (response.status !== 401) {
          throw new Error(`No se pudo consultar la sesión (HTTP ${response.status}).`);
        }
      })
      .catch((sessionError: Error) => setSignOutError(sessionError.message))
      .finally(() => setSessionReady(true));
  }, []);

  useEffect(() => {
    Promise.all([
      getJson<Summary>("/api/v1/jobs/summary", { pais: "ARG" }),
      getJson<Coverage[]>("/api/v1/coverage"),
      getJson<GraduateTrends>("/api/v1/graduates/trends"),
      getJson<GraduateProjection[]>("/api/v1/graduates/projections"),
    ])
      .then(([s, c, g, p]) => {
        setSummary(s);
        setCoverage(c);
        setGrads(g);
        setProjections(p);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      setQ(text);
      setOffset(0);
    }, 300);
    return () => clearTimeout(t);
  }, [text]);

  useEffect(() => {
    getJson<JobsPage>("/api/v1/jobs", { pais: "ARG", provincia, sector, q, limit: PAGE_SIZE, offset })
      .then(setJobs)
      .catch((e: Error) => setError(e.message));
  }, [provincia, sector, q, offset]);

  const provincias = useMemo(
    () => [...new Set(summary?.por_provincia_sector.map((c) => c.provincia) ?? [])].sort(),
    [summary],
  );
  const count = (p: string, s: string) =>
    summary?.por_provincia_sector.find((c) => c.provincia === p && c.sector === s)?.n ?? 0;
  const max = Math.max(0, ...(summary?.por_provincia_sector.map((c) => c.n) ?? [0]));

  const sectorTotals = useMemo(() => {
    const rows = SECTORS.map((s) => ({
      sector: s,
      n: (summary?.por_provincia_sector ?? [])
        .filter((c) => c.sector === s && (!provincia || c.provincia === provincia))
        .reduce((a, c) => a + c.n, 0),
    }));
    const others = rows.filter((r) => r.sector === "Otros");
    return [...rows.filter((r) => r.sector !== "Otros").sort((a, b) => b.n - a.n), ...others];
  }, [summary, provincia]);
  const barMax = Math.max(1, ...sectorTotals.map((r) => r.n));

  const topSector = [...sectorTotals].filter((r) => r.sector !== "Otros").sort((a, b) => b.n - a.n)[0];
  const covOf = (pais: string, s: string) => coverage.find((c) => c.pais === pais && c.sector === s);

  const gradRows = useMemo(
    () => (grads?.items ?? []).filter((g) => !gradCountry || g.pais === gradCountry),
    [grads, gradCountry],
  );
  const gradCountries = useMemo(() => [...new Set((grads?.items ?? []).map((g) => g.pais))], [grads]);
  const gradCount = (t: GraduateTrend["tendencia"]) => gradRows.filter((g) => g.tendencia === t).length;
  const projOf = (g: GraduateTrend) =>
    projections.filter((p) => p.pais === g.pais && p.nombre === g.nombre);

  function pick(p: string, s: string) {
    setProvincia(p);
    setSector(s);
    setOffset(0);
  }

  const total = jobs?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  async function signOut() {
    setSignOutError(null);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail ?? `No se pudo cerrar sesión (HTTP ${response.status}).`);
      }
      setUser(null);
    } catch (logoutError) {
      setSignOutError(
        logoutError instanceof Error ? logoutError.message : "No se pudo cerrar sesión.",
      );
    }
  }

  return (
    <main className="wrap">
      <header className="top">
        <div className="top-row">
          <div>
            <h1>Observa Tendencias</h1>
            <p>Observatorio laboral y educativo del Cono Sur · Argentina, Uruguay y Chile</p>
          </div>
          <nav className="session-nav" aria-label="Sesión">
            {sessionReady && user ? (
              <>
                <span className="session-email">{user.email}</span>
                <button className="btn" onClick={signOut}>Cerrar sesión</button>
              </>
            ) : (
              <Link className="btn" href="/auth">Iniciar sesión</Link>
            )}
          </nav>
        </div>
      </header>

      {signOutError && <p className="error" role="alert">{signOutError}</p>}
      <p className="notice">
        Las ofertas vienen de LinkedIn (recolección con Apify) y el sector se asigna por reglas según la
        industria de la empresa. <strong>No es una fuente oficial</strong> y es una instantánea de una
        semana, no una tendencia.
      </p>

      {error && (
        <div className="error" role="alert">
          <strong>No se pudieron cargar los datos.</strong> {error}
          <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>API: {API_URL}</div>
        </div>
      )}

      <section className="tiles" aria-label="Resumen">
        <div className="tile">
          <div className="label">Ofertas de empleo</div>
          <div className="value">{summary ? summary.total.toLocaleString("es-AR") : "—"}</div>
          <div className="sub">Argentina, última semana</div>
        </div>
        <div className="tile">
          <div className="label">Provincias</div>
          <div className="value">{summary ? provincias.length : "—"}</div>
          <div className="sub">{provincias.join(", ")}</div>
        </div>
        <div className="tile">
          <div className="label">Sector con más ofertas</div>
          <div className="value small">{topSector && topSector.n > 0 ? topSector.sector : "—"}</div>
          <div className="sub">
            {topSector && topSector.n > 0 ? `${topSector.n} ofertas${provincia ? ` en ${provincia}` : ""}` : ""}
          </div>
        </div>
        <div className="tile">
          <div className="label">Recolección</div>
          <div className="value small">{fmtDate(summary?.scraped_at ?? null)}</div>
          <div className="sub">Fuente: LinkedIn (Apify)</div>
        </div>
      </section>

      <div className="grid2">
        <section className="card">
          <h2>Ofertas por sector y provincia</h2>
          <p className="desc">Cantidad de ofertas. Hacé clic en una celda, un sector o una provincia para filtrar el listado.</p>
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Sector</th>
                  {provincias.map((p) => (
                    <th key={p} scope="col" className="num">
                      <button className="link-btn" onClick={() => pick(p, "")}>{p}</button>
                    </th>
                  ))}
                  <th scope="col" className="num">Total</th>
                </tr>
              </thead>
              <tbody>
                {SECTORS.map((s) => (
                  <tr key={s}>
                    <th scope="row" className="rowhead">
                      <button className="link-btn" onClick={() => pick("", s)}>{s}</button>
                    </th>
                    {provincias.map((p) => {
                      const n = count(p, s);
                      const active = provincia === p && sector === s;
                      return (
                        <td key={p}>
                          <button
                            className={`cell${n === 0 ? " zero" : ""}${active ? " active" : ""}`}
                            style={cellStyle(n, max)}
                            data-tip={`${s} · ${p}: ${n} ofertas`}
                            disabled={n === 0}
                            onClick={() => pick(p, s)}
                          >
                            {n}
                          </button>
                        </td>
                      );
                    })}
                    <td className="num" style={{ fontWeight: 600 }}>
                      {provincias.reduce((a, p) => a + count(p, s), 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="legend-ramp">
            <span>0</span>
            <span className="ramp" aria-hidden="true" />
            <span>{max} ofertas</span>
          </div>
        </section>

        <section className="card">
          <h2>Total por sector</h2>
          <p className="desc">{provincia ? `Solo ${provincia}.` : "Las tres provincias juntas."}</p>
          <div className="bars">
            {sectorTotals.map((r) => (
              <div className="bar-row" key={r.sector} data-tip={`${r.sector}: ${r.n} ofertas`}>
                <span>{r.sector}</span>
                <div className="track">
                  <div className="fill" style={{ width: `${(r.n / barMax) * 100}%` }} />
                </div>
                <span className="val">{r.n}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card">
        <h2>Listado de ofertas</h2>
        <p className="desc">Argentina. Usá los filtros o la tabla de arriba.</p>
        <div className="filters">
          <label>
            Provincia
            <select value={provincia} onChange={(e) => pick(e.target.value, sector)}>
              <option value="">Todas</option>
              {provincias.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <label>
            Sector
            <select value={sector} onChange={(e) => pick(provincia, e.target.value)}>
              <option value="">Todos</option>
              {SECTORS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Buscar en el título
            <input type="search" value={text} onChange={(e) => setText(e.target.value)} placeholder="ej. analista" />
          </label>
          {(provincia || sector || text) && (
            <button className="btn" onClick={() => { pick("", ""); setText(""); }}>
              Limpiar filtros
            </button>
          )}
        </div>

        {jobs && jobs.items.length === 0 ? (
          <p className="empty">No hay ofertas con esos filtros.</p>
        ) : (
          <div className="scroll">
            <table className="jobs">
              <thead>
                <tr>
                  <th>Oferta</th>
                  <th>Empresa</th>
                  <th>Provincia</th>
                  <th>Sector</th>
                  <th>Publicada</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {jobs?.items.map((j) => (
                  <tr key={j.id}>
                    <td>
                      <a href={j.url} target="_blank" rel="noreferrer">{j.titulo}</a>
                    </td>
                    <td className="muted">{j.empresa ?? "—"}</td>
                    <td className="muted">{j.provincia}</td>
                    <td><span className="chip">{j.sector}</span></td>
                    <td className="muted">{j.fecha_publicacion ?? "—"}</td>
                    <td className="muted">{j.nivel_experiencia === "Not Applicable" ? "—" : j.nivel_experiencia ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pager">
          <button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            ← Anterior
          </button>
          <span>{total === 0 ? "0 ofertas" : `${from}–${to} de ${total}`}</span>
          <button className="btn" disabled={to >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Siguiente →
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Graduados por carrera: tendencia y proyección</h2>
        <p className="desc">
          Graduados anuales de carreras vinculadas a los sectores (SIES en Chile, datos.gob.ar en
          Argentina). La tendencia usa los últimos 5 años.
        </p>
        <div className="filters">
          <label>
            País
            <select value={gradCountry} onChange={(e) => setGradCountry(e.target.value)}>
              <option value="">Todos</option>
              {gradCountries.map((c) => (
                <option key={c} value={c}>{COUNTRY_NAME[c] ?? titleCase(c)}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="tiles tiles-inner" aria-label="Resumen de graduados">
          <div className="tile">
            <div className="label">Carreras analizadas</div>
            <div className="value">{grads ? gradRows.length : "—"}</div>
          </div>
          <div className="tile">
            <div className="label">Creciendo</div>
            <div className="value">{grads ? gradCount("growing") : "—"}</div>
          </div>
          <div className="tile">
            <div className="label">Cayendo</div>
            <div className="value">{grads ? gradCount("declining") : "—"}</div>
            <div className="sub">
              {grads ? `${gradCount("stable")} estables · ${gradCount("insufficient_data")} sin datos` : ""}
            </div>
          </div>
          <div className="tile">
            <div className="label">Con proyección</div>
            <div className="value">
              {grads ? gradRows.filter((g) => g.proyeccion === "generada").length : "—"}
            </div>
            <div className="sub">Requiere 12 o más años de serie</div>
          </div>
        </div>

        <div className="scroll">
          <table className="jobs">
            <thead>
              <tr>
                <th>Carrera</th>
                <th>País</th>
                <th className="num">Graduados (inicio → último año)</th>
                <th className="num">Variación</th>
                <th>Tendencia</th>
                <th>Proyección {`${(projections[0]?.anio ?? "")}`}</th>
              </tr>
            </thead>
            <tbody>
              {gradRows.map((g) => {
                const t = TREND_LABEL[g.tendencia];
                const next = projOf(g)[0];
                return (
                  <tr key={`${g.pais}-${g.nombre}`}>
                    <td>{titleCase(g.nombre)}</td>
                    <td className="muted">{COUNTRY_NAME[g.pais] ?? g.pais}</td>
                    <td className="num">
                      {fmtNum(g.graduados_inicio_ventana)} → {fmtNum(g.graduados_ultimo)}
                      <div className="sub-note">{g.anio_hasta - g.ventana_anios + 1}–{g.anio_hasta}</div>
                    </td>
                    <td className="num">
                      {g.variacion_ventana_pct === null
                        ? "—"
                        : `${g.variacion_ventana_pct > 0 ? "+" : ""}${g.variacion_ventana_pct.toLocaleString("es-AR")}%`}
                    </td>
                    <td>
                      <span className={`trend trend-${g.tendencia}`}>{t.icon} {t.text}</span>
                    </td>
                    <td className="muted">
                      {next
                        ? `${fmtNum(next.graduados_proyectado)} (${fmtNum(next.limite_inferior)}–${fmtNum(next.limite_superior)})`
                        : g.proyeccion === "con_huecos"
                          ? "No disponible: serie con huecos"
                          : "No disponible: serie corta"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="desc" style={{ marginTop: 12 }}>
          Las variaciones sobre bases chicas son muy altas (por ejemplo, de 46 a 1.564 graduados): leelas
          junto con las cantidades. Las proyecciones son orientativas y muestran el rango entre paréntesis.
        </p>
      </section>

      <section className="card">
        <h2>Cobertura de datos oficiales</h2>
        <p className="desc">
          Qué tan completa es la serie histórica oficial por país y sector. Es independiente de las ofertas de LinkedIn.
        </p>
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Sector</th>
                {COUNTRIES.map((c) => (
                  <th key={c} scope="col">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SECTORS.filter((s) => s !== "Otros").map((s) => (
                <tr key={s}>
                  <th scope="row" className="rowhead">{s}</th>
                  {COUNTRIES.map((c) => {
                    const cv = covOf(c, s);
                    const st = STATE_LABEL[cv?.estado ?? "sin_datos_observados"];
                    return (
                      <td key={c}>
                        <div className={`cov-cell cov-${cv?.estado ?? "sin_datos_observados"}`}>
                          <span className="state">{st.icon} {st.text}</span>
                          <span className="years">
                            {cv && cv.n_anios_observados > 0
                              ? `${cv.n_anios_observados} años (${cv.anio_min}–${cv.anio_max})`
                              : "sin años observados"}
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="legend-ramp">
          <span>● Proyectable</span>
          <span>◐ Solo mostrar</span>
          <span>○ Sin datos</span>
        </div>
      </section>

      <p className="foot">
        Observa Tendencias · Datos: ofertas de LinkedIn (Apify) y informe de cobertura. Una cifra de 200 postulantes
        en LinkedIn debe leerse como «200 o más».
      </p>
    </main>
  );
}
