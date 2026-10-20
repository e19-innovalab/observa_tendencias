# Ocupaciones, carreras y habilidades: criterios y scripts

Este documento explica cómo el Observatorio clasifica las ocupaciones (CIUO-08), de dónde salen
sus nombres y datos de referencia, cómo se relacionan las carreras con las ocupaciones y qué scripts
generan y controlan esos archivos. Está pensado para el equipo de InnovaLab: Data Analytics,
Backend, Frontend y QA.

Estado al 18/10/2026. Las fuentes de datos, el ISE, las tendencias y las alertas están en
[`docs/fuentes_y_criterios.md`](../../../docs/fuentes_y_criterios.md).

---

## 1. Cómo leer un código CIUO-08

Las ocupaciones se identifican con su código de la **CIUO-08**, la Clasificación Internacional
Uniforme de Ocupaciones de la OIT (ISCO-08 en inglés). Es un código de **4 dígitos que se lee de
izquierda a derecha**: cada dígito agrega detalle. **No es un código de carrera.** Las carreras de
Mi Futuro no tienen un código propio; se identifican por su nombre genérico.

Ejemplo, **2132**:

| Dígitos | Nivel | Código | Nombre |
|---|---|---|---|
| 1 | Gran grupo | **2** | Profesionales científicos e intelectuales |
| 2 | Subgrupo principal | **21** | Profesionales de las ciencias y de la ingeniería |
| 3 | Subgrupo | **213** | Profesionales en ciencias biológicas |
| 4 | Grupo primario (la ocupación) | **2132** | Agrónomos y afines |

El primer dígito, el gran grupo, indica el tipo de trabajo y el nivel de calificación:

| Gran grupo | Nombre |
|---|---|
| 0 | Ocupaciones militares |
| 1 | Directores y gerentes |
| 2 | Profesionales científicos e intelectuales |
| 3 | Técnicos y profesionales de nivel medio |
| 4 | Personal de apoyo administrativo |
| 5 | Trabajadores de los servicios y vendedores de comercios y mercados |
| 6 | Agricultores y trabajadores calificados agropecuarios, forestales y pesqueros |
| 7 | Oficiales, operarios y artesanos de artes mecánicas y de otros oficios |
| 8 | Operadores de instalaciones y máquinas y ensambladores |
| 9 | Ocupaciones elementales |

Por eso **el 2 corresponde a profesionales y el 3 a técnicos**. La carrera "Agronomía" se asocia a
2132 (agrónomos) y "Técnico Agropecuario" a 3142 (técnicos agropecuarios).

En la API, cada ocupación trae su jerarquía completa: `hierarchy` en `GET /api/v1/occupations/{código}`
y en la revisión de la correspondencia (sección 5). En el Explorer, pasando el mouse sobre un
código.

---

## 2. Fuentes oficiales

| Fuente | Qué se toma | Dónde |
|---|---|---|
| **OIT**, Working Paper 140 (2025), *Generative AI and Jobs: A Refined Global Index of Occupational Exposure*, Anexo, Tabla A1 | Exposición a la IA generativa de 427 ocupaciones de 4 dígitos (media, desvío y gradiente) y su nombre en inglés | [PDF](https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf) · [DOI](https://doi.org/10.54394/HETP0387) |
| **CIUO-08 de Uruguay**, Ministerio de Economía y Finanzas, "Códigos de ocupación" | Nombres en español de las ocupaciones (4 dígitos) y de los grupos (1, 2 y 3 dígitos) | [PDF](https://www.gub.uy/ministerio-economia-finanzas/sites/ministerio-economia-finanzas/files/2021-01/codigos_ocupacion_0.pdf) |
| **ESCO** (Comisión Europea) | Habilidades y conocimientos de cada ocupación, en español | [API](https://ec.europa.eu/esco/api/doc/esco_api_doc.html) |
| **Mi Futuro** (MINEDUC, SIES, Chile) | Titulados de educación superior por carrera genérica, 2007-2025 | [Bases de titulados](https://www.mifuturo.cl/bases-de-datos-titulados/) |

---

## 3. Archivos de referencia de ocupaciones

Están en `backend/backend/config/reference/` y se generan con
[`generar_referencias_ciuo.py`](generar_referencias_ciuo.py) (sección 7). **No se editan a mano.**

| Archivo | Contenido |
|---|---|
| `ilo_genai_exposure.yaml` | Las 427 filas de la Tabla A1 de la OIT: media (0 a 1), desvío y gradiente |
| `isco08_occupations.yaml` | Universo de **436 ocupaciones** (4 dígitos) con nombre en español e inglés |
| `isco08_groups.yaml` | Nombres de los **183 grupos** de 1, 2 y 3 dígitos que usan esas ocupaciones |

**Cómo se construyeron:**

- **Universo de ocupaciones:** es la unión de las 427 ocupaciones de la OIT y las 424 de la CIUO-08 de Uruguay, que suman 436, el total de grupos primarios de la CIUO-08.
  - **Nombre en español:** el de Uruguay.
  - **Las 12 ocupaciones que esa lista no tiene** usan el nombre en inglés de la OIT (por ejemplo, 1113 *Traditional Chiefs and Heads of Villages*).
- **Exposición a la IA:** se extrae del texto del PDF. El script reconstruye las filas que el PDF parte en varias líneas y separa nombres pegados al número (por ejemplo, "Establishments0.12").
  - **Controles:** antes de escribir nada verifica que el resultado reproduzca los totales del paper (427 ocupaciones, 13 en el gradiente 4 y 112 expuestas). Si no coinciden, no escribe.
- **Grupos de 1 a 3 dígitos:** se leen por la sangría del PDF (0, 1 o 2 espacios según el nivel). Se ignoran los números de página y se unen los nombres que siguen en la línea siguiente.
  - **El grupo 224 no está en la lista de Uruguay:** como tiene una sola ocupación (2240), toma su nombre de la OIT.
- **Qué mide el puntaje de exposición** (OIT, sección 3.1 del paper):
  - Cada tarea de una ocupación tiene un puntaje de 0 (no se puede automatizar) a 1 (la IA generativa podría hacerla sola, sin una persona).
  - El valor de la ocupación es el promedio de sus tareas.
  - Mide exposición, no reemplazo: incluye tareas que la IA podría complementar.

---

## 4. Reglas de presentación (configurables)

Están en `backend/backend/config/catalog.yaml` y se aplican sin modificar los archivos de referencia.

- **"Gerentes" en lugar de "Directores":** si el nombre en inglés dice *Managers*, el nombre en español empieza con "Gerentes" (`occupation_name_rules`). Por ejemplo, 1211 "Directores financieros" se muestra como "Gerentes financieros". 1120 *Managing Directors and Chief Executives* sigue como "Directores generales".
- **Ocupaciones que no aplican a la región** (`excluded_occupations`, cada una con su motivo): 1113 (autoridades tradicionales) y 6310 a 6340 (agricultura, ganadería, pesca y recolección de subsistencia). Siguen en el listado completo, marcadas "No aplica a la región", pero no entran en el ISE ni en los rankings.
- **Ocupaciones destacadas** (`featured_occupations`): las 20 que se muestran por defecto, con su nombre de presentación y su sector estratégico. No limitan el cálculo: el ISE cubre las 436.

---

## 5. Correspondencia carrera → ocupación

### Qué es y para qué se usa

Para las **brechas de habilidades** hace falta saber para qué ocupaciones forma cada carrera. La
oferta de una habilidad se calcula con los titulados de las carreras que forman para las
ocupaciones que la usan. **No existe una correspondencia oficial** entre las carreras chilenas y
la CIUO-08, así que se armó una.

- **Archivo:** `backend/backend/config/reference/carreras_chile_ciuo.yaml`.
- **Carreras:** las 277 carreras genéricas de pregrado de Mi Futuro.
- **Resultado:** 252 se asocian a una o más ocupaciones y 25 son categorías genéricas sin ocupación. Las carreras con ocupación reúnen el **98,4 % de los titulados** de 2025.

### Criterios con los que se escribió

1. **Por profesión, no por palabras.** Cada carrera se asocia a la ocupación para la que forma principalmente.
2. **Carreras profesionales** → el grupo profesional (2xxx). **Carreras técnicas** ("Técnico en …") → el grupo técnico, de servicios u oficios del mismo campo (3xxx a 7xxx). Por ejemplo, "Enfermería" → 2221 y "Técnico en Enfermería" → 3221 y 5321.
3. **Varias ocupaciones** cuando la carrera lleva a varias. Los titulados se reparten en partes iguales (la columna "proporción" de la revisión). Por ejemplo, "Derecho" → 2611, 2612 y 2619, un tercio a cada una.
4. **Categorías genéricas sin ocupación:** "Otros técnicos de …", "Bachillerato …" y "plan común". No apuntan a una ocupación y quedan fuera de la oferta.
5. **Ninguna ocupación excluida** (sección 4) y todos los códigos existen en la CIUO-08. Lo controla `validate_crosswalk` (sección 7).

**Por qué no se generó automáticamente:** se probó la búsqueda de texto de ESCO y se descartó
porque busca palabras, no profesiones:

| Carrera | ESCO sugería | Correcto |
|---|---|---|
| Enfermería | auxiliar de enfermería (5321) | profesional de enfermería (2221) |
| Psicología | profesor universitario de psicología (2310) | psicólogo (2634) |
| Ingeniería Comercial | representante comercial (3322) | analista de gestión (2421) y economista (2631) |

### Estado: borrador sin revisar

El archivo tiene `reviewed: false`. Mientras sea así, la API informa `crosswalk_reviewed` y el
Explorer muestra un aviso. **Antes de publicar resultados de brechas, alguien del equipo debería
revisarla**, idealmente con conocimiento de las carreras chilenas. La tarea, con las carreras
prioritarias y los puntos dudosos, está en [`docs/pendientes_analytics.md`](../../../docs/pendientes_analytics.md).

### Cómo revisarla

1. **Verla:**
   - **En el Explorer** (http://localhost:8010/explorer), sección "Correspondencia carrera → ocupación (revisión)". Las carreras con más titulados aparecen primero, porque son las que más pesan. Se puede buscar por carrera, ocupación o código.
   - **En una planilla:** `GET /api/v1/graduates/crosswalk?country=CHL&format=csv` (o el botón "Descargar CSV"). Trae una fila por carrera y ocupación, con titulados, crecimiento, área CINE-F y los nombres de cada nivel de la jerarquía.
2. **Corregir:** editar la línea de la carrera en `carreras_chile_ciuo.yaml`. Los códigos van como números, por ejemplo `"Psicología": [2634]`, y una categoría sin ocupación lleva `[]`.
3. **Controlar:** `python -m app.jobs.validate_crosswalk` (desde `backend/backend`, con el entorno virtual activo).
4. **Aplicar:** `python -m app.jobs.recompute` recalcula las brechas.
5. **Cerrar la revisión:** cuando esté revisada, cambiar `reviewed: false` por `reviewed: true` y anotar en el encabezado quién la revisó y cuándo.

### Otros países

**Argentina:** `config/reference/carreras_argentina_ciuo.yaml`, escrita a mano con los mismos
criterios. La unidad es la disciplina específica del Departamento de Información Universitaria (37),
no la carrera, y una fila puede tener códigos distintos por nivel (`Pregrado` y `"*"` para los demás).
Tampoco está revisada: ver `docs/pendientes_analytics.md`, tarea 1b.

**Uruguay:** `config/reference/carreras_uruguay_ciuo.yaml` se **genera** con reglas, porque el
Anuario del MEC publica 534 nombres de carrera, con muchas variantes de la misma. No se edita a mano:
1. Editar `reglas_carreras_uruguay.yaml` (patrón sobre el nombre normalizado → códigos CIUO; gana la
   primera regla que coincide, así que las más específicas van antes).
2. Correr, con los egresados de Uruguay ya cargados:

       cd backend/backend && .venv/bin/python ../data/scripts/referencias/generar_correspondencia_uruguay.py

   Informa cuántas carreras tienen regla y qué parte de los egresados tiene ocupación, y lista las
   carreras sin regla. No escribe nada si una regla usa un código que no está en el universo.
3. Validar con `python -m app.jobs.validate_crosswalk --country URY` y recalcular.

Cada fila del archivo generado termina con los egresados 2020-2024 y la regla que la asoció. Tampoco
está revisada: ver `docs/pendientes_analytics.md`, tarea 1c.

**Para sumar otro país:**
1. Agregar un perfil de archivo oficial en `config/datasets/`.
2. Crear su correspondencia `config/reference/carreras_<país>_ciuo.yaml`.
3. Registrarla en `analytics.yaml → skill_gaps.crosswalks`.

---

## 6. Habilidades por ocupación (ESCO)

- **Qué se carga:** las habilidades de cada ocupación se cargan automáticamente desde la API de ESCO (fuente `esco` en `sources.yaml`, revisión mensual).
- **Peso de una habilidad para una ocupación CIUO:** el promedio, entre las ocupaciones ESCO de ese grupo, de **1** si la habilidad es esencial, **0,5** si es opcional y **0** si no figura. Por ejemplo, "programación informática" pesa 0,75 para 2512 (Desarrolladores de software).
- **Carga actual:** 11.551 habilidades para 424 de las 431 ocupaciones aplicables.
- **Sin datos en ESCO:** 1321 y 2142 (su registro en ESCO da error), y 2240, 3221, 4414, 7549 y 9624 (ESCO no las detalla).

La fórmula de las brechas está en [`docs/fuentes_y_criterios.md`](../../../docs/fuentes_y_criterios.md), sección 6.

---

## 7. Scripts y comandos

Se ejecutan desde `backend/backend` con el entorno virtual activo (`source .venv/bin/activate`),
salvo que se indique otra cosa.

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `python ../data/scripts/referencias/generar_referencias_ciuo.py` | Descarga los PDF de la OIT y de la CIUO-08 de Uruguay ([`fuentes.yaml`](fuentes.yaml)), extrae las tablas, controla los totales del paper y escribe los 3 archivos de referencia de la sección 3 | Si la OIT publica una nueva versión del índice o cambia la CIUO-08. Con `--solo-controlar` extrae y controla sin escribir. Los PDF quedan en `_descargas/`, que no se versiona. |
| `python -m app.jobs.validate_crosswalk` | Controla la correspondencia carrera → ocupación: códigos válidos, no excluidos y todas las carreras de los datos cubiertas | Después de editar `carreras_*_ciuo.yaml` |
| `python -m seeds.load` | Carga en la base el universo de ocupaciones, sus nombres, exclusiones y destacadas | Después de regenerar los archivos de referencia o de cambiar `catalog.yaml` |
| `python -m app.jobs.run --source esco` | Vuelve a cargar las habilidades de ESCO | Si ESCO publica una nueva versión (también corre solo el día 1 de cada mes) |
| `python -m app.jobs.run --source mifuturo_chile` | Busca la última base de titulados en la página oficial, la descarga si es nueva, controla su formato y la carga | Corre solo cada semana; a mano si se quiere forzar |
| `python -m app.jobs.recompute` | Recalcula ISE, tendencias, brechas y alertas sin descargar | Después de cambiar la correspondencia o `analytics.yaml` |

Los scripts de procesamiento del equipo de Data Analytics (LinkedIn y egresados seleccionados)
están documentados en [`../README.md`](../README.md).

---

## 8. Limitaciones

- **La correspondencia carrera → ocupación es un borrador** escrito por profesión, sin revisión externa.
- **Reparto en partes iguales:** cuando una carrera lleva a varias ocupaciones, los titulados se reparten en partes iguales, porque no hay datos de a qué ocupación llega cada egresado.
- **Nombres de la CIUO-08 de Uruguay:** se usan para los tres países porque es la versión oficial en español más completa que se encontró. Chile y Argentina tienen adaptaciones propias con algunas diferencias de redacción.
- **ESCO es europea:** las habilidades describen las ocupaciones como se definen en Europa y no varían por país.
