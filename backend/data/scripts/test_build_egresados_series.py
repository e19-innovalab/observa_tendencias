import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_egresados_series import clean


def _rows(pais, nombre, values, mujeres=None, hombre=None, start=2015):
    return [
        {
            "anio": start + i, "pais": pais, "carrera_objetivo": "0" if v == 0 else nombre,
            "graduados": float(v),
            "mujeres": 0.0 if mujeres is None else mujeres,
            "hombre": 0.0 if hombre is None else hombre,
            "nombre": nombre,
        }
        for i, v in enumerate(values)
    ]


def test_leading_zeros_trimmed_but_interior_gap_kept():
    df = pd.DataFrame(
        _rows("chile", "ia", [0, 0, 0, 38, 40, 0, 46])
        + _rows("chile", "otra", [0, 0, 0])  # never has graduates -> dropped
    )
    out = clean(df)
    assert "otra" not in set(out["nombre"])
    ia = out[out["nombre"] == "ia"]
    assert list(ia["anio"]) == [2018, 2019, 2020, 2021]
    assert list(ia["hueco"]) == [False, False, True, False]
    assert (ia["carrera_objetivo"] == "ia").all()
    assert (ia["n_anios_serie"] == 4).all() and ia["elegible_tendencia"].all()


def test_unreported_gender_becomes_missing():
    df = pd.DataFrame(
        _rows("argentina", "medicina", [100, 120])
        + _rows("chile", "medicina", [100, 120], mujeres=40.0, hombre=60.0)
    )
    out = clean(df)
    arg = out[out["pais"] == "argentina"]
    assert arg["mujeres"].isna().all() and arg["hombre"].isna().all()
    assert (out[out["pais"] == "chile"]["mujeres"] == 40.0).all()


def test_short_series_not_eligible_for_trend():
    out = clean(pd.DataFrame(_rows("chile", "nueva", [0, 0, 5, 9])))
    assert not out["elegible_tendencia"].any()
