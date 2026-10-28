"""analytics tables: dimensional model, facts and analytical reports

Revision ID: 0015
Revises: 0014
"""
from alembic import op

from app.models import (
    AnalisisGeneroIntegral,
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

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

TABLES = (
    DimPais,
    DimSector,
    DimTiempo,
    DimSexo,
    DimCarrera,
    FactoresMacroPPA,
    FactSalario,
    FactInstitucionesEgresados,
    FactOcupacionTerciarios,
    ReporteDensidadProfesional,
    RankingUniversidadesNacional,
    RankingUniversidadesRegional,
    AnalisisGeneroIntegral,
    ProyeccionesGraduadosSector,
    FactEgresados,
)


def upgrade() -> None:
    bind = op.get_bind()
    for model in TABLES:
        model.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for model in reversed(TABLES):
        model.__table__.drop(bind, checkfirst=True)
