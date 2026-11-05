# Guía de Datos Disponibles y Sugerencias de Gráficos
## Observatorio de Tendencias (Argentina, Chile y Uruguay)

Esta guía resume de forma sencilla qué datos produjo el equipo de analítica y ofrece algunas ideas de visualización para que el equipo de Frontend y UX/UI pueda diseñar con total libertad.

---

### 1. ¿Qué datos tenemos disponibles para mostrar?

| Grupo de Datos | ¿Qué información contiene? | Fuente Oficial / Origen | Endpoint de consulta |
| :--- | :--- | :--- | :--- |
| **Graduados Históricos** | Serie anual de personas tituladas por carrera y sector (ARG: 2016-2022, CHL: 2007-2025, URY: 2014-2023). | **ARG:** SPU / SIU-Araucano<br>**CHL:** SIES / Mi Futuro (Mineduc)<br>**URY:** MEC y UdelaR | `GET /api/v1/graduates/trends` |
| **Proyecciones de Graduados** | Estimación estadística a futuro del flujo de graduados, acompañada de un rango (límite inferior y superior). | Modelado de series de tiempo sobre datos de **SPU, SIES y MEC** | `GET /api/v1/graduates/projections` |
| **Densidad Profesional** | Relación entre graduados anuales y empleo activo (cuántos egresados genera la universidad por cada 1.000 trabajadores del sector). | **OIT (ILOSTAT)** + Censos universitarios nacionales | `GET /api/v1/analytics/densidad-profesional` |
| **Salarios** | Sueldos por sector en moneda local y en **USD PPA** (dólares ajustados por costo de vida para que sean comparables entre países). | **Regional:** OIT (ILOSTAT) + Banco Mundial (PPA)<br>**Locales:** CEP-XXI (ARG) y SIES (CHL) | `GET /api/v1/analytics/salarios/dual` |
| **Matriz de Habilidades** | Competencias clasificadas en 4 tipos para cada profesión: **Nucleares** (técnicas de base), **Emergentes del sector** (transición verde, sostenibilidad, industria 4.0), **Humanas/Transversales** (criterio, comunicación, ética) y **Digitales/IA**. | Homologación **CIUO-08**, taxonomía europea **ESCO** y validación con mercado | `GET /api/v1/analytics/habilidades` |
| **Exposición a Tecnología / IA** | Índice de la OIT sobre el nivel de complementariedad o impacto de la IA y automatización en la ocupación (escala de 0 a 1). | **OIT** (Working Paper 140, 2025: *GenAI and Jobs*) | `GET /api/v1/analytics/habilidades` |
| **Ofertas de Empleo en Vivo** | Muestra de búsquedas laborales reales de LinkedIn en la región, con títulos, requisitos y empresas. | Relevamiento de avisos en **LinkedIn Jobs Cono Sur** | `GET /api/v1/jobs` |
| **Paridad y Género** | Participación de mujeres y varones en egreso universitario y en el empleo sectorial formal. | **OIT (ILOSTAT)**, **INE Uruguay** y censos universitarios | `GET /api/v1/analytics/` |

> 📌 **Tip para UI:** Estas fuentes pueden colocarse como subtítulo pequeño o en un *tooltip* informativo al pie de cada gráfico (ej. *"Fuente: SIES / Mi Futuro (Chile) - OIT (ILOSTAT)"*).

---

### 2. Sugerencias de gráficos según lo que se quiera comunicar

Estas son recomendaciones habituales de visualización de datos, abiertas a la propuesta creativa del equipo de diseño:

#### A. Para mostrar evolución en el tiempo, tendencias y proyecciones
* **Tipo de gráfico sugerido:** **Líneas temporales**.
* **Idea visual para proyecciones:**  
  * Cuando se grafican datos pasados junto con proyecciones futuras, suele funcionar muy bien mostrar la parte histórica con una **línea continua** y la proyección con una **línea discontinua o punteada**, acompañada de un **área sombreada suave** de fondo que represente el margen entre el límite inferior y superior. Esto ayuda al usuario a entender a simple vista qué es dato histórico real y qué es una estimación.
* **Alternativa para comparar saltos (ej. inicio vs final de período):** Un gráfico de pendiente (*Slope chart*) o de puntos conectados (*Lollipop*).

#### B. Para comparar indicadores entre sectores o países
* **Tipo de gráfico sugerido:** **Barras (horizontales o verticales)**.
* **Para salarios:** Si se comparan Argentina, Chile y Uruguay en un mismo gráfico, conviene utilizar el valor en **USD PPA** para que la comparación sea justa y comprensible. Si se visualiza la ficha de un solo país, la moneda local resulta más familiar para el usuario.
* **Para densidad profesional:** Barras agrupadas por país para cada uno de los 5 sectores estratégicos.

#### C. Para explorar el perfil de habilidades de una carrera
* **Opciones visuales sugeridas:**
  * **Tarjetas o cuadrantes agrupados:** Mostrar las 4 dimensiones de competencias (Técnicas nucleares, Sostenibilidad/Verdes, Humanas y Digitales) en bloques o listas con etiquetas/chips.
  * **Gráfico de Radar (Spider chart):** Si se desea una vista multidimensional del equilibrio entre lo técnico, lo humano y lo digital.

#### D. Para cruzar demanda laboral vs impacto tecnológico
* **Tipo de gráfico sugerido:** **Gráfico de dispersión o cuadrantes (Scatter plot)**.
* **Idea:** Ubicar las carreras según su volumen de ofertas laborales (eje X) y su índice de exposición tecnológica de la OIT (eje Y), permitiendo identificar ocupaciones en transformación rápida versus ocupaciones de trabajo humano directo.

#### E. Para mostrar paridad de género
* **Tipo de gráfico sugerido:** **Barras 100% apiladas** (Mujeres vs Varones) o un **gráfico de mancuerna (Dumbbell)** que muestre la evolución de la participación femenina a lo largo de los años.

---

### 3. Consideraciones útiles sobre los datos

* **Diferencia de años entre países:** Las fuentes oficiales censales publican a ritmos distintos. Chile tiene datos consolidados hasta 2024/2025, Uruguay hasta 2023/2024 y Argentina hasta 2022/2023. No es un error de la API, sino el último dato oficial disponible.
* **Datos no relevados:** Si en algún país no existe relevamiento oficial de una variable (por ejemplo, encuestas anuales de inserción laboral continua en Argentina y Uruguay), el campo vendrá vacío o nulo; conviene mostrar un texto simple tipo *"Dato no relevado por censo oficial"* en lugar de un cero.
* **Base de la API:** En desarrollo local, los endpoints responden en `http://localhost:8010/api/v1`.
