"""analytics tables: dimensional model, facts and analytical reports

Revision ID: 0025
Revises: 0024
(first written as 0015 on main; renumbered when merging with the 0015-0024 chain of the backend)
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

revision = "0025"
down_revision = "0024"
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
