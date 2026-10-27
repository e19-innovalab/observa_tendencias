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
5. **Auditoría e Inspección Continua con Agentes de IA en Antigravity:** El diseño metodológico, la depuración del código, la inspección de consistencia matemática y la validación de paridad de este módulo se desarrollan mediante pair programming en **Google Antigravity**, apoyándose en agentes de IA para realizar revisiones exhaustivas paso a paso, trazabilidad en bitácoras y pruebas de estrés de los algoritmos.

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
   > **Se deben descargar los datasets desde la carpeta compartida de Google Drive e ingresarlos manualmente a la carpeta `data/raw/`** respetando la siguiente estructura y nombres de archivo exactos:
   >
   > * **`data/raw/argentina/`**:
   >   * `base_araucano_traducida.xlsx` *(Base de graduados universitarios SIU-Araucano)*
   >   * `anuario_csv_2020.zip` *(SPU Anuario Estadístico Universitario 2020)*
   >   * `anuario_csv_2021.zip` *(SPU Anuario Estadístico Universitario 2021)*
   >   * `anuario_csv_2022.zip` *(SPU Anuario Estadístico Universitario 2022)*
   >   * `puestos_privados_mensual_por_clae2.csv` *(o `puestos_depto_priv_por_clae2.csv`, empleo formal CEP-XXI)*
   >   * `w_mean_privado_mensual_por_clae2.csv` *(Salario medio formal CEP-XXI)*
   >   * `w_median_privado_mensual_por_clae2.csv` *(Salario mediano formal CEP-XXI)*
   >   * `share_mujer_privado_mensual_por_clae2.csv` *(Participación de mujeres CEP-XXI)*
   >
   > * **`data/raw/chile/`**:
   >   * `TITULADO_2007-2025_web_27_05_2026_E-1.xlsx` *(Base histórica de titulados de Mi Futuro)*
   >   * `Buscador_Estadisticas_por_carrera_2024_2025_SIES.xlsx` *(Estadísticas académicas SIES)*
   >   * `Buscador_Empleabilidad_e_Ingresos_2024_2025_SIES.xlsx` *(Ingresos y empleabilidad SIES)*
   >
   > * **`data/raw/uruguay/`**:
   >   * `00._educ_superior_datos.csv` *(Educación Superior del MEC)*
   >   * `1.Serie-Egresos-totales-Grado-por-Servicio-2000-2024.ods` *(Serie histórica de egresos de UdelaR)*
   >   * `Anuario Estadístico de Educación 2024.xlsx` *(Anuario MEC con desglose institucional)*
   >   * `10235_distribucion_porcentual_de_las_personas_ocupadas_segun_sexo_por_rama_de_actividad_en_ocupa.csv` *(Mercado laboral INE Uruguay)*
   >
   > * **`data/raw/linkedin_jobs/`** *(opcional / exploración NLP)*:
   >   * Archivos `.csv` de scraping de publicaciones laborales de LinkedIn.
   >
   > *(Nota: las series de Banco Mundial, CEPALSTAT, ILOSTAT e INDEC se descargan de forma automática vía API al correr el pipeline).*

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
   * **ILOSTAT (OIT):**
     * Serie de salarios medios mensuales de asalariados por rama de actividad (CIIU Rev. 4) y sexo (`EAR_EMTA_SEX_ECO_NB`) para Argentina, Chile y Uruguay.
     * Serie de ocupación laboral desagregada por nivel educativo (`EAP_TEAP_SEX_AGE_EDU_NB`).
3. **Auditoría de Ingesta:** Inspecciona y verifica la integridad de las fuentes locales y genera `output/resumen_ingesta.csv`.

### `02 · src/cleaning_02.py` (Limpieza y Armonización)
1. **Mapeo y Clasificación:** Mapea más de 20 carreras objetivo en los 5 sectores estratégicos con expresiones regulares y normalización fonética/ortográfica bajo CINE-F.
2. **Chile:** Normaliza la serie histórica de egresados de Mi Futuro (2007-2025) por institución e integra salarios en CLP al 4° año y empleabilidad desde SIES.
3. **Argentina:** Procesa la base de graduados SIU-Araucano (2016-2018) y los anuarios SPU (2020-2022) totalizando 6 años observados continuos en los 5 sectores estratégicos, e integra salarios medios/medianos y puestos formales por CLAE2 ponderados desde CEP-XXI (2007-2023).
4. **Uruguay:** Normaliza la base de Educación Superior del MEC (2014-2023), integra egresos del Anuario MEC 2024 y la serie histórica de UdelaR (2000-2024), e incorpora el relevamiento de empleo por sexo del INE Uruguay.
5. **Capa Salarial Supranacional OIT:** Procesa `EAR_EMTA_SEX_ECO_NB` para ARG, CHL y URY, estandariza a secciones CIIU Rev. 4 (D, I, J, M, Q) y deflacta a **USD PPA** mediante factores del Banco Mundial.
6. **Modelado Dimensional:** Exporta tablas de hechos (`hecho_egresados`, `hecho_instituciones_egresados`, `hecho_salario`, `hecho_ocupacion_terciarios`) y dimensiones maestras (`dim_pais`, `dim_sector`, `dim_carrera`, `dim_sexo`, `dim_tiempo`, `puente_carrera_sector`).

### `03 · src/indicadores_03.py` (Indicadores y Proyecciones)
1. **Tasas Interanuales y Z-Scores:** Mide el crecimiento relativo interanual y la aceleración estandarizada (Z-score con umbral $|Z| > 2.0$) por país y sector.
2. **Proyecciones Lineales con $t$-Student:** Modela tendencias de egresados a 3 y 5 años con intervalos de confianza al 95% para las series con $n \ge 5$ años observados (los 15 estratos de ARG, CHL y URY son ahora 100% elegibles y proyectables).
3. **Semáforo Presupuestario:** Recomienda prioridades presupuestarias formativas (`ALTA`, `MEDIA`, `BAJA PRIORIDAD`) para los 3 países.
4. **Comparativa Salarial Regional Multipais:** Matriz tripartita (ARG, CHL, URY) en USD PPA homologado bajo la serie supranacional de la OIT 2024 (`reporte_brecha_salarial_regional.csv`), complementada por la granularidad de CEP-XXI y SIES (`reporte_salarios_detalle_local.csv`).
5. **Diagnóstico Integral de Género y Brecha Salarial Observada:** Calcula tasas porcentuales de graduadas por sexo (F, M, NB) y empleo formal, junto a la **brecha salarial de género 100% observada** de la OIT 2024 (sin estimaciones simuladas ni números estáticos).
6. **Rankings Universitarios (100% Datos Observados con Paridad Temporal Controlada):**
   * **Top 10 Regional:** Universidades líderes del Cono Sur evaluadas estrictamente en el **último año común tripartito (2022)** para evitar distorsiones cronológicas, y acumulado histórico.
   * **Rankings Nacionales:** Universidades con más y menos egresados evaluando el **año más reciente observado por cada país** (ARG 2022, CHL 2025, URY 2024), con cobertura íntegra para países con $\le 10$ instituciones (Uruguay).

---

##  6. Catálogo de Entregables Generados (`output/`)

### Tablas de Hechos y Datos Normalizados:
* `hecho_egresados.csv`: Serie histórica completa de graduados (ARG, CHL, URY) en los 5 sectores estratégicos (173.890 registros observados).
* `hecho_instituciones_egresados.csv`: Serie de egresados con trazabilidad institucional oficial y paridad universitaria estricta (4.571 registros de SPU, Mi Futuro y MEC/UdelaR cubriendo 187 universidades normalizadas, excluyendo CFT/IP según Decisión Etapa 4).
* `hecho_salario.csv`: Salarios observados en moneda local y USD PPA (755 registros: CEP-XXI, SIES y OIT/ILOSTAT para ARG, CHL y URY).
* `hecho_ocupacion_terciarios.csv`: Métricas de puestos de trabajo, participación de mujeres y empleabilidad (173 registros).
* `factores_macro_ppa.csv`: Serie temporal de factores PPA del PIB del Banco Mundial (2010–2025).

### Reportes de Indicadores:
* `indicadores_interanuales_zscore.csv`: Variaciones porcentuales anuales calculadas exclusivamente sobre anos consecutivos observados y Z-scores con alertas de significancia (|Z| >= 1.4) con paridad metodologica tripartita.
* `proyecciones_graduados_sector.csv` (y `proyecciones_oferta_demanda.csv`): Estimaciones predictivas a 3 y 5 anos sobre el flujo de egresados de educacion superior con intervalos t-Student al 95% y alertas de tendencia (30 proyecciones para los 3 paises).
* `reporte_densidad_profesional_sector.csv`: Cruce de oferta universitaria vs. demanda laboral que mide la tasa de renovacion profesional (Graduados universitarios por cada 1.000 personas ocupadas en el sector segun OIT/ILOSTAT, 140 registros cruzados).
* `reporte_presupuesto_educativo.csv`: Semaforo presupuestario y recomendaciones de inversion formativa con cobertura integral de Argentina, Chile y Uruguay.
* `reporte_brecha_salarial_regional.csv`: Matriz regional tripartita de salarios USD PPA 2024 y brechas porcentuales entre paises.
* `reporte_salarios_detalle_local.csv`: Reporte complementario de salarios por rama y carrera de CEP-XXI (ARG) y SIES (CHL), con matriz completa de 15 filas donde Uruguay figura formalmente con celdas vacias observadas y advertencia explicita.
* `analisis_genero_integral.csv`: Paridad formativa por sexo (F, M, NB), empleo femenino y diagnostico de paridad bajo estandar internacional EIGE / OIT (40%-60%).
* `reporte_brechas_genero_detallado.csv`: Desglose anualizado y comparativo de graduados universitarios (ARG 2016-2018, CHL 2016-2018 y 2025, URY total observado) y empleo sectorial tripartito OIT 2024 con cantidades de F, M, otros y brechas porcentuales (70 registros).
* `ranking_universidades_regional.csv`: Ranking consolidado de las universidades lideres del Cono Sur en el ano comun tripartito 2022 y acumulado.
* `ranking_universidades_nacional.csv`: Desglose institucional por pais en el ano mas reciente observado por pais (ARG 2022, CHL 2025, URY 2024).
* `reporte_contexto_educativo_laboral.csv`: Cruce de tasa de desempleo terciario vs. general (Banco Mundial SL.UEM.ADVN.ZS / SL.UEM.TOTL.ZS) y evaluacion del efecto protector de la educacion superior (48 registros).
* `informe_cobertura.csv`: Auditoria de anos observados, ventana comun (2018-2022) y elegibilidad predictiva (15/15 estratos proyectables).

### Inventario de Fuentes:
* `fuentes.yaml`: Catálogo oficial y auditable de todas las APIs y datasets incorporados, variables extraídas y tratamiento metodológico.

### Visualizaciones Gráficas (`output/graficos/`):
* `proyeccion_graduados_ARG.png`: Series históricas y proyecciones para Argentina.
* `proyeccion_graduados_CHL.png`: Series históricas y proyecciones a 5 años para Chile.
* `proyeccion_graduados_URY.png`: Series históricas y proyecciones a 5 años para Uruguay.
* `brecha_salarial_regional_multipais.png`: Comparativa salarial de barras tripartita (ARG, CHL, URY) en USD PPA 2024.
* `analisis_genero_empleabilidad_brecha.png`: Gráfico comparativo de dos paneles (Graduados Universitarios vs. Empleo Formal Tripartito OIT 2024) con franja de paridad equilibrada (40%-60% EIGE/OIT).
* `ranking_universidades_regional_2022.png`: Top 10 regional de universidades con más graduados en el año común tripartito 2022.
* `desempleo_educacion_superior_regional.png`: Gráfico comparativo de desempleo total vs. población con educación superior por país (2024).

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

### Fase 4: Modelos Predictivos Avanzados y Detección de Quiebres Estructurales
* **Objetivo:** Robustecer las proyecciones temporales para series con más de 5 años observados.
* **Mejora:** Incorporar modelos de series temporales autorregresivos (ARIMA / SARIMAX) y pruebas de raíz unitaria (Dickey-Fuller), junto con algoritmos de detección de quiebres estructurales (Pettitt / Chow test), para alertar ante cambios bruscos en las tendencias de graduación y contratación.

---

## 9. Bitacora de Ejecucion y Control Metodologico (Tandas 1 a 5)

Este apartado sintetiza las decisiones de diseno, correcciones metodologicas y verificaciones tecnicas aplicadas en las 5 tandas de trabajo del modulo, consolidando la trazabilidad formal del observatorio.

### Tanda 1: Eliminacion de datos no observados y hardcodes
* **Objetivo:** Erradicar todo valor simulado, fallback fijo o estimacion no parametrica para asegurar el principio de dato 100% observado.
* **Diagnostico inicial:**
  * Presencia de series salariales y de empleo ficticias para Uruguay (`salarios_ury_sector`, `ury_bench`) atribuidas erroneamente a `UY_INE_ECH`.
  * Factores PPA de respaldo estaticos (`450.0` para Chile, `34.5` para Uruguay).
  * Catalogo manual de 25 instituciones con cifras de egresados inventadas (`catalogo_lideres`).
  * Simulacion de brechas de genero mediante porcentajes fijos (`21.5%`, `12.0%`, `15.8%`).
  * Z-scores forzados a `0.0` ante varianza nula y proyecciones truncadas a cero con `max(0, ...)`.
  * Asignacion incondicional `es_observado = True`.
* **Modificacion realizada:**
  * Supresion completa de `salarios_ury_sector`, `ury_bench` y `catalogo_lideres`.
  * Reemplazo de constantes fijas por celdas vacias (`NaN`) con rotulo explicito de "sin dato observado".
  * Derivacion dinamica de `es_observado` condicionada a la existencia real de observacion (`pd.notna`).
  * Columna `Brecha_Salarial_Genero_Estimada_Pct` fijada en `NaN` preservando tasas observadas de egresadas y empleadas hasta contar con fuentes salariales oficiales.
  * Preservacion de la matematica real en proyecciones con advertencias de tendencia negativa.
* **Resultado antes vs. despues:**
  * *Antes:* Tablas con registros sinteticos de Uruguay, brechas de genero simuladas y rankings institucionales basados en listas en memoria.
  * *Despues:* Cero registros inventados en `hecho_salario.csv` y `hecho_ocupacion_terciarios.csv`; integridad matematica en modelos de proyeccion; rankings universitarios mock suprimidos.

### Tanda 2: Correccion de lectura, agregacion y metricas base
* **Objetivo:** Subsanar errores de parsing numerico, agregaciones temporales, tratamiento de secreto estadistico y definicion unica de PPA.
* **Diagnostico inicial:**
  * En Uruguay (`00._educ_superior_datos.csv`), la falta de `thousands='.'` interpretaba miles como decimales fraccionarios.
  * En Argentina puestos (`puestos_depto_priv_por_clae2.csv`), el codigo `-99` (secreto estadistico) se sumaba algebraicamente restando 76,8M de puestos y la suma de 12 meses multiplicaba por 12 la masa anual de empleo.
  * En salarios CEP-XXI de Argentina, se aplicaba un promedio simple plano entre ramas en lugar de ponderar por masa salarial.
  * En salarios SIES de Chile, se utilizaba `.last()`, seleccionando arbitrariamente una sola carrera por sector y descartando decenas de programas.
  * Alternancia arbitraria via `fillna` entre factor PPA del PIB y Consumo Privado en Argentina.
  * Inexistencia de mecanismo de reconstruccion limpia de cache.
* **Modificacion realizada:**
  * Incorporacion de `thousands='.'` y tipado entero estricto en Uruguay, filtrando por `U_MED == 'Cantidad de personas'`.
  * Descarga e integracion de la serie nacional continua 2007-2023 de puestos por CLAE2 (`puestos_privados_mensual_por_clae2.csv`).
  * Reemplazo de `-99` por `NaN` y estandarizacion de puestos y salarios al promedio mensual observado de cada ano (con metadato explicito `meses_observados = 11` para 2023).
  * Ponderacion de salarios sectoriales por la masa de puestos observados de cada rama CLAE2 para todo el periodo 2007-2023 (Decision D2).
  * Agregacion estadistica sobre la totalidad de los 93 programas de SIES en Chile (media, mediana, minimo y maximo).
  * Adopcion homogenea y unica del factor PPA del PIB (`PA.NUS.PPP` del Banco Mundial) para ARG, CHL y URY para el horizonte 2010-2025 (Decision D1).
  * Implementacion del parametro `force_rebuild` y soporte de linea de comandos `--force` / `-f`.
* **Resultado antes vs. despues:**
  * *Antes:* Egresados de Uruguay con decimales; puestos de Argentina restando 76,8M y multiplicados por 12; salarios de Chile representados por un programa aislado; quiebre de serie PPA en 2022.
  * *Despues:* 768 filas enteras consolidadas en Uruguay (consistentes con Anuario MEC); empleo de Argentina ajustado al stock mensual real; salarios 100% ponderados por puestos; salarios de Chile agregados integralmente; serie PPA del PIB continua para los tres paises.

### Tanda 3: Clasificacion carrera-sector, SIES y paridad metodologica
* **Objetivo:** Resolver el desacople entre carreras y sectores, parsear la estructura multiancabezado de SIES, armonizar niveles educativos y fijar rigor inferencial.
* **Diagnostico inicial:**
  * SIES de Chile leido con encabezado simple omitia la columna de tipo de institucion y mezclaba ingresos del 1er ano con los del 4to ano de egreso.
  * Titulos tecnicos de CFT e IP eran mapeados erroneamente a carreras universitarias de grado e ingenierias, e inversamente ingenierias de IP eran rebajadas a nivel tecnico.
  * Disciplinas de ciencias exactas puras (Quimica y Fisica en Uruguay) asignadas acriticamente al sector Energia.
  * Proyecciones lineales calculadas sobre series de solo 3 puntos y con distribucion normal asintotica fija ($Z = 1.96$).
  * Z-scores sin umbral formal de significancia estadistica.
* **Modificacion realizada:**
  * Reescritura del parser de SIES con doble encabezado (`header=[0, 1]`), capturando tipo de institucion, `ingreso_4to_anio_clp` (Decision D4) y empleabilidad al 1er y 2do ano.
  * Armonizacion estricta de niveles educativos (Decision D5): CFTs y roles auxiliares a nivel `'tecnico'`, IPs desagregados (carreras tecnicas a `'tecnico'` e ingenierias profesionales a `'grado'`), y Universidades a `'grado'`. Prohibicion estricta de asignar titulos tecnicos a ingenierias o medicina de grado.
  * Desvinculacion de ciencias exactas basicas del sector Energia, exigiendo denominaciones explicitas de ingenieria.
  * Umbral estricto de minimo 5 puntos anuales continuos ($n \ge 5$) para proyecciones, aplicando distribucion t-Student con $n-2$ grados de libertad para intervalos de confianza al 95%; series con $n < 5$ rotuladas con `NaN` y advertencia `"No proyectable (n < 5)"` (Decision D7).
  * Umbral estandar $|Z| > 2.0$ ($p < 0.05$) para categorizar variaciones interanuales significativas como expansion o contraccion atipica (Decision D6).
* **Resultado antes vs. despues:**
  * *Antes:* Tecnico Dental clasificado como Odontologia; Ingenieria Industrial de IP degradada a tecnico; proyecciones de Argentina estimadas con 3 puntos; variaciones sin clasificacion de significancia.
  * *Despues:* Casos testigo de SIES validados; cero carreras tecnicas asignadas a ingenierias de grado; proyecciones de Argentina formalizadas como no proyectables; sectores elegibles de CHL y URY proyectados con t-Student; Z-scores evaluados al 95% de confianza.

### Tanda 4: Rankings universitarios y genero desde datos observados
* **Objetivo:** Reconstruir los rankings institucionales y las metricas de genero a partir de fuentes primarias oficiales sin tablas sinteticas.
* **Diagnostico inicial:**
  * En Chile, la columna institucional se descartaba durante el reshape de titulados y se omitian los egresados no binarios.
  * En Argentina, la base Araucano anonimizaba instituciones, pero se disponia de Anuarios Oficiales de la SPU (2020-2022).
  * En Uruguay, los egresos estaban agregados por tipo de gestion, pero el Anuario MEC 2024 desglosaba las instituciones en el Cuadro II-7.1.1.
  * En genero, el agregado `'T'` (Total) se utilizaba en analisis como si fuera una categoria de sexo.
  * Rankings universitarios pausados con DataFrames vacios desde la Tanda 1.
* **Modificacion realizada:**
  * Incorporacion de columna `institucion` en `hecho_egresados.csv` y extraccion de la categoria `NB` (No Binario / Indefinido) observada en Chile.
  * Creacion de `procesar_instituciones_oficiales()` en `cleaning_02.py`, consolidando `hecho_instituciones_egresados.csv` con 6.338 registros y 279 instituciones observadas de SPU (ARG), Mi Futuro (CHL) y MEC (URY) (Decision D9).
  * Algoritmo de rankings institucionales (Decision D10):
    * Top 10 Regional Conjunto (anual reciente y acumulado) de los 5 sectores estrategicos.
    * Top 10 Nacional Ascendente y Descendente por pais, con listado completo de las instituciones existentes para paises con 10 o menos universidades (Uruguay).
  * Normalizacion de genero (Decision D11): Total Graduados $= F + M + NB$, exclusion estricta de `'T'` como variable de sexo y calculo de tasas porcentuales observadas.
* **Resultado antes vs. despues:**
  * *Antes:* Tablas sin trazabilidad institucional; graduados no binarios omitidos; rankings institucionales deshabilitados.
  * *Despues:* `hecho_egresados.csv` con columna `institucion` (173.823 registros); `hecho_instituciones_egresados.csv` con 279 instituciones observadas; `ranking_universidades_regional.csv` y `ranking_universidades_nacional.csv` auditables y completos; genero con categorias `F`, `M`, `NB` observadas.

### Tanda 5: Incorporacion de fuentes nuevas y cierre metodologico
* **Objetivo:** Conectar APIs y datasets oficiales para cubrir vacios de paridad temporal, salarial y de genero supranacional.
* **Diagnostico inicial:**
  * La API de ILOSTAT solo descargaba la serie de PEA (`EAP_TEAP_SEX_AGE_EDU_NB`), sin consultar salarios por rama.
  * Uruguay poseia 0 registros salariales observados en `hecho_salario.csv`, limitando la comparativa salarial regional a dos paises.
  * Columna de brecha salarial por genero vacia (`NaN`) en `analisis_genero_integral.csv` a la espera de serie observada por sexo.
  * Uruguay no contaba con participacion de mujeres en empleo en `hecho_ocupacion_terciarios.csv`.
  * Ausencia del archivo formal de inventario de fuentes `fuentes.yaml`.
* **Modificacion realizada:**
  * Descarga automatizada de la serie `EAR_EMTA_SEX_ECO_NB` de la OIT/ILOSTAT para ARG, CHL y URY con cabecera User-Agent oficial.
  * Funcion `procesar_ilostat_salarios()` en `cleaning_02.py`: mapeo de secciones CIIU Rev. 4 (D: Energia, I: Turismo, J: Tecnologia, M: Economia del Conocimiento, Q: Salud), conversion a USD PPA mediante factor PIB del Banco Mundial e incorporacion de 527 registros OIT a `hecho_salario.csv` (755 filas totales, integrando a Uruguay con 195 filas).
  * Funcion `procesar_uruguay_laboral()` en `cleaning_02.py` procesando la Encuesta Continua de Hogares del INE Uruguay (`10235_...csv`) para derivar `share_mujeres` por rama (Decision T5.3 Opcion A).
  * Comparativa salarial regional bajo enfoque supranacional OIT para el ano comun estricto 2024 en `reporte_brecha_salarial_regional.csv` y grafico `brecha_salarial_regional_multipais.png` (Decision T5.1 Opcion B y T5.2 Opcion B).
  * Reporte complementario `reporte_salarios_detalle_local.csv` preservando el detalle por carrera y rama de CEP-XXI (ARG) y SIES (CHL).
  * Calculo de brechas salariales de genero 100% observadas $((M - F)/M \times 100)$ para 2024 en `analisis_genero_integral.csv` para los 15 estratos (5 sectores x 3 paises) y grafico `brecha_salarial_genero_observada.png`.
  * Creacion del catalogo estructurado `fuentes.yaml` con metadatos, endpoints y licencias de cada fuente.
* **Resultado antes vs. despues:**
  * *Antes:* Uruguay sin salarios observados; comparativa regional sin participacion de Uruguay; brechas salariales de genero vacias; sin archivo de inventario formal.
  * *Despues:* `hecho_salario.csv` con los tres paises observados; comparativa regional tripartita plena; brechas salariales de genero observadas para todos los sectores y paises sin imputaciones; catalogo `fuentes.yaml` formalmente integrado.

### Ronda de Revision Integral por Etapas (Etapas 1 a 7 - Cierre de Plan)
* **Etapa 1 (Glosario y Trazabilidad):** Incorporacion formal de UNESCO UIS (CINE-F 2013) y UNSD (CIIU Rev. 4) en `fuentes.yaml`; depuracion de columnas internas (`version`) en `puente_carrera_sector.csv`; adopcion de `share_mujer` tripartito via OIT/ILOSTAT (`EMP_TEMP_SEX_ECO_NB`); creacion de la Seccion 10 de Diccionario de Datos.
* **Etapa 2 (Cobertura y Paridad Temporal):** Integracion de Anuarios Oficiales SPU 2020-2022 para Argentina en `hecho_egresados.csv`, alcanzando 6 anos observados ($n=6 \ge 5$) en los 5 sectores estrategicos; ventana comun ampliada a 2018-2022; 100% de sectores habilitados para proyeccion con $t$-Student; inclusion del reporte de contexto educativo y desempleo terciario (`reporte_contexto_educativo_laboral.csv`).
* **Etapa 3 (Macro, PPA y Salarios Regionales):** Descarga e integracion de la API oficial del INDEC para la serie de IPC Nacional de Argentina (117 meses observados) armonizada en base comun 2016=100 con Chile y Uruguay; adopcion formal documentada de PPA del PIB (`PA.NUS.PPP`); nivelacion de SIES Chile al ingreso del 1er ano de egreso y empleabilidad al 2do ano; supresion de brechas salariales por genero para focalizar en brechas de graduacion y empleo.
* **Etapa 4 (Universidades y Rankings Homogeneos):** Normalizacion formal de nombres institucionales en Title Case con preservacion UTF-8; unificacion de UdelaR; exclusion metodologica estricta de Centros de Formacion Tecnica (CFT) e Institutos Profesionales (IP) de Chile en rankings universitarios, garantizando comparabilidad de 187 universidades observadas; fijacion del ano comun tripartito 2022 en el Ranking Regional (`ranking_universidades_regional.csv`) y exclusion de Bottom 10 para Uruguay.
* **Etapa 5 (Genero y Estandar EIGE/OIT):** Normalizacion estricta de categorias de genero (`F`, `M`, `NB` y total `T` aislado); asignacion de `NaN` en `NB` para Argentina y Uruguay respetando datos 100% observados sin imputar ceros presuntivos; adopcion formal de la franja de paridad equilibrada 40%-60% bajo estandar internacional EIGE/OIT; exportacion de `reporte_brechas_genero_detallado.csv` (70 filas anualizadas) y grafico comparativo dual de egresados vs. empleo formal.
* **Etapa 6 (Z-Score, Consecutividad y Densidad Profesional):** Calibracion de umbral paritario $|Z| \ge 1.4$ para los 3 paises, superando el limite algebraico de Shiffler en series cortas; validacion estricta de consecutividad temporal ($t - (t-1) = 1$) dejando 2020 en Argentina como vacio observado (`NaN`) con nota explicita de salto temporal; exportacion de `proyecciones_graduados_sector.csv` (30 estimaciones) y creacion del `reporte_densidad_profesional_sector.csv` (140 registros) cruzando egresados universitarios por cada 1.000 ocupados OIT; completamiento de Uruguay en `reporte_salarios_detalle_local.csv` con celdas observadas vacias y advertencia textual; incorporacion de la funcion `verificar_matriz_reportes_3x5()` en el pipeline.
* **Etapa 7 (Verificacion Final y Cierre del Plan):** Auditoria integral de punta a punta del pipeline; cumplimiento 100% verificado del checklist de condiciones (3 paises, 5 sectores, 25 carreras comunes CINE-F, aislamiento en `data_analytics/`, 100% datos observados sin imputaciones, paridad temporal y salarial PPA); erradicacion de emojis no autorizados en scripts (`pipeline.py` e `ingesta_01.py`); ratificacion de proyecciones sectoriales paritarias (Opcion B.1) y consolidacion de las 5 consultas estrategicas interdisciplinarias (incluyendo la Opcion B.2 de Chile como caso testigo/benchmark de datos abiertos).

---

## 10. Diccionario de Datos y Glosario Metodológico

Esta sección documenta formalmente los códigos, clasificadores internacionales y metadatos clave utilizados en el módulo de analítica para garantizar la interpretabilidad y trazabilidad por parte del equipo interdisciplinario y los usuarios finales:

| Campo / Concepto | Tipo de Variable | Definición y Función en el Observatorio |
|---|---|---|
| **cine_f_codigo** | Clasificador Internacional | Código de 4 dígitos de la clasificación CINE-F 2013 de la UNESCO (Clasificación Internacional Normalizada de la Educación: Campos de Educación y Capacitación). Permite homologar carreras universitarias con denominaciones dispares entre Argentina, Chile y Uruguay bajo un mismo estándar formativo internacional. |
| **ciiu_rev4_divisiones** | Clasificador Internacional | Códigos de dos dígitos de las divisiones de la CIIU Rev. 4 (Clasificación Industrial Internacional Uniforme de la ONU / CLAE a 2 dígitos en Argentina / ISIC Rev. 4 en OIT). Agrupa las actividades económicas formales que componen cada uno de los 5 sectores estratégicos del proyecto. |
| **peso** | Metadato de Correspondencia | Ponderador numérico (por defecto 1.0) en la matriz carrera-sector que define la proporción de graduados de una carrera que tributan a determinado sector. Un valor de 1.0 indica asignación completa (100%). |
| **tipo_vinculo** | Metadato de Gobernanza | Jerarquía de correspondencia formativo-laboral entre la carrera y el sector. El valor `'principal'` indica correspondencia primaria y directa de egreso. |
| **justificacion** | Metadato de Auditoría | Explicación textual auditable que explicita el criterio metodológico adoptado para vincular una carrera a un sector específico y su paridad de nivel. |
| **share_mujer** | Métrica Laboral | Cuota o proporción (expresada en tanto por uno de 0 a 1, o en porcentaje) de mujeres ocupadas sobre el total de puestos de trabajo en una rama o sector de actividad económica. Obtenida de forma observada vía OIT/ILOSTAT para los 3 países. |
| **zscore_dinamismo** | Métrica Estadística | Indicador estandarizado que mide la aceleración o desaceleración interanual de graduados respecto al promedio histórico del sector: $Z = (\text{var} - \mu) / \sigma$. Permite detectar si el dinamismo de un año es ordinario o anómalo. |
| **es_desvio_significativo** | Indicador Booleano | Bandera de alerta estadística. Toma valor `True` cuando el Z-score en valor absoluto es mayor o igual a 1.4 ($|Z| \ge 1.4$), umbral homogéneo adoptado para series de tamaño moderado/corto que garantiza paridad metodológica y permite detectar shocks históricos reales en los 3 países sin sesgo por longitud de serie. |
| **nota_consecutividad** | Metadato Temporal | Verificación de estricta consecutividad temporal ($t - (t-1) = 1$ año). Si una serie presenta una vacancia (como 2020 en Argentina tras la ausencia de 2019), el campo reporta `'Ano anterior no observado (salto temporal sin 2019)'` y la tasa interanual queda vacía (`NaN`), impidiendo que una tasa bienal se compute como anual. |
| **graduados_por_mil_ocupados** | Indicador Formativo-Laboral | Métrica de densidad profesional y renovación de capital humano: $\frac{\text{Graduados Anuales}}{\text{Personas Ocupadas (OIT)}} \times 1.000$. Expresa cuántos graduados universitarios genera el sistema educativo por cada 1.000 trabajadores activos en cada sector económico. |
| **ipc_base_2016** | Índice de Precios Armonizado | Serie oficial de IPC armonizada con base común tripartita $2016 = 100.0$ para Argentina (INDEC serie 145.3), Chile (Banco Mundial WDI) y Uruguay (Banco Mundial WDI). Permite comparar la evolución de precios acumulada desde el año común 2016 sin sesgos por bases dispares. |
| **ingreso_1er_anio_clp (SIES)** | Remuneración Muestral | Ingreso bruto promedio mensual en Pesos Chilenos al 1er año de egreso universitario o técnico publicado por SIES. Representa el salario de inserción laboral formal inicial de los titulados ante el SII, a moneda constante de septiembre de 2024. |
| **empleabilidad_2do_anio (SIES)** | Indicador de Inserción Laboral | Proporción de egresados de la educación superior que se encuentran ocupados de forma regular con cotización previsional al segundo año de haber recibido su título (fuente oficial SIES). |
| **salario_usd_ppa** | Moneda Homologada | Salario mensual convertido a Dólares Internacionales de Paridad de Poder Adquisitivo (USD PPA) utilizando el factor PPA del PIB del Banco Mundial (`PA.NUS.PPP`), lo que permite comparar el poder de compra real entre Argentina, Chile y Uruguay en un mismo año común (2024) sin distorsiones cambiarias locales. |
| **metodo_ppa** | Estándar de Conversión | Identificador metodológico explícito (`PPA_PIB_PA.NUS.PPP`). Se adopta la paridad del PIB debido a que es la única serie supranacional oficial con cobertura observada continua 2022-2024 para los 3 países (la serie de consumo privado fue discontinuada para Argentina por el Banco Mundial tras 2021). |
| **Semaforo_Prioridad_Formativa_Predictiva** | Métrica de Planificación Educativa | Recomendación de asignación de recursos formativos derivada de la pendiente de crecimiento proyectada a 5 años ($t$-Student) de graduados por sector, identificando cuellos de botella formativos (Alta Prioridad) frente a sectores con oferta en expansión (Baja Prioridad). |
| **paridad_eige_oit** | Estándar Internacional de Género | Criterio normativo de equilibrio de género adoptado por el Instituto Europeo para la Igualdad de Género (EIGE) y la Organización Internacional del Trabajo (OIT). Define como "Zona de Paridad Equilibrada" cualquier participación de un sexo comprendida entre el 40% y el 60% ($40\% \le \text{participación} \le 60\%$). Valores menores al 40% se clasifican como sub-representación / masculinización y mayores al 60% como concentración / segregación femenina. |
| **categoria_genero** | Clasificación Armonizada | Estandarización de categorías: `F` (femenino), `M` (masculino), `NB` (no binario / indefinido, observado en Chile 2025) y `T` (total ambos sexos como control volumétrico de egresados). Para fuentes sin apertura no binaria (Araucano o ILOSTAT), el campo se mantiene estrictamente como `NaN` (no disponible) sin imputar ceros presuntivos. |

---

## 11. Taxonomía de Fuentes: Datos Fríos (Históricos) vs. Datos Calientes (Dinámicos) y Arquitectura de Actualización

Con el fin de planificar la automatización y calendarización del observatorio en fases posteriores (cron jobs, orquestadores en la nube y backend), las fuentes se clasifican formalmente en dos naturalezas operativas según su frecuencia de publicación y ventana de consolidación oficial:

### 1. Datos Fríos / Históricos (Consolidación Administrativa Anual)
* **Naturaleza:** Balances estadísticos ministeriales y universitarios oficiales (Anuarios SPU de Argentina, Bases de Titulados Mi Futuro de Chile, Anuarios Estadísticos de Educación MEC y UdelaR de Uruguay).
* **Frecuencia de publicación:** 1 vez al año, usualmente con un rezago administrativo de 12 a 24 meses debido a los tiempos de consolidación, validación y auditoría de los ministerios nacionales.
* **Comportamiento en el Pipeline:** Una vez procesados, sus agregaciones y tablas de hechos son inmutables para los años ya cerrados. Se apoyan en el sistema de cachés `.csv` en `data/processed/` para evitar re-lecturas de planillas pesadas (30 a 50 MB) en cada corrida diaria.
* **Estrategia de Programación:** Ejecución programada de revisión semestral o anual (ej. revisión en junio y diciembre), o disparo manual únicamente cuando los ministerios publican un nuevo anuario cerrado.

### 2. Datos Calientes / Dinámicos (APIs Supranacionales y Series de Coyuntura)
* **Naturaleza:** APIs REST directas y relevamientos periódicos de mercado laboral y macroeconomía:
  * **Banco Mundial:** Factores PPA (`PA.NUS.PPP`), deflactores e IPC.
  * **CEPALSTAT:** Matrícula superior, desempleo y demografía juvenil.
  * **ILOSTAT (OIT):** Salarios medios mensuales por rama y sexo (`EAR_EMTA_SEX_ECO_NB`) y ocupación formal (`EMP_TEMP_SEX_ECO_NB`).
  * **CEP-XXI:** Series mensuales de salarios y puestos por rama CLAE2.
* **Frecuencia de actualización:** Mensual, trimestral o semestral, con publicación inmediata sin intermediación manual.
* **Comportamiento en el Pipeline:** El módulo `ingesta_01.py` las consulta directamente y actualiza las series de contexto macro y salarial de forma liviana (< 10 segundos).
* **Estrategia de Programación:** Apta para cron jobs periódicos (semanales o mensuales) que regeneran reportes de coyuntura (`reporte_brecha_salarial_regional.csv`, `analisis_genero_integral.csv`) sin necesidad de reprocesar las series históricas de graduados.

