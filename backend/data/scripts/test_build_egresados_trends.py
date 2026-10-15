import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_egresados_trends import analyze


def _series(nombre, values, start=2005, pais="chile"):
    return pd.DataFrame(
        {
            "anio": [start + i for i in range(len(values))], "pais": pais, "nombre": nombre,
            "graduados": [float(v) for v in values],
            "hueco": [v == 0 for v in values],
        }
    )


def test_growing_series_gets_projection_with_floor_at_zero():
    trends, proj = analyze(_series("a", [10 + 5 * i for i in range(15)]))
    row = trends.iloc[0]
    assert row["tendencia"] == "growing" and row["proyeccion"] == "generada"
    assert list(proj["anio"]) == [2020, 2021, 2022, 2023]
    assert (proj["limite_inferior"] >= 0).all()


def test_short_series_has_trend_but_no_projection():
    trends, proj = analyze(_series("b", [10, 12, 15, 19, 24], start=2021))
    assert trends.iloc[0]["tendencia"] == "growing"
    assert trends.iloc[0]["proyeccion"].startswith("historia_insuficiente")
    assert proj.empty


def test_gaps_block_projection_and_in_window_trend():
    trends, proj = analyze(_series("c", [5] * 10 + [0, 0, 7, 9, 12]))
    row = trends.iloc[0]
    assert row["tiene_huecos"] and row["proyeccion"] == "con_huecos"
    assert row["tendencia"] == "insufficient_data"
    assert proj.empty
