"use client";

import { useEffect, useMemo, useState } from "react";
import {
  type Coverage,
  type GraduateProjection,
  type GraduateTrend,
  type GraduateTrends,
  type JobsPage,
  type Summary,
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

  const [provincia, setProvincia] = useState("");
  const [sector, setSector] = useState("");
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);

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

  return (
    <main className="wrap">
      <header className="top">
        <h1>Observa Tendencias</h1>
        <p>Observatorio laboral y educativo del Cono Sur · Argentina, Uruguay y Chile</p>
      </header>

      <p>
        <a className="btn" href="/auth">
          Iniciar sesión o crear cuenta (opcional)
        </a>
      </p>
      <p className="foot">
        Observa Tendencias · Datos: ofertas de LinkedIn (Apify) y informe de cobertura. Una cifra de 200 postulantes
        en LinkedIn debe leerse como «200 o más».
      </p>
    </main>
  );
}
