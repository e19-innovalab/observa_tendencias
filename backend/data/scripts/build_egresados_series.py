"""Limpia indicadores_carrera_anio.csv para que sirva como serie de tiempo en el análisis.

    python data/scripts/build_egresados_series.py [entrada.csv]

Lee      data/raw/egresados/indicadores_carrera_anio.csv  (o la ruta pasada por argumento)
Escribe  data/processed/data_analytics/egresados_series.csv

Problemas que corrige:

1. Relleno de ceros al inicio. Antes de que exista un programa la fuente trae filas con
   graduados = 0 y carrera_objetivo = "0". Esos años no son datos observados y distorsionan
   la tendencia (un salto de 0 a 62 parece un crecimiento enorme). Se descartan los años
   anteriores al primer año con graduados > 0, por cada (pais, nombre).
2. Ceros intermedios o finales. Se conservan (por ejemplo, un programa que se interrumpió),
   pero se marcan con `hueco = True` para que el análisis decida cómo tratarlos.
3. Género faltante. En Argentina mujeres = hombres = 0 aunque haya graduados: no es un dato
   cero sino un dato no informado. Se reemplaza por vacío.
4. carrera_objetivo = "0" en filas con datos. Se reemplaza por el nombre de la carrera.

Agrega `n_anios_serie` (años con datos de la carrera, desde su inicio) y
`elegible_tendencia` (n_anios_serie >= MIN_POINTS_TREND, igual que app.analytics.trends).
"""
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1]
DEFAULT_IN = DATA / "raw" / "egresados" / "indicadores_carrera_anio.csv"
OUT = DATA / "processed" / "data_analytics" / "egresados_series.csv"

KEYS = ["pais", "nombre"]
MIN_POINTS_TREND = 4  # app.analytics.trends.DEFAULT_PARAMS["min_points"]


def trim_leading_zeros(df: pd.DataFrame) -> pd.DataFrame:
    """Drop, per (pais, nombre), the years before the first year with graduados > 0."""
    df = df.sort_values(KEYS + ["anio"])
    first_year = df[df["graduados"] > 0].groupby(KEYS)["anio"].min().rename("_inicio")
    df = df.join(first_year, on=KEYS)
    # A career that never has graduates has no series at all and is dropped.
    return df[df["_inicio"].notna() & (df["anio"] >= df["_inicio"])].drop(columns="_inicio")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["anio"] = df["anio"].astype(int)
    df = trim_leading_zeros(df)

    # Gender not reported (both 0 with graduates) is missing data, not zero.
    no_gender = (df["mujeres"] == 0) & (df["hombre"] == 0) & (df["graduados"] > 0)
    df.loc[no_gender, ["mujeres", "hombre"]] = pd.NA

    df["carrera_objetivo"] = df["nombre"]
    df["hueco"] = df["graduados"] == 0
    df["n_anios_serie"] = df.groupby(KEYS)["anio"].transform("count")
    df["elegible_tendencia"] = df["n_anios_serie"] >= MIN_POINTS_TREND
    return df.reset_index(drop=True)


def main(path: Path = DEFAULT_IN) -> None:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    out = clean(raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    dropped = len(raw) - len(out)
    print(f"{len(raw)} filas de entrada, {dropped} filas de relleno descartadas, {len(out)} filas -> {OUT}")
    resumen = out.groupby(KEYS).agg(
        desde=("anio", "min"), hasta=("anio", "max"), n=("anio", "count"),
        huecos=("hueco", "sum"), elegible=("elegible_tendencia", "first"),
    )
    print(resumen.to_string())


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN)
