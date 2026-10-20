# Pendientes de Data Analytics

Tareas que necesitan revisión o decisión del equipo de Data Analytics antes de publicar resultados.
Estado al 18/10/2026. Al cerrar una tarea, marcala como hecha y anotá quién la cerró y la fecha.

---

## 1. Revisar la correspondencia carrera → ocupación (Chile) · prioridad alta

**Estado:** pendiente · **Responsable:** a definir · **Bloquea:** la publicación de las brechas de
habilidades.

### Qué hay que revisar

El archivo `backend/backend/config/reference/carreras_chile_ciuo.yaml` asocia cada una de las
**277 carreras genéricas de pregrado** de Mi Futuro con las ocupaciones CIUO-08 para las que forma.
Con eso se calcula la oferta formativa de cada habilidad. Lo escribió el equipo de Backend por
profesión y **es un borrador** (`reviewed: false`), porque no existe una correspondencia oficial
entre carreras chilenas y CIUO-08.

Los criterios con los que se escribió, cómo leer un código CIUO-08 y por qué no se generó
automáticamente están en [`data/scripts/referencias/README.md`](../data/scripts/referencias/README.md),
secciones 1 y 5.

### Qué decidir en cada carrera

- **Ocupaciones:** ¿son las correctas? ¿Falta alguna a la que llegan muchos egresados? ¿Sobra alguna?
- **Nivel:** que una carrera profesional apunte a un grupo profesional (2xxx) y una técnica a uno técnico u operativo (3xxx a 7xxx).
- **Reparto:** hoy los titulados se reparten **en partes iguales** entre las ocupaciones de la carrera. Si una ocupación debería pesar más, anotarlo: el reparto con pesos distintos todavía no está implementado y se agregaría si hace falta.
- **Categorías genéricas** ("Otros técnicos de …", "Bachillerato …"): confirmar que queden sin ocupación.

### Cómo hacerlo

1. **Descargar la planilla:** en el Explorer (http://localhost:8010/explorer), sección "Correspondencia carrera → ocupación (revisión)", botón **Descargar CSV**. También se puede pedir `GET /api/v1/graduates/crosswalk?country=CHL&format=csv`. Trae una fila por carrera y ocupación, con titulados 2025, crecimiento, área CINE-F, la proporción asignada y los nombres de cada nivel de la jerarquía CIUO-08.
2. **Revisar en orden de titulados:** las primeras 25 carreras reúnen el **52 %** de los titulados y las primeras 50, el **73 %**. Con esas ya se cubre la mayor parte del efecto en las brechas.
3. **Anotar los cambios** en la planilla o directamente en el YAML. El formato es `"Carrera": [código, código]`, y `[]` para las genéricas.
4. **Controlar:** `python -m app.jobs.validate_crosswalk`, desde `backend/backend` con el entorno virtual activo.
5. **Aplicar:** `python -m app.jobs.recompute`.
6. **Cerrar:** cambiar `reviewed: false` por `reviewed: true` en el YAML y anotar en su encabezado quién revisó y cuándo. El aviso de borrador desaparece del Explorer y de la API.

### Las 25 carreras con más titulados (2025) y su asociación actual

| # | Carrera | Titulados | Ocupaciones CIUO-08 asignadas |
|---|---|---|---|
| 1 | Técnico en Enfermería | 11.804 | 3221 Profesionales de nivel medio de enfermería; 5321 Trabajadores de los cuidados personales en instituciones |
| 2 | Técnico en Administración de Empresas | 9.073 | 3343 Secretarios administrativos y ejecutivos |
| 3 | Psicología | 8.212 | 2634 Psicólogos |
| 4 | Administración de Empresas e Ing. Asociadas | 7.912 | 2421 Analista de gestión y organización; 1219 Gerentes de administración y servicios n.c.o.p. |
| 5 | Trabajo Social | 7.530 | 2635 Profesionales del trabajo social |
| 6 | Ingeniería Comercial | 7.256 | 2421 Analista de gestión y organización; 2631 Economistas |
| 7 | Ingeniería Civil Industrial | 6.607 | 2141 Ingenieros industriales y de producción |
| 8 | Técnico Asistente del Educador de Párvulos | 5.702 | 5311 Cuidadores de niños |
| 9 | Ingeniería en Computación e Informática | 5.098 | 2511 Analista de sistemas; 2512 Desarrollador/a de software; 2514 Programadores de aplicaciones |
| 10 | Derecho | 5.062 | 2611 Abogados; 2612 Jueces; 2619 Profesionales en derecho n.c.o.p. |
| 11 | Enfermería | 4.968 | 2221 Profesional de enfermería |
| 12 | Contador Auditor | 4.543 | 2411 Contador/a |
| 13 | Técnico en Computación e Informática | 3.849 | 3512 Técnicos en asistencia al usuario de TIC; 3511 Técnicos en operaciones de TIC |
| 14 | Técnico en Electricidad y Electricidad Industrial | 3.649 | 3113 Electrotécnicos; 7411 Electricistas de obras y afines |
| 15 | Técnico en Gastronomía y Cocina | 3.591 | 3434 Chefs; 5120 Cocinero/a |
| 16 | Técnico en Logística | 3.432 | 4321 Empleados de control de abastecimientos e inventario; 4323 Empleados de servicios de transporte |
| 17 | Ingeniería Industrial | 3.431 | 2141 Ingenieros industriales y de producción |
| 18 | Ingeniería en Mecánica Automotriz | 3.322 | 2144 Ingenieros mecánicos; 3115 Técnicos en ingeniería mecánica |
| 19 | Técnico en Mecánica Automotriz | 3.089 | 7231 Mecánicos y reparadores de vehículos de motor |
| 20 | Ingeniería en Electricidad | 2.946 | 2151 Ingeniero/a electricista; 3113 Electrotécnicos |
| 21 | Kinesiología | 2.656 | 2264 Fisioterapeutas |
| 22 | Administración Pública | 2.638 | 2422 Especialistas en políticas de administración |
| 23 | Técnico en Construcción y Obras Civiles | 2.571 | 3112 Técnicos en ingeniería civil; 3123 Supervisores de la construcción |
| 24 | Medicina | 2.560 | 2211 Médico/a generalista; 2212 Médicos especialistas |
| 25 | Técnico Asistente del Educador Diferencial | 2.533 | 5312 Auxiliares de maestros |

### Puntos dudosos para discutir primero

- **Derecho → 2612 Jueces:** un recién egresado no llega a juez. ¿Dejar solo 2611 y 2619?
- **Técnico en Administración de Empresas → solo 3343 (secretarios administrativos y ejecutivos):** ¿suman 3341 (supervisores de oficina) o 4110 (oficinistas generales)?
- **Ingeniería Comercial → 2631 Economistas:** en Chile la carrera es más de gestión que de economía. ¿Pesa igual que 2421?
- **Técnico en Enfermería → 3221 y 5321 en partes iguales:** ¿la mayoría trabaja como técnico de nivel medio (3221) o en cuidados (5321)?
- **Técnico Asistente del Educador de Párvulos → 5311 Cuidadores de niños:** ¿o 5312 Auxiliares de maestros, como el de educación diferencial?
- **Ingeniería en Mecánica Automotriz y en Electricidad:** combinan un grupo profesional (21xx) con uno técnico (31xx). Son "ingenierías de ejecución": ¿qué grupo corresponde mejor?
- **Tecnología Médica → 3211 y 3212:** en Chile es una carrera profesional de 5 años. ¿Debería ir a un grupo profesional (22xx)?

---

## 1b. Revisar la correspondencia disciplina → ocupación (Argentina) · prioridad alta

**Estado:** pendiente · **Responsable:** a definir · **Bloquea:** la publicación de las brechas de
habilidades de Argentina.

- **Archivo:** `config/reference/carreras_argentina_ciuo.yaml` (37 disciplinas, borrador sin revisar).
- **Para revisarla:** el Explorer, sección "Correspondencia carrera → ocupación" con país Argentina,
  o `GET /api/v1/graduates/crosswalk?country=ARG&format=csv` (una fila por disciplina, nivel y ocupación).
- **Puntos dudosos:**
  - "Economía y Administración" (la disciplina con más egresados) se reparte entre contadores, economistas
    y administradores. ¿Conviene ponderar en lugar de repartir en partes iguales?
  - "Paramédicas y Auxiliares de la Medicina" mezcla enfermería, nutrición, kinesiología y otras. Sin el
    detalle por carrera, el reparto es grueso.
  - "Otras Ciencias Aplicadas" y "Otras Ciencias Sociales" quedan sin ocupación: ¿está bien?
  - "Educación" de pregrado: ¿profesorados (2330, 2341) o auxiliares (5312)?
- Al terminar, cambiar `reviewed: false` por `reviewed: true` en el archivo.

---

## 1c. Revisar la correspondencia carrera → ocupación (Uruguay) · prioridad alta

**Estado:** pendiente · **Responsable:** a definir · **Bloquea:** la publicación de las brechas de
habilidades de Uruguay.

- **Qué revisar:** las reglas de `data/scripts/referencias/reglas_carreras_uruguay.yaml` (107 reglas
  para las 534 carreras). Se ven aplicadas en el Explorer (sección "Correspondencia carrera →
  ocupación", país Uruguay) o en `GET /api/v1/graduates/crosswalk?country=URY&format=csv`.
- **Cómo corregir:** editar la regla y regenerar el archivo (ver
  `data/scripts/referencias/README.md`, sección 5), no editar el archivo generado.
- **Puntos dudosos:**
  - **Licenciatura en Diseño de Comunicación Visual (UdelaR), 2024:** 366 egresados, contra 11 a 14
    en los años anteriores, con 2.695 matriculados. Hace crecer la oferta de diseñadores gráficos
    (2166) un 80 % anual, y esas habilidades quedan como las de menor brecha. ¿Cambio en el registro o
    error del anuario? Conviene consultarlo al MEC antes de publicar.
  - **Contador Público:** cae de 1.159 (2020) a 617 (2024) sumando todas las instituciones, y arrastra
    las habilidades contables al tope de las brechas. ¿Es real o cambió algún plan de estudios?
  - **Cambios de nombre:** "Doctor en Derecho" pasa a "Abogacía", "Escribano Público" a "Notariado" y
    "Arquitecto" a "Arquitectura". Llevan a las mismas ocupaciones, así que se compensan; un cambio
    de nombre hacia otra ocupación sí movería la oferta.
  - **Licenciatura en Educación Física:** ¿profesores (2330), entrenadores (3422) o ambos, como ahora?
- Al terminar, poner `revisada: true` en el archivo de reglas y regenerar.

---

## 2. Otras decisiones pendientes

| Tema | Decisión | Dónde se cambia |
|---|---|---|
| Brechas: crecimientos o niveles | Hoy la brecha compara crecimientos anuales (empleo vs. titulados). En Chile la oferta domina porque la demanda viene por gran grupo y casi no varía. La alternativa es comparar niveles (titulados por cada mil ocupados). | `analytics.yaml → skill_gaps` (requiere desarrollo) |
| Brechas: cómo presentarlas | Cuántas mostrar (¿20?) y con cuántas ocupaciones mínimas por habilidad (hoy 3) | `app.yaml → skills.gap_ranking_min_occupations` |
| ISE: tope por grupo en los rankings | Hoy hay como mucho 2 ocupaciones por subgrupo de 2 dígitos. Con 1 dígito, el top 20 no se llenaría de directivos. | `app.yaml → employability.ranking.group_digits` |
| Tasa de inserción del ISE | Enviar la solicitud de la base de empleabilidad por carrera al SIES (`docs/solicitud_sies_empleabilidad.md`). Cuando llegue: ¿se usa solo para Chile, aunque los rankings comparen los 3 países? | `analytics.yaml → employability.dimensions.insertion_rate` |
| Desajuste educación-ocupación en Uruguay | Los años 2023 y 2025 de ILOSTAT clasifican como "nivel 0" a entre 11 % y 16 % de los ocupados (2 % en 2022 y 2024), y la subcalificación salta 7 puntos. ¿Consultar a INE Uruguay u OIT, o excluir esos años? | `config/reference/isco_education_requirements.yaml` |
| ISE: exclusión dudosa | ¿Excluir 9624 (acarreadores de agua y recolectores de leña) como ocupación de subsistencia? | `catalog.yaml → excluded_occupations` |
| Argentina: demanda por ocupación | La EPH es urbana y la muestra por ocupación es chica. ¿Usar promedio móvil de 3 años o sumar los registros del SIPA? | `analytics.yaml → employability.dimensions` |
| Titulados de Argentina y Uruguay | Buscar el archivo oficial descargable (Departamento de Información Universitaria; Ministerio de Educación y Cultura) para que esos países tengan brechas | Nuevo perfil en `config/datasets/` |
