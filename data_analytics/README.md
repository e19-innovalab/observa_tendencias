# Observatorio Predictivo de Tendencias · Módulo Data Analytics
**Alcance Regional:** Argentina, Uruguay y Chile  
**Programa:** InnovaLab  
**Rol del Módulo:** Ingesta, limpieza, armonización multipaís, cálculo de indicadores y proyecciones de tendencias socioeconómicas, laborales y educativas.

---

##  1. Visión General del Módulo

Este módulo constituye la capa autónoma de analítica de datos del **Observatorio Predictivo de Tendencias**. Su objetivo es integrar fuentes oficiales de empleo, salarios, educación superior y series macroeconómicas de **Argentina, Chile y Uruguay**, para normalizarlas y producir métricas comparables, modelos de tendencia a 3 y 5 años con intervalos de confianza al 95%, diagnósticos de género y análisis institucional universitario.

###  Condiciones Básicas y Principios Metodológicos:
1. **100% Datos Observados:** No se aplican sustituciones sintéticas ni imputaciones calculadas. Cada dato proviene directamente de fuentes y relevamientos oficiales.
2. **Aislamiento e Independencia:** El módulo opera de forma autónoma. No requiere conectarse a bases del backend ni exporta directamente en directorios ajenos a `data_analytics/`.
3. **Paridad Internacional:**
   * Comparación de los mismos **5 sectores estratégicos**: *Tecnología, Economía del conocimiento, Salud, Energía y Turismo*.
   * Homologación de carreras y disciplinas según clasificaciones internacionales estándar (**CINE-F / CIIU Rev. 4**).
   * Conversión de salarios en moneda local (ARS, CLP, UYU) a **USD PPA (Paridad de Poder Adquisitivo)** utilizando los factores oficiales del Banco Mundial.
4. **Armonización de Género:** Estandarización de categorías en **F** (femenino), **M** (masculino) y opción **NS / Otros**.

---

##  2. Estructura de Directorios

```text
data_analytics/
├── data/
│   ├── raw/                  <- Datasets crudos y fuentes oficiales descargadas
│   │   ├── argentina/        <- Base SIU-Araucano, Anuarios SPU y salarios/empleo CEP-XXI
│   │   ├── chile/            <- Titulados Mi Futuro y estadísticas/ingresos SIES
│   │   ├── uruguay/          <- Educación Superior MEC, Anuarios y mercado laboral INE
│   │   └── linkedin_jobs/    <- Scraping de demanda laboral de puestos LinkedIn
│   └── processed/            <- Cachés y tablas normalizadas intermedias
├── output/                   <- Entregables consolidados de analytics (CSVs finales)
│   └── graficos/             <- Visualizaciones en alta resolución (.png)
├── src/                      <- Código fuente modular en Python
│   ├── __init__.py           <- Empaquetado del módulo y función ejecutar_todo()
│   ├── ingesta_01.py         <- Ingesta de APIs y verificación de fuentes
│   ├── cleaning_02.py        <- Normalización, limpieza y tablas de hechos
│   └── indicadores_03.py     <- Indicadores, Z-scores, brechas y proyecciones
├── pipeline.py               <- Script orquestador ejecutable de punta a punta
├── plan.md                   <- Bitácora viva y control de etapas del proyecto
├── requirements.txt          <- Dependencias de librerías Python
└── .gitignore                <- Reglas para evitar subir datasets pesados a GitHub
```

---

##  3. Requisitos del Sistema

* **Python 3.11 o superior** (probado y validado en Python 3.15).
* Entorno virtual de Python recomendado.

### Instalación de dependencias:
Desde la terminal, situarse en la carpeta `data_analytics` e instalar las librerías requeridas:

```bash
cd c:/proyectos/observa_tendencias/data_analytics
pip install -r requirements.txt
```

*Librerías principales empleadas:* `pandas`, `numpy`, `requests`, `scipy`, `matplotlib`, `openpyxl`, `odfpy`.

---

##  4. Guía de Ejecución

### 📋 Paso a Paso para Correr el Pipeline:

1. **Instalar dependencias y preparar el entorno:**
   Situarse en el directorio `data_analytics` e instalar las librerías requeridas:
   ```bash
   cd c:/proyectos/observa_tendencias/data_analytics
   pip install -r requirements.txt
   ```

2. **Descargar datasets desde Google Drive e ingresarlos a `data/raw/`:**
   > [!IMPORTANT]
   > Debido a las restricciones de tamaño de archivo y volumen en el repositorio, los datasets crudos oficiales no se versionan en Git.
   > **Se deben descargar los datasets desde Google Drive e ingresarlos manualmente a la carpeta `data/raw/`** respetando la siguiente estructura:
   > * `data/raw/argentina/`: Bases SIU-Araucano, Anuarios SPU y salarios/empleo CEP-XXI.
   > * `data/raw/chile/`: Bases de egresados de Mi Futuro y estadísticas/ingresos SIES.
   > * `data/raw/uruguay/`: Bases de Educación Superior del MEC y series de mercado laboral.
   > * `data/raw/linkedin_jobs/`: Archivos de scraping de ofertas laborales de LinkedIn.

3. **Ejecutar el pipeline de procesamiento:**
   Una vez colocados los datasets en `data/raw/`, ejecutar el pipeline completo o modular según se detalla a continuación.

### Opción A: Ejecución Integral del Pipeline (Recomendado)
Para correr las 3 etapas secuenciales (Ingesta ➔ Limpieza ➔ Indicadores):

```bash
python pipeline.py
```
*(Si tienes varias versiones de Python instaladas en Windows, puedes usar `py -3.15 pipeline.py`)*.

### Opción B: Ejecución Modular por Etapas
El script `pipeline.py` admite el argumento `--etapa` para correr pasos específicos:

```bash
# 1. Solo Ingesta (APIs de Banco Mundial, CEPALSTAT, ILOSTAT y zips):
python pipeline.py --etapa 1

# 2. Solo Limpieza y Armonización (Normalización multipaís y tablas de hechos):
python pipeline.py --etapa 2

# 3. Solo Indicadores y Proyecciones (Métricas, Z-scores, brechas y gráficos):
python pipeline.py --etapa 3
```

### Opción C: Ejecución Directa de cada Módulo
Cada archivo en `src/` puede ejecutarse de forma independiente:

```bash
python src/ingesta_01.py
python src/cleaning_02.py
python src/indicadores_03.py
```

### Opción D: Invocación Programática desde Python
```python
from src import ejecutar_todo, ejecutar_ingesta, ejecutar_limpieza, ejecutar_indicadores

# Ejecutar el flujo completo:
resultados = ejecutar_todo()
```

---

##  5. Funcionalidad de los Módulos

### `01 · src/ingesta_01.py` (Ingesta Automatizada)
1. **Descompresión Inteligente:** Detecta y extrae autónomamente paquetes `.zip` en `data/raw/` (como los anuarios universitarios de Argentina).
2. **APIs Oficiales Consumidas:**
   * **Banco Mundial:** Factores de Paridad de Poder Adquisitivo (`PA.NUS.PPP` y `PA.NUS.PRVT.PP`), IPC (`FP.CPI.TOTL`) y series de desempleo.
   * **CEPALSTAT:** Tasa bruta de matrícula terciaria (ID 99), desocupación por sexo (ID 127) y jóvenes en estudios superiores (ID 5701).
   * **ILOSTAT:** Series de ocupación laboral desagregadas por nivel educativo mediante la API SDMX/rplumber.
3. **Auditoría de Ingesta:** Inspecciona y verifica la integridad de las fuentes locales y genera `output/resumen_ingesta.csv`.

### `02 · src/cleaning_02.py` (Limpieza y Armonización)
1. **Mapeo y Clasificación:** Mapea más de 20 carreras objetivo en los 5 sectores estratégicos con expresiones regulares y normalización fonética/ortográfica.
2. **Chile:** Normaliza la serie histórica de egresados de Mi Futuro (2007-2025) e integra salarios en CLP al 4° año y empleabilidad desde SIES.
3. **Argentina:** Procesa la base de graduados SIU-Araucano desglosada por carrera, gestión y género, e integra salarios medios/medianos y puestos formales por CLAE2 desde CEP-XXI.
4. **Uruguay:** Normaliza la base de Educación Superior del MEC (2014-2023) asignando sectores, gestión y nivel académico.
5. **Conversión PPA:** Deflacta y homogeniza todos los salarios sectoriales a **USD PPA**.
6. **Modelado Dimensional:** Exporta tablas de hechos y dimensiones maestras (`dim_pais`, `dim_sector`, `dim_carrera`, `dim_sexo`, `dim_tiempo`, `puente_carrera_sector`).

### `03 · src/indicadores_03.py` (Indicadores y Proyecciones)
1. **Tasas Interanuales y Z-Scores:** Mide el crecimiento relativo interanual y la aceleración estandarizada (Z-score de dinamismo) por país y sector.
2. **Proyecciones Lineales a 3 y 5 Años:** Modela tendencias de egresados con intervalos de confianza al 95% para sectores con al menos 3 años observados.
3. **Semáforo Presupuestario:** Recomienda prioridades presupuestarias para orientar políticas públicas de formación técnica y universitaria (`ALTA`, `MEDIA`, `BAJA PRIORIDAD`).
4. **Brecha Salarial Regional:** Compara ingresos medios y medianos en USD PPA entre países para los mismos puestos y sectores.
5. **Diagnóstico Integral de Género:** Calcula tasas de participación femenina en graduados y empleo formal, identificando zonas de paridad (35%-65%), sub-representación en STEM y segregación en cuidados.
6. **Rankings Universitarios del Cono Sur:**
   * **Top 10 Regional:** Consolidado de las 10 instituciones con mayor volumen de egresados del Cono Sur.
   * **Rankings por País:** Tablas nacionales con cuota de participación y sector predominante.
   * **Ranking Descendente:** Identificación de universidades con menor volumen en países con más de 10 universidades.

---

##  6. Catálogo de Entregables Generados (`output/`)

### Tablas de Hechos y Datos Normalizados:
* `hecho_egresados.csv`: Serie histórica completa de graduados (ARG, CHL, URY) en los 5 sectores estratégicos (más de 228.000 registros).
* `hecho_salario.csv`: Salarios observados en moneda local y convertidos a USD PPA.
* `hecho_ocupacion_terciarios.csv`: Métricas de puestos de trabajo, participación de mujeres y empleabilidad.
* `factores_macro_ppa.csv`: Serie temporal de factores PPA e IPC del Banco Mundial.

### Reportes de Indicadores:
* `indicadores_interanuales_zscore.csv`: Variaciones porcentuales anuales y Z-scores por sector.
* `proyecciones_oferta_demanda.csv`: Estimaciones predictivas a 3 y 5 años con límites inferior y superior al 95%.
* `reporte_presupuesto_educativo.csv`: Semáforo presupuestario y recomendaciones de inversión formativa.
* `reporte_brecha_salarial_regional.csv`: Matriz regional de salarios y brechas porcentuales entre países.
* `analisis_genero_integral.csv`: Paridad formativa, tasa de feminización y brecha salarial estimada.
* `top_universidades_cono_sur.csv`: Ranking consolidado de universidades líderes regionales.
* `top_universidades_por_pais.csv`: Desglose institucional por país.
* `informe_cobertura.csv`: Auditoría de años observados y elegibilidad predictiva por sector y país.

### Visualizaciones Gráficas (`output/graficos/`):
* `proyeccion_graduados_ARG.png`: Series históricas y proyecciones a 5 años para Argentina.
* `proyeccion_graduados_CHL.png`: Series históricas y proyecciones a 5 años para Chile.
* `proyeccion_graduados_URY.png`: Series históricas y proyecciones a 5 años para Uruguay.
* `brecha_salarial_regional_multipais.png`: Gráfico comparativo de barras de salarios USD PPA por país y sector.
* `analisis_genero_empleabilidad_brecha.png`: Participación femenina por sector y franja de paridad.
* `top_universidades_cono_sur.png`: Gráfico de barras horizontales de las 10 universidades con más egresados del Cono Sur.
* `top_universidades_por_pais.png`: Panel comparativo de las universidades más destacadas por país.

---

##  7. Sugerencias de Fuentes Oficiales Adicionales

Para profundizar la precisión analítica y cubrir vacíos estructurales respetando la regla de **100% datos observados**, se recomienda incorporar las siguientes fuentes públicas y oficiales en futuras iteraciones:

### 🇦🇷 Argentina
1. **INDEC – Encuesta Permanente de Hogares (EPH - Microdatos Trimestrales):**
   * **Aporte clave:** Permite calcular salarios horarios y mensuales reales, tasa de actividad y subocupación desagregada por ocupación específica mediante el Clasificador Nacional de Ocupaciones (CNO), homologable a CIUO-08.
   * **Acceso:** Descarga pública directa desde el portal de bases de datos del INDEC.
2. **Secretaría de Educación / Capital Humano – Anuarios Universitarios Actualizados:**
   * **Aporte clave:** Extender la serie histórica de graduados universitarios a los años 2023 y 2024 para las universidades públicas y privadas de todo el país.
3. **MECON – Dirección Nacional de Asuntos Provinciales:**
   * **Aporte clave:** Desagregación salarial y de empleo a nivel regional/provincial para evaluar asimetrías geográficas.

### 🇺🇾 Uruguay
1. **INE Uruguay – Encuesta Continua de Hogares (ECH - Microdatos Anuales):**
   * **Aporte clave:** Reemplazar los benchmarks sectoriales estáticos por series temporales observadas continuas (2015-2024) de ingresos laborales, puestos ocupados y horas trabajadas, con codificación CIUO-08 a 4 dígitos y CIIU Rev. 4.
   * **Acceso:** Catálogo de microdatos del Instituto Nacional de Estadística (INE).
2. **Catálogo Nacional de Datos Abiertos (AGESIC / MEC):**
   * **Aporte clave:** Registro detallado de títulos otorgados por la Universidad de la República (UdelaR), la Universidad Tecnológica (UTEC) y universidades privadas por carrera individual.
3. **BPS (Banco de Previsión Social):**
   * **Aporte clave:** Estadísticas de puestos cotizantes formales y salarios imponibles por rama de actividad.

### 🇨🇱 Chile
1. **SIES / Mi Futuro – Base Longitudinal de Empleabilidad e Ingresos por Carrera:**
   * **Aporte clave:** Provee el seguimiento cohorte por cohorte del ingreso al 1°, 2° y 5° año de titulación, esencial para calcular el Índice Sintético de Empleabilidad (ISE).
2. **INE Chile – Encuesta Nacional de Empleo (ENE):**
   * **Aporte clave:** Microdatos mensuales y trimestrales móviles sobre ocupación calificada, desempleo y brecha de ingresos con codificación CIUO-08.cl.
3. **SENCE – Sistema de Análisis de Bolsas de Empleo (SABE):**
   * **Aporte clave:** Monitoreo mensual de avisos laborales, ocupaciones demandadas, salarios ofertados y habilidades requeridas en el mercado laboral chileno.

###  Demanda Laboral en Tiempo Cercano al Real (Cono Sur)
* **Dataset de Scraping de Puestos de LinkedIn (`data/raw/linkedin_jobs/`):**
  * **Aporte clave:** Contiene publicaciones recientes de empleo en tecnología, salud, energía, finanzas y turismo en los tres países. Permite extraer habilidades técnicas y blandas emergentes y compararlas con los planes formativos.

---

##  8. Hoja de Ruta: Mejoras Técnicas Propuestas al Código (en Etapas)

Se propone un plan de evolución técnica estructurado en 4 fases de implementación gradual:

### 🔹 Fase 1: Homologación Ocupacional Regional (CIUO-08 / ISCO-08)
* **Objetivo:** Definir e implementar una tabla puente canónica `data/processed/puente_carrera_ciuo.csv`.
* **Mejora:** Enlazar las 20+ carreras analizadas con los códigos CIUO-08 de 4 dígitos correspondientes a las **5 ocupaciones específicas de cada uno de los 5 sectores estratégicos**, garantizando paridad conceptual exacta entre Argentina, Chile y Uruguay.

### 🔹 Fase 2: Ingestor y Ponderador de Microdatos de Hogares (EPH / ECH)
* **Objetivo:** Automatizar la lectura y expansión muestral de encuestas de hogares.
* **Mejora:** Desarrollar scripts de carga que apliquen los factores de expansión (`PONDERA` en INDEC y `PESOPR` en INE) para calcular medianas salariales ponderadas, percentiles 25/75 y brechas de género observadas a nivel ocupación sin interpolaciones sintéticas.

### 🔹 Fase 3: Minería de Habilidades y Análisis de Brechas de Demanda (NLP)
* **Objetivo:** Procesar el contenido de los avisos de empleo de `linkedin_jobs/`.
* **Mejora:** Implementar un extractor con expresiones regulares y taxonomías de competencias para clasificar las habilidades requeridas (lenguajes de programación, herramientas de análisis, certificaciones, idiomas) y contrastarlas contra los perfiles de egreso universitarios.

### 🔹 Fase 4: Modelos Predictivos Avanzados y Detección de Quiebres Estructurales
* **Objetivo:** Robustecer las proyecciones temporales para series con más de 5 años observados.
* **Mejora:** Incorporar modelos de series temporales autorregresivos (ARIMA / SARIMAX) y pruebas de raíz unitaria (Dickey-Fuller), junto con algoritmos de detección de quiebres estructurales (Pettitt / Chow test), para alertar ante cambios bruscos en las tendencias de graduación y contratación.

