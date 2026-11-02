# Observa Tendencias · frontend minimal + visual

Segunda versión del frontend, con el mismo backend y los mismos datos que `../frontend`. Cambia la
experiencia: cada pantalla responde una pregunta con un gráfico grande y el menú es mínimo.

- Una barra superior: 10 secciones (Panorama, Sectores, Ocupaciones, Habilidades, Tendencias, Pulso
  laboral, Moctezuma, Ludita, Reina Roja, Sísifo), buscador global, alertas y cuenta. Alertas, Metodología y Administración
  están en el menú de la cuenta.
- Buscador (⌘K / Ctrl+K): no muestra nada hasta que se escribe. Cada palabra tiene que coincidir con
  el comienzo de una palabra del nombre, en cualquier orden y sin importar tildes ("ganado asesorar").
  Un número es un código CIUO ("2221", "ciuo 33") y el nombre de un país ("chile", "arg") abre las
  ocupaciones en ese país. Entiende nombres locales ("remisero", "gasfíter") y no le importan
  plural ni género ("enfermera" encuentra "enfermería"). Resultados agrupados (indicadores, sectores, ocupaciones, habilidades y
  secciones), con lo que coincide en negrita. La misma regla usa el backend en `/occupations?q=` y
  `/skills?q=` (`app/core/search.py`).
- Panorama entra en una sola pantalla en computadoras (el gráfico toma el alto que queda); en el
  teléfono se desplaza normalmente. Debajo, la sección "Brecha generacional": una tarjeta por país
  con la frase de `GET /generational-gap` y la evolución de la brecha.
- Tendencias suma las burbujas "Las ocupaciones en movimiento" (`MotionChart.tsx`): gran grupo ×
  país, animadas año a año, con selector del eje vertical y tabla de datos.
- Indicadores temáticos, cada uno en su pantalla (selector de año, por ahora, solo en Sísifo):
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
- Salario: primero en USD (tipo de cambio de mercado) y debajo en USD PPA, que es lo que usa el ISE.
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
  desde una ficha. Muestra la respuesta, un aviso si algún número no coincide con los datos y
  enlaces a las páginas con esos datos. Si la pregunta es ambigua (varias ocupaciones, falta el país),
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
- `src/app/(app)/{panorama,sectores,ocupaciones,habilidades,tendencias,pulso}`: las pantallas
  principales; `{moctezuma,ludita,reina-roja,sisifo}`: los indicadores temáticos, con sus gráficos en
  `src/components/minimal/` (`MoctezumaCharts`, `LuditaCharts`, `SisyphusChart`, `MotionChart`).
- `src/components/minimal/AssistantDock.tsx` y `src/app/api/assistant`: el asistente. La ruta
  reenvía la pregunta al backend con la sesión (la cookie no es legible desde el navegador).
- `src/app/api/search`: búsqueda del encabezado (consulta el backend desde el servidor, interpreta
  códigos CIUO y países, y ordena los resultados). Las reglas de coincidencia están en
  `src/lib/utils/search.ts`.
- Ficha de ocupación, Alertas, Metodología y Administración vienen del frontend original con el
  encabezado nuevo.
