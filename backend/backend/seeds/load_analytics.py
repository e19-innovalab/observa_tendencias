"""Script de carga transaccional por lotes SQL para el Modelo Dimensional de Data Analytics.

Carga y persiste:
1. Actualizacion de coverage_report (homologacion ARG, CHL, URY).
2. Dimensiones: dim_pais, dim_sector, dim_tiempo, dim_sexo, dim_carrera.
3. Hechos y reportes: factores_macro_ppa, hecho_salario, hecho_instituciones_egresados,
   hecho_ocupacion_terciarios, reporte_densidad_profesional_sector, ranking_universidades_nacional,
   ranking_universidades_regional, analisis_genero_integral, proyecciones_graduados_sector,
   hecho_egresados.

Ejecucion:
  cd c:/proyectos/observa_tendencias/backend/backend
  .venv/Scripts/python -m seeds.load_analytics
"""

import sys
import time
from pathlib import Path

# Configurar codificacion UTF-8 para consola en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal, engine
from app.models import (
    AnalisisGeneroIntegral,
    CoverageReport,
    DimCarrera,
    DimPais,
    DimSector,
    DimSexo,
    DimTiempo,
    FactEgresados,
    FactInstitucionesEgresados,
    FactOcupacionTerciarios,
    FactSalario,
    FactoresMacroPPA,
    ProyeccionesGraduadosSector,
    RankingUniversidadesNacional,
    RankingUniversidadesRegional,
    ReporteDensidadProfesional,
)


def find_output_dir() -> Path:
    candidates = [
        Path("c:/proyectos/observa_tendencias/data_analytics/output"),
        Path(__file__).resolve().parents[3] / "data_analytics" / "output",
        Path(__file__).resolve().parents[2] / "data_analytics" / "output",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("No se encontró el directorio data_analytics/output")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Reemplaza NaN, infinitos y cadenas vacias con None para que Postgres almacene NULL."""
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    return df


def load_coverage_report(output_dir: Path, session) -> int:
    path = output_dir / "informe_cobertura.csv"
    if not path.exists():
        print(f"  [OMITIDO] {path.name} no existe")
        return 0

    df = pd.read_csv(path)
    df = clean_dataframe(df)
    cols = ["pais", "sector", "n_anios_observados", "anio_min", "anio_max", "elegible_proyeccion", "estado"]
    rows = df[cols].to_dict(orient="records")

    for row in rows:
        stmt = insert(CoverageReport).values(**row)
        update = {k: v for k, v in row.items() if k not in ("pais", "sector")}
        session.execute(stmt.on_conflict_do_update(
            index_elements=["pais", "sector"],
            set_=update
        ))
    return len(rows)


def load_table_simple(csv_file: Path, model, session, key_cols: list[str] | None = None) -> int:
    if not csv_file.exists():
        print(f"  [OMITIDO] {csv_file.name} no existe")
        return 0

    df = pd.read_csv(csv_file)
    df.columns = [c.lower() for c in df.columns]
    df = clean_dataframe(df)

    # Filtrar solo columnas existentes en el modelo
    table_cols = {c.name for c in model.__table__.columns if c.name != "id"}
    valid_cols = [c for c in df.columns if c in table_cols]
    df = df[valid_cols]

    rows = df.to_dict(orient="records")
    if not rows:
        return 0

    if key_cols:
        for row in rows:
            stmt = insert(model).values(**row)
            update = {k: v for k, v in row.items() if k not in key_cols}
            if update:
                session.execute(stmt.on_conflict_do_update(
                    index_elements=key_cols,
                    set_=update
                ))
            else:
                session.execute(stmt.on_conflict_do_nothing(
                    index_elements=key_cols
                ))
    else:
        # Truncar tabla e insertar filas
        session.execute(text(f"TRUNCATE TABLE {model.__tablename__} RESTART IDENTITY CASCADE;"))
        session.bulk_insert_mappings(model, rows)

    return len(rows)


def load_hecho_egresados(csv_file: Path, session, chunksize: int = 10000) -> int:
    if not csv_file.exists():
        print(f"  [OMITIDO] {csv_file.name} no existe")
        return 0

    print(f"  -> Truncando {FactEgresados.__tablename__}...")
    session.execute(text(f"TRUNCATE TABLE {FactEgresados.__tablename__} RESTART IDENTITY CASCADE;"))
    session.commit()

    total_rows = 0
    print(f"  -> Leyendo e insertando por lotes ({chunksize} filas/bloque)...")
    table_cols = {c.name for c in FactEgresados.__table__.columns if c.name != "id"}

    for chunk in pd.read_csv(csv_file, chunksize=chunksize, low_memory=False):
        chunk.columns = [c.lower() for c in chunk.columns]
        chunk = clean_dataframe(chunk)
        valid_cols = [c for c in chunk.columns if c in table_cols]
        chunk = chunk[valid_cols]

        rows = chunk.to_dict(orient="records")
        with SessionLocal() as s:
            s.bulk_insert_mappings(FactEgresados, rows)
            s.commit()
        total_rows += len(rows)
        sys.stdout.write(f"\r     Filas insertadas: {total_rows:,}")
        sys.stdout.flush()

    print()
    return total_rows


def main() -> None:
    t_inicio = time.time()
    output_dir = find_output_dir()
    print("=" * 75)
    print("🚀 CARGA TRANSACCIONAL POR LOTES SQL · MODELO ANALÍTICO EN POSTGRESQL")
    print(f"Directorio de datos analíticos: {output_dir}")
    print("=" * 75)

    resultados: dict[str, int] = {}

    with SessionLocal() as session:
        try:
            # 1. Coverage Report (Actualizacion en el esquema del backend)
            print("\n[1/4] Actualizando 'coverage_report' (homologación tripartita)...")
            n = load_coverage_report(output_dir, session)
            session.commit()
            resultados["coverage_report"] = n
            print(f"  ✓ coverage_report: {n} filas actualizadas")

            # 2. Tablas Dimensionales
            print("\n[2/4] Cargando tablas dimensionales...")
            dims = [
                ("dim_pais.csv", DimPais, ["pais_iso3"]),
                ("dim_sector.csv", DimSector, ["sector"]),
                ("dim_tiempo.csv", DimTiempo, ["anio"]),
                ("dim_sexo.csv", DimSexo, ["sexo_codigo"]),
                ("dim_carrera.csv", DimCarrera, ["carrera_id"]),
            ]
            for filename, model, keys in dims:
                n = load_table_simple(output_dir / filename, model, session, keys)
                session.commit()
                resultados[model.__tablename__] = n
                print(f"  ✓ {model.__tablename__}: {n} filas")

            # 3. Tablas de Hechos y Reportes Analiticos
            print("\n[3/4] Cargando hechos y reportes analíticos consolidados...")
            reports = [
                ("factores_macro_ppa.csv", FactoresMacroPPA, ["pais", "anio"]),
                ("hecho_salario.csv", FactSalario, None),
                ("hecho_instituciones_egresados.csv", FactInstitucionesEgresados, None),
                ("hecho_ocupacion_terciarios.csv", FactOcupacionTerciarios, None),
                ("reporte_densidad_profesional_sector.csv", ReporteDensidadProfesional, None),
                ("ranking_universidades_nacional.csv", RankingUniversidadesNacional, None),
                ("ranking_universidades_regional.csv", RankingUniversidadesRegional, None),
                ("analisis_genero_integral.csv", AnalisisGeneroIntegral, None),
                ("proyecciones_graduados_sector.csv", ProyeccionesGraduadosSector, None),
            ]
            for filename, model, keys in reports:
                n = load_table_simple(output_dir / filename, model, session, keys)
                session.commit()
                resultados[model.__tablename__] = n
                print(f"  ✓ {model.__tablename__}: {n} filas")

        except Exception as e:
            session.rollback()
            print(f"\n❌ Error durante la carga: {e}")
            raise e

    # 4. Hecho Egresados (carga masiva por lotes)
    print("\n[4/4] Cargando hecho_egresados (microdatos masivos)...")
    with SessionLocal() as session:
        n_egr = load_hecho_egresados(output_dir / "hecho_egresados.csv", session, chunksize=10000)
        resultados[FactEgresados.__tablename__] = n_egr
        print(f"  ✓ {FactEgresados.__tablename__}: {n_egr} filas totales cargadas")

    t_total = round(time.time() - t_inicio, 2)
    print("\n" + "=" * 75)
    print(f"✅ CARGA COMPLETA EXITOSA EN {t_total} SEGUNDOS")
    print("Resumen de registros en PostgreSQL:")
    for tabla, filas in resultados.items():
        print(f"  - {tabla}: {filas:,} filas")
    print("=" * 75)


if __name__ == "__main__":
    main()
