import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_consolidado_fuentes import control, most_graduates, tidy_yearbook_table, to_number


def test_missing_markers_are_not_zero():
    assert to_number("s/d") is None and to_number("-") is None and to_number(None) is None
    assert to_number(0) == 0
    assert to_number("1.475") == 1475


def test_yearbook_rows_keep_kind_and_skip_totals():
    rows = [
        [None, 2021, 2022],
        ["Total Instituciones Estatales", 30, 40],
        ["Total Universidades Nacionales ", 20, 30],
        ["Buenos Aires", 20, 30],
        ["Total Institutos Universitarios Nacionales", 10, 10],
        ["Patagónico de las Artes", "-", 10],
    ]
    out = tidy_yearbook_table(rows, "publica", "fuente", "archivo")
    assert set(out.institucion) == {"Buenos Aires", "Patagónico de las Artes"}
    assert out[out.institucion == "Buenos Aires"].tipo_institucion.iloc[0] == "universidad"
    institute = out[out.institucion == "Patagónico de las Artes"]
    assert institute.tipo_institucion.iloc[0] == "instituto universitario"
    assert list(institute.anio) == [2022]


def test_control_flags_gaps_over_the_tolerance():
    assert control("x", 2022, 100, 100)["resultado"] == "ok"
    assert control("x", 2022, 90, 100)["resultado"] == "revisar"


def _university(name, country, year, value, main=True, kind="universidad"):
    return {"pais": country, "institucion": name, "gestion": "publica", "tipo_institucion": kind, "anio": year,
            "nivel": "Grado", "egresados": value, "fuente": "f", "es_principal": main}


def test_ranking_uses_main_source_and_only_universities():
    frame = pd.DataFrame([
        _university("UdelaR", "URY", 2022, 6968),
        _university("UdelaR", "URY", 2022, 6577, main=False),
        _university("UBA", "ARG", 2022, 25970),
        _university("Instituto", "ARG", 2022, 99999, kind="instituto universitario"),
        _university("UBA", "ARG", 2024, 26000),
    ])
    out = most_graduates(frame, year=2022, top=2)
    regional = out[out.alcance == "regional"]
    assert list(regional.institucion) == ["UBA", "UdelaR"]
    assert list(regional.egresados) == [25970, 6968]
    national = out[(out.alcance == "nacional") & (out.pais == "ARG")]
    assert list(national.anio) == [2024]
