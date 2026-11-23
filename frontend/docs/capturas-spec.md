# Especificación de Diseño – Observa Tendencias

**Producto:** Observa Tendencias (observatorio de datos de empleo y educación para Argentina, Uruguay y Chile)
**Stack objetivo:** Next.js + Tailwind CSS
**Estado:** Solo análisis y documentación. No se modifica código de la aplicación.
**Fuente de los datos visuales:** 8 capturas PNG en `frontend/src/capturas/`
**Tokens de diseño referencia:** `frontend/src/styles/design-tokens.css` (valores aproximados, no exactos de las imágenes)

---

## Tabla resumen

| Captura | Pantalla | Ruta del nav | Relación con la par | Bloques principales |
|---------|----------|--------------|---------------------|---------------------|
| 1. `inicio.png` | Inicio (dashboard) | `/inicio` — Inicio | — | Header, nav, saludo, 4 KPIs, Accesos rápidos (5 tarjetas), Últimas tendencias |
| 2. `tendencias.png` | Tendencias | `/tendencias` — Tendencias | Distinta pantalla a la 1 (no es otro estado) | Hero, filtros (país/sector/ocupación/desde/hasta), frecuencia, grupo de indicadores, chips rápidos, gráfico de línea |
| 3. `sectores1.png` | Sectores (parte superior) | `/sectores` — Sectores | Parte superior de la misma pantalla que la 4 | Hero, filtros, pills de sector, 4 KPIs, barra progreso ISE, ranking sectorial inicial |
| 4. `sectores2.png` | Sectores (parte inferior / scroll) | `/sectores` — Sectores | Continuación por scroll de la 3 | Ítems 3-4 del ranking, tarjetas de definición, gráfico barras intersectorial |
| 5. `ocupaciones1.png` | Ocupaciones (tabla, filas 1-2) | `/ocupaciones` — Ocupaciones | Parte superior de la misma pantalla que la 6 | Hero, filtros, nota metodológica, tabla ranking filas 1-2 |
| 6. `ocupaciones2.png` | Ocupaciones (tabla, filas 3-5 + paginación) | `/ocupaciones` — Ocupaciones | Continuación por scroll de la 5 | Filas 3-5, paginación "Mostrando 5 de 5" |
| 7. `habilidades1.png` | Habilidades / Brechas (resumen) | `/formacion` — Habilidades | Parte superior de la misma pantalla que la 8 | Hero, pestañas Brechas/Proyecciones, filtros, pestañas Mayores/Menores/Todas, 4 KPIs |
| 8. `habilidades2.png` | Habilidades / Brechas (matriz detallada) | `/formacion` — Habilidades | Continuación por scroll de la 7 | Tabla Matriz Comparativa de Brechas (página 1 de 17), paginación |

> **Relación pares (imágenes pares):** En los 3 pares (sectores, ocupaciones, habilidades), la imagen 2 es la misma pantalla que la imagen 1 en estado de **scroll hacia abajo** (contenido adicional / continuación). La captura 2 (`tendencias.png`) es una pantalla distinta de la captura 1 (`inicio.png`), no un estado alternado.

---

## Elementos comunes a todas las pantallas

### AppHeader (reutilizable, existe en `AppHeader.tsx`)
- **Barra superior:** `border-b border-gray-200 bg-white`, altura fija, contenedor `max-w-7xl`, `px-6 py-4`.
- **Logo:** texto "LOGO" (placeholder), `text-2xl font-bold text-gray-700`, con ícono de cuadrícula a la izquierda.
- **Grupo derecho (flex, gap-4):**
  1. Botón "Administración" + `ChevronDown`: `rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-slate-200`.
  2. Botón campana (notificaciones): `relative rounded-md p-2 text-blue-700 hover:bg-slate-100`, ícono `Bell` (size-5). Badge rojo `bg-red-600` con contador cuando `unreadAlerts > 0` (máx "9+").
  3. Perfil de usuario: avatar azul `bg-blue-400 text-white` (ícono `User`), nombre `text-sm font-semibold text-gray-900`, rol `text-xs text-gray-500`. En capturas se lee "Santiago Morales / Administrador".
- **Colores observados:** fondo blanco, texto gris oscuro, primario azul (#172bc4 aproximado), borde gris claro.

### MainNav (reutilizable, existe en `MainNav.tsx`)
- **Nav horizontal scrollable:** `grid auto-cols-fr grid-flow-col overflow-x-auto bg-gray-200`.
- Ítems: Inicio, Panorama regional, Sectores, Ocupaciones, Habilidades, Tendencias.
- Activo: fondo `bg-blue-600`, texto blanco, `font-medium`. Inactivo: texto `text-gray-900`, hover `hover:bg-gray-300`.
- Cada ítem: `min-w-36 px-4 py-6 text-center text-sm`.

### PageHero (reutilizable, existe en `PageHero.tsx`)
- **Sección hero:** `bg-blue-600 px-6 py-14 text-center text-white`.
- `h1`: `text-4xl font-bold tracking-tight`.
- `p` descripción: `mx-auto mt-4 max-w-3xl text-base leading-relaxed text-blue-50`.
- En capturas reales el texto del cuerpo es **Lorem ipsum** (placeholder), salvo en Inicio donde hay texto real.

### ChartCard (reutilizable, existe en `ChartCard.tsx`)
- `border border-gray-300 bg-white p-4`.
- `h3` título: `text-lg font-semibold text-gray-900`.
- Subtítulo opcional: `mt-1 text-sm text-gray-600`.
- Leyenda: `ul mt-3 flex flex-wrap gap-4 text-sm text-gray-600`, ítems con punto de color `size-3 rounded-full`.
- Footer: `mt-4 flex ... border border-gray-300 px-4 py-3 text-sm`, con "Fuente", "Actualización", y link "Ver metodología" (`text-blue-600 hover:underline`).

### TrendLineChart (reutilizable, existe en `TrendLineChart.tsx`)
- Contenedor `h-72 w-full`, `ResponsiveContainer` de recharts.
- `CartesianGrid` stroke `#e5e7eb`, solo horizontal.
- Ejes sin línea, ticks `#4b5563` fontSize 12.
- Tooltip con formato de valor.

### KpiCard (reutilizable, existe en `KpiCard.tsx`)
- `border border-gray-300 bg-white p-4`.
- Label: `text-sm text-gray-700`.
- Valor: `text-2xl font-semibold text-gray-900`.
- Pill de variación: `rounded-full px-3 py-1 text-xs font-medium`, negativo `bg-gray-600 text-white`, positivo `bg-gray-100 text-gray-800`.
- Caption opcional: `mt-1 text-xs text-gray-500`.

### FilterBar (reutilizable, existe en `FilterBar.tsx`)
- `grid gap-4`, columnas `repeat(auto-fit,minmax(14rem,1fr))`.
- Selects: `w-full appearance-none border-b border-gray-400 bg-slate-50 px-4 py-3 pr-10 text-sm text-gray-900`.
- Ícono `ChevronDown` a la derecha.

### IndicatorSidebar (reutilizable, existe en `IndicatorSidebar.tsx`)
- `h2` "Indicadores": `bg-gray-300 px-4 py-3 text-center text-sm font-semibold text-gray-900`.
- Lista de enlaces con borde izquierdo `border-l-4`, activo `border-blue-600 bg-indigo-50 font-medium text-blue-700`.

### Design tokens (design-tokens.css) — valores aproximados observados en capturas
- Fondo canvas: `#ffffff`
- Superficie alt: `#f5f7fd` / superficie: `#fafbfe` / surface-2: `#edf2fc`
- Heading: `#050c1e`, cuerpo: `#0f172a`, muted: `#475569`
- Marca/primario: `#172bc4` (azul), hover `#0f00a9`
- Borde/línea: `#aebdde`
- País ARG: `#38bdf8` (cian claro), CHL: `#b91c1c` (rojo), URY: `#d97706` (ámbar)
- Éxito: `#16a34a`, advertencia: `#d97706`, peligro: `#dc2626`, info: `#2563eb`
- Sombra suave: `rgb(0 0 0 / 0.08)`

> **Nota:** Los hex indicados son aproximaciones extraídas de `design-tokens.css` y del aspecto visual de las capturas. No se midieron píxeles de las imágenes.

### Tipografía (relativa)
- h1 (héroe): `text-4xl` (~36-40px), `font-bold`, `tracking-tight`.
- h2 (secciones): `text-2xl` / `text-xl` aproximado, `font-bold`.
- h3 (títulos de cards/gráficos): `text-lg` (~18px), `font-semibold`.
- Body: `text-base` (~16px), `leading-relaxed`.
- Labels/captions: `text-sm` (~14px) y `text-xs` (~12px).
- Valores KPI: `text-2xl` (~24px), `font-semibold`.
- Pesos: `font-bold` (títulos), `font-semibold` (valores, subtítulos), `font-medium` (pills, tabs), `font-normal` (cuerpo).

---

## Detalle por captura

### 1. `inicio.png` — Pantalla Inicio (ruta `/inicio`)

**Estructura visual (arriba a abajo):**
1. AppHeader (LOGO, Administración, campana, usuario Santiago Morales).
2. MainNav (pestaña "Inicio" activa, azul).
3. Saludo: "¡Hola Santiago!" (`text-2xl font-bold`).
4. Subtítulo: "Estos son los datos más destacados del observatorio. Podés explorar las secciones del menú o usar los accesos rápidos" (`text-gray-600`).
5. Fila de 4 KPI cards (grid 4 columnas).
6. Sección "Accesos rápidos": 5 tarjetas gris (2 arriba, 2 abajo, 1 grande abajo).
7. Sección "Últimas tendencias": lista con viñetas azules, link "Ver todas" a la derecha.

**Texto transcrito:**
- "¡Hola Santiago!"
- "Estos son los datos más destacados del observatorio. Podés explorar las secciones del menú o usar los accesos rápidos"
- KPI 1: "TASA DE DESOCUPACIÓN" | "7,38%" | "ARG, CHL, URY" | "2025" | "+0,2 pp"
- KPI 2: "TASA DE ACTIVIDAD" | "61,91%" | "ARG, CHL, URY" | "2025" | "+0,1 pp"
- KPI 3: "POBLACIÓN QUE USA INTERNET" | "89,67%" | "ARG, CHL, URY" | "2024" | "+0,4 pp"
- KPI 4: "FINALIZACIÓN DE SECUNDARIA BÁSICA" | "94,99%" | "ARG, CHL, URY" | "2023" | "-3,8 pp"
- Accesos rápidos: "Panorama regional / Comparar países", "Sectores / Analizar tendencias", "Ocupaciones / Investigar una ocupación", "Habilidades / Explorar brechas de habilidades", "Tendencias / Analizar tendencias"
- Últimas tendencias: "Ver todas"; items con viñeta (títulos de noticias/alertas con país y fecha, ej. "Variación significativa - Inflación - Datos Argentina (Series de Tiempo)...")

**KPIs:**
| Label | Valor | Unidad | Variación pill | Color pill |
|-------|-------|--------|----------------|------------|
| TASA DE DESOCUPACIÓN | 7,38 | % | +0,2 pp | gris claro (positivo) |
| TASA DE ACTIVIDAD | 61,91 | % | +0,1 pp | gris claro |
| POBLACIÓN QUE USA INTERNET | 89,67 | % | +0,4 pp | gris claro |
| FINALIZACIÓN DE SECUNDARIA BÁSICA | 94,99 | % | -3,8 pp | gris oscuro (negativo) |

**Componentes:** AppHeader, MainNav, KpiCard (x4), tarjetas de acceso rápido (nuevo), lista de tendencias (nuevo).
**Ambigüedades:** Texto de los items de "Últimas tendencias" se lee parcialmente; algunas fechas son inciertas.

---

### 2. `tendencias.png` — Pantalla Tendencias (ruta `/tendencias`)

**Relación con captura 1:** Es una pantalla distinta, no otro estado de Inicio.

**Estructura visual:**
1. Hero azul `bg-blue-600` con texto Lorem ipsum (placeholder, multilinea).
2. Pestaña "Tendencias" (azul, ancha).
3. Cuerpo Lorem ipsum.
4. FilterBar: PAÍSES, SECTOR, OCUPACIÓN, DESDE, HASTA.
5. FRECUENCIA: Trimestral | Mensual | Anual (Mensual activa, pill azul).
6. GRUPO DE INDICADORES: Socioeconómicos 4 | Laborales 5 | Educativos 3.
7. Chips rápidos: "Ver todos (5)", "Crecimiento del PBI" (activo, negro), "Actividad económica interanual", "Inflación", "PBI per cápita".
8. Badge info: "Indicador activo en visualización: Variación anual del PBI a precios constantes - Unidad: porcentaje".
9. ChartCard "Tendencia" con leyenda "Tendencia actual" / "Proyección".
10. Gráfico de línea (recharts), meses Ene-Dec en X, 0-1000 en Y.
11. Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

**Texto transcrito:**
- Héroe: "Lorem ipsum dolor sit amet..." (repetido, placeholder).
- Filtros: "PAÍSES", "Todos [3]", "ARG", "CHI", "URY"; "SECTOR", "Tecnología"; "OCUPACIÓN", "Analista de sistemas"; "DESDE", "2024"; "HASTA", "2025".
- "FRECUENCIA", "Trimestral", "Mensual", "Anual".
- "GRUPO DE INDICADORES:", "Socioeconómicos 4", "Laborales 5", "Educativos 3".
- Chips: "Ver todos (5)", "Crecimiento del PBI", "Actividad económica interanual", "Inflación", "PBI per cápita".
- Badge: "Indicador activo en visualización: Variación anual del PBI a precios constantes - Unidad: porcentaje".
- Chart: "Tendencia", leyenda "Tendencia actual", "Proyección".
- Footer: "Actualización: 12-05-2025", "Ver fuente y metodología".

**Gráfico:**
- Tipo: línea (TrendLineChart).
- Series: "Tendencia actual" (gris sólido con puntos), "Proyección" (gris punteado/más claro).
- Eje X: Ene, Feb, Mar, ..., Dic.
- Eje Y: 0, 100, ..., 1000.
- Tooltip: sí (recharts).
- Grid: horizontal solo, `#e5e7eb`.

**Componentes:** AppHeader, MainNav, PageHero (texto Lorem), FilterBar, chips de frecuencia (nuevo), grupo de indicadores (nuevo), chips rápidos (nuevo), badge info (nuevo), ChartCard, TrendLineChart.
**Ambigüedades:** El texto del héroe y cuerpo es Lorem ipsum; no se sabe si es definitivo.

---

### 3. `sectores1.png` — Pantalla Sectores (ruta `/sectores`, parte superior)

**Relación con captura 4:** Misma pantalla (`/sectores`). La 4 es continuación por scroll.

**Estructura visual:**
1. AppHeader (pestaña "Sectores" activa).
2. Hero azul "Sectores" + Lorem ipsum.
3. FilterBar: PAÍSES (Todos [3], ARG/CHI/URY), DESDE 2024, HASTA 2025.
4. Pills de SECTOR: Tecnología, Energía, Salud, **Economía del Conoc (activo, fondo negro)**, Turismo.
5. 4 KPI cards en fila.
6. Barra de progreso "Índice orientativo por ocupación".
7. Sección "Índice de empleabilidad (ISE) sectorial" con ranking inicial (ítems 1 y 2).

**Texto transcrito:**
- "Sectores" + Lorem ipsum.
- Filtros: "PAÍSES", "Todos [3]", "ARG", "CHI", "URY", "DESDE", "2024", "HASTA", "2025".
- Pills sector: "Tecnología", "Energía", "Salud", "Economía del Conoc" (activa), "Turismo".
- KPI 1: "ISE PROMedio SECTOR ECONOMÍA DEL CONOCIMIENTO" | "52,6" | "/100 pts" | "+2,7 pp vs promedio 2024".
- KPI 2: "OCUPACIÓN LÍDER (RANK #1)" | "Analista de Gestión & Organización" | "56,1" | "CIUO 3212" | link "Ver desglose ISE de la ocupación".
- KPI 3: "BRECHA SALARIAL PPA PROMEDIO" | "USD 2.005" | "/ mes" | "+38,1% vs Salario Medio Nac. 2024".
- KPI 4: "RIESGO DE AUTOMATIZACIÓN (EXPOSICIÓN A IA GENERATIVA)" | "0,51" | "/100" | "Nivel Medio Controlado".
- "Índice orientativo por ocupación:" + fórmula + barra progreso con porcentajes (Demanda 35%, Salario PPA 25%, Tasa de inserción 20%, Exposición a IA 15%).
- "Índice de empleabilidad (ISE) sectorial" + descripción + link "Ver desglose completo en Ocupaciones →".
- Ítem 1: "1. Demanda Neta Sectorial" | "Paso eff: 48,7%" | barra | "58,2 /100" | "+8,8% anual".
- Ítem 2: "2. Nivel Salarial PPA Sectorial" | "Paso eff: 33,3%" | barra | "54,4 /100" | "Promedio regional: USD 1.450".

**KPIs:**
| Label | Valor | Unidad | Variación | Color |
|-------|-------|--------|-----------|-------|
| ISE Promedio Sector Economía del Conocimiento | 52,6 | /100 pts | +2,7 pp vs promedio 2024 | — |
| Ocupación líder (Rank #1) | Analista de Gestión & Organización | 56,1 (CIUO 3212) | — | — |
| Brecha salarial PPA promedio | USD 2.005 | / mes | +38,1% vs Salario Medio Nac. 2024 | — |
| Riesgo de automatización (IA generativa) | 0,51 | /100 (Escala 0 a 1) | — | "Nivel Medio Controlado" |

**Tablas/listados:** Ranking ISE sectorial con barras de progreso horizontal, valor a la derecha, variación anual.
**Componentes:** AppHeader, MainNav, PageHero, FilterBar, pills de sector (nuevo), KpiCard (x4), barra progreso (nuevo), listado ranking con barras (nuevo).
**Ambigüedades:** "Economía del Conoc" parece texto truncado ("Economía del Conocimiento").

---

### 4. `sectores2.png` — Pantalla Sectores (ruta `/sectores`, continuación scroll)

**Relación con captura 3:** Misma pantalla, scroll hacia abajo.

**Estructura visual:**
1. Continuación ranking: ítems 3 y 4.
2. Tarjetas de definición: "Definición de Salario PPA", "Índice de Exposición a IA", "Gobernanza de Calibración".
3. ChartCard "Comparativa Intersectorial de Empleabilidad (ISE 2025)".
4. Gráfico de barras horizontales intersectorial.
5. Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

**Texto transcrito:**
- Ítem 3: "3. Tasa de Inserción de Graduados" | badge "En calibración" | "Peso redistribuido" | nota + texto pequeño.
- Ítem 4: "4. Riesgo de automatización (exposición a IA generativa) sectorial" | "Paso eff: 20,0%" | barra | "42,0 /100" | "-12,6% ajuste neto".
- "Ver fuente y metodología" (x2).
- Tarjetas: "Definición de Salario PPA", "Índice de Exposición a IA", "Gobernanza de Calibración" con textos descriptivos.
- Chart: "Comparativa Intersectorial de Empleabilidad (ISE 2025)" | "Promedio Ponderado Regional: 48,6 pts".
- Barras: Tecnología 58,4 /100; Economía del Conocimiento (Activa) 52,6 /100; Salud 48,2 /100; Energía 44,1 /100; Turismo 39,8 /100.
- Footer: "Actualización: 12-05-2025", "Ver fuente y metodología".

**Gráfico:** Barras horizontales, 5 series (sectores), valor numérico al final de cada barra, línea de referencia/promedio.
**Componentes:** Listado ranking (continuación), tarjetas de definición (nuevo), ChartCard + gráfico de barras (nuevo).
**Ambigüedades:** Ninguna relevante.

---

### 5. `ocupaciones1.png` — Pantalla Ocupaciones (ruta `/ocupaciones`, filas 1-2)

**Relación con captura 6:** Misma pantalla (`/ocupaciones`). La 6 es continuación por scroll.

**Estructura visual:**
1. AppHeader (pestaña "Ocupaciones" activa).
2. Hero azul "Ocupaciones" + Lorem ipsum.
3. FilterBar: PAÍSES (Todos [3], ARG activo), DESDE 2024, HASTA 2025.
4. Pills sector: Tecnología, Energía, Salud, **Economía del Conoc (activo, negro)**, Turismo.
5. Tarjeta "Nota Metodológica: Ponderación Dinámica del ISE".
6. Título sección: "Ranking de Ocupaciones y Coeficientes ISE (Sector Salud)".
7. Select orden: "PUNTAJE", "Mayor" (activo, azul), "Menor".
8. Tabla ranking con cabecera y filas 1-2.
9. Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

**Texto transcrito:**
- "Ocupaciones" + Lorem ipsum.
- Filtros: "PAÍSES", "Todos [3]", "ARG" (activo), "CHI", "URY", "DESDE", "2024", "HASTA", "2025".
- Pills sector: igual que sectores1, "Economía del Conoc" activa.
- Nota Metodológica: "Ponderación Dinámica del Índice de Empleabilidad (ISE)..." + desglose de pesos (Demanda neta 35%-46,7%, Salario USD PPA 25%-33,3%, Riesgo IA 15%-20,0%).
- Leyenda pesos: Demanda neta (+46,7%), Salario USD PPA (+33,3%), Riesgo IA (-20,0%), Tasa inserción (en espera de fuente).
- "Ranking de Ocupaciones y Coeficientes ISE (Sector Salud)".
- Orden: "PUNTAJE", "Mayor", "Menor".
- Cabecera tabla: RANK, OCUPACIÓN & CIUO, PAÍS, PUNTAJE ISE, DEMANDA NETA, SALARIO (USD PPA), TASA INSERCIÓN, RIESGO IA, COBERTURA PONDERADA, ACCIÓN.
- Fila 1: "1", "Analista den gestión y organización", "Economía del conocimiento", "CIUO 3212", "ARG", "56,1 pts", "+8,5%", "USD 2.005", "—", "0,46", "Exposición Media", "75%", "Ver ocupación →".
- Fila 2: "2", "Contador/a", "Economía del conocimiento", "CIUO 2221", "ARG", "54,4 pts", "+8,5%", "USD 2.005", "—", "0,51", "Exposición Media", "75%", "Ver ocupación →".

**Tabla:**
- Columnas: 10 (incluyendo ACCIÓN).
- Filas visibles: 2.
- Badges: país ARG (pastilla), cobertura con barra + "75%".
- Acción: botón "Ver ocupación" con flecha.

**Componentes:** AppHeader, MainNav, PageHero, FilterBar, pills sector, tarjeta nota metodológica (nuevo), tabla ranking (nuevo), botón acción (nuevo).
**Ambigüedades:** "Analista den gestión" parece typo de "de gestión".

---

### 6. `ocupaciones2.png` — Pantalla Ocupaciones (ruta `/ocupaciones`, filas 3-5 + paginación)

**Relación con captura 5:** Misma pantalla, scroll hacia abajo.

**Estructura visual:**
1. Filas 3, 4, 5 de la tabla ranking.
2. Paginación: "Mostrando 5 de 5 registros", flechas, página "1" activa, botón "Siguiente".
3. Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

**Texto transcrito:**
- Fila 3: "3", "Profesional de marketing y publicidad", "Economía del conocimiento", "CIUO 2211", "ARG", "53,1 pts", "+8,5%", "USD 2.005", "—", "0,55", "Exposición Media", "75%", "Ver ocupación →".
- Fila 4: "4", "Diseñador/a gráfico y multimedia", "Economía del conocimiento", "CIUO 2166", "ARG", "51,4 pts", "+7,0%", "USD 2.005", "—", "0,49", "Exposición Media", "75%", "Ver ocupación →".
- Fila 5: "5", "Estadístico/a y actuario/a", "Economía del conocimiento", "CIUO 2164", "ARG", "49,1 pts", "+7,0%", "USD 2.005", "—", "0,56", "Exposición Baja", "75%", "Ver ocupación →".
- Paginación: "Mostrando 5 de 5 registros", "<", "1" (activa, negra), "2", "3", "...", "17", "Siguiente →".
- Footer: "Actualización: 12-05-2025", "Ver fuente y metodología".

**Tabla:** 3 filas adicionales, misma estructura que captura 5.
**Paginación:** 17 páginas totales (aunque dice "5 de 5 registros" — ambigüedad, ver preguntas UX).
**Componentes:** Tabla ranking (continuación), paginación (nuevo).
**Ambigüedades:** "Mostrando 5 de 5 registros" vs paginación hasta 17 — contradictorio, incierto.

---

### 7. `habilidades1.png` — Pantalla Habilidades / Brechas (ruta `/formacion`, parte superior)

**Relación con captura 8:** Misma pantalla (`/formacion`, pestaña Brechas de Habilidades). La 8 es continuación por scroll.

**Estructura visual:**
1. AppHeader (pestaña "Habilidades" activa).
2. Hero azul "Habilidades" + Lorem ipsum.
3. Pestañas secundarias: "Brechas de Habilidades" (activa, azul) | "Proyecciones".
4. Cuerpo Lorem ipsum.
5. FilterBar: PAÍSES (Todos [3], ARG activo), SECTOR (Tecnología), OCUPACIÓN (Todas (25)), DESDE 2024, HASTA 2025.
6. Pestañas BRECHAS: "Mayores" (activa, lila) | "Menores" | "Todas".
7. Nota: "65 habilidades con brechas y usadas por al menos 20 ocupaciones en las 3 páginas · 56 con demanda y/o oferta - 2024-2025".
8. Badge info: "La correspondencia carrera - ocupación (CHL, ARG, URY) es un estándar armonizado CNO-08 / CNO con defatificación estadística."
9. 4 KPI cards en fila.
10. (Continuación en captura 8)

**Texto transcrito:**
- "Habilidades" + Lorem ipsum.
- Pestañas: "Brechas de Habilidades" (activa), "Proyecciones".
- Filtros: "PAÍSES", "Todos [3]", "ARG" (activo), "CHI", "URY"; "SECTOR", "Tecnología"; "OCUPACIÓN", "Todas (25)"; "DESDE", "2024"; "HASTA", "2025".
- Pestañas brechas: "Mayores" (activa), "Menores", "Todas".
- Nota: "65 habilidades con brechas y usadas por al menos 20 ocupaciones en las 3 páginas · 56 con demanda y/o oferta - 2024-2025".
- Badge: "La correspondencia carrera - ocupación (CHL, ARG, URY) es un estándar armonizado CNO-08 / CNO con defatificación estadística."
- KPI 1: "BRECHA PROMEDIO NACIONAL" | "-14,2 pp" | "Déficit crítico".
- KPI 2: "MAYOR BRECHA DETECTADA" | "-22,4 pp" | "Uruguay / Tri-Nac".
- KPI 3: "OCUPACIONES IMPACTADAS" | "35" | "Perfiles ocupacionales transferibles".
- KPI 4: "COBERTURA DE MICRODATOS" | "94,6%" | "1658 habilidades analizadas con brecha", badge "Validado".

**KPIs:**
| Label | Valor | Unidad | Variación/tag | Color |
|-------|-------|--------|---------------|-------|
| Brecha promedio nacional | -14,2 | pp | Déficit crítico | — |
| Mayor brecha detectada | -22,4 | pp | Uruguay / Tri-Nac | — |
| Ocupaciones impactadas | 35 | — | Perfiles ocupacionales transferibles | — |
| Cobertura de microdatos | 94,6 | % | 1658 habilidades analizadas con brecha | badge "Validado" |

**Componentes:** AppHeader, MainNav, PageHero, SectionTabs (Brechas/Proyecciones), FilterBar, pestañas Mayores/Menores/Todas (nuevo), KpiCard (x4).
**Ambigüedades:** Texto del cuerpo es Lorem ipsum.

---

### 8. `habilidades2.png` — Pantalla Habilidades / Brechas (ruta `/formacion`, matriz detallada)

**Relación con captura 7:** Misma pantalla, scroll hacia abajo.

**Estructura visual:**
1. Título: "Matriz Comparativa de Brechas" | "Página 1 de 17".
2. Leyenda: brecha Deficit (-) | Superávit (+).
3. Tabla con cabecera y ~7 filas visibles.
4. Paginación: "Mostrando 1 a 9 de 368 registros amortizados", páginas 1, 2, 3, ..., 17, "Siguiente".
5. Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

**Texto transcrito:**
- "Matriz Comparativa de Brechas", "Página 1 de 17".
- Leyenda: "Leyenda brecha: ● Deficit (-)  ○ Superávit (+)".
- Cabecera: HABILIDAD, PAÍS, DEMANDA (%/AÑO), FORMACIÓN (%/AÑO), BRECHA (PP), OCUPACIONES, PRINCIPALES OCUPACIONES, ACCIONES.
- Filas (todas URY, brecha negativa):
  1. "proporcionar documentación técnica" | URY | +4,2% | +20,1% | -15,9 pp | 31 | "Administradores de sistemas..." | checkbox
  2. "lenguaje de programación SAS (SAS language)" | URY | +3,6% | +26,0% | -22,4 pp | 21 | "Programadores de..." | checkbox
  3. "comunicarse de forma efectiva en el sistema sanitario" | URY | +3,4% | +8,6% | -5,3 pp | 26 | "Gerentes de servicios de salud..." | checkbox
  4. "empatiar con el usuario de la asistencia sanitaria" | URY | +3,3% | +8,7% | -5,4 pp | 27 | "Profesional de enfermería..." | checkbox
  5. "contribuir a la continuidad de la asistencia sanitaria" | URY | +3,3% | +3,2% | +0,1 pp | 23 | "Profesionales de enfermería..." | checkbox
  6. "cumplir la legislación reguladora de la asistencia sanitaria" | URY | +3,2% | +4,8% | -1,6 pp | 37 | "Profesionales de enfermería..." | checkbox
  7. "trabajar en entornos multiculturales en la atención sanitaria" | URY | +3,2% | +3,5% | -0,3 pp | 33 | "Gerentes de servicios de salud..." | checkbox
  (más filas truncadas)
- Paginación: "Mostrando 1 a 9 de 368 registros amortizados", "Anterior", "1" (activa negra), "2", "3", "...", "17", "Siguiente".
- Footer: "Actualización: 12-05-2025", "Ver fuente y metodología".

**Tabla:**
- Columnas: 8.
- Filas visibles: ~7 (más filas parciales).
- Badges: país URY.
- Valores de brecha: rojos (negativo/déficit) o verdes (positivo).
- Acción: checkbox por fila.
- Paginación: 17 páginas, 368 registros.

**Componentes:** Tabla matriz (nuevo), paginación (nuevo), checkbox de fila (nuevo).
**Ambigüedades:** "registros amortizados" — término inusual, incierto.

---

## Mapa de componentes

### Existentes (reutilizar sin modificar)
| Componente | Ruta | Usado en capturas |
|------------|------|-------------------|
| AppHeader | `src/components/ui/layout/AppHeader.tsx` | Todas |
| MainNav | `src/components/ui/layout/MainNav.tsx` | Todas |
| PageHero | `src/components/ui/layout/PageHero.tsx` | Todas (héroe azul) |
| SectionTabs | `src/components/ui/navigation/SectionTabs.tsx` | 7 (Brechas/Proyecciones) |
| FilterBar | `src/components/ui/filters/FilterBar.tsx` | 2, 3, 5, 6, 7, 8 |
| KpiCard | `src/components/ui/indicators/KpiCard.tsx` | 1, 3, 4, 7 |
| IndicatorSidebar | `src/components/ui/indicators/IndicatorSidebar.tsx` | No se ve en capturas (disponible) |
| ChartCard | `src/components/ui/charts/ChartCard.tsx` | 2, 4 |
| TrendLineChart | `src/components/ui/charts/TrendLineChart.tsx` | 2 |

### Nuevos (habría que crear)
| Componente | Capturas | Descripción |
|------------|----------|-------------|
| Tarjetas de Acceso Rápido | 1 | 5 tarjetas gris con ícono sonriente, título y subtítulo |
| Lista de Últimas Tendencias | 1 | Lista con viñetas azules, texto de noticias y fechas |
| Pills de Sector | 3, 4, 5, 6 | Botones pastilla de selección de sector (uno activo oscuro) |
| Chips de Frecuencia | 2 | Trimestral / Mensual / Anual |
| Grupo de Indicadores | 2 | Chips con contadores (Socioeconómicos 4, etc.) |
| Chips rápidos de indicador | 2 | "Ver todos (5)", "Crecimiento del PBI", etc. |
| Badge de indicador activo | 2 | Texto informativo con ícono de ojo |
| Barra de progreso ISE | 3 | Barra horizontal con leyenda de pesos |
| Listado ranking con barras | 3, 5, 6 | Filas con barra progresiva y valor a la derecha |
| Tarjeta Nota Metodológica | 5 | Texto informativo con ícono de info |
| Botón "Ver ocupación" | 5, 6 | Botón de acción con flecha |
| Paginación de tabla | 6 | "Mostrando X de Y", números de página, Siguiente |
| Pestañas Brechas (Mayores/Menores/Todas) | 7, 8 | Select de tipo de brecha |
| Badge "Validado" | 7 | Badge verde en KPI de cobertura |
| Tabla Matriz Comparativa de Brechas | 8 | Tabla de 8 columnas con paginación y checkboxes |
| Tarjetas de definición | 4 | 3 tarjetas informativas (Salario PPA, IA, Gobernanza) |
| Gráfico de barras intersectorial | 4 | Barras horizontales con valores |

---

## Tokens de color observados (hex aproximados)

| Uso | Hex aproximado | Token design-tokens.css más parecido |
|-----|----------------|--------------------------------------|
| Fondo principal / canvas | #ffffff | --color-canvas (#ffffff) |
| Fondo hero / primario | #172bc4 / #2563eb | --color-brand (#172bc4) |
| Texto hero (blanco) | #ffffff | --color-brand-foreground |
| Texto títulos oscuros | #050c1e | --color-heading (#050c1e) |
| Texto cuerpo | #0f172a | --color-body (#0f172a) |
| Texto secundario/muted | #475569 | --color-muted-text (#475569) |
| Fondo tarjetas / superficie | #fafbfe / #f5f7fd | --color-surface / --color-surface-alt |
| Bordes | #aebdde | --color-line / --border (#aebdde) |
| País ARG (gráficos) | #38bdf8 | --color-country-arg (#38bdf8) |
| País CHL (gráficos) | #b91c1c | --color-country-chl (#b91c1c) |
| País URY (gráficos) | #d97706 | --color-country-ury (#d97706) |
| Nav activo | #172bc4 | --color-brand |
| Nav inactivo fondo | #e5e7eb (gris-200) | — (no es token de color) |
| Píldora variación positiva | #f3f4f6 / texto #4b5563 | --color-success-soft (aprox) |
| Píldora variación negativa | #4b5563 / blanco | — |
| Badge crítico / alerta | #fee2e2 / #991b1b | --color-alert-critical-* |
| Badge válido / positivo | #d1fae5 / #166534 | --color-alert-positive-* |
| Grid de gráficos | #e5e7eb | --color-chart-grid (#e2e8f0) |

> Todos los hex son aproximaciones visuales extraídas de las capturas y comparados con `design-tokens.css`. No se hicieron mediciones de píxeles.

---

## Preguntas para UX/UI

1. **Paginación contradictoria (ocupaciones2):** Se lee "Mostrando 5 de 5 registros" pero la paginación muestra páginas hasta 17. ¿Es un error de placeholder o hay inconsistencia en los datos de prueba?
2. **Texto truncado (sectores1):** La pill activa se lee "Economía del Conoc". ¿Es "Economía del Conocimiento" truncado por falta de espacio o el dato real es así?
3. **Typo (ocupaciones1):** Fila 1 dice "Analista den gestión y organización". ¿Es "de" o "den"?
4. **Lorem ipsum (tendencias, sectores, ocupaciones, habilidades):** Héroes y cuerpos contienen Lorem ipsum. ¿Es contenido definitivo o placeholder por reemplazar?
5. **"Registros amortizados" (habilidades2):** Término inusual en "Mostrando 1 a 9 de 368 registros amortizados". ¿Es la redacción correcta?
6. **Fechas de actualización:** Todas las pantallas muestran "12-05-2025". ¿Es una fecha fija de mock o vendrá dinámica de la API (`source_updated_at`)?
7. **Proyecciones puntuadas:** En el gráfico de Tendencias se ve una serie "Proyección", pero `TrendLineChart` actual no diferencia estilo de línea entre observada y proyectada. ¿Se necesita un prop adicional para línea punteada o banda de confianza?
8. **Sidebar de indicadores:** `IndicatorSidebar` existe pero no aparece en ninguna captura. ¿Se usa en alguna pantalla no capturada (Panorama regional)?
9. **Orden "Mayor/Menor" (ocupaciones):** Select de orden solo sobre puntaje. ¿Habrá orden por otras columnas (salario, brecha, etc.)?
10. **País "CHI" vs "CHL":** Los filtros muestran "CHI" en algunas capturas pero el diseño y API usan "CHL" (ISO3). ¿Es inconsistencia de las capturas o hay mapeo pendiente?

---

## Archivo creado

`C:\Users\Eugenia\observa_tendencias\frontend\docs\capturas-spec.md`

Este documento contiene la especificación completa de las 8 capturas, el mapa de componentes (existentes vs nuevos), los tokens de color observados y las preguntas abiertas para UX/UI. Otro agente puede usarlo directamente para implementar las pantallas en Next.js + Tailwind sin modificar el código existente.