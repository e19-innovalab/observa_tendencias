from pathlib import Path

import pytest

from build_ofertas_linkedin import classify_sector, province_from_file


@pytest.mark.parametrize(
    ("industries", "title", "expected"),
    [
        ("Hospitals and Health Care", "Neurólogo", "Salud"),
        ("Hospitality", "Recepcionista", "Turismo"),  # must not match "hospital"
        ("Oil and Gas", "Tax Compliance Analyst", "Energía"),
        ("IT Services and IT Consulting", "Account Manager", "Tecnología"),
        ("Advertising Services", "Paid Media Analyst", "Economía del conocimiento"),
        ("Human Resources Services", "Chef ejecutivo", "Turismo"),
        ("Retail", "Repositor", "Otros"),
        ("", "", "Otros"),
    ],
)
def test_classify_sector(industries, title, expected):
    assert classify_sector(industries, title)[0] == expected


def test_province_from_file():
    assert province_from_file(Path("dataset_x_2026-10-13_17-54-27-392.csv")) == "Santa Fe"
    with pytest.raises(ValueError):
        province_from_file(Path("dataset_x_2026-10-14_09-00-00-000.csv"))
