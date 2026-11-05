# Observa Tendencias · frontend minimal + visual

Segunda versión del frontend, con el mismo backend y los mismos datos que el frontend original. Cambia la
experiencia: cada pantalla responde una pregunta con un gráfico grande y el menú es mínimo.

- Una barra superior con 5 secciones, buscador global, alertas y cuenta. Las secciones con pestañas las
  muestran debajo (`src/components/minimal/nav.ts` y `SubNav.tsx`):
  - **Panorama:** Indicadores · Brecha generacional · Ocupaciones en movimiento.
  - **Empleo y habilidades:** Sectores · Ocupaciones · Brechas de habilidades · Titulados y proyecciones ·
    Indicadores por sector · Género.
  - **Pulso laboral.**
  - **Experimental:** Moctezuma · Ludita · Reina Roja · Sísifo.
  - **Metodología y fuentes:** también en el menú de la cuenta, junto con Alertas y Administración.
- Buscador (⌘K / Ctrl+K): no muestra nada hasta que se escribe. Cada palabra tiene que coincidir con
  el comienzo de una palabra del nombre, en cualquier orden y sin importar tildes ("ganado asesorar").
  Un número es un código CIUO ("2221", "ciuo 33") y el nombre de un país ("chile", "arg") abre las
  ocupaciones en ese país. Entiende nombres locales ("remisero", "gasfíter") y no le importan
  plural ni género ("enfermera" encuentra "enfermería"). También encuentra las ocupaciones ESCO
  ("electricista de automóviles"), que abren la ficha de su grupo CIUO. Resultados agrupados (indicadores, sectores, ocupaciones, habilidades y
  secciones), con lo que coincide en negrita. La misma regla usa el backend en `/occupations?q=` y
  `/skills?q=` (`app/core/search.py`).
- Panorama → Indicadores entra en una sola pantalla en computadoras (el gráfico toma el alto que queda); en el
  teléfono se desplaza normalmente. Si el indicador tiene tendencia, suma la proyección punteada y las
  tarjetas de tendencia; si no, muestra la serie observada. `/tendencias` redirige acá.
- Panorama → Brecha generacional: una tarjeta por país con la frase de `GET /generational-gap` y la
  evolución de la brecha.
- Panorama → Ocupaciones en movimiento (`MotionChart.tsx`): burbujas por gran grupo × país, animadas
  año a año, con selector del eje vertical y tabla de datos. Cada grupo despliega sus ocupaciones.
- Género: titulados y ocupados por sexo, brechas y diagnóstico de paridad (`GenderView.tsx`).
- Indicadores por sector suma Argentina con CEP-XXI: puestos, % de mujeres, USD, USD PPA, pesos, salario
  real y el dólar oficial mayorista del último día hábil anterior, con su fecha (`SectorKpisView.tsx`).
- Ficha de ocupación: cada habilidad dice Esencial u Opcional, sin puntajes, y se ven primero las 10 más
  compartidas. "¿Cómo se leen estas habilidades?" lo explica y lista las ocupaciones ESCO del grupo; cada
  una muestra sus propias habilidades (`?esco=`).
- Metodología y fuentes → Fuentes de datos: de dónde sale cada salario y cada indicador de género, cómo se
  calcula y qué se extrapola (`GET /sources/notes`), junto con el estado de cada fuente.
- Indicadores experimentales, cada uno en su pantalla (selector de año, por ahora, solo en Sísifo):
  - **Moctezuma:** ranking, plano Ritmo × Capacidad con guía de lectura y el gráfico histórico de
    1518–1568 con sus hitos (1519, 1520, 1521, 1531) y fuentes.
  - **Ludita:** casos históricos frente a hoy, cuadrante de caminos (tejedor, cajero, otras causas,
    fuera del alcance) y ranking.
  - **Reina Roja:** ranking por novedades por año; al tocar una fila se ve qué entró y salió del
    perfil (▼/▲ despliega la lista completa). Filtro por carrera.
  - **Sísifo:** grandes grupos con su definición y enlaces a las ocupaciones de cada grupo,
    cuadrante y vista por país.
  - Los textos que explican cada gráfico se arman con los parámetros de la metodología y los datos
    (`src/lib/methodology/twoSided.ts`), así que siguen siendo correctos si cambian.
- En Ocupaciones, Sectores y Habilidades la ficha de la derecha queda fija al desplazar la lista.
  En Ocupaciones, "Abrir ficha" es un botón y cada fila tiene una flecha que abre la ficha directo.
- Los términos técnicos (Escalado, Aporte al ISE, Salario) tienen una explicación al pasar el mouse.
  Esos textos y el formato de las unidades vienen de la API (`texts`), no del frontend.
- Salario: primero en USD (tipo de cambio oficial promedio del año) y debajo en USD PPA, que es lo que usa el ISE.
- Sin banners: el título del gráfico es el título de la página. Los filtros son una línea sobre el
  gráfico; los chips de país son también la leyenda y cada línea tiene su etiqueta al final.
- Columna de lectura a la derecha: último dato, qué cambió, fuente y "¿Cómo se calcula?".
- Carga manual de datos (Administración → Datos):
  - Botones para bajar la plantilla (Excel con los códigos válidos, o CSV) y dos archivos de ejemplo, uno que pasa y otro con errores.
  - Los errores se muestran agrupados ("Países fuera del catálogo: 2 filas (2, 9) · «BRA», «PER» — Usá ARG, CHL o URY"), con el detalle fila por fila debajo.
  - Si el archivo repite valores de fuentes oficiales, avisa y pide marcar una casilla antes de cargar.
  - Las descargas pasan por `src/app/api/datasets/download`.
- Asistente: una pestaña fija en el borde derecho abre un panel de conversación. Manda la pregunta
  con lo que se está mirando (país, ocupación y sector de la URL), así "¿y en Uruguay?" funciona
  desde una ficha. Muestra la respuesta, un aviso si algún número no coincide con los datos,
  el enlace a cada ocupación que nombra, las páginas con esos datos y, aparte, las fuentes de afuera. Si la pregunta es ambigua (varias ocupaciones, falta el país),
  muestra botones para elegir. Mientras responde, el botón de enviar pasa a "Detener": corta
  la pregunta, el backend detiene el modelo y no cuenta para el límite. La conversación sigue al
  cambiar de página. El nombre, los
  textos y las preguntas de ejemplo vienen de `GET /assistant` (`app.yaml → assistant`). Si el
  asistente está apagado o el backend no responde, la pestaña no aparece.

## Correr en local

```bash
npm install
npm run dev        # http://localhost:3001 (el frontend original usa el 3000)
```

Necesita el backend en `NEXT_PUBLIC_API_URL` (`.env.local`, por defecto http://localhost:8010) y un
usuario del backend para entrar (`python -m app.jobs.create_user`).

## Dónde está cada cosa

- `src/components/minimal/`: encabezado, buscador, gráfico de líneas (etiquetas directas, tooltip,
  proyección con intervalo), selector de indicador, controles segmentados y piezas de diseño.
- `src/app/(app)/{panorama,sectores,ocupaciones,habilidades,pulso}`: las pantallas
  principales; `{moctezuma,ludita,reina-roja,sisifo}`: los indicadores experimentales, con sus gráficos en
  `src/components/minimal/` (`MoctezumaCharts`, `LuditaCharts`, `SisyphusChart`, `MotionChart`).
- `src/components/minimal/AssistantDock.tsx` y `src/app/api/assistant`: el asistente. La ruta
  reenvía la pregunta al backend con la sesión (la cookie no es legible desde el navegador).
- `src/app/api/search`: búsqueda del encabezado (consulta el backend desde el servidor, interpreta
  códigos CIUO y países, y ordena los resultados). Las reglas de coincidencia están en
  `src/lib/utils/search.ts`.
- Ficha de ocupación, Alertas, Metodología y Administración vienen del frontend original con el
  encabezado nuevo.
