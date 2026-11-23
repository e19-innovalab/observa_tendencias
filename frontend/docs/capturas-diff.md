# Informe de Diff de Capturas (UI Revisión de Fidelidad Visual)

**Producto:** Observa Tendencias  
**Fuente diseño (Figma):** `frontend/frontend/src/capturas/` (8 PNG)  
**Fuente implementación renderizada (Chrome headless, 1440px):** `C:\Users\Eugenia\AppData\Local\Temp\opencode\ui-check\` (5 PNG)  
**Estatus:** Solo análisis. No se modificó código de la aplicación.

---

## Convención de comparación

- Los pares `sectores1+2`, `ocupaciones1+2`, `habilidades1+2` son **UNA sola vista cada uno**; la segunda captura de Figma es scroll hacia abajo. La implementación es una sola página por par.
- Las capturas de implementación son más anchas y muestran más contenido vertical. No se compara escala píxel a píxel: se compara estructura, orden de bloques, jerarquía, componentes presentes/ausentes y estilo general.
- El "Lorem ipsum" del diseño original fue reemplazado por textos reales en español en la implementación: **no se reporta como error**.

---

## Pantalla 1 — Inicio

### 1. Qué coincide bien
- AppHeader con LOGO, botón "Administración", campana de notificaciones y perfil "Santiago Morales / Administrador".
- MainNav con pestaña "Inicio" activa (fondo azul).
- Saludo "¡Hola Santiago!" y subtítulo.
- Fila de 4 KPI cards con los mismos valores (7,38% / 61,91% / 89,67% / 94,99%) y variaciones.
- Sección "Accesos rápidos" con las 5 tarjetas (Panorama regional, Sectores, Ocupaciones, Habilidades, Tendencias).
- Sección "Últimas tendencias" con lista de items con viñeta azul y link "Ver todas".
- Fecha de actualización "12-05-2025".

### 2. Qué falta o sobra
- **Falta:** en Figma las tarjetas de acceso rápido son 5 dispuestas "2 arriba, 2 abajo, 1 grande abajo". En la implementación son **4 tarjetas en cuadrícula 2x2** (Panorama regional, Sectores, Ocupaciones, Habilidades) + **1 tarjeta ancha abajo** (Tendencias). Sobra la quinta tarjeta por fila en la versión original; la implementación consolida en 2 columnas. No falta contenido, pero cambia la distribución visual.
- **Sobra:** nada sustancial. Todos los bloques del diseño original están presentes.

### 3. Diferencias de layout
- Figma: 4 KPI cards en fila completa; 5 tarjetas de acceso rápido con una última ocupando ancho doble. Implementación: 4 KPI cards en fila; acceso rápido como grilla 2x2 + 1 tarjeta ancha. El orden es el mismo.
- La implementación es más ancha (1440px) y hay más espacio blanco entre bloques.

### 4. Diferencias de estilo
- Figma: KPI con variación pill gris claro (positivo) / gris oscuro (negativo). Implementación: igual, pero la pill negativa del KPI 4 aparece como badge oscuro a la derecha del valor en lugar de pill dentro de la card.
- Figma: tarjetas de acceso rápido gris con ícono sonriente. Implementación: tarjetas con ícono de sección (globo, capas, edificio, graduado, gráfico) y color de fondo más claro, más minimalistas.

### 5. Problemas visibles de la implementación
- **Texto:** "Variación +3,8 pp" del KPI 4 se ve como "-3,8 pp" (sin signo de menos claro) dentro de un badge oscuro; contraste bajo sobre fondo oscuro.
- **Alineación:** las 4 tarjetas de acceso rápido tienen altura desigual porque "Tendencias" ocupa el ancho completo de la segunda fila, dejando un espacio vacío abajo a la derecha.
- No hay overflow horizontal ni texto cortado evidente.

### 6. Prioridad
**Media** — la pantalla es funcional; solo ajuste de distribución de tarjetas de acceso rápido y contraste de la pill negativa.

---

## Pantalla 2 — Tendencias

### 1. Qué coincide bien
- Héroe azul `bg-blue-600` con título "Tendencias".
- Pestañas secundarias "Tendencias" (activa) y "Proyecciones".
- FilterBar: PAÍSES (Todos [3], ARG/CHL/URY), SECTOR (Tecnología), OCUPACIÓN (Analista de sistemas), DESDE 2024, HASTA 2025.
- FRECUENCIA: Trimestral | Mensual (activa) | Anual.
- GRUPO DE INDICADORES: Socioeconómicos 4 | Laborales 5 | Educativos 3.
- Chips rápidos: "Ver todos (5)", "Crecimiento del PBI" (activo), "Actividad económica interanual", "Inflación", "PBI per cápita".
- Badge info: "Indicador activo en visualización: Variación anual del PBI...".
- ChartCard "Tendencia" con leyenda "Tendencia actual" / "Proyección".
- Gráfico de línea con meses Ene-Dec en X y 0-1000 en Y.
- Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

### 2. Qué falta o sobra
- **Falta:** nada sustancial. Todos los bloques del diseño están presentes.
- **Sobra:** nada.

### 3. Diferencias de layout
- Figma: Filtros PAÍSES, SECTOR, OCUPACIÓN, DESDE, HASTA en una fila tipo select con borde inferior. Implementación: PAÍSES como pills redondeadas (Todos (3), ARG, CHL, URY) y el resto como selects con chevron. Cambio de componente (pills vs select) en el filtro de países.
- Figma: chips de frecuencia como pills simples. Implementación: pills con fondo azul en la activa ("Mensual") y gris en las inactivas.
- El héroe en la implementación tiene texto real en español ("Seguí la evolución...") en lugar de Lorem ipsum (esperado por contexto).

### 4. Diferencias de estilo
- Figma: serie "Proyección" gris punteada. Implementación: serie proyectada como línea desmarcada/dashed, coherente.
- Figma: badge de indicador activo a la derecha. Implementación: mismo, dentro de un panel azul claro.
- Los chips rápidos en Figma incluyen "Crecimiento del PBI" activo en negro; en la implementación el chip activo tiene fondo azul oscuro con texto blanco.

### 5. Problemas visibles de la implementación
- **Texto:** en Figma el filtro de país se lee "CHI" pero en la implementación y el diseño usa "CHL" (ISO3). La implementación usa "CHL" correctamente; el diseño Figma tiene "CHI" (inconsistencia del diseño, no de la implementación).
- **Alineación:** el filtro de países con pills ocupa más ancho que un select tradicional, desplazando ligeramente los siguientes filtros en pantallas estrechas, pero a 1440px no hay overflow.
- **Contraste:** el chip activo "Crecimiento del PBI" en fondo muy oscuro con texto blanco es legible.

### 6. Prioridad
**Baja** — la implementación es fiel; solo menor ajuste de ancho del filtro de países.

---

## Pantalla 3 — Sectores (parte superior + scroll, 1 página de implementación)

### 1. Qué coincide bien
- AppHeader con pestaña "Sectores" activa.
- Héroe azul "Sectores" con texto real.
- FilterBar: PAÍSES (Todos [3], ARG activo), DESDE 2024, HASTA 2025.
- Pills de SECTOR: Tecnología, Energía, Salud, **Economía del Conocimiento (activa, fondo negro)**, Turismo. Nota: en Figma se leía "Economía del Conoc" truncado; en la implementación se lee completo "Economía del Conocimiento".
- 4 KPI cards: ISE promedio sector (52,6 /100 pts), Ocupación líder (Analista de Gestión & Organización, 56,1, CIUO 3212), Brecha salarial PPA promedio (USD 2.005 /mes), Riesgo de automatización IA (0,51 /100, Nivel Medio Controlado).
- Barra de progreso "Índice orientativo por ocupación" con pesos (Demanda 35%, Salario PPA 25%, Tasa inserción 20%, Exposición IA 15%).
- "Índice de empleabilidad (ISE) sectorial" con ranking inicial (ítems 1 y 2).
- Ítems 3 y 4 del ranking (continuación del scroll).
- Tarjetas de definición: "Definición de Salario PPA", "Índice de Exposición a IA", "Gobernanza de Calibración".
- ChartCard "Comparativa Intersectorial de Empleabilidad (ISE 2025)" con gráfico de barras horizontales (5 sectores) y línea de referencia promedio ponderado regional 48,6 pts.
- Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

### 2. Qué falta o sobra
- **Falta:** nada sustancial. Todos los bloques de ambas capturas de Figma (1 y 2) están en la página de implementación.
- **Sobra:** nada.

### 3. Diferencias de layout
- Figma: pill activa "Economía del Conoc" (texto truncado). Implementación: "Economía del Conocimiento" completo. Esto resuelve la ambigüedad del diseño.
- Figma: ranking con ítems 1-2 en captura 1 y 3-4 en captura 2. Implementación: los 4 ítems del ranking en secuencia continua.
- Figma: tarjetas de definición y gráfico intersectorial en captura 2. Implementación: aparecen tras el ranking, en el orden correcto.
- El gráfico de barras en Figma tiene valores al final de cada barra; en la implementación también, más una línea vertical de referencia (promedio ponderado regional).

### 4. Diferencias de estilo
- Figma: pill activa de sector con fondo negro. Implementación: mismo (fondo negro/azul muy oscuro).
- Figma: barra de progreso ISE con segmento azul y leyenda de pesos debajo. Implementación: barra segmentada en colores (azul, cian, púrpura, naranja) con etiquetas de porcentaje debajo; más detallada visualmente.
- Figma: KPI "Riesgo de automatización" con texto "Nivel Medio Controlado". Implementación: badge "Medio" amarillo junto al valor 0,51 y "Nivel medio controlado" debajo.

### 5. Problemas visibles de la implementación
- **Texto:** el KPI 4 muestra "0,51 /100" y un badge "Medio"; el texto "Nivel medio controlado" queda debajo, bien legible.
- **Alineación:** el gráfico de barras horizontales tiene etiquetas de sector a la izquierda y valores a la derecha; la barra de "Economía del Conocimiento (Activa)" está resaltada en azul oscuro, coherente con el filtro activo.
- No se observan textos cortados ni overflow.

### 6. Prioridad
**Baja** — la implementación cubre fielmente ambos estados de Figma; mejora el truncado de "Economía del Conoc".

---

## Pantalla 4 — Ocupaciones (filas 1-5 + paginación, 1 página de implementación)

### 1. Qué coincide bien
- AppHeader con pestaña "Ocupaciones" activa.
- Héroe azul "Ocupaciones" con texto real.
- FilterBar: PAÍSES (Todos [3], ARG activo), DESDE 2024, HASTA 2025.
- Pills sector: Tecnología, Energía, Salud, Economía del Conocimiento (activa), Turismo.
- Tarjeta "Nota Metodológica: Ponderación Dinámica del ISE" con pesos (Demanda neta 46,7%, Salario USD PPA 33,3%, Riesgo IA -20,0%, Tasa inserción en espera de fuente).
- Título sección: "Ranking de ocupaciones y coeficientes ISE (Economía del Conocimiento)".
- Select orden: "PUNTAJE", "Mayor" (activo, azul), "Menor".
- Tabla ranking con cabecera de 10 columnas: RANK, OCUPACIÓN & CIUO, PAÍS, PUNTAJE ISE, DEMANDA NETA, SALARIO (USD PPA), TASA INSERCIÓN, RIESGO IA, COBERTURA PONDERADA, ACCIÓN.
- Filas 1 a 5 con los mismos valores que Figma.
- Paginación: "Mostrando 1 a 5 de 5 registros", página 1 activa, botón "Siguiente".
- Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

### 2. Qué falta o sobra
- **Falta:** en Figma la paginación decía "Mostrando 5 de 5 registros" con páginas hasta 17 (contradictorio). En la implementación se lee "Mostrando 1 a 5 de 5 registros" y solo hay página 1 + "Siguiente". **Se elimina la paginación ficticia hasta 17** (mejora, no falta).
- **Sobra:** nada.

### 3. Diferencias de layout
- Figma: columna "OCUPACIÓN & CIUO" con ocupación en negrita y CIUO debajo pequeño. Implementación: misma estructura.
- Figma: columna ACCIÓN con botón "Ver ocupación →". Implementación: mismo botón con flecha.
- Figma: badge de país ARG (pastilla). Implementación: pill "ARG" gris.
- Figma: cobertura con barra + "75%". Implementación: barra de progreso + "75%".
- La implementación corrigió la paginación contradictoria (solo 5 registros, 1 página).

### 4. Diferencias de estilo
- Figma: fila 1 "Analista den gestión" (posible typo). Implementación: "Analista de gestión y organización" (corregido).
- Figma: valores de demanda neto con flecha verde "+8,5%". Implementación: igual.
- Figma: riesgo IA con "Exposición Media" / "Exposición Baja". Implementación: igual, con texto debajo del valor numérico.

### 5. Problemas visibles de la implementación
- **Texto:** fila 5 "Estadístico/a y actuario/a" muestra "Exposición baja"; consistente.
- **Alineación:** la tabla tiene 10 columnas; a 1440px se ve completa sin scroll horizontal. En pantallas más estrechas podría overflow, pero no aplica a esta revisión.
- No hay texto cortado ni elementos desalineados evidentes.

### 6. Prioridad
**Baja** — la implementación corrige ambigüedades del diseño (paginación, typo "den"); muy fiel.

---

## Pantalla 5 — Habilidades / Brechas (resumen + matriz, 1 página de implementación)

### 1. Qué coincide bien
- AppHeader con pestaña "Habilidades" activa.
- Héroe azul "Habilidades" con texto real.
- Pestañas secundarias: "Brechas de Habilidades" (activa, azul) | "Proyecciones".
- FilterBar: PAÍSES (Todos [3], ARG activo), SECTOR (Tecnología), OCUPACIÓN (Todas (25)), DESDE 2024, HASTA 2025.
- Pestañas BRECHAS: "Mayores" (activa, azul) | "Menores" | "Todas".
- Nota: "65 habilidades con brechas y usadas por al menos 20 ocupaciones en las 3 páginas · 56 con demanda y/o oferta - 2024-2025".
- Badge info: "Correspondencia carrera - ocupación (CHL, ARG, URY) es un estándar armonizado CNO-08 / CNO con clasificación estadística común."
- 4 KPI cards: Brecha promedio nacional (-14,2 pp, Déficit crítico), Mayor brecha detectada (-22,4 pp, Uruguay / Tri-Nac), Ocupaciones impactadas (35), Cobertura de microdatos (94,6%, Validado).
- Título: "Matriz comparativa de brechas" con subtítulo y leyenda "Déficit (-) ○ Superávit (+)".
- Tabla matriz con cabecera: HABILIDAD, PAÍS, DEMANDA (%/AÑO), FORMACIÓN (%/AÑO), BRECHA (PP), OCUPACIONES, PRINCIPALES OCUPACIONES, ACCIONES.
- Filas visibles (todas URY, brecha negativa/superávit) con valores de brecha en rojo/verde.
- Paginación: "Mostrando 1 a 9 de 9 registros", página 1 activa, botón "Siguiente".
- Footer: "Actualización: 12-05-2025" | "Ver fuente y metodología".

### 2. Qué falta o sobra
- **Falta:** en Figma la paginación decía "Mostrando 1 a 9 de 368 registros amortizados" con 17 páginas. En la implementación se lee "Mostrando 1 a 9 de 9 registros" y solo página 1. **Se elimina la paginación ficticia de 17 páginas / 368 registros** (mejora, no falta).
- **Falta:** en Figma había una pestaña "Tipo de brecha" con "Mayores/Menores/Todas" como select. En la implementación son pills "Mayores" (activa), "Menores", "Todas". Equivalente.
- **Sobra:** nada.

### 3. Diferencias de layout
- Figma: pestañas brechas "Mayores" (activa, lila). Implementación: "Mayores" activa con fondo azul (más que lila).
- Figma: tabla con ~7 filas visibles + filas truncadas. Implementación: 9 filas visibles, paginación "1 a 9 de 9 registros".
- Figma: paginación con "Anterior", "1" (activa negra), "2", "3", "...", "17", "Siguiente". Implementación: solo "<", "1" (activa negra), "Siguiente >" (coherente con 9 registros totales).
- Figma: columna ACCIONES con checkbox por fila. Implementación: checkbox por fila, presente.

### 4. Diferencias de estilo
- Figma: valores de brecha negativa en rojo, positiva en verde. Implementación: idéntico (-15,9 pp en rojo, +0,1 pp en verde).
- Figma: badge país URY (pastilla). Implementación: pill "URY" gris.
- Figma: KPI "Cobertura de microdatos" con badge "Validado" verde. Implementación: badge "Validado" verde claro.
- Figma: KPI "Mayor brecha detectada" con tag "Uruguay / Tri-Nac". Implementación: "Uruguay - análisis tri-nacional".

### 5. Problemas visibles de la implementación
- **Texto:** ninguna fila truncada; todas las 9 filas se ven completas.
- **Alineación:** la tabla de 8 columnas a 1440px se ve completa; la columna "PRINCIPALES OCUPACIONES" con texto largo no se corta.
- **Contraste:** los valores de brecha negativa en rojo sobre fondo blanco tienen buen contraste.
- No hay overflow horizontal ni imágenes/íconos rotos.

### 6. Prioridad
**Baja** — la implementación corrige la paginación ficticia del diseño y es visualmente fiel.

---

## Top 10 Arreglos Priorizados

| Prioridad | Página / Componente | Hallazgo | Acción sugerida |
|-----------|---------------------|----------|-----------------|
| Alta | Inicio — Tarjetas de acceso rápido | Distribución 2x2 + 1 ancha difiere del diseño (5 tarjetas con 1 de ancho doble). | Ajustar grilla de acceso rápido para mantener jerarquía visual del diseño o confirmar que la nueva distribución es intencional. |
| Alta | Inicio — KPI 4 variación negativa | Badge oscuro con texto de variación de bajo contraste ("-3,8 pp" difícil de leer). | Asegurar contraste WCAG AA en la pill/badge de variación negativa (texto blanco sobre fondo oscuro puede fallar en tamaños pequeños). |
| Media | Tendencias — Filtro de países | Cambio de select (diseño) a pills (implementación) que ocupa más ancho y puede desplazar filtros en pantallas estrechas. | Revisar ancho del filtro de países o volver a select para mantener alineación de filtros DESDE/HASTA. |
| Media | Sectores — Barra de progreso ISE | Barra segmentada con colores y pesos debajo difiere del diseño (barra única azul + leyenda). | Estandarizar estilo de barra de progreso según design tokens si se busca fidelidad visual estricta. |
| Media | Sectores — Gráfico intersectorial | Línea de referencia de promedio ponderado regional no especificada claramente en el diseño. | Añadir etiqueta visible de la línea de referencia para claridad del usuario. |
| Baja | Ocupaciones — Tabla de 10 columnas | A 1440px se ve completa, pero en pantallas más estrechas podría overflow horizontal. | Añadir scroll horizontal contenedor o reducir columnas en puntos de ruptura menores. |
| Baja | Habilidades — Pestañas brechas | "Mayores" activa usa fondo azul en lugar de lila del diseño. | Ajustar color de pestaña activa a tono lila para coincidir con diseño, si es requerido por marca. |
| Baja | Tendencias — Héroe | Texto real en español reemplaza Lorem ipsum (correcto, no es error). | Ninguna acción; verificar que el copy final esté aprobado. |
| Baja | Ocupaciones — Paginción | Implementación corrige paginación ficticia de Figma (5 registros, 1 página). | Ninguna acción; mantener comportamiento actual. |
| Baja | Habilidades — Paginación | Implementación corrige paginación ficticia de Figma (9 registros, 1 página vs 368/17). | Ninguna acción; mantener comportamiento actual. |

---

## Resumen

Se revisaron 5 pantallas de implementación contra 8 capturas de Figma (3 pares por scroll). La implementación es **visualmente fiel** a la especificación: estructura, orden de bloques, jerarquía y componentes coinciden en todas las pantallas. Se corrigieron ambigüedades del diseño (paginación ficticia en Ocupaciones y Habilidades, texto truncado "Economía del Conoc", typo "den gestión"). Los únicos hallazgos de cierta relevancia son: (1) distribución distinta de tarjetas de acceso rápido en Inicio, (2) bajo contraste de la pill de variación negativa del KPI 4 en Inicio, y (3) el filtro de países implementado como pills en lugar de select, lo que afecta el ancho en pantallas estrechas. No hay textos cortados, overflow horizontal, íconos rotos ni problemas de contraste críticos. El informe detallado se encuentra en `C:\Users\Eugenia\observa_tendencias\frontend\docs\capturas-diff.md`.