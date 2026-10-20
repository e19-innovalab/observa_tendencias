"""Idempotent catalog seed from config/*.yaml: python -m seeds.load

Loads countries, sectors, occupations (catalog.yaml + its occupation universe), sources
(sources.yaml) and indicator definitions (indicators.yaml). Occupations no longer in config are
removed together with the rows that reference them. Re-run it after editing any of those files.
"""
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config_files import catalog, indicators, sources
from app.core.database import SessionLocal
from app.models import (
    Country,
    EmployabilityScore,
    Indicator,
    Observation,
    Occupation,
    OccupationSkill,
    Sector,
    Source,
    TrendResult,
)

OCCUPATION_DEPENDENTS = (Observation, TrendResult, EmployabilityScore, OccupationSkill)


def upsert(session, model, rows, key):
    for row in rows:
        stmt = insert(model).values(**row)
        update = {k: v for k, v in row.items() if k != key}
        session.execute(stmt.on_conflict_do_update(index_elements=[key], set_=update))


def catalog_rows() -> dict[type, tuple[list[dict], str]]:
    cat = catalog()
    return {
        Country: ([c.model_dump() for c in cat.countries], "iso3"),
        Sector: ([s.model_dump(exclude={"ilostat_eco"}) for s in cat.sectors], "sector_code"),
        Occupation: ([o.model_dump() for o in cat.occupations], "occupation_code"),
        Source: (
            [dict(source_code=s.source_code, name=s.name, source_kind=s.kind,
                  base_url=s.base_url, expected_frequency=s.expected_frequency)
             for s in sources().sources],
            "source_code",
        ),
        Indicator: (
            [dict(indicator_code=i.code, name=i.name, unit=i.unit, description=i.description,
                  domain=i.domain, higher_is_better=i.higher_is_better)
             for i in indicators().indicators],
            "indicator_code",
        ),
    }


def prune_occupations(session) -> int:
    keep = {o.occupation_code for o in catalog().occupations}
    stale = [c for c in session.scalars(select(Occupation.occupation_code)).all() if c not in keep]
    if stale:
        for model in OCCUPATION_DEPENDENTS:
            session.execute(delete(model).where(model.occupation_code.in_(stale)))
        session.execute(delete(Occupation).where(Occupation.occupation_code.in_(stale)))
    return len(stale)


def main() -> None:
    with SessionLocal() as s:
        for model, (rows, key) in catalog_rows().items():
            upsert(s, model, rows, key)
            print(f"{model.__tablename__}: {len(rows)}")
        removed = prune_occupations(s)
        if removed:
            print(f"occupations removed (no longer in config): {removed}")
        s.commit()


if __name__ == "__main__":
    main()
