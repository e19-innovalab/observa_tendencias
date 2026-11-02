from app.models.analytics import (  # noqa: F401
    CoverageReport,
    Graduate,
    GraduateProjection,
    GraduateTrend,
    JobPosting,
)
from app.models.assistant import AssistantLog  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.catalog import (  # noqa: F401
    Country,
    Occupation,
    OccupationCrosswalk,
    OccupationSkill,
    Sector,
    Skill,
    SkillGroup,
)
from app.models.methodology import (  # noqa: F401
    Alert,
    EmployabilityScore,
    LuditaScore,
    Methodology,
    MoctezumaScore,
    RedQueenScore,
    SkillGap,
    SkillGroupGap,
    SkillProfile,
    TrendResult,
)
from app.models.sources import (  # noqa: F401
    DataRevision,
    DatasetFile,
    EducationMismatchCell,
    Indicator,
    IngestionRun,
    Observation,
    Source,
)
from app.models.users import User  # noqa: F401
from app.models.analytics_dm import (  # noqa: F401
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
