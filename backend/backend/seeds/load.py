"""Idempotent catalog seed: python -m seeds.load"""
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models import Country, Occupation, Sector, Source
from seeds import catalog


def upsert(session, model, rows, key):
    for row in rows:
        stmt = insert(model).values(**row)
        update = {k: v for k, v in row.items() if k != key}
        session.execute(stmt.on_conflict_do_update(index_elements=[key], set_=update))


def main() -> None:
    with SessionLocal() as s:
        upsert(s, Country, [dict(iso3=a, name_es=b, name_en=c) for a, b, c in catalog.COUNTRIES], "iso3")
        upsert(s, Sector, [dict(sector_code=a, name=b, isic_codes=c) for a, b, c in catalog.SECTORS], "sector_code")
        upsert(s, Occupation, [dict(occupation_code=a, name=b, isco08_code=c, sector_code=d)
                               for a, b, c, d in catalog.OCCUPATIONS], "occupation_code")
        upsert(s, Source, [dict(source_code=a, name=b, source_kind=c, base_url=d, expected_frequency=e)
                           for a, b, c, d, e in catalog.SOURCES], "source_code")
        s.commit()
    print("seeded")


if __name__ == "__main__":
    main()
