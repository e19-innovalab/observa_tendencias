import re

import pytest

from app.core.config_files import analytics, app_config, catalog, indicators, sources


def test_featured_occupations_have_known_sectors():
    sectors = {s.sector_code for s in catalog().sectors}
    featured = [o for o in catalog().occupations if o.is_featured]
    assert len(featured) == 20 and all(o.sector_code in sectors for o in featured)
    assert all(o.sector_code is None for o in catalog().occupations if not o.is_featured)


def test_occupation_universe_is_isco08_unit_groups():
    occs = catalog().occupations
    codes = [o.occupation_code for o in occs]
    assert len(codes) == len(set(codes)) == 436  # ISCO-08 has 436 unit groups
    assert all(re.fullmatch(r"\d{4}", c) and o.isco08_code == c for c, o in zip(codes, occs))
    assert catalog().occupation("2512").name == "Desarrollador/a de software"  # featured name
    assert catalog().occupation("4132").name == "Grabadores de datos"  # CIUO-08 (Uruguay)


def test_indicator_series_point_to_sources_with_connectors():
    # indicators() validates sources and required series fields when it loads
    assert all(ind.series for ind in indicators().indicators)
    assert all(sources().get(s.source).connector
               for ind in indicators().indicators for s in ind.series)


def test_invalid_series_config_fails_at_load(tmp_path, monkeypatch):
    import shutil

    import yaml

    from app.core import config_files

    for name in ("sources", "catalog", "app", "analytics"):
        shutil.copy(config_files.settings.config_dir / f"{name}.yaml", tmp_path)
    bad = {"indicators": [{"code": "x", "name": "x", "unit": "percent", "domain": "labor",
                           "series": [{"source": "world_bank", "frequency": "A"}]}]}
    (tmp_path / "indicators.yaml").write_text(yaml.safe_dump(bad))
    monkeypatch.setattr(config_files.settings, "config_dir", tmp_path)
    config_files.indicators.cache_clear()
    config_files.sources.cache_clear()
    try:
        with pytest.raises(ValueError, match="needs"):
            config_files.indicators()
    finally:
        config_files.indicators.cache_clear()
        config_files.sources.cache_clear()


def test_dashboard_and_domains_reference_configured_values():
    codes = {i.code for i in indicators().indicators}
    assert all(h.indicator in codes for h in app_config().dashboard.highlights)
    assert {i.domain for i in indicators().indicators} <= set(app_config().domains)


def test_employability_weights_are_consistent():
    ise = analytics()["employability"]
    assert abs(sum(ise["weights"].values()) - 1) < 1e-9
    assert set(ise["weights"]) == set(ise["higher_is_better"])


def test_managers_are_called_gerentes():
    occs = [o for o in catalog().occupations
            if not o.is_featured and o.name_en and re.search(r"\bManagers\b", o.name_en)]
    assert occs and not any(o.name.startswith("Directores") for o in occs)
    assert catalog().occupation("1211").name == "Gerentes financieros"
    assert catalog().occupation("1349").name.startswith("Gerentes de servicios profesionales")
    assert catalog().occupation("1120").name.startswith("Directores generales")  # not "Managers"
