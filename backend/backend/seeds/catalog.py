"""Static catalog data for the MVP. Loaded by seeds/load.py (idempotent)."""

COUNTRIES = [
    ("ARG", "Argentina", "Argentina"),
    ("URY", "Uruguay", "Uruguay"),
    ("CHL", "Chile", "Chile"),
]

# OPEN DECISION (plan, section 7): technology and knowledge economy overlap on ISIC J62-63.
# These mappings follow the plan's example and must be confirmed and documented.
SECTORS = [
    ("technology", "Tecnología", ["J62", "J63"]),
    ("health", "Salud", ["Q86", "Q87", "Q88"]),
    ("energy", "Energía", ["D35", "B06", "C19"]),
    ("tourism", "Turismo", ["I55", "I56", "N79"]),
    ("knowledge_economy", "Economía del conocimiento",
     ["J62", "J63", "M69", "M70", "M71", "M72", "M73", "M74", "M75"]),
]

# (occupation_code, name, isco08_code, sector_code). Provisional list of 20.
OCCUPATIONS = [
    ("systems_analyst", "Analista de sistemas", "2511", "technology"),
    ("software_developer", "Desarrollador/a de software", "2512", "technology"),
    ("web_developer", "Desarrollador/a web y multimedia", "2513", "technology"),
    ("network_professional", "Profesional de redes informáticas", "2523", "technology"),
    ("physician", "Médico/a generalista", "2211", "health"),
    ("nurse", "Profesional de enfermería", "2221", "health"),
    ("lab_technician", "Técnico/a de laboratorio médico", "3212", "health"),
    ("pharmacist", "Farmacéutico/a", "2262", "health"),
    ("electrical_engineer", "Ingeniero/a electricista", "2151", "energy"),
    ("power_plant_operator", "Operador/a de planta de energía", "3131", "energy"),
    ("electrical_mechanic", "Mecánico/a electricista", "7412", "energy"),
    ("hotel_manager", "Gerente de hotel", "1411", "tourism"),
    ("cook", "Cocinero/a", "5120", "tourism"),
    ("event_planner", "Organizador/a de eventos", "3332", "tourism"),
    ("travel_guide", "Guía de turismo", "5113", "tourism"),
    ("accountant", "Contador/a", "2411", "knowledge_economy"),
    ("marketing_professional", "Profesional de marketing y publicidad", "2431", "knowledge_economy"),
    ("management_analyst", "Analista de gestión y organización", "2421", "knowledge_economy"),
    ("statistician", "Estadístico/a y actuario/a", "2120", "knowledge_economy"),
    ("graphic_designer", "Diseñador/a gráfico y multimedia", "2166", "knowledge_economy"),
]

# (source_code, name, kind, base_url, expected_frequency). URLs to be confirmed in Week 1.
SOURCES = [
    ("world_bank", "World Bank Open Data", "api", "https://api.worldbank.org/v2", "weekly"),
    ("ilostat", "ILOSTAT", "api", None, "weekly"),
    ("cepalstat", "CEPALSTAT", "api", None, "monthly"),
    ("datos_argentina", "Datos Argentina (Series de Tiempo)", "api",
     "https://apis.datos.gob.ar/series/api", "daily"),
    ("simel_chile", "SIMEL (INE Chile)", "api", None, "monthly"),
    ("bcentral_chile", "Banco Central de Chile", "api", None, "monthly"),
    ("manual_upload", "Carga manual", "manual", None, None),
]
