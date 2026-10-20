"""Check a career -> CIUO crosswalk after editing it (config/reference/carreras_*_ciuo.yaml).

    python -m app.jobs.validate_crosswalk              # every country in analytics.yaml
    python -m app.jobs.validate_crosswalk --country CHL

Checks that every code is a CIUO-08 occupation of the catalog and not excluded, that every career
loaded from the official file (graduates table) has a row, and that no row names a career that
is not in the data. Exits with an error if something is wrong.
"""
import argparse
import sys

from sqlalchemy import select

from app.analytics.skill_gaps_run import (
    ANY_LEVEL,
    crosswalk_codes,
    crosswalk_levels,
    load_crosswalk,
)
from app.core.config_files import analytics_params, catalog
from app.core.database import SessionLocal
from app.datasets.profiles import normalize_text
from app.models import Graduate


def check(country: str, path: str) -> list[str]:
    cw = load_crosswalk(path)
    problems = []
    for career, entry in cw["careers"].items():
        levels = (entry or {}).keys() if isinstance(entry, dict) else []
        for level in levels:
            if level != ANY_LEVEL and level not in crosswalk_levels(cw):
                problems.append(f"{career}: nivel {level!r} no está en levels {crosswalk_levels(cw)}")
        all_codes = [c for v in entry.values() for c in v] if isinstance(entry, dict) else entry
        for code in crosswalk_codes(all_codes, ANY_LEVEL):
            occ = catalog().occupation(code)
            if occ is None:
                problems.append(f"{career}: {code} no es una ocupación CIUO-08 del catálogo")
            elif occ.is_excluded:
                problems.append(f"{career}: {code} está excluida ({occ.exclusion_reason})")
    with SessionLocal() as s:
        data = set(s.scalars(select(Graduate.career).where(
            Graduate.country_iso3 == country,
            Graduate.level.in_(crosswalk_levels(cw))).distinct()).all())
    rows = {normalize_text(k) for k in cw["careers"]}
    problems += [f"Carrera sin fila en la correspondencia: {c}" for c in sorted(data)
                 if normalize_text(c) not in rows]
    problems += [f"Fila sin carrera en los datos: {k}" for k in cw["careers"]
                 if data and normalize_text(k) not in {normalize_text(c) for c in data}]
    mapped = sum(1 for v in cw["careers"].values() if v)
    print(f"{country} ({path}): {len(cw['careers'])} carreras, {mapped} con ocupación, "
          f"{len(cw['careers']) - mapped} genéricas | revisada: {'sí' if cw.get('reviewed') else 'no'}"
          f" | carreras en los datos: {len(data)}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--country", help="ISO3 (default: todos los de analytics.yaml)")
    args = parser.parse_args()
    crosswalks = analytics_params("skill_gaps")["crosswalks"]
    selected = {args.country.upper(): crosswalks[args.country.upper()]} if args.country else crosswalks
    problems = [p for country, path in selected.items() for p in check(country, path)]
    for p in problems:
        print("  ✗", p)
    if problems:
        sys.exit(f"{len(problems)} problemas")
    print("Sin problemas.")


if __name__ == "__main__":
    main()
