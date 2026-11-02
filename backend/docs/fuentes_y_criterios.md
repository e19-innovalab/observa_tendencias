# Fuentes y criterios del Observatorio (indicadores e ISE)

Qué datos usa hoy el backend de Observa Tendencias, de dónde salen, cómo se consultan y con qué criterios se
calculan los indicadores, las tendencias, las proyecciones y el Índice Sintético de Empleabilidad
(ISE), y los indicadores temáticos (Moctezuma, Ludita, Reina Roja, Sísifo, Brecha generacional y
burbujas de Tendencias). Estado al 01/11/2026.

Todo lo que se describe acá está en archivos de configuración: no hay valores fijos en el código.
Si cambia un criterio, cambia en el archivo indicado en cada sección y este documento debe
actualizarse.

| Archivo | Contenido |
|---|---|
| `backend/config/sources.yaml` | Fuentes, URLs, frecuencia esperada, opciones de cada conector, reintentos HTTP |
| `backend/config/indicators.yaml` | Indicadores y las series de cada fuente que los alimentan |
| `backend/config/catalog.yaml` | Países, sectores, universo de ocupaciones, ocupaciones destacadas, reglas de nombres |
| `backend/config/analytics.yaml` | Metodología: ISE, tendencias, proyecciones, alertas e indicadores temáticos |
| `backend/config/app.yaml` | Etiquetas, tarjetas de Inicio, paginación, rangos y definiciones que muestra la API |
| `backend/config/reference/` | Tablas de referencia citadas (ocupaciones CIUO-08 y definiciones de sus grandes grupos, exposición a IA de la OIT, series históricas de Moctezuma y Ludita) |
| `backend/.env` | Secretos y valores por entorno (base de datos, CORS, API key) |

---

## 1. Fuentes

### 1.1 Fuentes con conector activo

| Fuente | Tipo | Qué aporta | Países | Autenticación | Frecuencia esperada |
|---|---|---|---|---|---|
| World Bank Indicators API | API REST (JSON) | Indicadores socioeconómicos, laborales y educativos | ARG, URY, CHL | No | Semanal |
| ILOSTAT (OIT) | API SDMX (CSV) | Desocupación, empleo e ingresos por sector y por ocupación | ARG, URY, CHL | No | Semanal |
| Datos Argentina, Series de Tiempo | API REST (JSON) | IPC, EMAE y EPH trimestral (INDEC) | ARG | No | Diaria |
| OIT, exposición a la IA generativa (WP 140) | Tabla de referencia | Exposición de cada ocupación a la IA generativa | Igual para los 3 | No aplica | Estática |
| ESCO (Comisión Europea) | API REST (JSON) | Habilidades y conocimientos de cada ocupación CIUO-08 | Igual para los 3 | No | Revisión mensual (versiones aprox. anuales) |
| SIMEL (INE Chile) | API SDMX (CSV) | Ocupados por gran grupo ocupacional (Encuesta Nacional de Empleo) | CHL | No | Mensual (trimestres móviles) |
| INE Uruguay | Archivo oficial (XLSX), descarga automática | IPC total país y variaciones, mensual desde 1937 | URY | No | Mensual |
| Mi Futuro, titulados (MINEDUC, Chile) | Archivo oficial (XLSX), descarga automática | Titulaciones de educación superior por programa, 2007 en adelante | CHL | No | Anual (se revisa semanalmente) |
| SIPA, trabajo registrado (Secretaría de Trabajo) | Archivo oficial (XLSX), descarga automática | Asalariados registrados del sector privado por rama, mensual desde 2009 | ARG | No | Mensual |
| O*NET Technology Skills, por versión (EE. UU.) | Archivo oficial (ZIP), descarga automática | Tecnologías que usa cada ocupación, versiones 25.1 (2020) a 31.0 (2026), para el indicador Reina Roja | Igual para los 3 | No | Anual |
| ESCO, por versión (Comisión Europea) | API REST (JSON) | Habilidades de cada ocupación en las versiones v1.0.9 a v1.2.1, para el indicador Reina Roja | Igual para los 3 | No | Anual |

#### World Bank Indicators API

- **Documentación:** https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- **Base URL:** `https://api.worldbank.org/v2`
- **Consulta:** `GET /country/ARG;URY;CHL/indicator/{id}?format=json&per_page=1000&date=2000:{año actual}&page={n}`
- **Respuesta:** `[metadatos, filas]`. `metadatos.lastupdated` se guarda como fecha de actualización de la fuente.
- **Ejemplo:** https://api.worldbank.org/v2/country/ARG;URY;CHL/indicator/SL.UEM.1524.ZS?format=json&per_page=1000&date=2020:2025

#### ILOSTAT (OIT)

- **Documentación:** https://ilostat.ilo.org/resources/sdmx-tools/
- **Base URL:** `https://sdmx.ilo.org/rest`
- **Consulta:** `GET /data/ILO,{dataflow},1.0/{key}?startPeriod=2000`
- **Header obligatorio:** `Accept: application/vnd.sdmx.data+csv;version=1.0.0`
- **Clave:** en `{key}`, `{countries}` se reemplaza por `ARG+URY+CHL`.
- **Ejemplo:** `https://sdmx.ilo.org/rest/data/ILO,DF_EMP_TEMP_SEX_OC2_NB,1.0/ARG+URY+CHL.A..SEX_T.?startPeriod=2022` (con el header de arriba).
- **Cuidado con Argentina:** la OIT procesa la EPH de INDEC, que solo cubre los 31 aglomerados urbanos. Cada fila de Argentina dice `"Geographical coverage: Main cities or metropolitan areas"`. Los totales son urbanos y, a 2 dígitos de ocupación, la muestra es chica y varía mucho de un año a otro.
- **Cuidado con Chile:** el empleo por ocupación a 2 dígitos solo tiene datos dispersos (en los últimos años, 2020 y 2022), de la encuesta CASEN.

#### Datos Argentina, Series de Tiempo

- **Documentación:** https://datosgobar.github.io/series-tiempo-ar-api/
- **Buscador de series:** https://apis.datos.gob.ar/series/api/search/?q=desocupacion
- **Base URL:** `https://apis.datos.gob.ar/series/api`
- **Consulta:** `GET /series/?ids={id}&start_date=2003-01-01&limit={n}&start={offset}`. Para agregar a años se suma `&collapse=year&collapse_aggregation=avg`, que solo devuelve años completos.
- **Una serie por pedido:** si se piden varias juntas, la API las lleva a la frecuencia más baja.
- **Caché con respuestas viejas:** la API guarda en caché cada URL exacta y algunas respuestas están desactualizadas. Períodos que tienen datos vuelven vacíos: en la EPH de desocupación faltaban 37 de 93 trimestres.
  - **Solución:** el conector lee cada serie 5 veces con distinto `limit` (`reads` en `sources.yaml`), con lo que cada lectura cae en otra entrada de la caché, y combina los valores no vacíos.
- **Variación interanual calculada por el conector:** no se usa `representation_mode`. La fórmula es `valor / valor del mismo período un año antes − 1`.

#### OIT: exposición ocupacional a la IA generativa

- **Fuente:** Gmyrek, P., Berg, J., Kamiński, K., Konopczyński, F., Ładna, A., Nafradi, B., Rosłaniec, K., Troszyński, M. (2025). *Generative AI and Jobs: A Refined Global Index of Occupational Exposure*. ILO Working Paper 140. https://doi.org/10.54394/HETP0387 · [PDF](https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf)
- **Qué se usa:** las 427 filas del Anexo, Tabla A1 (media, desvío y gradiente por ocupación CIUO-08 de 4 dígitos). Están en `config/reference/ilo_genai_exposure.yaml`.
- **Cómo se verificó:** la extracción del PDF reproduce los totales del paper (427 ocupaciones, 13 en el gradiente 4, 112 expuestas), y 20 valores se cotejaron a mano.
- **Qué mide** (sección 3.1 del paper): cada tarea tiene un puntaje de 0 (*no se puede automatizar*) a 1 (*la IA generativa podría hacerla sola, sin una persona*), y el valor de la ocupación es el promedio de sus tareas. Observado: de 0,09 (oficios de la construcción) a 0,70 (grabadores de datos).
- **Gradientes** (Tabla 5 del paper; μ = media, σ = desvío):
  - **Gradiente 4:** μ ≥ 0,6 y μ − σ ≥ 0,5.
  - **Gradiente 3:** 0,5 ≤ μ < 0,6 y μ + σ ≥ 0,5.
  - **Gradiente 2:** 0,4 ≤ μ < 0,5 y μ + σ ≥ 0,5.
  - **Gradiente 1:** μ < 0,4 y μ + σ ≥ 0,5.
  - **Exposición mínima:** μ < 0,5 y μ + σ > 0,4.
  - **No expuesta:** el resto.
- **Uso:** no varía por país; se guarda igual para ARG, URY y CHL. Se usa como aproximación del "riesgo de automatización", con la aclaración de que la exposición incluye tanto tareas que la IA podría reemplazar como tareas que podría complementar.

#### ESCO: habilidades por ocupación (Comisión Europea)

- **Documentación:** https://ec.europa.eu/esco/api/doc/esco_api_doc.html
- **Base URL:** `https://ec.europa.eu/esco/api`. Pública, sin clave; se consulta en español (`language=es`).
- **Consulta:**
  1. `GET /resource/concept?uri=http://data.europa.eu/esco/isco/C{código}` lista las ocupaciones ESCO de cada grupo CIUO-08 de 4 dígitos.
  2. `GET /resource/occupation?uri=...` da las habilidades esenciales y opcionales de cada una.
- **Peso de una habilidad en un grupo CIUO:** el promedio, entre las ocupaciones ESCO del grupo, de 1 si es esencial, 0,5 si es opcional y 0 si no figura (`relation_weights` en `sources.yaml`).
- **Categoría de la relación (`occupation_skills.relation`):** *esencial* si la habilidad es esencial para al menos una ocupación ESCO del grupo; si no, *opcional* (`relation_categories` en `sources.yaml`). Se usa la categoría de ESCO, no un porcentaje del peso.
- **Jerarquía y definiciones (`app/skills/esco_hierarchy.py`):** cada habilidad guarda su definición (en español; si ESCO no la tiene, en inglés) y su grupo de la jerarquía de ESCO (`skills.group_code`, tabla `skill_groups`): S para habilidades (S2 > S2.2 > S2.2.1), A actitudes, L idiomas, T transversales; los conocimientos siguen los campos CINE-F (04 > 041 > 0412). Se usa el nivel `skill_gaps.group_level` de `analytics.yaml` (hoy 3). Se actualiza con cada carga de ESCO o con `python -m app.jobs.esco_hierarchy`. Algunos registros de ESCO devuelven error del servidor siempre; se omiten y se listan.
- **Descripciones en español:** cada descripción guarda el original en inglés de ESCO (`description_en`) y el texto en español que se muestra (`description`), con su origen (`description_origin`): `esco` si ESCO la publica en español (todas las habilidades) o `translation` si viene de `config/reference/esco_traducciones_es.yaml`. Ese archivo es el documento fuente de las traducciones: para cada grupo tiene el texto en inglés exactamente como lo devuelve la API de ESCO y su traducción; es propia del equipo, no oficial, y está sin revisar (`reviewed: false`). Una traducción solo se usa mientras su original coincida con el texto actual de ESCO; si ESCO lo cambia, vuelve a mostrarse el inglés hasta actualizarla. Hoy: 488 grupos traducidos, 3 con español de ESCO y 49 sin descripción en ESCO.
- **Brechas por grupo (`skill_group_gaps`):** el mismo método que por habilidad, sobre las ocupaciones que usan alguna habilidad del grupo; en cada ocupación el grupo pesa lo que su habilidad más fuerte. Sirve para no mostrar cuatro versiones casi iguales del mismo tema con brechas distintas.
- **Ocupaciones ESCO detrás de cada relación (`occupation_skills.via`):** para cada grupo CIUO y habilidad se guardan las ocupaciones de ESCO del grupo que la usan y cómo. Explica casos que parecen raros: "asesorar e informar sobre ganado" es esencial para el grupo 7515 (catadores y clasificadores de alimentos y bebidas) porque ESCO pone ahí al "controlador de leche de granja"; ESCO no se la asigna al "ganadero" (6121), que solo tiene como opcional "asesorar sobre la productividad del ganado". La página lo muestra como "vía …".
- **Habilidades por sector:** una habilidad es de un sector si es **esencial** para alguna de sus ocupaciones (`skills.sector_relation` en `app.yaml`); con "También opcionales" se suman las opcionales. Si es esencial en dos o más sectores es **transversal**. Ejemplo: "aconsejar sobre la preparación de alimentos de dieta" es esencial para dietistas (Salud) y opcional para cocineros (Turismo). La brecha de una habilidad se calcula siempre con todas las ocupaciones que la usan, de todos los sectores.
- **Carga del 18/10/2026:**
  - 11.551 habilidades (2.580 conocimientos y 8.971 habilidades o competencias).
  - 424 de los 431 grupos aplicables, con 44.374 relaciones.
- **Sin habilidades en ESCO:**
  - 1321 y 2142: su única ocupación ESCO devuelve error del servidor.
  - 2240, 3221, 4414, 7549 y 9624: ESCO no detalla ocupaciones para esos grupos.
- **Registros con error:** se omiten y se listan en la corrida. Si fallan más de `max_failed_share` (2 %), no se reemplaza nada.
- **Uso:** ESCO no varía por país; las mismas relaciones valen para los tres. Tablas `skills` y `occupation_skills`.

#### Versiones de O*NET y ESCO (indicador Reina Roja)

Conector `skill_versions` (`app/skills/versions.py`); configuración en `sources.yaml → onet_technology`
y `esco_versions`. Guarda el perfil de cada ocupación CIUO-08 en cada versión (tabla `skill_profiles`):
no reemplaza versiones anteriores.

- **O*NET (Technology Skills):**
  - Base de datos de cada versión: `https://www.onetcenter.org/dl_files/database/db_{versión}_text.zip`,
    archivo `Technology Skills.txt`, columna `Example`. En la 31.0 O*NET lo renombró a
    `Software Skills.txt`, columna `Workplace Example` (se configura por versión en `releases`).
  - Las ocupaciones de EE. UU. (O*NET-SOC 2019) se llevan a CIUO-08 con el cruce oficial
    ESCO–O*NET: https://www.onetcenter.org/crosswalks/esco/ESCO_to_ONET-SOC.xlsx. Una ocupación CIUO
    reúne las tecnologías de todas sus ocupaciones O*NET.
  - Los ZIP originales quedan en `data/raw/datasets/onet/`.
  - Versiones cargadas: 25.1 (11/2020), 26.0, 27.0, 28.0, 29.0, 30.0 y 31.0 (08/2026).
- **ESCO:** la misma API de la sección anterior, con `selectedVersion` y en inglés (los nombres
  comparables entre versiones). Versiones: v1.0.9 (11/2021), v1.1.1 (09/2022), v1.2.0 (05/2024) y
  v1.2.1 (12/2025).
- **Nuevas versiones:** se agregan en `releases` con su fecha de publicación.

#### SIMEL: Sistema de Información del Mercado Laboral (INE Chile)

- **Guía de uso y API:** https://www.ine.gob.cl/simel/guia-de-uso
- **Base URL:** `https://sdmx.ine.gob.cl/rest`, agencia `CL01`.
- **Consulta:** `GET /data/CL01,{dataflow},1.0/{key}?startPeriod=2017-01`, con el header `Accept: application/vnd.sdmx.data+csv;version=1.0.0`.
- **Qué se usa:** `DF_OCUCIUO_CIUO_SEXO` con clave `M.OCUCIUO._T..AS`: ocupados según gran grupo ocupacional CIUO-08.CL (1 dígito), total nacional, ambos sexos. Encuesta Nacional de Empleo, desde enero-marzo de 2017.
- **Ejemplo:** https://sdmx.ine.gob.cl/rest/data/CL01,DF_OCUCIUO_CIUO_SEXO,1.0/M.OCUCIUO._T..AS?startPeriod=2024-01 (con el header de arriba).
- **Períodos:** trimestres móviles (`2026-04-01/P3M` = abril-junio). El valor anual es el promedio de los 4 trimestres calendario (enero-marzo, abril-junio, julio-septiembre, octubre-diciembre), solo para años completos.
- **Calidad:** no se cargan las estimaciones marcadas por el INE como `X` (no fiable) ni `Y` (poco fiable), según el código `CL_OBS_STATUS`.
- **Unidad:** personas, que se pasan a miles (`scale: 0.001`).
- **Por qué SIMEL y no ILOSTAT para Chile:** ILOSTAT solo tiene el empleo de Chile por ocupación hasta 2022 y con huecos. La serie de ILOSTAT por ocupación se restringe a Argentina y Uruguay (`countries` en `indicators.yaml`), para no mezclar en una misma serie grupos de 2 dígitos con grupos de 1 dígito.

#### INE Uruguay: Índice de Precios del Consumo

- **Página oficial:** https://www.ine.gub.uy/ipc-indice-de-precios-del-consumo
- **Archivo:** `IPC gral y variaciones_base 2022.xlsx` (base octubre 2022 = 100), en `www5.ine.gub.uy`. INE lo actualiza todos los meses **con la misma URL**, así que el perfil lo descarga siempre (`always_download`) y lo compara por checksum: si no cambió, no carga nada.
- **Qué se usa:** la columna "Acum.12 meses", la variación respecto del mismo mes del año anterior, para `inflation_monthly_yoy` de Uruguay. Hay datos desde 1938 (los primeros 12 meses de la serie no tienen variación) hasta 09/2026.
- **Certificado del sitio:** los servidores del INE envían un certificado intermedio equivocado, y desde Python no se pueden verificar con el conjunto estándar. Se agregó el intermedio correcto (Sectigo DV R36, descargado de la dirección que figura en el propio certificado) en `config/certs/`, declarado en `sources.yaml → http.extra_ca_files`. La verificación sigue activa hasta la raíz.
- **Perfil:** `config/datasets/ine_uy_ipc.yaml`.

**Encuesta Continua de Hogares (empleo):** INE Uruguay no publica las series de la ECH como un archivo descargable estable: tiene boletines HTML y un tablero interactivo (Shiny) que no se puede consumir. Los datos laborales de Uruguay ya vienen de su encuesta nacional a través de ILOSTAT, que procesa la ECH: cada fila dice `"LFS - Encuesta Continua de Hogares"`. Llegan hasta 2025 e incluyen el desglose por ocupación.

#### Mi Futuro: titulados de educación superior (MINEDUC, Chile)

- **Página oficial:** https://www.mifuturo.cl/bases-de-datos-titulados/ (Servicio de Información de Educación Superior, SIES).
- **Archivo:** `TITULADO_2007-<último año>_web_<fecha>_E.xlsx`, con la serie completa. La versión cargada es `TITULADO_2007-2025_web_27_05_2026_E-1.xlsx` (41 MB, 234.074 filas, una por programa, institución y año). El enlace se busca en la página con el patrón del perfil, y el archivo de un solo año no se usa.
- **Qué se usa:** se suman las titulaciones (`TOTAL TITULACIONES`) por carrera genérica (`ÁREA CARRERA GENÉRICA`), nivel (`NIVEL GLOBAL`) y año (`AÑO`, por ejemplo `TIT_2025`). Se guarda también el área y la subárea CINE-F 2013 más frecuente de cada carrera.
- **Resultado:** 277 carreras de pregrado, más posgrado y postítulo, de 2007 a 2025, en la tabla `graduates`. Son 3.291.292 titulaciones de pregrado, que coinciden con el total del archivo.
- **Control de formato:** las 42 columnas exactas, años desde 2007, al menos 15 años y valores no negativos. Las cifras de años anteriores a los últimos 3 no pueden cambiar más de 10 %.
- **Perfil:** `config/datasets/mifuturo_titulados.yaml`.

#### Indicadores CTI: estudiantes y egresados universitarios por área OCDE (Argentina)

- **Página oficial:** https://www.argentina.gob.ar/ciencia/indicadores-cti/datasets/dataset-estudiantes-y-egresados-nivel-superior-por-areas-de-ocde (Subsecretaría de Ciencia, Tecnología e Innovación, con datos del Departamento de Información Universitaria).
- **Archivo:** `00._educ_superior_datos.csv` (separador `;`, codificación latin-1, miles con punto). Se actualiza en el mismo lugar, así que se descarga siempre y se compara el contenido.
- **Qué se usa:** las filas con `TIPO_ALUMNO = EGRESADOS`, sumadas por disciplina específica (`DISCIP_ESPECIF`), nivel académico (`NIVEL_ACADEM`: Grado y Pregrado) y año.
- **Resultado:** 1.060 filas, de 2014 a 2023. En 2023 hubo 138.799 egresados de grado y pregrado.
- **Limitaciones:** solo universidades: los institutos terciarios no universitarios no están en el archivo. La unidad es la disciplina (37), mucho más amplia que la carrera genérica de Chile: "Ingeniería" agrupa todas las ingenierías.
- **Perfil:** `config/datasets/arg_egresados_universitarios.yaml`.

#### Anuario Estadístico del Sistema Universitario: egresados por disciplina (DIU, Argentina)

- **Página oficial:** https://www.argentina.gob.ar/educacion/universidades/informacion/publicaciones/anuarios (Departamento de Información Universitaria, Secretaría de Educación). Cada anuario es un `.zip` con planillas; a veces sale primero un "adelanto" parcial.
- **Para qué:** es la misma información que el archivo de Indicadores CTI (comparado en 2023: idéntico en las 37 disciplinas), pero se publica antes. Se usan solo los anuarios desde 2024 y solo para los años que el archivo CTI todavía no tiene (`skill_gaps.supply_supplements` en `analytics.yaml`). Si el archivo CTI publica ese año, manda el CTI.
- **Qué se usa:** en las planillas "Pregrado y Grado Gestión Estatal" y "Gestión Privada", los cuadros de estudiantes, nuevos inscriptos, reinscriptos y egresados por disciplina (2.1.14 a 2.1.18a y 2.2.14 a 2.2.18a): la columna de egresados (EGR en 2023, EGRE en 2024) de la fila de total de cada disciplina, sumando gestión estatal y privada.
- **Archivo cargado:** `adelanto_anuario_24_14-08.zip`, adelanto parcial del Anuario 2024, con planillas fechadas el 14/08/2026 (el servidor lo marca modificado el 18/08/2026). El anuario final 2024 puede corregir las cifras: si se publica, reemplaza el año 2024 y los cambios quedan en el historial de revisiones.
- **Control:** las disciplinas tienen que sumar el total de egresados del propio anuario (cuadros 2.1.4 y 2.2.4, fila "Total Instituciones"); una diferencia de hasta 1 % es un aviso. 2024: 145.235 egresados (96.183 estatales + 49.052 privados), igual al total del anuario.
- **Pregrado y grado juntos (estimación):** el anuario da cada disciplina sin separar pregrado de grado. Para calcular las brechas se reparte con la proporción de esa disciplina en el último año del archivo CTI que la tiene (hoy 2023). Es una estimación hasta que el CTI publique el año con el detalle.
- **Perfil:** `config/datasets/arg_anuario_diu_egresados.yaml` (lector de cuadros por disciplina, `app/datasets/reader.py`).

#### Anuario Estadístico de Educación: egresados universitarios por carrera (MEC, Uruguay)

- **Página oficial:** https://www.gub.uy/ministerio-educacion-cultura/datos-y-estadisticas/datos (División de Investigación y Estadística, Dirección Nacional de Educación). La lista enlaza una página por anuario, y cada página enlaza su planilla.
- **Archivos:** un anuario por año, como `.xlsx` desde 2020 (los anteriores no tienen planilla). Cada año se descarga de su propia página y reemplaza solo los datos de ese año. Un año nuevo aparece solo cuando el MEC lo agrega a la lista.
- **Qué se usa:** las hojas II-7.2.1 (universidades públicas: UdelaR y UTEC), II-7.2.2 (universidades privadas) y II-7.2.3 (institutos universitarios), columna H (total de egresados). Cada hoja anida institución › facultad › sede › carrera: los encabezados están en negrita y las carreras no. Las carreras con el mismo nombre se suman entre instituciones y sedes.
- **Resultado:** 7.601 egresados de grado en 2020, 8.774 en 2021, 8.812 en 2022, 8.809 en 2023 y 9.117 en 2024, con 534 nombres de carrera distintos.
- **Control de formato:** las tres hojas, el año del título igual al de la página, la fila de total y que las carreras sumen ese total. Una diferencia de hasta 2 % es un aviso y una mayor bloquea la carga: en 2024, universidades privadas, dos carreras están vacías mientras su sede las cuenta (23 de 2.321 egresados).
- **Limitaciones:** solo universidades: la formación docente (ANEP) y la terciaria no universitaria (UTU) están en otras hojas y todavía no se usan. Los egresados de UdelaR del último año son preliminares.
- **Perfil:** `config/datasets/mec_uy_egresados_grado.yaml`.

#### SIPA: situación y evolución del trabajo registrado

- **Página oficial:** https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado
- **Archivo:** anexo estadístico mensual `trabajoregistrado_<AAMM>_estadisticas.xlsx`, en `https://www.argentina.gob.ar/sites/default/files/`. Ejemplo: `trabajoregistrado_2607_estadisticas.xlsx` es julio de 2026.
- **Cómo se encuentra:** el nombre cambia cada mes, así que se busca el enlace en la página oficial con el patrón del perfil. Solo se acepta el host `www.argentina.gob.ar`.
- **Qué se usa:** hoja `A.2.1`, asalariados registrados del sector privado por rama de actividad, serie original, en miles.
- **Formato del archivo:**
  - Los períodos son fechas hasta enero de 2015 y después texto como `feb-15`.
  - Los meses provisorios llevan `*`.
  - Después de los datos vienen notas al pie.
- **Sectores:** las ramas son secciones CIIU **Rev.3**. Solo coinciden una a una con el catálogo Turismo (Hoteles y restaurantes), Salud (Servicios sociales y de salud) y Energía (Suministro de electricidad, gas y agua), además del total. Tecnología y Economía del conocimiento están dentro de secciones más amplias y no se separan.
- **Perfil:** `config/datasets/sipa_asalariados_por_rama.yaml`.

### 1.2 Fuentes declaradas sin conector todavía

CEPALSTAT y Banco Central de Chile. Están en `sources.yaml` para la trazabilidad y
para tener la estructura lista, pero todavía no se consultan.

Revisados y descartados por ahora como archivo descargable (17/10/2026):

| Dataset | Motivo |
|---|---|
| Empleabilidad e ingresos por carrera (Mi Futuro, MINEDUC); los titulados sí se usan (ver 1.1) | Se publica solo como [buscador interactivo](https://www.mifuturo.cl/buscador-de-empleabilidad-e-ingresos/) con su [metodología](https://mifuturo.cl/wp-content/uploads/2025/12/Metodologia-Buscador-Empleabilidad-e-Ingresos_2025-2026.pdf). Las [bases de datos](https://www.mifuturo.cl/bases-de-datos/) cubren matrícula y titulados, no empleabilidad. |
| Ocupados por grupo de ocupación (ENE, INE Chile) como archivo | La [página](https://www.ine.gob.cl/estadisticas-por-tema/mercado-laboral/ocupacion-y-desocupacion) publica boletines y microdatos, no un cuadro descargable por grupo. Se resolvió con la API de SIMEL (ver 1.1). |

### 1.3 Datos que no son estadística oficial

Se muestran siempre con su aviso (`notices` en `app.yaml`). **No entran en el ISE.**

| Dataset | Origen | Alcance |
|---|---|---|
| Ofertas de LinkedIn | Búsquedas de Apify del equipo de Data Analytics | 640 avisos del 6 al 13/10/2026, solo Buenos Aires, Córdoba y Santa Fe. Clasificados por reglas. |
| Egresados y proyecciones | SIES (Chile) y datos.gob.ar (Argentina), procesado por Data Analytics | 19 carreras seleccionadas. Cuenta egresados; no tiene tasa de inserción laboral. Para las brechas se usa la base oficial completa de Mi Futuro (277 carreras). |

### 1.4 Archivos oficiales: descarga automática y carga manual

Cada archivo que se lee, descargado o cargado a mano, pasa por el mismo control antes de tocar la
base, y queda registrado en `dataset_files` con su URL, versión, checksum, ubicación y reporte.

**Perfiles** (`config/datasets/*.yaml`). Cada uno dice:
- dónde está el archivo: página oficial, patrón del enlace y hosts permitidos;
- cómo leerlo: hoja, fila de encabezados, formato de los períodos y qué columna va a qué indicador, sector u ocupación;
- qué formato debe mantener: encabezados exactos, primer período, cantidad mínima de períodos, rango de valores y revisión máxima permitida de datos ya publicados.

**Descarga automática:**
1. Se busca el enlace vigente en la página oficial.
2. Si es el mismo que el último cargado, no se descarga nada.
3. Si es nuevo, se descarga y se guarda sin pisar los anteriores (`data/raw/datasets/<fuente>/`).
4. Se controla el formato y las revisiones.
5. Si pasa, se carga, el archivo anterior queda como "reemplazado" y se recalculan tendencias, ISE y alertas.
6. Si no pasa, **no se carga nada**, se mantienen los datos anteriores, la corrida queda como `format_changed` y se registra una alerta de severidad alta con el motivo (por ejemplo, una columna renombrada).

**Revisiones:** un archivo nuevo puede corregir los últimos `revision_grace_periods` períodos (12 en SIPA). Si valores más viejos cambian más que `max_revision` (5 %), se bloquea la carga porque puede ser otra serie.

**Carga manual.** En los frontends está en menú de la cuenta → Carga de datos. En la API son dos pasos: `POST /datasets/upload` y después `POST /datasets/{id}/commit`. Requiere sesión con permiso `manage_data` o el `X-API-Key`.

1. **Control del archivo, antes de leerlo** (`app/datasets/filecheck.py`). Se rechaza:
   - un `.xlsx` que no es un Excel real, tiene macros, o descomprimido supera `datasets.max_unzipped_bytes` (300 MB);
   - un `.csv` que en realidad es un Excel, es binario o no está en UTF-8.

   El archivo rechazado queda en el historial con el motivo.
2. **Validación.** Se valida contra el perfil, se guarda en `data/uploads/` y se devuelve el reporte con una vista previa. Todavía no se carga nada. El reporte trae:
   - los errores **agrupados** por tipo: cuántas filas, cuáles, qué valores y qué hacer (`app.yaml → datasets.group_titles` y `group_hints`);
   - el detalle fila por fila (los primeros 50).

   Hay un máximo de `datasets.max_rows` filas (200.000).
3. **Choque con datos oficiales.** Si un valor ya existe en otra fuente (mismo indicador, país, sector, ocupación, período y frecuencia), el reporte lo avisa, con la cantidad por fuente y ejemplos. Para cargar hay que confirmarlo (`{"confirm_overlap": true}`). Los valores cargados se guardan como fuente aparte (`manual_upload`) y **nunca reemplazan el dato oficial**.
4. **Confirmar.** Se vuelve a validar y se carga. Se recalculan tendencias, proyecciones, ISE y alertas.

La **plantilla genérica** (`plantilla_generica`) acepta cualquier dato oficial en formato largo (`indicador, pais, periodo, frecuencia, valor`, más `sector` y `ocupacion` opcionales). Exige declarar el nombre y la URL de la fuente, que se guardan con el archivo. Una nueva versión de la misma fuente declarada reemplaza los valores de la anterior.

- **Plantilla:** se descarga en Excel o CSV (`GET /datasets/profiles/plantilla_generica/template`). La hoja de datos trae solo los encabezados, para que nunca se carguen ejemplos por error. Las otras hojas traen las instrucciones con filas de ejemplo y los códigos válidos de indicadores, países, sectores y ocupaciones, sacados de la configuración.
- **Archivos de ejemplo** (`config/datasets/ejemplos/`): uno válido, con valores reales de ILOSTAT y del Banco Mundial, que muestra el aviso de choque con datos oficiales, y uno con errores puestos a propósito.

**Actualización programada** (`python -m app.jobs.scheduler`, configurada en `sources.yaml → scheduler`):
- World Bank e ILOSTAT: los lunes a las 6:00.
- Datos Argentina y SIPA: todos los días a las 6:00. Las fuentes mensuales se revisan a diario porque la fecha de publicación varía, y revisar no cuesta nada si no hay versión nueva.
- Control de fuentes desactualizadas: todos los días a las 7:30.
- En el despliegue, el mismo trabajo puede correr desde el cron de la plataforma con `python -m app.jobs.run --source <código> --triggered-by scheduler`.

---

## 2. Indicadores

Hay 18 indicadores. El dominio corresponde a la pestaña del mockup: economic → Socioeconómicos, labor
→ Laborales, education → Educativos.

### 2.1 Socioeconómicos

| Código | Indicador | Unidad | Fuente y serie | Frecuencia | Datos hasta |
|---|---|---|---|---|---|
| `gdp_growth` | Crecimiento del PBI | % | World Bank `NY.GDP.MKTP.KD.ZG` | Anual | 2025 |
| `gdp_per_capita_ppp` | PBI per cápita (USD PPA 2021) | USD PPA | World Bank `NY.GDP.PCAP.PP.KD` | Anual | 2025 |
| `inflation` | Inflación (promedio anual) | % | ARG: Datos Argentina `148.3_INIVELNAL_DICI_M_26` (IPC Nacional, promedio anual, variación interanual). URY y CHL: World Bank `FP.CPI.TOTL.ZG` | Anual | 2025 |
| `inflation_monthly_yoy` | Inflación interanual mensual | % | ARG: Datos Argentina `148.3_INIVELNAL_DICI_M_26`. URY: INE Uruguay (IPC, "Acum. 12 meses") | Mensual (ARG, URY) | 08/2026 ARG, 09/2026 URY |
| `economic_activity_yoy` | Actividad económica interanual (EMAE) | % | Datos Argentina `143.3_NO_PR_2004_A_21` | Mensual (ARG) | 07/2026 |

### 2.2 Laborales

| Código | Indicador | Unidad | Fuente y serie | Frecuencia | Datos hasta |
|---|---|---|---|---|---|
| `unemployment_rate` | Tasa de desocupación (15+) | % | ILOSTAT `DF_UNE_DEAP_SEX_AGE_RT`, clave `{countries}.A..SEX_T.AGE_YTHADULT_YGE15` | Anual | 2025 |
| `unemployment_rate_quarterly` | Desocupación trimestral (EPH) | % | Datos Argentina `42.3_EPH_PUNTUATAL_0_M_30` (× 100) | Trimestral (ARG) | 2026-T2 |
| `activity_rate_quarterly` | Actividad trimestral (EPH) | % | Datos Argentina `43.2_ECTAT_0_T_33` (× 100) | Trimestral (ARG) | 2026-T2 |
| `youth_unemployment_rate` | Desocupación juvenil (15 a 24) | % | World Bank `SL.UEM.1524.ZS` | Anual | 2025 |
| `youth_unemployment_rate_survey` | Desocupación juvenil (15 a 24 años, encuestas) | % | ILOSTAT `DF_UNE_DEAP_SEX_AGE_RT`, clave `{countries}.A..SEX_T.AGE_YTHADULT_Y15-24`. La misma serie de encuestas que `unemployment_rate`, para la Brecha generacional. La del World Bank (estimación modelada de la OIT) se mantiene | Anual | 2025 (ARG desde 2004; CHL y URY desde 2000) |
| `labor_force_participation` | Tasa de actividad | % | World Bank `SL.TLF.CACT.ZS` | Anual | 2025 |
| `self_employment_share` | Trabajo por cuenta propia | % | World Bank `SL.EMP.SELF.ZS` | Anual | 2025 |
| `registered_private_employment` | Asalariados registrados del sector privado (SIPA) | Miles | SIPA, hoja A.2.1: total, Turismo, Salud y Energía | Mensual (ARG) | 07/2026 (últimos 10 meses provisorios) |
| `employment` | Personas ocupadas | Miles | ILOSTAT `DF_EMP_TEMP_SEX_ECO_NB` (total y por sector, 3 países). Por ocupación: ILOSTAT `DF_EMP_TEMP_SEX_OC2_NB` (2 dígitos, ARG y URY) y SIMEL `DF_OCUCIUO_CIUO_SEXO` (gran grupo, CHL) | Anual | 2025 |
| `mean_monthly_earnings_ppp` | Ingreso laboral mensual promedio | USD PPA | ILOSTAT `DF_EAR_EMTA_SEX_ECO_CUR_NB` (sector) y `DF_EAR_EMTA_SEX_OCU_CUR_NB` (ocupación, 1 dígito), `CUR_TYPE_PPP` | Anual | 2025 ARG, 2024 URY y CHL |
| `mean_monthly_earnings_usd` | Ingreso laboral mensual promedio (para mostrar) | USD | ILOSTAT, las mismas dos series con `CUR_TYPE_USD` (tipo de cambio de mercado) | Anual | 2025 ARG, 2024 URY y CHL |
| `earnings_tertiary_ppp`, `earnings_tertiary_usd` | Ingreso laboral mensual promedio con educación superior | USD PPA y USD | ILOSTAT `DF_EAR_EMTA_SEX_EDU_CUR_NB`, `EDU_AGGREGATE_ADV` | Anual | 2025 ARG, 2024 URY y CHL |
| `earnings_secondary_ppp`, `earnings_secondary_usd` | Ingreso laboral mensual promedio con secundaria | USD PPA y USD | ILOSTAT `DF_EAR_EMTA_SEX_EDU_CUR_NB`, `EDU_AGGREGATE_INT` | Anual | 2025 ARG, 2024 URY y CHL |
| `genai_exposure` | Exposición a la IA generativa | Índice 0 a 1 | OIT WP 140, Tabla A1 | Estática (2025) | 2025 |

### 2.3 Educativos

| Código | Indicador | Unidad | Fuente y serie | Frecuencia | Datos hasta |
|---|---|---|---|---|---|
| `tertiary_enrollment` | Matrícula en educación superior (bruta) | % | World Bank `SE.TER.ENRR` | Anual | 2024 |
| `lower_secondary_completion` | Finalización de secundaria básica | % | World Bank `SE.SEC.CMPT.LO.ZS` | Anual | 2024 |
| `internet_users` | Población que usa internet | % | World Bank `IT.NET.USER.ZS` | Anual | 2024 |
| `overeducation_rate` | Sobrecalificación (educación mayor a la que pide la ocupación) | % | ILOSTAT `DF_EMP_TEMP_SEX_OCU_EDU_NB`, calculado (ver 2.5) | Anual (nacional y por gran grupo) | 2025 |
| `undereducation_rate` | Subcalificación (educación menor a la que pide la ocupación) | % | Ídem | Anual (nacional y por gran grupo) | 2025 |

### 2.4 Tarjetas de la pantalla Inicio

`app.yaml → dashboard.highlights`: desocupación, tasa de actividad, finalización de secundaria básica y
población que usa internet. Cada tarjeta muestra el último valor y su cambio respecto del período
anterior, en puntos porcentuales.

### 2.5 Desajuste entre educación y ocupación

Responde, para los tres países con la misma regla, qué parte de los ocupados tiene más o menos
educación de la que pide su ocupación. Complementa las brechas de habilidades (sección 6), que
Uruguay todavía no tiene.

- **Fuente:** ILOSTAT, ocupados por gran grupo de ocupación (CIUO-08, 1 dígito) y nivel educativo
  (CINE-97 en Argentina y Uruguay, CINE-11 en Chile). Sale de la encuesta de hogares de cada país:
  EPH urbana (Argentina), ECH (Uruguay) y ENE (Chile).
- **Regla (enfoque normativo de la OIT):** cada gran grupo pide un nivel. Grupos 1 a 3 (directivos,
  profesionales y técnicos): terciaria (CINE 5 o más). Grupos 4 a 8: secundaria (CINE 2 a 4).
  Grupo 9 (ocupaciones elementales): primaria. Quien tiene un nivel mayor está sobrecalificado, y
  quien tiene uno menor, subcalificado. Es la equivalencia entre niveles de competencia y niveles
  educativos de la CIUO-08 ([OIT](https://www.ilo.org/publications/international-standard-classification-occupations-2008-isco-08-structure)).
- **Qué se excluye:** fuerzas armadas (grupo 0, que mezcla niveles), ocupación o nivel educativo sin
  informar.
- **Por gran grupo:** las ocupaciones del mismo grupo comparten el valor. No se guarda la
  sobrecalificación de los grupos 1 a 3 ni la subcalificación del grupo 9, porque por construcción
  son 0 (no hay nivel por encima de terciaria ni por debajo de primaria).
- **Quiebres de serie:** solo se usan los años desde el último quiebre que marca ILOSTAT (estado
  `B`). Uruguay empieza en 2022, porque antes la ECH clasificaba al 53 % de los ocupados como
  primaria y después al 24 %. Chile empieza en 2020 y Argentina tiene la serie completa (2004–2025).
- **Sin escolaridad y preescolar** cuentan como primaria: en Uruguay, 2023 y 2025 pasan entre 11 % y
  16 % de los ocupados de primaria a "nivel 0" y luego vuelven, un cambio de codificación.
- **Configuración:** `config/reference/isco_education_requirements.yaml` (niveles, requisitos por
  grupo, grupos excluidos, estado de quiebre y el texto de "¿Cómo se calcula?") y la opción
  `education_mismatch` de la serie en `indicators.yaml`.
- **Datos de origen a la vista:** además de las tasas, se guardan los ocupados por país, año, gran
  grupo y nivel educativo (tabla `education_mismatch_cells`), y las tasas se calculan a partir de
  esas mismas celdas. `GET /api/v1/education-mismatch?country=ARG` las devuelve, y el Explorer las
  muestra como una tabla coloreada (verde: nivel que pide la ocupación; naranja: sobrecalificados;
  azul: subcalificados). Ejemplo, Argentina 2025: 2.237 mil sobrecalificados ÷ 13.144 mil ocupados
  en el cálculo = 17,0 %. Fuera del cálculo quedan 252 mil (fuerzas armadas, ocupación o nivel no
  informados).

**Resultados (2025):**

| País | Sobrecalificación | Subcalificación |
|---|---|---|
| Argentina | 17,0 % | 20,3 % |
| Chile | 20,2 % | 14,2 % |
| Uruguay | 10,4 % | 31,7 % |

La sobrecalificación se concentra en las ocupaciones elementales (Chile 86 %, Argentina 73 %) y en
los empleados de oficina (27 % a 30 % en Argentina y Chile). La subcalificación se concentra en
técnicos y directivos sin título terciario.

**Limitaciones:** mide niveles, no especialidades: un ingeniero que trabaja de contador figura como
bien calificado. Argentina es solo urbana (EPH). En Uruguay, la subcalificación salta de 28,7 % (2024)
a 36,0 % (2023) y 31,7 % (2025), lo que sigue el problema de codificación de esos años: conviene leer
la serie con cautela hasta confirmarlo con INE Uruguay.

---

## 3. Criterios de normalización

- **Búsqueda de ocupaciones y habilidades** (`/occupations?q=`, `/skills?q=`, buscador del encabezado y asistente). Cada palabra tiene que coincidir con el comienzo de una palabra del nombre:
  - en cualquier orden y sin importar tildes;
  - sin importar plural ni género: se busca la raíz, sacando -es, -as, -os, -a, -o o -s si quedan al menos 4 letras. Así "enfermera" encuentra "enfermería" y "desarrolladores" encuentra "Desarrollador/a".
  
  Un número de hasta 4 dígitos es un código CIUO. La regla está en `app/core/search.py` y, igual, en el frontend (`src/lib/utils/search.ts`).
- **Nombres locales de ocupaciones** (`config/reference/ocupaciones_nombres_locales.yaml`). Son 251 palabras de Argentina, Chile y Uruguay que no están en la CIUO ni en ESCO (escrito en español de España), con su código CIUO-08: remisero, gasfíter, colectivero, patovica… Algunas puntualizaciones:
  - cada código se eligió según la definición de ISCO-08 Vol. 1 (OIT, 2012), y si ESCO asigna otro grupo, manda ISCO-08;
  - una palabra puede tener otro sentido en otro país: "colectivero" es chofer de bus en Argentina (8331) y de taxi compartido en Chile (8322);
  - `also` agrega otros grupos posibles.
  
  Revisado y aprobado por Paula Vergara el 2026-11-01. Una búsqueda que coincide con un nombre local devuelve también su ocupación.
- **Países:** códigos ISO3 (ARG, URY, CHL).
- **Períodos:** cada dato se guarda en su frecuencia original, con fecha de inicio, fecha de fin y frecuencia (A, Q, M). No se transforma la frecuencia al guardar.
- **Tipo de dato:** cada valor es `observed` (de la fuente), `calculated` (lo calcula la plataforma) o `projected` (proyección). La API lo devuelve con su etiqueta.
- **Trazabilidad:** cada valor trae su fuente, la fecha de actualización de la fuente (si la informa), la fecha de descarga y, si es calculado o proyectado, el id de la metodología con los parámetros usados.
- **Historial (no se borra nada):**
  - **Datos de las fuentes:** cuando una fuente corrige o deja de publicar un valor ya cargado, el valor anterior se guarda en la tabla `data_revisions` antes de reemplazarlo: qué registro, valor anterior, valor nuevo (vacío si se quitó), la ejecución que lo cargó y la que lo cambió. Vale para los indicadores, los egresados y las celdas del desajuste educación-ocupación. Si la fuente no cambió nada, no se registra nada. Se consulta en `GET /api/v1/sources/{fuente}/revisions` (filtros `dataset` y `run_id`).
  - **Archivos oficiales:** cada archivo descargado o cargado se guarda en `data/raw/datasets/` o `data/uploads/`, con su huella (sha256) y su reporte en `dataset_files`; el que reemplaza a otro queda marcado como `replaced`, sin borrarse.
  - **Resultados:** los calculados con parámetros anteriores (otra versión de la metodología) se conservan (`analytics.yaml → recompute.keep_superseded_results: true`). La API muestra solo los de la versión vigente, y la tabla `methodologies` documenta los parámetros de cada versión.
- **Varias fuentes para un mismo indicador:** gana la primera listada en `indicators.yaml`, para cada país y período. Ejemplo: la inflación de Argentina sale de Datos Argentina y la de Uruguay y Chile del Banco Mundial.
- **Sectores:** los 5 sectores se definen por divisiones CIIU Rev.4 (`isic_codes`). ILOSTAT publica secciones, así que cada sector se aproxima con su sección (`ilostat_eco`):
  - Tecnología: J.
  - Salud: Q.
  - Energía: D.
  - Turismo: I.
  - Economía del conocimiento: J + M.
  - El empleo de varias secciones se suma y el ingreso se promedia. Si falta una sección, no se informa el sector.
  - **Decisión abierta:** Tecnología y Economía del conocimiento comparten la sección J.
- **Ocupaciones:** el universo son las 436 ocupaciones de CIUO-08 (4 dígitos), identificadas por su código. Como la OIT publica el empleo por grupos de 2 dígitos y el ingreso por grupos de 1 dígito, cada ocupación toma el valor de su grupo. El perfil de cada ocupación informa qué grupo se usó y qué otras ocupaciones lo comparten.
- **Nombres en español:** CIUO-08 publicada por el Ministerio de Economía y Finanzas de Uruguay ([PDF](https://www.gub.uy/ministerio-economia-finanzas/sites/ministerio-economia-finanzas/files/2021-01/codigos_ocupacion_0.pdf)).
  - Los 12 códigos que esa lista no tiene usan el nombre en inglés de la OIT.
  - Regla en `catalog.yaml`: si el nombre en inglés dice *Managers*, en español es "Gerentes" en lugar de "Directores".
- **Ocupaciones que no aplican a la región** (`excluded_occupations` en `catalog.yaml`, cada una con su motivo): 1113 (autoridades tradicionales) y 6310 a 6340 (agricultura, ganadería, pesca y recolección de subsistencia). Siguen en el catálogo y en el listado completo, marcadas como "No aplica a la región", pero no entran en el grupo comparado del ISE ni en los rankings.
- **Ocupaciones destacadas:** las 20 del catálogo (`featured_occupations`) se muestran por defecto y tienen sector. No limitan el cálculo.
- **Actualizaciones idempotentes:** volver a correr una carga actualiza los valores y no duplica filas. Cada corrida queda en `ingestion_runs`, que es el historial de actualizaciones. Lo que no se puede mapear se informa en la corrida; no se descarta en silencio.

---

## 4. Tendencias y proyecciones

Se recalculan solas después de cada carga, para los indicadores que cambiaron. Para recalcular sin
volver a descargar: `python -m app.jobs.recompute`.

### Tendencias (`analytics.yaml → trends`)

- **Método:** regresión lineal sobre los últimos `window_points` = 5 valores observados.
- **Normalización:** la pendiente se divide por el nivel medio de la serie.
  - Mayor que `threshold` (0,02): **crecimiento**.
  - Menor que −0,02: **disminución**.
  - En el medio: **estabilidad**.
  - Con menos de `min_points` (4) valores: **datos insuficientes**.
- **Excepciones por indicador** (`indicators.yaml → trend`):
  - PBI e inflación anual: ya son tasas de variación, así que se usa la pendiente sin normalizar con un umbral de 0,5 puntos por año.
  - Series mensuales: ventana de 12 meses.
  - EPH trimestral: ventana de 8 trimestres.
- **Período elegido:** con `from_year` y `to_year`, la tendencia se calcula con todos los valores observados de esos años.
- **Valoración:** favorable, desfavorable o neutral, según si al indicador le conviene subir (`higher_is_better`).
- **Historial:** se guarda por período, para detectar cambios de tendencia.

### Proyecciones (`analytics.yaml → projections`)

- **Método:** suavizado exponencial de Holt con tendencia aditiva, ajustado a cada serie por separado.
- **Horizonte:** `horizon` = 4 períodos en la frecuencia de la serie.
- **Intervalo:** `valor ± ci_z × σ × √h`, con ci_z = 1,96 y σ el desvío de los residuos del modelo.
- **Historia mínima:** sin al menos `min_points` = 12 valores no se proyecta.
- **Limitaciones:** sin estacionalidad, sin amortiguar la tendencia, intervalo aproximado. Son orientativas.
- **Por ocupación:** solo se calculan para las destacadas (`recompute.occupation_series: featured`), porque el resto repite los valores de su grupo.

---

## 5. Índice Sintético de Empleabilidad (ISE)

Configuración: `analytics.yaml → employability` (versión 0.2). Textos y rangos que muestra la API:
`app.yaml → employability`.

### 5.1 Fórmula

```
ISE = 0,35·Demanda neta + 0,25·Salario PPA + 0,25·Tasa de inserción − 0,15·Riesgo de automatización
```

Cada dimensión se escala de 0 a 100 con mínimo-máximo dentro del grupo comparado. El grupo
(`cohort: all`) son todas las ocupaciones de los 3 países en el mismo año, así que los puntajes se
pueden comparar entre países. El riesgo de automatización se invierte (menos exposición, más
puntaje), y así se aplica el signo negativo.

### 5.2 Dimensiones

| Dimensión | Peso | Fuente | Cálculo | Unidad | Rango posible | Observado en 2025 |
|---|---|---|---|---|---|---|
| Demanda neta | 35 % | `employment` por ocupación (ARG y URY: ILOSTAT, 2 dígitos; CHL: SIMEL, 1 dígito) | Crecimiento anual promedio entre el primer y el último valor de una ventana de 3 años | % anual | Sin límite fijo | −16,9 % a +15,0 % |
| Salario | 25 % | `mean_monthly_earnings_ppp` por ocupación (ILOSTAT, 1 dígito) | Último valor | USD PPA por mes | Desde 0 | 770 a 5.084 |
| Tasa de inserción | 25 % | Sin fuente todavía | — | % | 0 a 100 % | Sin datos |
| Riesgo de automatización | 15 % (se invierte) | `genai_exposure` (OIT WP 140) | Valor de la tabla | Índice 0 a 1 | 0 a 1 | 0,09 a 0,70 |

**Salario que se muestra.** Las pantallas muestran primero el salario en dólares al tipo de cambio
de mercado (`mean_monthly_earnings_usd`, ILOSTAT `CUR_TYPE_USD`) y debajo el valor en USD PPA. El
ISE sigue usando USD PPA, porque corrige las diferencias de precios entre países y permite comparar
poder de compra. El valor en USD es el del mismo país, grupo CIUO y año que usó el índice; si
ILOSTAT no lo publica para ese año, se muestra solo el de USD PPA. Se configura en
`app.yaml → employability.display_values`.

**Tasa de inserción: sin fuente oficial todavía.**
- **Chile:** Mi Futuro (SIES, MINEDUC) calcula la empleabilidad al 1.er y 2.º año por carrera
  genérica y tipo de institución, con datos del SII
  ([metodología](https://mifuturo.cl/wp-content/uploads/2025/12/Metodologia-Estadisticas-por-Carrera_2025-2026.pdf)).
  No la publica como archivo: el sitio la carga carrera por carrera con llamadas internas, cuyos
  nombres de campo no coinciden con los años que muestra (por ejemplo, `emplea_1_2015` cuando la
  página dice "cohortes 2018 a 2022"). Se decidió no usar esas llamadas y pedir la base al SIES:
  borrador en [`solicitud_sies_empleabilidad.md`](solicitud_sies_empleabilidad.md). Cuando llegue,
  se carga con un perfil de archivo oficial y la correspondencia carrera → ocupación.
- **Argentina y Uruguay:** no se encontró una fuente oficial de inserción por carrera u ocupación.
  ILOSTAT publica los desocupados por ocupación anterior solo para Uruguay.
- **Mientras tanto:** el ISE se calcula con las otras tres dimensiones, que pasan a pesar 46,7 %
  (demanda neta), 33,3 % (salario) y 20 % (riesgo de automatización). La API lo informa en
  `/employability` (`no_source_note`, y `has_source`, `source_status` y `effective_weight` en cada
  dimensión) y el Explorer lo muestra sobre el ranking.

Criterios de la demanda neta:
- **Sin 2020 ni 2021** (`exclude_years`). La caída y el rebote de la pandemia se leían como demanda: Chile solo tenía 2020 y 2022, y daba +36 % anual.
- **Grupo mínimo de 10 mil ocupados al inicio** (`min_base`, en miles). Con muestras más chicas la encuesta varía demasiado.
- **Antigüedad máxima:** no se usan valores con más de `max_age_years` = 5 años respecto del año de referencia.
- **Excepción para la exposición a IA:** es una característica de las tareas, no una medición anual, así que se aplica a todos los años (`applies_to_all_years`).

### 5.3 Puntaje, niveles y cobertura

- **Puntaje:** de 0 a 100 y relativo. 100 es la mejor combinación del grupo y 0 la peor; no es un porcentaje.
- **Niveles:** Baja por debajo de 40, Alta por encima de 70, Media en el medio.
- **Cobertura:** qué parte del peso total tiene datos para esa ocupación y país.
  - El peso de las dimensiones sin datos se reparte entre las demás.
  - Hoy nadie tiene tasa de inserción, así que la cobertura máxima es **75 %**.
  - Si la cobertura es menor que `min_coverage` (60 %), no hay puntaje y se muestra "Datos insuficientes".
- **Aporte:** cada dimensión informa valor original, valor escalado, peso y aporte. Los aportes suman el puntaje.
- **Años:** se calcula para cada año de referencia desde `first_year` (2018) hasta el último con datos.
- **Metodología:** cada combinación de parámetros tiene su id en `methodologies`, y la API solo muestra los puntajes de la combinación vigente.
- **Rankings (Mejores y Peores)** (`app.yaml → employability.ranking`):
  - Como mucho `max_per_group` (2) ocupaciones por grupo CIUO de `group_digits` (2) dígitos, para que una familia no ocupe toda la lista.
  - Cada fila informa cuántas de su grupo quedaron afuera.
  - Con `group_digits: 1` el tope es por gran grupo (por ejemplo, 2 directivos en total).
  - El listado completo ("Todas") no tiene tope.

### 5.4 Estado actual (2025)

| País | Ocupaciones con puntaje | Las que no tienen puntaje |
|---|---|---|
| Argentina | 408 de 436 | Grupos sin datos de empleo en la ventana o con menos de 10 mil ocupados, y ocupaciones que la OIT no puntúa (fuerzas armadas y algunas residuales) |
| Uruguay | 398 de 436 | Lo mismo; en Uruguay hay más grupos chicos |
| Chile | 433 de 436 | La demanda sale de SIMEL (Encuesta Nacional de Empleo, 2022 a 2025) por gran grupo. Sin puntaje: ocupaciones sin datos de exposición ni de grupo (fuerzas armadas). |

### 5.5 Limitaciones conocidas

- **Valores compartidos por grupo.** La demanda es por grupo de 2 dígitos (Argentina y Uruguay) o de 1 dígito (Chile), y el salario por grupo de 1 dígito. En Chile, por ejemplo, todos los profesionales (grupo 2) tienen la misma demanda. Dentro de un grupo, solo la exposición a IA diferencia a las ocupaciones. Por eso el top 20 está dominado por gerentes del grupo 13, y "Gerente de hotel" recibe el promedio de todos los directivos.
- **EPH urbana y muestras chicas** para Argentina a 2 dígitos (ver ILOSTAT en 1.1).
- **Exposición a IA ≠ automatización.** La medida de la OIT incluye tareas que la IA podría complementar.
- **Sin tasa de inserción.** Mi Futuro (Chile) la publica por carrera; requiere un conector de descarga.

---

## 6. Brechas de habilidades

Configuración: `analytics.yaml → skill_gaps` (versión 0.2).

- **Demanda de una habilidad:** el crecimiento anual promedio del empleo de las ocupaciones que la usan (el mismo dato que la demanda neta del ISE), promediado con el peso de la habilidad en cada ocupación (ESCO).
- **Oferta de una habilidad:** el crecimiento anual promedio de los titulados (Chile: pregrado; Argentina: grado y pregrado universitario; Uruguay: grado universitario) de las carreras que forman para esas ocupaciones, con los mismos pesos. Una carrera que forma para varias ocupaciones reparte sus titulados en partes iguales.
- **Brecha:** demanda − oferta, en puntos porcentuales. Es positiva si la demanda crece más rápido que la formación.
- **Ventana de la demanda:** la misma que el ISE (3 años, sin 2020 ni 2021).
- **Ventana de la oferta:** 3 años, sin excluir años (`supply_window_years`, `supply_exclude_years`). La exclusión de 2020 y 2021 responde a la caída del empleo en la pandemia, que no tuvo un equivalente en las titulaciones. Además, como los datos de Argentina llegan a 2023, excluir esos años dejaba una ventana de un solo año que amplificaba cualquier salto (por ejemplo, Veterinaria de pregrado: 120 egresados en 2022 y 2 en 2023). Hace falta un mínimo de `min_supply_base` (30) titulados al inicio.
- **Cuándo se calcula:** solo si las ocupaciones con datos de oferta suman al menos `min_supply_coverage` (30 %) del peso de la habilidad. Si no, "Datos insuficientes".
- **Emergente:** una habilidad cuya demanda crece más de `emerging_growth` (10 %) por año.

**Correspondencia carrera → ocupación, desde v0.2 a través de la CINE-F 2013** (criterios, cómo
revisarla y scripts en [`data/scripts/referencias/README.md`](../data/scripts/referencias/README.md)):
- **Dos clasificaciones distintas:** la CIUO-08 clasifica **ocupaciones** (lo que se hace en el
  trabajo) y la CINE-F 2013 de la UNESCO clasifica **campos de estudio** (lo que se estudió). Los datos
  laborales (ILOSTAT, SIMEL, encuestas de hogares), las habilidades (ESCO) y el ISE están por
  ocupación, así que la CIUO-08 se mantiene. La CINE-F se usa solo para las carreras.
- **Ruta:** carrera → campo detallado CINE-F (`config/reference/carreras_<país>_cine.yaml`) →
  ocupaciones, con **una tabla común a los tres países** (`config/reference/cine_f_ciuo.yaml`). Cada
  campo tiene ocupaciones para carreras universitarias y profesionales (`"*"`) y, si difieren, para
  carreras técnicas (`tecnico`). Una carrera es técnica por su nombre (técnico, tecnólogo,
  tecnicatura…) o por su nivel (en Argentina, Pregrado).
- **Clasificación:** los 99 campos detallados de la CINE-F 2013 (`config/reference/cine_f_2013.yaml`),
  con los nombres de la versión internacional de la UNESCO publicados por el DANE (Colombia),
  [CINE-F 2013 A.C., §7.1](https://www.dane.gov.co/files/noticias/CINE/cine-2013/Documento-CINE-F-2013-AC.pdf).
- **Asignación del campo:** reglas por nombre de carrera, compartidas por los tres países
  (`data/scripts/referencias/reglas_carreras_cine.yaml`). Tienen campo el 98,3 % de los titulados de
  Chile, el 98,5 % de Argentina y el 100 % de Uruguay. En Chile se controla contra el campo
  específico que publica Mi Futuro: coinciden todas las carreras salvo cuatro, anotadas para revisar.
- **Comparación con v0.1** (correspondencia directa por país): las brechas se parecen
  (correlación 0,66 en Argentina, 0,72 en Chile y 0,81 en Uruguay). Argentina cambia más porque
  cada disciplina pasa por un solo campo. Los resultados de v0.1 se conservan.

**Correspondencias directas carrera → ocupación (hasta v0.1, se conservan para comparar):**
- Las 277 carreras genéricas de Chile llevan a grupos CIUO-08: 252 con ocupación y 25 categorías genéricas sin ocupación ("Otros…", "Bachillerato…", plan común).
- **Es un borrador escrito por profesión, sin revisar** (`reviewed: false`). No existe una correspondencia oficial.
- Argentina: 37 disciplinas. Como una disciplina es amplia, casi todas llevan a varias ocupaciones. Una fila puede tener códigos distintos por nivel: `{Pregrado: [...], "*": [...]}`, donde `"*"` vale para los demás niveles (por ejemplo, Informática de pregrado lleva a técnicos 351x y la de grado a profesionales 251x). "Otras Ciencias Aplicadas" y "Otras Ciencias Sociales" quedan sin ocupación.
- Uruguay: 534 nombres de carrera, porque la misma carrera aparece con varios nombres ("Licenciatura en Psicología" y "Licenciado en Psicología"). La correspondencia se genera con reglas ordenadas (patrón → códigos, gana la primera que coincide) en `data/scripts/referencias/reglas_carreras_uruguay.yaml`. Los ciclos iniciales comunes quedan sin ocupación.
- Se descartó la búsqueda de texto de ESCO porque confunde palabras con profesiones (por ejemplo, "enfermería" daba auxiliar de enfermería 5321).
- La API informa `crosswalk_reviewed` y el Explorer lo muestra.

**Rankings** (`/skills/gaps`, vistas `top` y `bottom`): solo habilidades con brecha calculada y usadas por al menos `gap_ranking_min_occupations` (3) ocupaciones, configurable en `app.yaml`. Así las habilidades de una sola ocupación no ocupan la lista. "Todas" no tiene filtro.

**Estado (2025):**

| País | Brechas calculadas | Motivo |
|---|---|---|
| Chile | 5.242 de 11.551 habilidades | El resto no tiene oferta suficiente |
| Argentina (2023) | 3.134 de 11.551 habilidades | Igual que Chile. La correspondencia por disciplina es más gruesa, así que muchas ocupaciones comparten la misma oferta |
| Uruguay (2024) | 1.167 habilidades con brecha | Menos que Chile y Argentina: la demanda por ocupación de Uruguay (ILOSTAT, 2 dígitos) tiene más grupos sin datos o con menos de 10 mil ocupados |

**Limitaciones:**
- **En Chile la oferta domina la brecha.** La demanda sale de SIMEL por gran grupo (1 dígito) y casi no varía entre ocupaciones (+2 % a +6 % anual), mientras los titulados por carrera cambian ±20 a 40 % anual. Hoy la brecha se lee sobre todo como "dónde crece o cae la formación".
- **Una alternativa metodológica**, todavía no implementada, es comparar niveles (titulados por cada mil ocupados de la ocupación) en lugar de crecimientos.

---

## 7. Indicadores temáticos

Indicadores que cuentan una idea con una analogía histórica o literaria. Todos se calculan con los
mismos datos y correspondencias que el ISE y las brechas, guardan su metodología con parámetros
(`GET /methodologies/{tipo}`) y conservan los resultados de cada año y versión. Los textos que
explican cada gráfico se arman en el frontend con esos parámetros y los datos, así que si cambian
los datos o la configuración el texto cambia con ellos.

**Motor común de dos lados** (`app/analytics/moctezuma.py → compute_two_sided_index`), usado por
Moctezuma, Ludita y Sísifo:
- Cada dimensión se escala de 0 a 100 entre todas las ocupaciones (o grupos) de los 3 países en el
  mismo año (min-max). Si todas valen lo mismo, `flat_cohort_score` (50).
- Cada lado es el promedio ponderado de sus dimensiones con datos.
- Indicador = peso₁ · Lado₁ + peso₂ · (100 − Lado₂) (`side_weights`, hoy 0,5 y 0,5). 50 es equilibrio.
- Solo se calcula si cada lado tiene datos para al menos `min_side_coverage` (50 %) de su peso.
- Niveles: bajo por debajo de `levels.low` (40), alto por encima de `levels.high` (60).
- Es un puntaje relativo al grupo comparado, no una medida absoluta.

### 7.1 Indicador Moctezuma

Configuración: `analytics.yaml → moctezuma` (versión 0.1); textos: `app.yaml → moctezuma`; serie
histórica: `config/reference/moctezuma_history.yaml`. Tabla `moctezuma_scores`.

- **Qué mide:** la asimetría entre el ritmo con que llega el cambio tecnológico a una ocupación y la
  capacidad de respuesta para incorporarlo.
- **Ritmo:** exposición a la IA generativa (OIT, 2025) y crecimiento anual de la población que usa
  internet en el país (`internet_users`).
- **Capacidad de respuesta:** crecimiento de los titulados de las carreras que forman para la
  ocupación, subcalificación del gran grupo (en contra) y matrícula bruta en educación superior.
- **Años:** desde 2018, con datos de hasta `max_age_years` (5) años de antigüedad.
- **Referencia histórica:** la población del centro de México de 1518 a 1568 (Cook y Borah, con la
  alternativa de Rosenblat), con los hitos de 1519 (llegada de Cortés), 1520 (viruela), 1521 (caída de
  Tenochtitlan) y 1531 (sarampión), y el primer dato después de la conquista (1532). Cada valor y
  cada hito citan su fuente en el archivo.
- **Limitación:** la exposición a la IA es una foto fija, así que el ritmo cambia en el tiempo solo
  por la digitalización.

### 7.2 Indicador Ludita

Configuración: `analytics.yaml → ludita` (versión 0.1); textos: `app.yaml → ludita`; casos
históricos: `config/reference/ludita_history.yaml`. Tabla `ludita_scores` (migración 0022).

- **Qué mide:** cuánto se parece hoy una ocupación al camino de los oficios que la tecnología
  desplazó.
- **Exposición:** exposición a la IA generativa (OIT, 2025).
- **Vitalidad:** crecimiento anual promedio del empleo del grupo en 3 años (sin 2020 ni 2021, base
  mínima 10 mil) y de los titulados (base mínima 30).
- **Indicador** = 0,5 · Exposición + 0,5 · (100 − Vitalidad). Desde 2018.
- **Camino** (con los valores sin escalar, para que signifique lo mismo todos los años; `paths`):
  - expuesta (exposición ≥ 0,40, donde empiezan los gradientes 2 a 4 de la OIT) y el mercado se
    retira (crecimiento promedio < 0): **camino del tejedor**;
  - expuesta y el mercado crece: **camino del cajero de banco**;
  - poco expuesta y se achica: **otras causas**;
  - poco expuesta y crece: **fuera del alcance, por ahora**.
- **Casos históricos** (empleo con base 100 en el año de llegada de la tecnología): tejedores
  manuales en Inglaterra (Wood 1910, vía Acemoglu y Johnson 2024; telar mecánico, 1813), operadoras
  telefónicas en EE. UU. (Richmond Fed; discado automático, 1921) y cajeros de banco en EE. UU. (BLS y
  Bessen; cajero automático, 1970). Hoy se compara con la IA generativa (2022) en el gran grupo 4.
- **Limitaciones:** la exposición es una foto fija; el empleo es del grupo de 2 dígitos (1 en
  Chile); 3 años después de la IA generativa son pocos para hablar de desplazamiento.

### 7.3 Indicador Reina Roja

Configuración: `analytics.yaml → red_queen` (versión 0.1). Fuentes: versiones de O*NET y ESCO
(sección 1.1). Tablas `skill_profiles` y `red_queen_scores` (migración 0023).

- **Qué mide:** cuánto tiene que actualizarse una ocupación solo para no quedarse atrás.
- **Perfil:** las tecnologías de O*NET o las habilidades de ESCO de la ocupación en cada versión.
  Perfiles con menos de `min_items` (20) elementos no se usan.
- **Comparación:** cada año, la última versión publicada hasta ese año contra la última de al menos
  `window_years` (3) años antes (como mínimo `min_years`, 1). Desde 2022.
- **Renombres:** un nombre que solo cambia de forma (se agrega o quita el fabricante o una palabra,
  con al menos `rename_min_chars` = 5 letras) cuenta como el mismo elemento; en ESCO, una habilidad con
  el mismo nombre y código nuevo también.
- **Puntaje: novedades por año**, los elementos nuevos divididos por los años entre versiones,
  escalados de 0 a 100 por fuente; el indicador es el promedio de las dos fuentes con dato. Se eligió
  frente al recambio relativo, que favorecía a los perfiles chicos.
- **Se muestran al lado:** el recambio (distancia de Jaccard, anualizada) y la vida media del perfil
  (años hasta compartir solo la mitad, con tope `half_life_cap` = 50), y las listas completas de lo
  que entró y salió.
- **Filtro por carrera:** con `country` y `career`, solo las ocupaciones a las que lleva la carrera
  (la misma correspondencia CINE-F de las brechas).
- **Sesgo y limitaciones:** los perfiles grandes suman más novedades; O*NET es de EE. UU. y no
  revisa todas las ocupaciones en cada versión; ESCO refleja revisiones de expertos; no varía por
  país; un cambio puede ser una corrección de la clasificación.

### 7.4 Indicador Sísifo

Configuración: `analytics.yaml → sisyphus` (versión 0.1); textos: `app.yaml → sisyphus`;
definiciones de los grandes grupos: `config/reference/isco08_groups.yaml` (OIT, CIUO-08 vol. 1). Se
calcula al consultar (son pocos grupos), no se guarda en una tabla.

- **Qué mide:** dónde estudiar más no rinde, por gran grupo CIUO-08 (1 dígito), país y año.
- **La piedra:** sobreeducación del grupo (OIT, enfoque normativo). Los grupos 1 a 3 piden el nivel
  más alto, no pueden estar sobreeducados y quedan afuera.
- **La recompensa:** ingreso medio del grupo / ingreso medio con educación superior en el país ese
  año (los dos en USD PPA). Se muestran también en USD.
- **Indicador** = 0,5 · Piedra + 0,5 · (100 − Recompensa). Desde 2015, con datos de hasta 2 años de
  antigüedad.
- **Cuadrante** (valores sin escalar): sobreeducado desde 20 %, mal pago debajo de 0,5.
- **Por país:** proporción de ocupados con educación superior en grupos que no la piden (tabla del
  desajuste educación-ocupación) y prima salarial (ingreso con superior / con secundaria − 1).
- **Limitación:** la OIT no publica ingresos por educación dentro de cada ocupación; la recompensa
  compara el promedio del grupo con el de los graduados.

### 7.5 Brecha generacional

Configuración: `app.yaml → generational_gap` (indicadores que se comparan, textos y la frase
destacada).

- **Brecha** = desocupación de 15 a 24 años (`youth_unemployment_rate_survey`) / desocupación total
  (`unemployment_rate`), por país y año, solo en los años con las dos tasas. Las dos salen de las
  mismas encuestas de hogares (ILOSTAT). 1 es no tener brecha.
- **2025:** Uruguay 3,3 (24,4 % frente a 7,3 %), Argentina 2,6 y Chile 2,5.

### 7.6 Ocupaciones en movimiento (burbujas de Tendencias)

Configuración: `app.yaml → motion`. Se calcula al consultar.

- Cada burbuja es un gran grupo (1 dígito) en un país y un año, desde 2015.
- **Eje horizontal:** ingreso mensual promedio en USD (escala logarítmica), con el valor en USD PPA
  en el detalle. **Tamaño:** ocupados.
- **Eje vertical, a elegir:** crecimiento del empleo respecto del año anterior (base mínima 30 mil),
  exposición a la IA o ISE promedio del grupo.
- Si a un grupo le falta un año, se repite el último valor hasta `max_carry_years` (1) año.

---

## 8. Alertas

Configuración: `analytics.yaml → alerts`; etiquetas: `app.yaml → alerts`. Se evalúan después de cada
actualización, para los indicadores que cambiaron.

| Tipo | Regla | Severidad |
|---|---|---|
| Variación significativa | El último valor frente al del período inmediatamente anterior (sin huecos y con a lo sumo `max_age_years` = 2 años de antigüedad). Cantidades, dinero e índices: cambio relativo mayor que `change_pct` (10 %), ignorando bases menores que `min_base` (30). Porcentajes: cambio mayor que `absolute_change` (1 punto); el PBI usa 3 puntos (`indicators.yaml → alerts`). También dispara si el cambio supera `z_threshold` (2) desvíos de los cambios previos. | Alta si supera 2 veces el umbral; si no, media |
| Cambio de tendencia | La tendencia de la última ventana es distinta de la de la ventana que termina un período antes | Media |
| Cambio de nivel del ISE | Una ocupación destacada cambió de nivel (Baja, Media, Alta) respecto del año anterior | Media |
| Fuente desactualizada | La última actualización exitosa es más vieja que 1,5 veces la frecuencia esperada | Baja |
| Formato de archivo cambiado | Un archivo oficial descargado no tiene el formato validado (ver 1.4). No se carga. | Alta |

- **Alcance por ocupación** (`occupation_scope: featured`): las series por ocupación y los niveles del ISE se revisan solo para las ocupaciones destacadas.
- **Ocupaciones del mismo grupo CIUO:** comparten el valor, así que generan una sola alerta, que nombra a todas.
- **Sin duplicados:** cada alerta tiene una clave única (regla + serie + período), y volver a evaluar con los mismos datos no registra nada nuevo.
- **Qué guarda:** valor anterior y actual (o estado anterior y actual), período, fuente y metodología.
- **Leídas:** se marcan con `X-API-Key`.

---

## 9. Configuración y API

### 9.1 Variables de entorno (`backend/.env`)

| Variable | Uso |
|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL. Local: `postgresql+psycopg://rumbo:...@localhost:5432/rumbo`. Supabase: ver `docs/conexion_supabase.md`. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Postgres local con `docker compose` |
| `DATABASE_CONNECT_TIMEOUT` | Segundos de espera al conectar (5) |
| `CORS_ORIGINS` | Orígenes del frontend, por ejemplo `["http://localhost:3010"]` |
| `ADMIN_API_KEY` | Clave para los endpoints de administración (header `X-API-Key`) |
| `AUTH_SECRET` | Firma las sesiones de los usuarios; vacío = nadie puede iniciar sesión |
| `ANTHROPIC_API_KEY` | Asistente con `provider: anthropic` |
| `ASSISTANT_LOCAL_API_KEY` | Asistente con `provider: local`, solo si el servidor del modelo pide una clave |
| `BCENTRAL_USER`, `BCENTRAL_PASSWORD` | Para el futuro conector del Banco Central de Chile |
| `CONFIG_DIR` | Opcional: otra carpeta de archivos YAML |

Ninguna fuente activa necesita credenciales. Las de Banco Central de Chile van solo en `.env`.

### 9.2 Puesta en marcha y actualización

Desde `backend/backend`, con el entorno virtual activo:

```bash
docker compose up -d                    # Postgres 17 local
alembic upgrade head                    # migraciones
python -m seeds.load                    # catálogo, fuentes e indicadores desde config/
python -m app.jobs.run --all            # descarga las fuentes y recalcula todo
python -m app.jobs.run --source ilostat # una sola fuente
python -m app.jobs.recompute            # recalcula sin descargar (tras cambiar analytics.yaml)
python -m app.jobs.scheduler            # actualización automática (queda corriendo)
python -m app.jobs.scheduler --list     # qué corre y cuándo
uvicorn app.main:app --reload --port 8010
```

### 9.3 Endpoints (prefijo `/api/v1`)

Documentación interactiva: http://localhost:8010/docs. Explorer (herramienta de desarrollo):
http://localhost:8010/explorer.

| Endpoint | Para qué |
|---|---|
| `GET /countries`, `/sectors`, `/occupations?featured=&q=&sector=` | Catálogos para los filtros |
| `GET /indicators?domain=` | Definiciones de indicadores |
| `GET /observations?indicator=&country=&sector=&occupation=&from_year=&to_year=&data_type=` | Serie con fuente y fecha en cada punto |
| `GET /compare?indicator=&countries=&sector=` | Último valor por país frente al anterior (gráfico de barras) |
| `GET /dashboard/summary?country=` | Tarjetas de Inicio |
| `GET /trends?indicator=&domain=&country=&from_year=&to_year=&state=` | Estado de tendencia y valoración |
| `GET /projections?indicator=&country=&from_year=` | Serie observada más la proyección con intervalo |
| `GET /methodologies/{trend\|projection\|employability_index\|moctezuma_index\|ludita_index\|red_queen_index\|sisyphus_index}` | Texto y parámetros de cada metodología |
| `GET /employability` | ISE. Parámetros: `view=top\|bottom\|all`, `sort_by=score\|net_demand\|salary_ppp\|insertion_rate\|automation_risk\|coverage\|occupation\|isco\|country`, `order=asc\|desc`, `country`, `sector`, `featured`, `q`, `year`, `limit`, `offset`. Devuelve también `dimension_ranges`. |
| `GET /employability/history?occupation=&country=` | Evolución del ISE |
| `GET /occupations/{código CIUO}` | Perfil: grupos usados, ISE por país, últimos valores |
| `GET /alerts?country=&severity=&alert_type=&indicator=&sector=&occupation=&unread=` | Panel de alertas, con `unread` (para la campana) y `by_severity` |
| `PATCH /alerts/{id}`, `POST /alerts/read-all` | Marcar como leídas (requiere `X-API-Key`) |
| `GET /datasets/profiles` | Archivos que la plataforma sabe leer y el formato esperado (`has_template`, `example_files`) |
| `GET /datasets/profiles/{código}/template?format=xlsx\|csv` · `/datasets/profiles/{código}/examples/{nombre}` | Plantilla para completar y archivos de ejemplo |
| `GET /datasets?origin=download\|upload`, `/datasets/{id}` | Historial de archivos leídos y su reporte de validación |
| `POST /datasets/upload` (multipart: `file`, `profile`, `declared_source_name`, `declared_source_url`, `reference_date`) | Validar un archivo (permiso `manage_data` o `X-API-Key`). Reporte con errores agrupados (`groups`) y choques con datos oficiales (`overlaps`) |
| `POST /datasets/{id}/commit` con `{"confirm_overlap": true}` si hace falta | Cargar un archivo validado (permiso `manage_data` o `X-API-Key`) |
| `GET /occupations/{código}/skills?skill_type=&limit=` | Habilidades de una ocupación (ESCO), con peso y fuente |
| `GET /skills?q=&skill_type=` · `GET /skills/{código}` | Buscar habilidades y ver qué ocupaciones las usan |
| `GET /skills/gaps?country=&view=top\|bottom\|all&sort_by=gap\|demand_growth\|supply_growth\|occupations&order=&min_occupations=&emerging=&q=` | Brechas de habilidades, con estado de la correspondencia carrera → ocupación |
| `GET /moctezuma?country=&sector=&featured=&year=&view=&limit=&offset=` | Indicador Moctezuma por ocupación, con `available_years`, lados y rangos |
| `GET /moctezuma/countries`, `/moctezuma/history?occupation=&country=`, `/moctezuma/reference` | Promedio por país y año, evolución de una ocupación y la serie histórica de 1518–1568 |
| `GET /ludita?country=&sector=&featured=&path=weaver\|teller\|other_causes\|out_of_reach&year=&view=` | Indicador Ludita y camino de cada ocupación |
| `GET /ludita/countries`, `/ludita/history?country=` | Promedio y caminos por país y año; casos históricos frente a hoy |
| `GET /red-queen?year=&country=&career=&featured=&view=&limit=&offset=` | Indicador Reina Roja, con lo que entró y salió de cada perfil |
| `GET /red-queen/years`, `/red-queen/careers?country=` | Medianas por año; carreras para el filtro |
| `GET /sisyphus?country=&year=`, `/sisyphus/countries?country=` | Indicador Sísifo por gran grupo; vista por país |
| `GET /generational-gap?country=` | Brecha generacional por país y año |
| `GET /occupation-groups/motion?y=growth\|ai_exposure\|employability&country=` | Burbujas de Tendencias |
| `GET /sources`, `/sources/{code}/runs` | Estado de las fuentes e historial de actualizaciones |
| `POST /sources/{code}/refresh` | Actualiza una fuente (requiere `X-API-Key`) |
| `POST /auth/login`, `GET /auth/me`, `/users` | Inicio de sesión y usuarios (roles en `app.yaml → auth`) |
| `GET /assistant` · `POST /assistant/ask` | Asistente: estado y textos; preguntar (con sesión). Ver 8.4 |

Cada valor que devuelve la API incluye `source`, `source_updated_at`, `fetched_at`, `data_type` y,
cuando corresponde, `methodology_id`.

### 8.4 Asistente: de dónde salen las respuestas

El asistente ("Baqueano") solo usa datos del observatorio. Responde de dos maneras:

1. **Por plantilla, sin modelo** (`app.yaml → assistant.scripted`). Es para las preguntas frecuentes: salario, empleabilidad o habilidades de una ocupación, ranking y sectores de un país, y cómo se calcula el ISE.
   - **Cómo reconoce la pregunta.** El tipo sale de palabras clave. La ocupación, de un código, un nombre o un nombre local. El país, de su nombre o de la página que se está mirando.
   - **De dónde salen los números.** Se copian de los mismos endpoints que usan las pantallas. Las plantillas agregan las aclaraciones que corresponden: por ejemplo, que un salario es el promedio del gran grupo CIUO cuando la fuente no lo publica para la ocupación sola.
   - **Ambigüedad y límite.** Si hay varias ocupaciones posibles, ofrece elegir. No cuentan para el límite diario.
2. **Con un modelo**, para lo demás. Por defecto es un modelo abierto local (Ollama, `qwen2.5:7b-instruct`); también puede ser Claude.
   - **Qué puede consultar.** Solo los endpoints de lectura de `assistant.tools`. Solo puede usar códigos CIUO que salieron de la búsqueda, de la pregunta o de la página.
   - **Chequeo de números.** Todo número de la respuesta tiene que estar en los datos consultados, con una tolerancia de 0,5 %; una proporción también vale como porcentaje. Si no está, la respuesta se reemplaza por un aviso (`numbers_check.on_unverified: block`).
   - **Límites.** 30 preguntas por persona por día y 500 en total.

Cada pregunta queda en `assistant_logs`: pregunta, contexto, consultas, respuesta, números no verificados, tokens y tiempo. Esos registros no se editan. Limitación conocida: una afirmación sin números ("tiene un ISE alto") no se puede verificar así.

---

## 10. Pendientes

- **Scheduler en el despliegue:** como proceso aparte o como cron de Render/Railway.
- **Más perfiles de archivos oficiales:** ECH (INE Uruguay), ANEP, SABE.
- **Argentina:** registros de SIPA y promedio móvil de la EPH para estabilizar la demanda.
- **Tasa de inserción:** enviar la solicitud al SIES y cargar la base cuando llegue (ver sección 5.2).
- **Revisar la correspondencia carrera → ocupación de Chile** (`reviewed: false`) antes de publicar brechas: ver [`pendientes_analytics.md`](pendientes_analytics.md).
- **Uruguay, más formación:** sumar la formación docente (ANEP, hoja II-6.2.1 del mismo anuario) y la terciaria no universitaria.
- **Revisar exclusiones dudosas:** por ejemplo 9624 (acarreadores de agua y recolectores de leña), hoy incluida.
- **Carga manual, segunda etapa:** retirar una carga sin borrarla y marcar en las pantallas los datos de carga manual.
- **Asistente:** elegir el modelo para lo que no cubren las plantillas (el de 7B local no siempre completa la búsqueda y la consulta) y sumar plantillas para las preguntas que más llegan al modelo (`assistant_logs`).
- **Búsqueda por significado:** entrenar y evaluar el modelo de `backend/ml/occupation_match/` (frase → código CIUO) y conectarlo al buscador.
- **Indicadores temáticos:**
  - Moctezuma y Ludita: falta una serie de adopción de IA por país, para que el ritmo y la exposición
    cambien en el tiempo.
  - Moctezuma: evaluar límites fijos para las dimensiones nacionales en lugar del min-max del año.
  - Reina Roja: corregir el sesgo por tamaño del perfil de O*NET.
