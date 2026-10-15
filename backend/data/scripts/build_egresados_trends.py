"""Calcula tendencias y proyecciones de graduados por carrera con app.analytics.

    python data/scripts/build_egresados_trends.py

Lee      data/processed/data_analytics/egresados_series.csv  (salida de build_egresados_series.py)
Escribe  data/processed/data_analytics/egresados_tendencias.csv     una fila por (pais, nombre)
         data/processed/data_analytics/egresados_proyecciones.csv   una fila por año proyectado

Usa classify_trend sobre los últimos TREND_WINDOW años y project_series sobre la serie completa.
Las proyecciones son orientativas: solo se generan con historia suficiente (12 puntos) y sin
huecos, y el piso se fija en 0 porque no existen graduados negativos.
"""
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA.parent / "backend"))

from app.analytics.projections import DEFAULT_PARAMS as PROJ_PARAMS
from app.analytics.projections import project_series
from app.analytics.trends import classify_trend

SERIES = DATA / "processed" / "data_analytics" / "egresados_series.csv"
OUT_TRENDS = DATA / "processed" / "data_analytics" / "egresados_tendencias.csv"
OUT_PROJ = DATA / "processed" / "data_analytics" / "egresados_proyecciones.csv"

TREND_WINDOW = 5  # años


def analyze(series: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    trends, projections = [], []
    for (pais, nombre), g in series.sort_values("anio").groupby(["pais", "nombre"]):
        values = g["graduados"].tolist()
        last_year = int(g["anio"].max())
        window = values[-TREND_WINDOW:]
        res = classify_trend(window)
        has_gaps = bool(g["hueco"].any())
        # Gaps inside the window make growth rates meaningless (division by a zero year).
        if window and 0 in window:
            res = {"slope": None, "pct_change": None, "trend_state": "insufficient_data"}

        proj = None if has_gaps else project_series(values)
        if proj:
            for p in proj:
                projections.append(
                    {
                        "pais": pais, "nombre": nombre, "anio": last_year + p["step"],
                        "graduados_proyectado": round(p["value"]),
                        "limite_inferior": max(0, round(p["lower_bound"])),
                        "limite_superior": round(p["upper_bound"]),
                    }
                )
        trends.append(
            {
                "pais": pais, "nombre": nombre, "anio_desde": int(g["anio"].min()),
                "anio_hasta": last_year, "n_anios_serie": len(values),
                "ventana_anios": len(window),
                "graduados_inicio_ventana": int(window[0]),
                "graduados_ultimo": int(window[-1]),
                "pendiente_normalizada": res["slope"],
                "variacion_ventana_pct": None if res["pct_change"] is None
                else round(res["pct_change"] * 100, 2),
                "tendencia": res["trend_state"], "tiene_huecos": has_gaps,
                "proyeccion": "generada" if proj else (
                    "con_huecos" if has_gaps else f"historia_insuficiente(<{PROJ_PARAMS['min_points']})"
                ),
            }
        )
    return pd.DataFrame(trends), pd.DataFrame(projections)


def main() -> None:
    series = pd.read_csv(SERIES, encoding="utf-8-sig")
    trends, projections = analyze(series)
    trends.to_csv(OUT_TRENDS, index=False, encoding="utf-8-sig")
    projections.to_csv(OUT_PROJ, index=False, encoding="utf-8-sig")
    print(f"{len(trends)} series -> {OUT_TRENDS}\n{len(projections)} filas -> {OUT_PROJ}\n")
    print(trends[["pais", "nombre", "n_anios_serie", "variacion_ventana_pct", "tendencia",
                  "proyeccion"]].to_string(index=False))


if __name__ == "__main__":
    main()
