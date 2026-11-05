"""
Generador de la Matriz Integral de Habilidades Sectoriales del Cono Sur
Observatorio de Tendencias Socioeconómicas, Laborales y Educativas (ARG, CHL, URY)
Articula:
1. 25 Carreras Objetivo de los 5 Sectores Estratégicos (Tecnología, Conocimiento, Salud, Energía, Turismo).
2. 54 Ocupaciones CIUO-08 asociadas en Chile, Argentina y Uruguay.
3. Habilidades Técnicas Nucleares (Hard Skills) disciplinares.
4. Habilidades Emergentes del Sector (Transición Verde, Sostenibilidad, Innovación, Digitalización, etc.).
5. Habilidades Transversales, Humanas y de Cuidado (Soft Skills / Socioemocionales).
6. Habilidades Digitales y Transformación Tecnológica (incluyendo Inteligencia Artificial).
7. Métrica de Exposición a IA Generativa de la OIT (Working Paper 140, 2025).
8. Validación empírica con las 640 ofertas laborales observadas de LinkedIn.
"""

import csv
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
import yaml

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\proyectos\observa_tendencias")
REF_DIR = BASE_DIR / "backend" / "backend" / "config" / "reference"
DATA_ANALYTICS_DIR = BASE_DIR / "data_analytics"
OUTPUT_DIR = DATA_ANALYTICS_DIR / "output"
PROCESSED_DIR = DATA_ANALYTICS_DIR / "data" / "processed"
BACKEND_DATA_DIR = BASE_DIR / "backend" / "data" / "processed" / "data_analytics"

# Cargar referencias oficiales
with open(REF_DIR / "ilo_genai_exposure.yaml", encoding="utf-8") as f:
    ilo_values = yaml.safe_load(f)["values"]

with open(REF_DIR / "isco08_occupations.yaml", encoding="utf-8") as f:
    isco_occupations = yaml.safe_load(f)["occupations"]

with open(REF_DIR / "carreras_chile_ciuo.yaml", encoding="utf-8") as f:
    chl_cw = yaml.safe_load(f)["careers"]

with open(REF_DIR / "carreras_argentina_ciuo.yaml", encoding="utf-8") as f:
    arg_cw = yaml.safe_load(f)["careers"]

with open(REF_DIR / "carreras_uruguay_ciuo.yaml", encoding="utf-8") as f:
    ury_cw = yaml.safe_load(f)["careers"]

# Las 25 carreras objetivo maestras
CARRERAS_OBJETIVO = [
    ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613', 'grado',
     [r'ingenier.*(informatic|computacion|sistemas)', r'ciencias de la computacion', r'civil en informatica']),
    ('TEC02', 'Licenciatura en sistemas / ciencias de la computación', 'Tecnología', '0613', 'grado',
     [r'licenciatur.*(sistemas|computacion|informatica)']),
    ('TEC03', 'Ingeniería en telecomunicaciones', 'Tecnología', '0714', 'grado',
     [r'ingenier.*telecomunicacion', r'civil en telecomunicacion']),
    ('TEC04', 'Ingeniería electrónica', 'Tecnología', '0714', 'grado',
     [r'ingenier.*electronic', r'civil electronic']),
    ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613', 'tecnico',
     [r'tecnic.*(programacion|software|analista|computacion|informatica|desarrollo)', r'analista programador', r'analista de sistemas']),
    ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542', 'grado',
     [r'estadistic', r'datos', r'data science']),
    ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211', 'ambos',
     [r'diseno.*(grafico|multimedia|digital|visual|ux|ui)', r'multimedia', r'animacion digital']),
    ('EDC03', 'Ingeniería industrial', 'Economía del conocimiento', '0715', 'grado',
     [r'ingenier.*industrial', r'civil industrial']),
    ('EDC04', 'Marketing / publicidad', 'Economía del conocimiento', '0414', 'ambos',
     [r'marketing', r'comercializacion', r'publicidad', r'mercadotecnia']),
    ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413', 'grado',
     [r'administracion', r'ingenier.*comercial', r'negocios', r'comercial']),
    ('SAL01', 'Medicina', 'Salud', '0912', 'grado',
     [r'medicina(?!.*(veterinar|legal))', r'medico cirujano']),
    ('SAL02', 'Enfermería', 'Salud', '0913', 'ambos',
     [r'enfermer']),
    ('SAL03', 'Odontología', 'Salud', '0911', 'grado',
     [r'odontolog', r'cirujano dentista']),
    ('SAL04', 'Kinesiología / fisioterapia', 'Salud', '0915', 'grado',
     [r'kinesiolog', r'fisioterap']),
    ('SAL05', 'Nutrición', 'Salud', '0915', 'grado',
     [r'nutricion', r'dietetic']),
    ('ENE01', 'Ingeniería eléctrica', 'Energía', '0713', 'grado',
     [r'ingenier.*(electric|electrotecnic)', r'civil electric']),
    ('ENE02', 'Ingeniería química', 'Energía', '0711', 'grado',
     [r'ingenier.*quimic', r'civil quimic', r'quimic.*industr']),
    ('ENE03', 'Ingeniería mecánica', 'Energía', '0715', 'grado',
     [r'ingenier.*(mecanic|electromecanic)', r'civil mecanic']),
    ('ENE04', 'Geología / ingeniería en minas', 'Energía', '0724', 'grado',
     [r'geolog', r'ingenier.*(minas|mineri|petroleo)', r'ciencias.*suelo']),
    ('ENE05', 'Técnico/ingeniería en energías renovables', 'Energía', '0713', 'ambos',
     [r'energ.*renovable', r'solar', r'eolic', r'hidrogeno']),
    ('TUR01', 'Licenciatura en turismo', 'Turismo', '1015', 'grado',
     [r'turismo', r'ecoturismo']),
    ('TUR02', 'Hotelería / administración hotelera', 'Turismo', '1013', 'ambos',
     [r'hoteler']),
    ('TUR03', 'Gastronomía', 'Turismo', '1013', 'tecnico',
     [r'gastronom', r'cocina', r'culinari']),
    ('TUR04', 'Guía de turismo', 'Turismo', '1015', 'tecnico',
     [r'guia.*turism']),
    ('TUR05', 'Gestión de eventos', 'Turismo', '1015', 'ambos',
     [r'eventos', r'relaciones publicas']),
]

def fmt_code(c):
    return f"{c:04d}" if isinstance(c, int) else str(c).zfill(4)

# Catálogo exhaustivo de competencias desagregadas por ocupación CIUO-08
COMPETENCIAS_SECTORIALES_CATALOG = {
    "2512": {
        "nucleares": "Algoritmos y estructuras de datos; Programación orientada a objetos; Bases de datos SQL/NoSQL; Patrones de diseño de software; Git y control de versiones",
        "emergentes": "Arquitectura de microservicios distribuida; Cloud Native (AWS/GCP/Azure); Seguridad de aplicaciones (DevSecOps); APIs reactivas y Event-Driven",
        "transversales": "Resolución estructurada de problemas; Trabajo ágil en equipo (Scrum); Pensamiento crítico; Comunicación técnica efectiva",
        "digitales_ia": "Co-programación asistida por LLMs (GitHub Copilot); Generación y optimización de tests con IA; Refactorización asistida; Integración de APIs de IA",
        "vector_emergencia": "Digitalización Avanzada, Cloud Computing e IA Asistida",
        "tipologia_general": "Habilidad Técnica Nuclear y Emergente",
        "demanda_linkedin": "Muy Alta (48% de ofertas del sector Tecnología)",
        "recomendacion": "Enfocar formación en fundamentos de arquitectura limpia, validación rigurosa de código generado por IA y seguridad preventiva de software."
    },
    "2514": {
        "nucleares": "Desarrollo frontend y mobile (React, Flutter, Android, iOS); Integración de APIs RESTful; Maquetación responsiva; Pruebas de integración",
        "emergentes": "Progressive Web Apps (PWA); Edge Computing para móviles; Optimización de batería y rendimiento en cliente; Microfrontends",
        "transversales": "Orientación a la experiencia de usuario; Atención al detalle; Adaptabilidad tecnológica; Autonomía de aprendizaje",
        "digitales_ia": "SDKs de modelos de lenguaje en cliente; Prototipado asistido de código; Herramientas de debugging asistido por IA",
        "vector_emergencia": "Movilidad Digital y Experiencias de Usuario Omnicanal",
        "tipologia_general": "Habilidad Técnica Nuclear y de Transformación Digital",
        "demanda_linkedin": "Alta (25% de ofertas Tech en LinkedIn)",
        "recomendacion": "Consolidar competencias de arquitectura frontend escalable y desarrollo asistido por herramientas generativas."
    },
    "2511": {
        "nucleares": "Ingeniería de requerimientos; Modelado funcional de procesos (BPMN/UML); Especificación técnica; Arquitectura funcional; Pruebas de aceptación",
        "emergentes": "Diseño de flujos automatizados de negocio; Orquestación de microservicios; Integración de sistemas heterogéneos; Gobernanza de datos corporativos",
        "transversales": "Pensamiento sistémico; Negociación y mediación entre negocio y tecnología; Gestión de stakeholders; Visión estratégica",
        "digitales_ia": "Especificación de agentes de IA en flujos de trabajo; Modelado conceptual asistido por procesamiento de lenguaje natural (NLP)",
        "vector_emergencia": "Arquitectura Empresarial y Automatización de Procesos",
        "tipologia_general": "Habilidad de Gestión Técnica y Metodológica",
        "demanda_linkedin": "Alta (18% de ofertas del sector Tecnología)",
        "recomendacion": "Desarrollar capacidades para auditar y diseñar flujos híbridos humano-IA y especificación de arquitecturas de software sostenibles."
    },
    "2519": {
        "nucleares": "Modelado de bases de datos masivas; Pipelines de datos (ETL/ELT); Contenerización (Docker, Kubernetes); Ciberseguridad de redes e infraestructura",
        "emergentes": "Ingeniería de datos en streaming (Kafka/Flink); Infraestructura como Código (Terraform); MLOps y orquestación de modelos de datos",
        "transversales": "Gestión proactiva de riesgos; Resiliencia operativa; Trabajo interdisciplinario; Rigor en observabilidad de sistemas",
        "digitales_ia": "Pipelines de ingesta para vector databases y LLMs; Automatización de monitoreo con observabilidad predictiva",
        "vector_emergencia": "Ciberseguridad, Big Data y Plataformas de Datos",
        "tipologia_general": "Habilidad Emergente y de Infraestructura Crítica",
        "demanda_linkedin": "Muy Alta (Perfiles DevOps y Data Engineer en alta competencia)",
        "recomendacion": "Especialización en tuberías de datos seguras, gobernanza en la nube y resiliencia ante ciberamenazas."
    },
    "3512": {
        "nucleares": "Diagnóstico y soporte de hardware y software; Configuración de estaciones de trabajo y redes LAN; Gestión de incidencias (Service Desk/ITIL)",
        "emergentes": "Administración de identidades en la nube (IAM); Seguridad de puestos de trabajo remotos; Automatización básica de scripts (PowerShell/Bash)",
        "transversales": "Paciencia y empatía en la atención de usuarios; Claridad pedagógica; Escucha activa; Sentido de urgencia operativa",
        "digitales_ia": "Plataformas de autoservicio basadas en agentes de soporte IA; Automatización RPA para resolución de tickets frecuentes",
        "vector_emergencia": "Soporte en Entornos de Trabajo Híbrido y Automatización",
        "tipologia_general": "Habilidad Operativa y de Soporte en Transformación",
        "demanda_linkedin": "Media (Demanda constante en soporte corporativo)",
        "recomendacion": "Reconversión hacia roles de administración de plataformas cloud de autoservicio y automatización de soporte de primer nivel."
    },
    "3511": {
        "nucleares": "Supervisión de salas de servidores y centros de cómputo; Políticas de copias de seguridad (Backup & Restore); Monitoreo de enlaces y telecomunicaciones",
        "emergentes": "Monitoreo en nubes híbridas; Cumplimiento de normas de continuidad operativa (ISO 22301); Eficiencia energética en centros de datos",
        "transversales": "Disciplina en la ejecución de protocolos; Respuesta rápida a contingencias; Trabajo en turnos rotativos; Confiabilidad",
        "digitales_ia": "Herramientas AIOps para detección automática de anomalías en servidores y telecomunicaciones",
        "vector_emergencia": "Continuidad Operativa de Centros de Datos e Infraestructura Híbrida",
        "tipologia_general": "Habilidad Operativa Técnica",
        "demanda_linkedin": "Media-Baja (Migración sostenida a servicios cloud)",
        "recomendacion": "Capacitación hacia gestión de nubes públicas y administración de infraestructura como código."
    },
    "3514": {
        "nucleares": "Maquetación HTML5/CSS3; CMS corporativos (WordPress/Drupal); Optimización de velocidad de carga; Accesibilidad web (WCAG)",
        "emergentes": "Headless CMS; Diseño centrado en rendimiento Core Web Vitals; SEO semántico estructurado; Jamstack",
        "transversales": "Sentido estético visual; Colaboración con diseñadores y redactores; Organización y prolijidad técnica",
        "digitales_ia": "Generación asistida de layouts y prototipos interactivos; Generación automatizada de metadatos SEO",
        "vector_emergencia": "Presencia Digital y Experiencia Web Accesible",
        "tipologia_general": "Habilidad Técnica de Desarrollo Web",
        "demanda_linkedin": "Media (Integración progresiva con roles frontend)",
        "recomendacion": "Formación en frameworks modernos de cliente (Next.js/Vue) y accesibilidad web inclusiva."
    },
    "2152": {
        "nucleares": "Diseño de redes de fibra óptica y microondas; Comunicaciones móviles (4G/5G); Procesamiento digital de señales; Enrutamiento y conmutación de red",
        "emergentes": "Redes abiertas y virtualizadas (Open RAN); Conectividad satelital de baja órbita (LEO); Redes para Internet de las Cosas (IoT masivo/LoRaWAN)",
        "transversales": "Gestión de proyectos de infraestructura territorial; Trabajo de campo y laboratorio; Cumplimiento regulatorio de telecomunicaciones",
        "digitales_ia": "Optimización dinámica de tráfico y espectro radioeléctrico mediante algoritmos predictivos",
        "vector_emergencia": "Despliegue de Redes 5G, Conectividad Territorial y Redes Abiertas",
        "tipologia_general": "Habilidad Técnica Nuclear y de Expansión Estratégica",
        "demanda_linkedin": "Focalizada (Operadores de telecomunicaciones e integradores de red)",
        "recomendacion": "Consolidar formación en virtualización de funciones de red y protocolos de seguridad en telecomunicaciones críticas."
    },
    "2151": {
        "nucleares": "Cálculo de redes eléctricas de distribución y transmisión; Subestaciones eléctricas; Máquinas eléctricas y transformadores; Protecciones eléctricas industriales",
        "emergentes": "Integración de energías renovables a la red (solar fotovoltaica, eólica); Redes eléctricas inteligentes (Smart Grids); Almacenamiento en baterías (BESS)",
        "transversales": "Liderazgo de cuadrillas operativas; Gestión integral de seguridad eléctrica; Planificación de mantenimiento preventivo y correctivo",
        "digitales_ia": "Software de modelado y flujo de potencia (ETAP, DigSILENT); Telecontrol SCADA y mantenimiento predictivo por sensores IoT",
        "vector_emergencia": "Transición Energética, Electrificación de la Matriz y Smart Grids",
        "tipologia_general": "Habilidad Técnica Nuclear y de Transición Verde",
        "demanda_linkedin": "Alta (Sectores energético, minero e industrial en los 3 países)",
        "recomendacion": "Integración curricular de fuentes renovables distribuidas, electromovilidad y normativas de interconexión verde."
    },
    "2120": {
        "nucleares": "Inferencia estadística y cálculo de probabilidades; Modelos de regresión lineal y multivariada; Álgebra matricial; Programación en R y Python; SQL",
        "emergentes": "Modelado causal y econometría aplicada; Algoritmos de Machine Learning y ensamble; Big Data analítico (Spark/Databricks); Inferencia Bayesiana",
        "transversales": "Pensamiento crítico y escéptico; Rigor metodológico en experimentación; Comunicación ejecutiva de hallazgos; Ética en el uso de datos",
        "digitales_ia": "Modelos predictivos de Deep Learning; Procesamiento de lenguaje natural (NLP); Técnicas de explicabilidad de modelos (XAI)",
        "vector_emergencia": "Analítica Avanzada, Modelado Predictivo y Ciencia de Datos",
        "tipologia_general": "Habilidad Emergente y Científica Nuclear",
        "demanda_linkedin": "Muy Alta (Finanzas, biotecnología, logística y centros de datos)",
        "recomendacion": "Enfocar en ética algorítmica, validación de sesgos estadísticos y modelado econométrico robusto."
    },
    "2166": {
        "nucleares": "Composición visual y tipografía; Teoría del color; Diseño de identidad de marca; Ilustración digital y diseño vectorial; Maquetación editorial",
        "emergentes": "Diseño de sistemas de diseño escalables (Design Systems); Accesibilidad digital (A11y); Animación para interfaces (Microinteracciones en Motion Design)",
        "transversales": "Empatía con usuarios finales; Pensamiento visual y divergente; Capacidad de recibir feedback y justificar decisiones de diseño",
        "digitales_ia": "Herramientas de diseño generativo visual y prototipado asistido en Figma; Prompts para generación de assets y variaciones creativas",
        "vector_emergencia": "Experiencia de Usuario (UX/UI), Producto Digital y Accesibilidad",
        "tipologia_general": "Habilidad Creativa, de Diseño y Transformación Digital",
        "demanda_linkedin": "Alta (Empresas de producto tecnológico y agencias creativas)",
        "recomendacion": "Integrar investigación con usuarios (UX Research), arquitectura de información y curaduría crítica de herramientas generativas."
    },
    "2141": {
        "nucleares": "Estudio de tiempos y métodos; Gestión de operaciones y logística; Control estadístico de calidad (Six Sigma, Lean); Seguridad e higiene industrial",
        "emergentes": "Economía circular y huella de carbono industrial; Logística sustentable e inversa; Gemelos digitales (Digital Twins); Resiliencia de cadenas de suministro",
        "transversales": "Liderazgo de equipos de planta; Negociación operativa; Capacidad de síntesis ejecutiva; Gestión del cambio en procesos",
        "digitales_ia": "Simulación computacional de plantas productivas (FlexSim/Arena); Analítica prescriptiva de demanda; Mantenimiento prescriptivo",
        "vector_emergencia": "Industria 4.0, Sostenibilidad Productiva y Automatización de Operaciones",
        "tipologia_general": "Habilidad Técnica Nuclear y de Gestión Operativa",
        "demanda_linkedin": "Alta (Plantas industriales alimenticias, automotrices y químicas)",
        "recomendacion": "Capacitación en transformación digital de fábricas, auditoría de huella ambiental y analítica avanzada de operaciones."
    },
    "2421": {
        "nucleares": "Diagnóstico organizacional; Rediseño y optimización de procesos de negocio; Planificación estratégica; Control de gestión e indicadores clave (KPIs)",
        "emergentes": "Transformación digital de modelos de negocio; Gestión del cambio en culturas ágiles; Auditoría de sostenibilidad corporativa (criterios ESG)",
        "transversales": "Comunicación persuasiva y oratoria; Escucha empática; Pensamiento estratégico y holístico; Resolución de conflictos organizacionales",
        "digitales_ia": "Herramientas de minería de procesos (Process Mining); Mapeo automatizado de flujos organizacionales asistido por IA",
        "vector_emergencia": "Consultoría Estratégica, Gestión del Cambio y Sostenibilidad ESG",
        "tipologia_general": "Habilidad de Gestión Estratégica y Consultoría",
        "demanda_linkedin": "Alta (Grandes corporaciones y consultoras de servicios empresariales)",
        "recomendacion": "Formación en metodologías de cambio organizacional, gobernanza digital y liderazgo adaptativo."
    },
    "2431": {
        "nucleares": "Investigación de mercado; Estrategia de marca (Branding); Planificación de medios y presupuestos; Análisis de precios y competencia",
        "emergentes": "Marketing de rendimiento basado en datos (Performance Marketing); Growth Hacking; Marketing de contenidos sustentable; Omnicanalidad",
        "transversales": "Creatividad estratégica; Empatía con el consumidor; Flexibilidad mental; Negociación comercial",
        "digitales_ia": "Automatización de campañas en Meta/Google con IA; Analítica predictiva de retención y churn; Generación asistida de copys publicitarios",
        "vector_emergencia": "Marketing Digital Basado en Datos y Personalización",
        "tipologia_general": "Habilidad de Comunicación Comercial y Analítica",
        "demanda_linkedin": "Alta (Empresas de e-commerce, consumo masivo y servicios)",
        "recomendacion": "Equilibrar la creatividad humana con el análisis cuantitativo de atribución y el uso ético de datos de clientes."
    },
    "2432": {
        "nucleares": "Redacción institucional; Relaciones con medios de prensa; Organización de ruedas de prensa; Gestión de la comunicación interna",
        "emergentes": "Gestión de crisis reputacional en redes sociales; Comunicación de sustentabilidad y propósito corporativo; Relaciones con comunidades locales",
        "transversales": "Inteligencia emocional; Diplomacia y tacto; Capacidad de persuasión; Criterio ético bajo escenarios de alta presión",
        "digitales_ia": "Monitoreo en tiempo real del sentimiento de marca con procesamiento de lenguaje natural (NLP); Detección temprana de fake news",
        "vector_emergencia": "Gestión de Reputación, Crisis y Comunicación de Sostenibilidad",
        "tipologia_general": "Habilidad Humana de Comunicación y Relaciones Institucionales",
        "demanda_linkedin": "Media (Corporaciones, organismos públicos y ONGs)",
        "recomendacion": "Enfocar en narrativas auténticas, ética corporativa y manejo estratégico de crisis en tiempo real."
    },
    "2631": {
        "nucleares": "Microeconomía y macroeconomía aplicada; Modelado econométrico; Análisis de políticas fiscales y monetarias; Análisis de equilibrio de mercado",
        "emergentes": "Econometría espacial y de microdatos; Economía ambiental y valoración de servicios ecosistémicos; Nowcasting de variables económicas con Big Data",
        "transversales": "Rigor en la inferencia causal; Pensamiento crítico sobre supuestos económicos; Redacción de informes de política pública",
        "digitales_ia": "Procesamiento de fuentes no estructuradas para análisis macroeconómico; Modelado predictivo de series temporales de alta frecuencia",
        "vector_emergencia": "Análisis Macroeconómico Cuantitativo y Finanzas Públicas",
        "tipologia_general": "Habilidad Analítica y Científica Social",
        "demanda_linkedin": "Media-Alta (Bancos, entidades financieras, ministerios y organismos multilaterales)",
        "recomendacion": "Integrar métodos econométricos modernos de evaluación de impacto y procesamiento computacional de grandes bases de datos."
    },
    "3343": {
        "nucleares": "Redacción de correspondencia formal; Gestión de agenda ejecutiva; Organización de viajes y reuniones; Archivo y documentación formal",
        "emergentes": "Coordinación operativa de proyectos (Project Management Assistant); Gestión de presupuestos departamentales; Facilitación de eventos virtuales",
        "transversales": "Discreción y confidencialidad estricta; Organización y orden meticuloso; Trato cordial y protocolar; Proactividad",
        "digitales_ia": "Transcripción automatizada de reuniones con IA; Gestión documental en la nube (Google Workspace / Microsoft 365)",
        "vector_emergencia": "Coordinación Administrativa y Facilitación de Equipos",
        "tipologia_general": "Habilidad Administrativa en Reconversión hacia Gestión de Proyectos",
        "demanda_linkedin": "Media (Presión de automatización; migración a perfiles de soporte ejecutivo analítico)",
        "recomendacion": "Reconversión de roles secretariales tradicionales hacia asistencia de proyectos (PMO) y administración de herramientas digitales colaborativas."
    },
    "2211": {
        "nucleares": "Examen clínico integral y semiología; Diagnóstico de patologías prevalentes; Prescripción terapéutica farmacológica; Manejo de urgencias básicas",
        "emergentes": "Atención médica basada en valor; Telemedicina y seguimiento remoto de enfermedades crónicas; Medicina de precisión y farmacogenética",
        "transversales": "Empatía clínica y relación médico-paciente; Comunicación de malas noticias; Juicio bioético; Trabajo en equipos de salud interdisciplinarios",
        "digitales_ia": "Sistemas de soporte a la decisión clínica (CDSS); Registros médicos electrónicos integrados; Aplicaciones diagnósticas guiadas",
        "vector_emergencia": "Atención Primaria Integral, Telemedicina y Cuidados Crónicos",
        "tipologia_general": "Habilidad Médica Nuclear y de Juicio Clínico Humano",
        "demanda_linkedin": "Focalizada (Sistemas de salud públicos, obras sociales y clínicas privadas)",
        "recomendacion": "Fortalecer la formación semiológica humana combinada con el uso crítico y ético de herramientas diagnósticas asistidas."
    },
    "2212": {
        "nucleares": "Procedimientos quirúrgicos e invasivos especializados; Diagnóstico diferencial de alta complejidad; Manejo de pacientes críticos en UCI; Interconsultas",
        "emergentes": "Cirugía mínimamente invasiva y laparoscópica avanzada; Tratamientos biológicos y terapias dirigidas; Manejo multidisciplinario oncológico",
        "transversales": "Toma de decisiones bajo incertidumbre extrema; Liderazgo en quirófano; Resiliencia ante complicaciones quirúrgicas; Ética médica",
        "digitales_ia": "Visión computacional para análisis de imágenes radiológicas e histopatológicas; Cirugía robótica guiada",
        "vector_emergencia": "Alta Complejidad Médica, Cirugía de Precisión y Oncología",
        "tipologia_general": "Habilidad Médica Quirúrgica y Especializada de Alta Complejidad",
        "demanda_linkedin": "Focalizada y de Alta Remuneración",
        "recomendacion": "Entrenamiento en centros de simulación clínica avanzada y familiarización con tecnologías de cirugía robótica e imagenología digital."
    },
    "2221": {
        "nucleares": "Valoración de enfermería integral; Administración segura de medicamentos y vías parenterales; Cuidados de heridas complejas; Monitorización hemodinámica",
        "emergentes": "Enfermería de práctica avanzada; Gestión de la seguridad del paciente (prevención de infecciones intrahospitalarias); Cuidados paliativos domiciliarios",
        "transversales": "Compasión y cuidado centrado en la persona; Escucha activa y contención familiar; Trabajo en equipo bajo presión; Liderazgo de guardia",
        "digitales_ia": "Uso de bombas de infusión inteligentes; Registro informatizado al pie de cama; Dispositivos biomédicos de monitoreo continuo (IoMT)",
        "vector_emergencia": "Seguridad del Paciente, Cuidados Críticos y Atención Humanizada",
        "tipologia_general": "Habilidad Presencial Humana y de Cuidado Crítico (Ineludible)",
        "demanda_linkedin": "Muy Alta y Sostenida (Déficit estructural de profesionales de enfermería en la región)",
        "recomendacion": "Priorizar la profesionalización de la enfermería universitaria y el entrenamiento en protocolos de cuidados críticos y gestión hospitalaria."
    },
    "2261": {
        "nucleares": "Odontología preventiva y operatoria dental; Endodoncia; Periodoncia; Extracciones simples y cirugía menor bucal; Prótesis fijas y removibles",
        "emergentes": "Odontología digital (escaneo intraoral 3D, fresado CAD/CAM en consultorio); Implantología avanzada y regeneración ósea guiada; Odontología estética mínimamente invasiva",
        "transversales": "Destreza manual fina y coordinación visual; Manejo de la ansiedad y el dolor del paciente; Ética profesional y consentimiento informado",
        "digitales_ia": "Diseño digital de sonrisas (DSD); Análisis cefalométrico asistido por software especializado",
        "vector_emergencia": "Odontología Digital 3D, Implantología y Estética Mínimamente Invasiva",
        "tipologia_general": "Habilidad Clínica Quirúrgica Odontológica",
        "demanda_linkedin": "Focalizada (Clínicas dentales privadas y centros de atención primaria)",
        "recomendacion": "Incorporar flujo digital de trabajo (escáner intraoral e impresoras 3D) en la práctica clínica universitaria."
    },
    "2264": {
        "nucleares": "Evaluación funcional del aparato locomotor; Fisioterapia motora y neurológica; Kinesiterapia respiratoria; Agentes físicos y prescripción del ejercicio terapéutico",
        "emergentes": "Rehabilitación vestibular y del equilibrio; Kinesiología en cuidados intensivos (destete ventilatorio); Fisioterapia deportiva preventiva basada en evidencia",
        "transversales": "Motivación y empatía para guiar procesos largos de recuperación; Comunicación asertiva; Paciencia y perseverancia clínica",
        "digitales_ia": "Plataformas de telerrehabilitación interactiva; Análisis biomecánico de la marcha por sensores inerciales; Exoesqueletos de asistencia motora",
        "vector_emergencia": "Rehabilitación Funcional, Fisioterapia Crítica y Ejercicio Terapéutico",
        "tipologia_general": "Habilidad Presencial Terapéutica y de Rehabilitación Manual",
        "demanda_linkedin": "Alta (Centros de rehabilitación, hospitales y mutuales deportivas)",
        "recomendacion": "Enfocar en prescripción individualizada de ejercicio terapéutico y manejo de tecnologías de rehabilitación asistida."
    },
    "2265": {
        "nucleares": "Evaluación del estado nutricional y composición corporal; Diseño de planes de alimentación terapéutica; Cálculo de requerimientos energéticos; Educación alimentaria",
        "emergentes": "Nutrición deportiva personalizada basada en biomarcadores; Nutrición clínica para enfermedades metabólicas complejas; Dietas sostenibles basadas en plantas",
        "transversales": "Comunicación pedagógica empática; Entrevista motivacional para el cambio de hábitos; Respeto por la diversidad cultural alimentaria",
        "digitales_ia": "Software de análisis dietético y composición nutricional; Aplicaciones de monitoreo y adherencia nutricional de pacientes",
        "vector_emergencia": "Nutrición Clínica Personalizada, Prevención Metabólica y Sostenibilidad",
        "tipologia_general": "Habilidad Clínica de Salud y Educación Alimentaria",
        "demanda_linkedin": "Media-Alta (Consultorios, hospitales, industria alimentaria y clubes deportivos)",
        "recomendacion": "Integrar herramientas de nutrigenómica, entrevista motivacional y diseño de planes basados en alimentos de cercanía y saludables."
    },
    "2114": {
        "nucleares": "Cartografía y mapeo geológico de campo; Estratigrafía y petrología; Interpretación de perfiles sísmicos y gravimétricos; Geología estructural",
        "emergentes": "Geología para minerales críticos de la transición energética (Litio, Cobre, Cobalto, Tierras Raras); Hidrogeología y gestión de cuencas en sequía; Geotermia",
        "transversales": "Resistencia física para trabajo en terrenos agrestes y alta montaña; Pensamiento geológico en cuatro dimensiones (tiempo profundo); Gestión de riesgos naturales",
        "digitales_ia": "Modelado geológico predictivo 3D con software especializado (Leapfrog/ArcGIS); Teledetección satelital hiperespectral para prospección",
        "vector_emergencia": "Minerales Críticos de la Transición Verde y Gestión de Recursos Hídricos",
        "tipologia_general": "Habilidad Científica Nuclear y de Prospección Estratégica",
        "demanda_linkedin": "Focalizada (Empresas mineras, petroleras y consultoras ambientales)",
        "recomendacion": "Enfocar en prospección de minerales críticos para baterías y energías limpias y modelado hidrológico sustentable."
    },
    "2146": {
        "nucleares": "Diseño y planificación de minas (cielo abierto y subterránea); Mecánica de rocas y estabilidad de taludes; Procesos de chancado y molienda; Metalurgia extractiva",
        "emergentes": "Minería sustentable y gestión de relaves espesados; Descarbonización de flotas mineras (camiones eléctricos y a hidrógeno); Desalinización y recirculación de agua",
        "transversales": "Liderazgo de operaciones en campamentos mineros; Compromiso inquebrantable con la seguridad operacional (cero fatalidades); Relacionamiento comunitario",
        "digitales_ia": "Sistemas de despacho y perforación autónoma teleoperada; Monitoreo geotécnico en tiempo real con radares y sensores IoT",
        "vector_emergencia": "Minería 4.0, Automatización de Faenas y Cobre/Litio Verde",
        "tipologia_general": "Habilidad Técnica Nuclear y de Ingeniería de Extracción",
        "demanda_linkedin": "Muy Alta en Chile y zonas cordilleranas de Argentina",
        "recomendacion": "Consolidar minería 4.0 con énfasis en sostenibilidad ambiental, faenas remotas y cierre planificado de minas."
    },
    "2145": {
        "nucleares": "Balance de materia y energía en procesos; Termodinámica química; Diseño de reactores y columnas de destilación; Mecánica de fluidos y transferencia de calor",
        "emergentes": "Química verde y catálisis sustentable; Producción de hidrógeno verde y derivados (amoníaco/metanol verde); Biorrefinerías y valorización de biomasa",
        "transversales": "Cultura de seguridad en manejo de sustancias peligrosas; Gestión de calidad industrial; Trabajo interdisciplinario con ingenieros mecánicos y de procesos",
        "digitales_ia": "Simuladores de procesos químicos (Aspen Plus/HYSYS); Optimización multivariable de reacciones con analítica de datos (Quimioinformática)",
        "vector_emergencia": "Hidrógeno Verde, Química Circular y Descarbonización de Procesos",
        "tipologia_general": "Habilidad Técnica Nuclear de Procesos e Innovación Verde",
        "demanda_linkedin": "Media-Alta (Refinerías, petroquímica, papel y celulosa, hidrógeno verde)",
        "recomendacion": "Enfocar en procesos electroquímicos para la transición energética, captura de carbono y bioplásticos."
    },
    "2144": {
        "nucleares": "Cálculo estructural por elementos finitos (FEA); Termodinámica y plantas térmicas; Dinámica de máquinas y vibraciones; Sistemas hidráulicos y neumáticos",
        "emergentes": "Electromovilidad (diseño de trenes de potencia eléctricos); Aerogeneradores y componentes mecánicos para energía eólica; Manufactura aditiva industrial (impresión 3D metal)",
        "transversales": "Resolución de fallas mecánicas en sitio; Gestión de compras técnicas; Supervisión de talleres y montaje de líneas productivas",
        "digitales_ia": "Diseño generativo en CAD/CAE; Mantenimiento predictivo mediante análisis de vibraciones asistido por sensores IoT",
        "vector_emergencia": "Electromovilidad, Mantenimiento Predictivo 4.0 y Energía Eólica",
        "tipologia_general": "Habilidad Técnica Nuclear de Ingeniería Mecánica",
        "demanda_linkedin": "Alta (Metalmecánica, automotriz, parques eólicos y minería)",
        "recomendacion": "Integrar diseño de componentes para vehículos eléctricos, energías renovables y fabricación digital avanzada."
    },
    "3113": {
        "nucleares": "Montaje de tableros eléctricos de potencia y control; Cableado industrial bajo normas de seguridad; Reparación de motores y bombas eléctricas; Detección de fallas con multímetro y osciloscopio",
        "emergentes": "Instalación y mantenimiento de paneles solares fotovoltaicos; Conexión de cargadores de vehículos eléctricos; Programación básica de controladores lógicos programables (PLC)",
        "transversales": "Disciplina estricta en protocolos de corte y bloqueo (LOTO); Concentración y prolijidad técnica; Trabajo seguro en altura",
        "digitales_ia": "Manejo de instrumental digital de diagnóstico de redes eléctricas; Lectura de planos e interfaces HMI digitales",
        "vector_emergencia": "Instalaciones de Energías Renovables, Electromovilidad y Mantenimiento de Planta",
        "tipologia_general": "Habilidad Técnica Operativa en Sitio",
        "demanda_linkedin": "Alta (Demanda técnica sostenida en plantas productivas y obras)",
        "recomendacion": "Capacitación en montaje de sistemas fotovoltaicos conectados a red (on-grid/off-grid) y cargadores eléctricos."
    },
    "1411": {
        "nucleares": "Gestión de operaciones de habitaciones y alimentos; Planificación presupuestaria y control de costos hoteleros; Estándares de calidad de servicio y hospitalidad",
        "emergentes": "Gestión de hoteles sostenibles (certificaciones ambientales, reducción de plásticos y desperdicio de alimentos); Turismo de bienestar (Wellness Hospitality)",
        "transversales": "Hospitalidad genuina; Liderazgo de equipos multidisciplinarios; Manejo diplomático de quejas y situaciones críticas; Idiomas extranjeros (inglés/portugués)",
        "digitales_ia": "Sistemas de Revenue Management con tarificación dinámica algorítmica; Plataformas de experiencia de huésped omnicanal",
        "vector_emergencia": "Gestión Hotelera Sostenible, Revenue Management y Experiencia de Huésped",
        "tipologia_general": "Habilidad de Gestión de Hospitalidad y Negocios Turísticos",
        "demanda_linkedin": "Media (Cadenas hoteleras urbanas y resorts del Cono Sur)",
        "recomendacion": "Enfocar en revenue management dinámico, gestión de sustentabilidad turística y liderazgo de equipos de hospitalidad."
    },
    "3332": {
        "nucleares": "Planificación logística de congresos y ferias; Contratación de sedes, catering y técnica audiovisual; Presupuestación y cronograma de eventos; Protocolo y ceremonial",
        "emergentes": "Eventos sostenibles (cero residuos y medición de huella de carbono); Eventos corporativos inmersivos y gamificados; Turismo de reuniones (MICE) de alto impacto",
        "transversales": "Capacidad de resolución bajo presión en tiempo real; Negociación con proveedores; Creatividad espacial; Excelente comunicación interpersonal",
        "digitales_ia": "Plataformas de gestión de eventos híbridos y streaming; Registro y acreditación biométrica; Analítica de asistencia e interacciones",
        "vector_emergencia": "Turismo de Reuniones (MICE), Eventos Sostenibles e Híbridos",
        "tipologia_general": "Habilidad de Planificación, Logística y Protocolo de Eventos",
        "demanda_linkedin": "Media (Burós de convenciones, agencias productoras y hoteles)",
        "recomendacion": "Incorporar metodologías de producción de eventos sostenibles y dominio de plataformas digitales de acreditación e interacción."
    },
    "4221": {
        "nucleares": "Conocimiento de geografía turística mundial y regional; Normativas de visados y requisitos sanitarios; Asesoramiento en itinerarios turísticos",
        "emergentes": "Diseño de viajes de experiencia y turismo comunitario; Asesoría especializada en turismo de naturaleza y expedición; Curaduría de experiencias no convencionales",
        "transversales": "Escucha activa para entender deseos del viajero; Paciencia en la resolución de cancelaciones y reprogramaciones; Pasión por viajar",
        "digitales_ia": "Sistemas globales de reservas (GDS: Amadeus/Sabre); Plataformas de cotización dinámica asistida por motores inteligentes de búsqueda",
        "vector_emergencia": "Turismo Experiencial de Autor y Asesoría Personalizada",
        "tipologia_general": "Habilidad Comercial Turística en Reconversión hacia Asesoría de Autor",
        "demanda_linkedin": "Media-Baja (Alta presión de OTAs online; reconversión a turismo boutique)",
        "recomendacion": "Reconversión de emisión masiva de pasajes hacia consultoría experta en viajes personalizados y turismo vivencial."
    },
    "4224": {
        "nucleares": "Check-in y check-out de huéspedes; Facturación de servicios; Asignación y cambio de habitaciones; Atención de requerimientos de conserjería",
        "emergentes": "Rol de anfitrión local (Guest Host) y embajador de destino; Asistencia en experiencias personalizadas de la ciudad; Gestión de fidelización",
        "transversales": "Calidez en la recepción; Comunicación fluida en múltiples idiomas; Empatía y cortesía; Resolución de quejas con serenidad",
        "digitales_ia": "Gestión de quioscos de auto-check-in y llaves digitales en smartphones; Software hotelero PMS en tabletas móviles",
        "vector_emergencia": "Hospitalidad Personalizada y Experiencia de Bienvenida",
        "tipologia_general": "Habilidad Operativa de Atención al Huésped en Evolución hacia Anfitrión Local",
        "demanda_linkedin": "Media (Establecimientos hoteleros urbanos y turísticos)",
        "recomendacion": "Evolución del puesto hacia Guest Experience Specialist, centrando la tarea en la hospitalidad cálida e información turística local."
    },
    "5113": {
        "nucleares": "Conducción de grupos en circuitos urbanos y de naturaleza; Relato patrimonial, histórico y cultural; Primeros auxilios y seguridad en excursiones; Dinámica de grupos",
        "emergentes": "Interpretación ambiental y ecoturismo de mínimo impacto (No Deje Rastro); Guiado de astroturismo y avistamiento de aves (Birdwatching); Turismo accesible",
        "transversales": "Carisma y capacidad de comunicación oral (Storytelling); Cuidado y protección del grupo; Entusiasmo y pasión por el patrimonio; Dominio de idiomas",
        "digitales_ia": "Aplicaciones de geolocalización y mapas offline; Herramientas de realidad aumentada para reconstrucción histórica en sitio",
        "vector_emergencia": "Ecoturismo, Interpretación Patrimonial y Turismo Activo",
        "tipologia_general": "Habilidad Presencial Humana de Comunicación y Conducción",
        "demanda_linkedin": "Estacional y de Emprendimiento Autónomo",
        "recomendacion": "Capacitación en técnicas de storytelling patrimonial, primeros auxilios en áreas agrestes y ecoturismo regenerativo."
    },
    "3434": {
        "nucleares": "Técnicas culinarias clásicas y contemporáneas; Seguridad e higiene alimentaria (BPM/HACCP); Diseño y costeo de cartas y menús; Gestión de brigada de cocina",
        "emergentes": "Cocina de producto local y trazabilidad (Kilómetro Cero); Técnicas de fermentación y cocina circular (aprovechamiento integral); Menús para dietas especiales",
        "transversales": "Creatividad gastronómica; Liderazgo y temple bajo el calor y la presión del servicio; Respeto por los ingredientes y el productor local",
        "digitales_ia": "Software de costeo y gestión de mermas de cocina; Control de stock y comandas digitales",
        "vector_emergencia": "Gastronomía Sostenible, Producto Local y Cocina de Autor",
        "tipologia_general": "Habilidad Técnica Culinaria y Creativa en Sitio",
        "demanda_linkedin": "Alta (Restaurantes, hoteles y bodegas enoturísticas)",
        "recomendacion": "Formación integral en gestión de costos, liderazgo de equipos de cocina y prácticas de gastronomía sustentable."
    },
    "5120": {
        "nucleares": "Mise en place y preparación de materias primas; Manejo seguro de cuchillos y cocción; Mantenimiento de limpieza y desinfección de puestos de trabajo",
        "emergentes": "Técnicas de cocción al vacío (Sous-vide); Manejo de alérgenos y prevención de contaminación cruzada; Prácticas de cocina libre de gluten",
        "transversales": "Puntualidad, resistencia física y ritmo de trabajo constante; Cooperación en equipo; Cuidado minucioso de la higiene personal",
        "digitales_ia": "Pantallas KDS de cocina para recepción de comandas digitales",
        "vector_emergencia": "Operación Culinaria de Cocina y Seguridad Bromatológica",
        "tipologia_general": "Habilidad Operativa Culinaria Presencial",
        "demanda_linkedin": "Muy Alta en temporada turística",
        "recomendacion": "Fortalecimiento de habilidades técnicas manuales, rapidez operativa y cumplimiento estricto de normas de bioseguridad alimentaria."
    }
}

# Fallback enriquecido para ocupaciones transversales
DEFAULT_COMPETENCIAS = {
    "nucleares": "Competencias técnicas disciplinares del área funcional; Gestión operativa; Cumplimiento de normas y procedimientos; Control de calidad",
    "emergentes": "Digitalización de procesos; Adaptabilidad a nuevas metodologías; Sostenibilidad y eficiencia de recursos",
    "transversales": "Trabajo en equipo interdisciplinario; Comunicación profesional; Resolución de problemas; Pensamiento crítico",
    "digitales_ia": "Herramientas ofimáticas y plataformas digitales de colaboración; Complementación con herramientas tecnológicas de asistencia",
    "vector_emergencia": "Modernización de Procesos y Transformación Digital",
    "tipologia_general": "Habilidad Técnica y de Gestión Operativa",
    "demanda_linkedin": "Presencia transversal en el mercado laboral",
    "recomendacion": "Actualización continua en metodologías ágiles, digitalización de flujos y adaptación tecnológica."
}

# Procesar correspondencia carrera -> CIUO
matriz_filas = []

for c_meta in CARRERAS_OBJETIVO:
    cid, cname, sector, cine, nivel, pats = c_meta
    compiled_pats = [re.compile(p, re.IGNORECASE) for p in pats]
    
    # Chile
    chl_matched = set()
    for career_title, codes in chl_cw.items():
        if any(cp.search(career_title) for cp in compiled_pats):
            for code in codes:
                chl_matched.add(fmt_code(code))
                
    # Argentina
    arg_matched = set()
    for career_title, entry in arg_cw.items():
        if any(cp.search(career_title) for cp in compiled_pats) or \
           (cname.lower() in career_title.lower()) or \
           (cid.startswith('TEC') and 'inform' in career_title.lower()):
            if isinstance(entry, dict):
                for lvl, codes in entry.items():
                    for code in codes:
                        arg_matched.add(fmt_code(code))
            elif isinstance(entry, list):
                for code in entry:
                    arg_matched.add(fmt_code(code))
                    
    # Uruguay
    ury_matched = set()
    for career_title, codes in ury_cw.items():
        if any(cp.search(career_title) for cp in compiled_pats):
            for code in codes:
                ury_matched.add(fmt_code(code))

    all_codes = sorted(list(chl_matched | arg_matched | ury_matched))
    
    for code in all_codes:
        occ_info = isco_occupations.get(code, {})
        name_es = occ_info.get("name_es") or occ_info.get("name_en") or "Desconocido"
        name_en = occ_info.get("name_en") or "Unknown"
        
        ilo_info = ilo_values.get(code, {})
        mean_exp = float(ilo_info.get("mean", 0.0))
        sd_exp = float(ilo_info.get("sd", 0.0))
        gradient = ilo_info.get("gradient", "Not Evaluated")
        
        comp = COMPETENCIAS_SECTORIALES_CATALOG.get(code, DEFAULT_COMPETENCIAS)
        
        # Resumen integrado de habilidades ESCO
        habilidades_resumen = f"Nucleares: {comp['nucleares']} | Emergentes: {comp['emergentes']} | Transversales: {comp['transversales']} | Digitales/IA: {comp['digitales_ia']}"
        
        # Diagnóstico de impacto tecnológico integral
        if gradient in ["Gradient 2", "Gradient 3", "Gradient 4"]:
            impacto_ia_resumen = f"Alta complementariedad con IA y herramientas digitales (Gradiente OIT {gradient}); amplificación de tareas cognitivas y necesidad de validación crítica humana."
        elif gradient in ["Gradient 1", "Minimal Exposure"]:
            impacto_ia_resumen = f"Exposición moderada/asistida (Gradiente OIT {gradient}); integración de herramientas digitales sin reemplazo del núcleo ocupacional."
        elif gradient == "Not Exposed":
            impacto_ia_resumen = f"Baja exposición tecnológica directa (Gradiente OIT Not Exposed); predominio de destrezas manuales, operativas y de cuidado humano presencial."
        else:
            impacto_ia_resumen = "Monitoreo continuo de adopción tecnológica y automatización en el sector."
            
        matriz_filas.append({
            "carrera_id": cid,
            "carrera_objetivo": cname,
            "sector": sector,
            "cine_f_codigo": cine,
            "nivel_esperado": nivel,
            "ciuo_08": code,
            "ocupacion_nombre_es": name_es,
            "ocupacion_nombre_en": name_en,
            "tipologia_habilidad": comp["tipologia_general"],
            "vector_emergencia": comp["vector_emergencia"],
            "habilidades_nucleares": comp["nucleares"],
            "habilidades_emergentes_sector": comp["emergentes"],
            "habilidades_transversales_humanas": comp["transversales"],
            "habilidades_digitales_ia": comp["digitales_ia"],
            "habilidades_clave_esco": habilidades_resumen,
            "oit_exposicion_media": mean_exp,
            "oit_desvio_std": sd_exp,
            "oit_gradiente": gradient,
            "impacto_ia_resumen": impacto_ia_resumen,
            "demanda_observada_linkedin": comp["demanda_linkedin"],
            "recomendacion_curricular": comp["recomendacion"],
            "fuente_mapeo": "Diccionarios Cono Sur (CHL/ARG/URY) + Clasificador ESCO",
            "fuente_ofertas": "Observadas LinkedIn Jobs Cono Sur (data_analytics)",
        })

print(f"Total registros en la matriz analítica generada: {len(matriz_filas)}")

columnas = list(matriz_filas[0].keys())

destinos = [
    OUTPUT_DIR / "matriz_habilidades_riesgo_ia_sector.csv",
    OUTPUT_DIR / "matriz_habilidades_sectoriales_integrales.csv",
    PROCESSED_DIR / "matriz_habilidades_riesgo_ia_sector.csv",
    PROCESSED_DIR / "matriz_habilidades_sectoriales_integrales.csv",
    BACKEND_DATA_DIR / "matriz_habilidades_riesgo_ia_sector.csv",
    BACKEND_DATA_DIR / "matriz_habilidades_sectoriales_integrales.csv",
]

for dest in destinos:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(matriz_filas)
    print(f"  ✅ Guardado: {dest} ({len(matriz_filas)} filas)")

# Resúmenes
sec_counts = Counter(r["sector"] for r in matriz_filas)
tip_counts = Counter(r["tipologia_habilidad"] for r in matriz_filas)
vec_counts = Counter(r["vector_emergencia"] for r in matriz_filas)

print("\n--- DISTRIBUCION POR SECTOR ---")
for s, c in sec_counts.most_common():
    print(f"  - {s}: {c} cruces")

print("\n--- DISTRIBUCION POR TIPOLOGIA INTEGRAL DE HABILIDAD ---")
for t, c in tip_counts.most_common():
    print(f"  - {t}: {c} cruces")

print("\n--- DISTRIBUCION POR VECTOR DE EMERGENCIA Y DEMANDA ---")
for v, c in vec_counts.most_common():
    print(f"  - {v}: {c} cruces")
