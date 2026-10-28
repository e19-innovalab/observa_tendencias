# Catálogo de Datos y Contratos de Interfaz para Frontend y UX/UI
## Observatorio de Tendencias Socioeconómicas, Laborales y Educativas (ARG, CHL, URY)
**Rama:** `feature/data-analytics`  
**Destinatarios:** Equipos de Desarrollo Frontend, Diseño UX/UI, QA y Producto (InnovaLab)  
**Estado:** Documento Oficial de Entrega y Contrato Técnico de Integración (Etapa 5 - Opción 5.B)

---

### 1. Principios Rectores para Frontend y Diseño UX/UI

Para garantizar la rigurosidad científica y la coherencia del Observatorio ante organismos públicos, universidades y decisores de políticas educativas, **la interfaz de usuario (UI) debe adherir estrictamente a los siguientes principios:**

1. **Datos 100% Reales y Observados:**
   * La UI **nunca debe generar datos simulados, interpolados ni figurados** para completar gráficos o rellenar huecos visuales.
   * Si para un país, carrera o año no existe dato publicado por la fuente oficial correspondiente, el componente visual debe mostrar el estado explícito: `"Dato no relevado oficialmente"` o `"Fuente censal no disponible"`, evitando líneas continuas engañosas en gráficos de series de tiempo.
2. **Enfoque Dual en Visualizaciones:**
   * **Nivel Ficha Local / Nacional:** Debe mostrar la **máxima actualidad temporal observada** de cada país (Chile hasta 2024/2025 vía SIES/Mi Futuro; Uruguay hasta 2023/2024 vía MEC/UdelaR; Argentina hasta 2022/2023 vía SPU/Araucano y CEP-XXI).
   * **Nivel Comparativa Regional Tripartita (ARG - CHL - URY):** Debe utilizar exclusivamente la **ventana temporal común armonizada (2018-2022 para series continuas; 2024 para OIT PPA)** para evitar sesgos cronológicos en comparaciones cruzadas.
3. **Paridad Salarial y Moneda Común:**
   * Las comparaciones salariales entre países deben presentarse obligatoriamente en **USD PPA (Paridad de Poder Adquisitivo del Banco Mundial, deflactadas a IPC base 2016=100)**.
   * En las fichas locales se puede alternar con la moneda local oficial deflactada (ARS constante de CEP-XXI, CLP constante de SIES).
4. **Claridad Metodológica y Transparencia:**
   * Cada gráfico o tarjeta de datos debe incluir un icono o tooltip de **Información Metodológica** con: Fuente oficial, año de corte, concepto de la métrica y nota técnica.

---

### 2. Inventario Maestro de Datos Reales Disponibles

| Dimensión / Indicador | Argentina (ARG) | Chile (CHL) | Uruguay (URY) | Regional Tripartito | Fuente Oficial |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Egresados Universitarios por Carrera** | 2016 - 2022 (anual) | 2007 - 2025 (anual) | 2014 - 2023 (anual) | **2018 - 2022** (ventana común) | SPU-Araucano (ARG), SIES-Mi Futuro (CHL), MEC-UdelaR (URY) |
| **Tasa de Densidad Profesional** (Graduados / 1.000 ocupados) | 2016 - 2022 (anual) | 2013 - 2025 (anual) | 2014 - 2023 (anual) | **2018 - 2022** (Año común: 2022) | OIT (ILOSTAT) + Fuentes educativas nacionales |
| **Salarios Armonizados USD PPA** | 2024 (OIT) / 2016-2023 (CEP-XXI) | 2024 (OIT) / 2016-2024 (SIES) | 2024 (OIT PPA) | **2024** (USD PPA deflactado IPC 2016) | OIT ILOSTAT, Banco Mundial (`PA.NUS.PPP`), CEP-XXI, SIES |
| **Tasa de Inserción Laboral Formal** | *No disponible en censo anual continuo* | **2016 - 2024** (1° y 2° año) | *No disponible en censo anual continuo* | *Redistribuido proporcionalmente en ISE* | SIES / Mi Futuro (Chile) |
| **Correspondencia Formativa CIUO-08** | 37 disciplinas universitarias | 277 carreras de pregrado | 534 carreras MEC | **54 ocupaciones estratégicas** | CIUO-08 / OIT / SIES / SPU / MEC |
| **Impacto IA Generativa (OIT WP 140)** | 54 ocupaciones estratégicas | 54 ocupaciones estratégicas | 54 ocupaciones estratégicas | **427 ocupaciones (Escala 0 a 1)** | OIT WP 140 (2025), Gmyrek et al. |
| **Ofertas Laborales Observadas** | 640 ofertas de empleo | *En integración de scraping* | *En integración de scraping* | **Cono Sur (Muestra observada)** | LinkedIn Jobs (data_analytics) |

> [!WARNING]
> **Lo que NO existe y NO debe inventarse en la interfaz:**
> * **No inventar tasas de inserción para Argentina ni Uruguay:** Mostrar el aviso transparente de que el país no dispone de relevamiento censal anual equivalente y que el ISE redistribuye ese peso.
> * **No inventar datos de graduados de 2024 o 2025 para Argentina:** El último anuario censal oficial consolidado por SPU es 2022 (con microdatos 2023).

---

### 3. Contratos de Interfaz (Endpoints de API y Esquemas JSON)

Base URL de la API: `http://localhost:8010/api/v1`

---

#### 3.1. Endpoint de Tasa de Densidad Profesional
* **Ruta:** `GET /api/v1/analytics/densidad-profesional`
* **Parámetros de consulta (Query Params):**
  * `enfoque`: `"regional_comun"` (ventana común 2018-2022), `"local"` (serie histórica completa por país), o `"todos"` (default).
  * `country` / `pais`: `"ARG"`, `"CHL"`, `"URY"` (opcional).
  * `sector`: `"Tecnología"`, `"Salud"`, `"Energía"`, `"Economía del conocimiento"`, `"Turismo"` (opcional).
  * `year` / `anio`: año específico (ej. `2022`).
* **Ejemplo de Respuesta JSON:**
```json
{
  "total": 15,
  "enfoque": "regional_comun",
  "ventana_temporal": "Ventana común 2018-2022 (Año común: 2022)",
  "nota_metodologica": "Ventana común armonizada tripartita (2018-2022) para cotejo comparativo regional sin distorsiones temporales (Año común de referencia: 2022).",
  "items": [
    {
      "pais": "URY",
      "sector": "Tecnología",
      "anio": 2022,
      "graduados_anuales": 3418.0,
      "puestos_empleo": 21390.0,
      "graduados_por_mil_ocupados": 159.80,
      "ratio_graduados_vs_empleo_pct": 15.98,
      "fuente_graduados": "MEC_Uruguay",
      "fuente_empleo": "OIT_ILOSTAT",
      "concepto": "Graduados anuales por cada 1.000 ocupados"
    },
    {
      "pais": "CHL",
      "sector": "Tecnología",
      "anio": 2022,
      "graduados_anuales": 9505.0,
      "puestos_empleo": 202404.0,
      "graduados_por_mil_ocupados": 46.96,
      "ratio_graduados_vs_empleo_pct": 4.70,
      "fuente_graduados": "SIES_MiFuturo",
      "fuente_empleo": "OIT_ILOSTAT",
      "concepto": "Graduados anuales por cada 1.000 ocupados"
    },
    {
      "pais": "ARG",
      "sector": "Tecnología",
      "anio": 2022,
      "graduados_anuales": 2813.0,
      "puestos_empleo": 271486.0,
      "graduados_por_mil_ocupados": 10.36,
      "ratio_graduados_vs_empleo_pct": 1.04,
      "fuente_graduados": "Araucano_SPU",
      "fuente_empleo": "OIT_ILOSTAT",
      "concepto": "Graduados anuales por cada 1.000 ocupados"
    }
  ]
}
```

---

#### 3.2. Endpoint de Salarios Duales (Regional PPA vs Local Oficial)
* **Ruta:** `GET /api/v1/analytics/salarios/dual`
* **Parámetros de consulta:**
  * `enfoque`: `"regional"` (comparativa OIT 2024 en USD PPA), `"local"` (series históricas en moneda local constante y USD PPA), o `"todos"`.
  * `country`: `"ARG"`, `"CHL"`, `"URY"`.
  * `sector`: Sector estratégico.
* **Ejemplo de Respuesta JSON:**
```json
{
  "total": 3,
  "enfoque": "regional",
  "nota_metodologica": "Matriz regional tripartita armonizada OIT 2024 en USD PPA del PIB (Banco Mundial PA.NUS.PPP) y base IPC 2016=100 para paridad estricta entre países.",
  "items": [
    {
      "pais": "CHL",
      "sector": "Tecnología",
      "anio": 2024,
      "fuente_id": "OIT_ILOSTAT",
      "carrera_objetivo": null,
      "salario_moneda_local": null,
      "moneda_local": "CLP",
      "factor_ppa": 482.42,
      "salario_usd_ppa": 2240.50,
      "tipo_salario": "promedio_mensual_usd_ppa",
      "metodo_ppa": "PA.NUS.PPP",
      "es_observado": true
    },
    {
      "pais": "URY",
      "sector": "Tecnología",
      "anio": 2024,
      "fuente_id": "OIT_ILOSTAT",
      "carrera_objetivo": null,
      "salario_moneda_local": null,
      "moneda_local": "UYU",
      "factor_ppa": 34.12,
      "salario_usd_ppa": 2180.20,
      "tipo_salario": "promedio_mensual_usd_ppa",
      "metodo_ppa": "PA.NUS.PPP",
      "es_observado": true
    },
    {
      "pais": "ARG",
      "sector": "Tecnología",
      "anio": 2024,
      "fuente_id": "OIT_ILOSTAT",
      "carrera_objetivo": null,
      "salario_moneda_local": null,
      "moneda_local": "ARS",
      "factor_ppa": 465.18,
      "salario_usd_ppa": 1820.75,
      "tipo_salario": "promedio_mensual_usd_ppa",
      "metodo_ppa": "PA.NUS.PPP",
      "es_observado": true
    }
  ]
}
```

---

#### 3.3. Endpoint de Matriz Integral de Habilidades Sectoriales
* **Rutas:** `GET /api/v1/analytics/habilidades` y `GET /api/v1/analytics/habilidades-ia` (ambos disponibles)
* **Parámetros de consulta:**
  * `sector`: `"Tecnología"`, `"Salud"`, `"Energía"`, `"Economía del conocimiento"`, `"Turismo"`.
  * `tipologia`: Filtrar por tipología general (ej. `"Nuclear"`, `"Emergente"`, `"Transformación"`, `"Operativa"`).
  * `vector`: Filtrar por vector de demanda (ej. `"Transición Energética"`, `"Cloud"`, `"Cuidados Críticos"`, `"Sostenibilidad"`).
  * `ciuo`: Código CIUO-08 de 4 dígitos (ej. `"2512"`).
  * `gradiente`: `"Gradient 2"`, `"Gradient 3"`, `"Gradient 4"`, `"Minimal Exposure"`, `"Not Exposed"`.
* **Estructura del Payload JSON:**
```json
{
  "total": 55,
  "sector_filtro": "Tecnología",
  "tipologia_filtro": null,
  "resumen_por_sector": {
    "Tecnología": 55,
    "Economía del conocimiento": 22,
    "Salud": 18,
    "Turismo": 12,
    "Energía": 7
  },
  "resumen_por_tipologia": {
    "Habilidad Técnica y de Gestión Operativa": 33,
    "Habilidad Técnica Nuclear y Emergente": 5,
    "Habilidad Técnica Nuclear y de Transformación Digital": 5,
    "Habilidad Emergente y de Infraestructura Crítica": 5
  },
  "nota_metodologica": "Articulación metodológica integral de competencias sectoriales (Hard Skills nucleares, Habilidades Emergentes, Transversales Humanas y Digitales/IA) para las 25 carreras objetivo en los 5 sectores estratégicos del Cono Sur (ARG, CHL, URY), con métricas de exposición a IA OIT (WP 140) y validación en ofertas de empleo de LinkedIn.",
  "items": [
    {
      "carrera_id": "TEC01",
      "carrera_objetivo": "Ingeniería en informática / computación",
      "sector": "Tecnología",
      "cine_f_codigo": "0613",
      "nivel_esperado": "grado",
      "ciuo_08": "2512",
      "ocupacion_nombre_es": "Desarrolladores de software",
      "ocupacion_nombre_en": "Software Developers",
      "tipologia_habilidad": "Habilidad Técnica Nuclear y Emergente",
      "vector_emergencia": "Digitalización Avanzada, Cloud Computing e IA Asistida",
      "habilidades_nucleares": "Algoritmos y estructuras de datos; Programación orientada a objetos; Bases de datos SQL/NoSQL; Patrones de diseño de software; Git y control de versiones",
      "habilidades_emergentes_sector": "Arquitectura de microservicios distribuida; Cloud Native (AWS/GCP/Azure); Seguridad de aplicaciones (DevSecOps); APIs reactivas y Event-Driven",
      "habilidades_transversales_humanas": "Resolución estructurada de problemas; Trabajo ágil en equipo (Scrum); Pensamiento crítico; Comunicación técnica efectiva",
      "habilidades_digitales_ia": "Co-programación asistida por LLMs (GitHub Copilot); Generación y optimización de tests con IA; Refactorización asistida; Integración de APIs de IA",
      "oit_exposicion_media": 0.53,
      "oit_desvio_std": 0.07,
      "oit_gradiente": "Gradient 3",
      "impacto_ia_resumen": "Alta complementariedad con IA y herramientas digitales (Gradiente OIT Gradient 3); amplificación de tareas cognitivas y necesidad de validación crítica humana.",
      "habilidades_clave_esco": "Nucleares: Algoritmos y estructuras de datos; POO | Emergentes: Microservicios; Cloud Native | Transversales: Scrum; Pensamiento crítico | Digitales/IA: Co-programación LLMs",
      "demanda_observada_linkedin": "Muy Alta (48% de ofertas del sector Tecnología)",
      "recomendacion_curricular": "Enfocar formación en fundamentos de arquitectura limpia, validación rigurosa de código generado por IA y seguridad preventiva de software.",
      "fuente_mapeo": "Diccionarios Cono Sur (CHL/ARG/URY) + Clasificador ESCO",
      "fuente_ofertas": "Observadas LinkedIn Jobs Cono Sur (data_analytics)"
    }
  ]
}
```

---

#### 3.4. Endpoint de Metodología de Inserción Laboral (ISE)
* **Ruta:** `GET /api/v1/analytics/ise/metodologia-insercion`
* **Propósito:** Mostrar de forma transparente la fórmula y pesos del Índice Sintético de Empleabilidad.
* **Ejemplo de Respuesta JSON:**
```json
{
  "metodologia": "Índice Sintético de Empleabilidad (ISE) - Paridad Regional Tripartita",
  "version": "0.2",
  "tratamiento_insercion": "Redistribución proporcional de peso en comparativa regional tripartita",
  "justificacion_metodologica": "Chile cuenta con relevamiento censal anual de inserción laboral formal a 1 y 2 años vía SIES/Mi Futuro. Argentina y Uruguay no disponen de relevamientos censales continuos homologables para el conjunto de sus instituciones universitarias. Para garantizar el principio rector de 100% de datos observados sin penalizar a países sin fuente censal ni generar imputaciones sintéticas, el 25% de peso nominal de la tasa de inserción se redistribuye proporcionalmente entre las tres dimensiones con datos 100% observados en los 3 países (Demanda Neta: 46.7%, Salario PPA: 33.3%, Riesgo de Automatización OIT: 20.0%). En las fichas locales, Chile reporta la tasa observada de SIES de manera informativa.",
  "pesos_nominales": {
    "net_demand": 0.35,
    "salary_ppp": 0.25,
    "insertion_rate": 0.25,
    "automation_risk": 0.15
  },
  "pesos_efectivos_redistribuidos": {
    "net_demand": 0.467,
    "salary_ppp": 0.333,
    "insertion_rate": 0.0,
    "automation_risk": 0.200
  },
  "disponibilidad_por_pais": {
    "CHL": "Disponible oficialmente vía SIES / Mi Futuro (incorporada en ficha local y análisis complementario)",
    "ARG": "No disponible en serie censal anual universitaria homogénea (peso redistribuido proporcionalmente)",
    "URY": "No disponible en serie censal anual universitaria homogénea (peso redistribuido proporcionalmente)"
  }
}
```

---

#### 3.5. Endpoint de Ofertas Laborales Observadas (LinkedIn)
* **Rutas:**
  * `GET /api/v1/jobs?sector=Tecnología&limit=20` (lista paginada de avisos)
  * `GET /api/v1/jobs/summary` (matriz de ofertas por provincia y sector)
* **Campos clave por aviso:** `id`, `pais`, `provincia`, `sector`, `titulo`, `empresa`, `ubicacion`, `fecha_publicacion`, `postulantes`, `url`.

---

#### 3.6. Endpoints de Tendencias y Proyecciones de Graduados
* **Rutas:**
  * `GET /api/v1/graduates/trends?country=CHL` (tendencias observadas en serie histórica)
  * `GET /api/v1/graduates/projections?country=CHL` (proyecciones estadísticas con intervalos)
* **Estructura del Payload JSON:**
```json
{
  "items": [
    {
      "pais": "chile",
      "nombre": "Ingeniería en Computación e Informática",
      "anio_desde": 2007,
      "anio_hasta": 2025,
      "n_anios_serie": 19,
      "ventana_anios": 5,
      "graduados_inicio_ventana": 3820,
      "graduados_ultimo": 5098,
      "variacion_ventana_pct": 33.45,
      "tendencia": "growing",
      "tiene_huecos": false,
      "proyeccion": "generada"
    }
  ]
}
```
* **Payload de Proyecciones:**
```json
[
  {
    "pais": "chile",
    "nombre": "Ingeniería en Computación e Informática",
    "anio": 2026,
    "graduados_proyectado": 5280,
    "limite_inferior": 4890,
    "limite_superior": 5670
  }
]
```

---

### 4. Catálogo Detallado de Sugerencias de Visualización y Gráficos (Dashboard & Explorer)

Esta sección orienta a los equipos de **Diseño UX/UI y Frontend** sobre las mejores prácticas de visualización de datos cuantitativos según el tipo de indicador entregado:

#### Visualización 1: Gráfico de Proyecciones con Cono de Incertidumbre (Fan Chart)
* **Indicadores:** Egresados observados (`graduados_ultimo`) vs Egresados proyectados (`graduados_proyectado`, `limite_inferior`, `limite_superior`).
* **Tipo de Gráfico Recomendado:** **Línea Temporal con Banda de Confianza Sombreada (Fan Chart / Prediction Interval)**.
* **Especificaciones de Diseño UI:**
  * **Serie Histórica (Observada):** Línea continua y sólida con marcadores circulares en cada año real. Color de acento primario (ej. Azul Cono Sur `#1E40AF`).
  * **Punto de Quiebre (Último Año Observado):** Marcador destacado con tooltip `"Último dato censal oficial publicado"`.
  * **Serie Proyectada:** Línea punteada o discontinua (`stroke-dasharray="4,4"`), partiendo del último año observado hacia el horizonte proyectado (ej. 2026 - 2030).
  * **Intervalo de Confiabilidad (Banda Sombreada):** Área semitransparente (`opacity: 0.20`) delimitada entre el `limite_inferior` y `limite_superior`. Indica que no es una predicción determinista sino un rango estadístico esperado al 95% de confianza.
  * **Tarjetas KPI Contextuales:** Acompañar el gráfico con badges semánticos:
    * 🟢 *Tendencia Creciente (`growing`):* Variación positiva sólida.
    * 🟡 *Tendencia Estable (`stable`):* Variación interanual en rango $\pm 5\%$.
    * 🔴 *Tendencia en Descenso (`declining`):* Variación negativa sostenida.
    * ⚠️ *Alerta de Hueco (`tiene_huecos: true`):* Indicador de discontinuidad en la serie original.

#### Visualización 2: Gráfico de Variación de Ventana (Slope Chart / Lollipop Chart)
* **Indicadores:** `graduados_inicio_ventana` vs `graduados_ultimo` y `variacion_ventana_pct`.
* **Tipo de Gráfico Recomendado:** **Gráfico de Pendiente (Slope Chart) o Gráfico de Mancuerna / Piruleta (Lollipop Chart)**.
* **Especificaciones de Diseño UI:**
  * Permite al usuario comparar en un golpe de vista el punto de inicio de la ventana de 5 años contra el cierre actual para múltiples carreras.
  * Colores semánticos en el conector: verde para expansión porcentual alta, rojo para contracción, neutro para estabilidad.
  * Selector interactivo para ordenar por volumen absoluto de graduados o por porcentaje relativo de crecimiento.

#### Visualización 3: Gráfico de Densidad Profesional y Capacidad de Absorción
* **Indicadores:** `graduados_por_mil_ocupados`, `graduados_anuales` y `puestos_empleo`.
* **Tipo de Gráficos Recomendados:**
  1. **Barras Agrupadas Horizontales (Enfoque Regional Tripartito):**
     * Eje Y: Sectores Estratégicos (Tecnología, Conocimiento, Salud, Energía, Turismo).
     * Eje X: Graduados anuales por cada 1.000 ocupados.
     * Tres barras por sector (Argentina en celeste, Chile en rojo/azul, Uruguay en azul claro) para el año común de referencia (2022).
  2. **Gráfico de Doble Eje (Dual-Axis Chart - Enfoque Local por País):**
     * Eje Izquierdo (Barras): Flujo anual de egresados universitarios (`graduados_anuales`).
     * Eje Derecho (Línea suave): Stock total de puestos de trabajo formal del sector (`puestos_empleo`).
     * Permite visualizar si el flujo formativo acompaña o desacopla la demanda estructural de empleo.

#### Visualización 4: Gráficos de Salarios Armonizados USD PPA y Moneda Constante
* **Indicadores:** `salario_usd_ppa` (factor Banco Mundial `PA.NUS.PPP`), `salario_moneda_local` y deflactor IPC base 2016.
* **Tipo de Gráficos Recomendados:**
  1. **Barras Horizontales con Línea Benchmark:**
     * Comparativa Cono Sur en USD PPA del PIB para los 5 sectores.
     * Línea de referencia vertical con la mediana salarial regional.
     * Tooltip explicativo con la fórmula: `"Salario PPA = Moneda Local / Factor PPA Oficial del Banco Mundial"`.
  2. **Líneas Temporales de Poder Adquisitivo Real (Moneda Constante):**
     * En la ficha local de Argentina y Chile, mostrar la evolución salarial deflactada a precios constantes de 2016. Evita la ilusión monetaria nominal causada por la inflación.

#### Visualización 5: Gráficos de Paridad y Brechas de Género
* **Indicadores:** Share de mujeres (`pct_mujeres`), egresados por sexo (`mujeres` vs `hombre`) y brecha salarial de género.
* **Tipo de Gráficos Recomendados:**
  1. **Barras 100% Apiladas Horizontales:**
     * Barra dividida en dos segmentos: `% Mujeres` y `% Varones`.
     * Marcador vertical central de paridad (50%).
     * Permite identificar inmediatamente la segregación horizontal: alta feminización en Salud y Educación vs baja participación en Tecnología e Ingenierías.
  2. **Gráfico Dumbbell de Evolución Histórica de Paridad:**
     * Muestra la posición del porcentaje femenino en 2016 (círculo gris) conectado con una línea hacia la posición actual (círculo de color). Muestra si la brecha de género se está cerrando o estancando.

#### Visualización 6: Gráfico Radar de Competencias Sectoriales (Spider Chart)
* **Indicadores:** Habilidades desagregadas (`habilidades_nucleares`, `habilidades_emergentes_sector`, `habilidades_transversales_humanas`, `habilidades_digitales_ia`).
* **Tipo de Gráfico Recomendado:** **Gráfico Radar / Spider Chart de 5 Ejes**.
* **Especificaciones de Diseño UI:**
  * Ejes del polígono:
    1. *Técnicas Nucleares (Hard Skills disciplinares)*
    2. *Emergentes e Innovación Sectorial (Transición verde, metodologías ágiles, bioseguridad)*
    3. *Transversales, Humanas y de Cuidado (Pensamiento crítico, empatía, ética, comunicación)*
    4. *Digitales y Automatización (Software especializado, plataformas, cloud)*
    5. *Complementación Tecnológica e IA (Uso de asistentes, prompts, validación crítica)*
  * Permite visualizar el perfil integral del profesional del sector, desmitificando que todo se reduce a IA o a habilidades puramente teóricas.

#### Visualización 7: Cuadrante Interactivo de Demanda Laboral vs Impacto Tecnológico
* **Indicadores:** OIT Exposición a IA (`oit_exposicion_media`), Demanda observada en LinkedIn y Vector de emergencia.
* **Tipo de Gráfico Recomendado:** **Diagrama de Cuadrantes (Scatter / Bubble Plot)**.
* **Ejes:**
  * **Eje Y:** Nivel de Exposición Tecnológica OIT (0.00 a 1.00).
  * **Eje X:** Demanda Observada de Mercado (Volumen de avisos de empleo / Postulantes en LinkedIn).
  * **Tamaño de la burbuja:** Masa de graduados anuales de la carrera.
  * **Color:** Sector Estratégico.
  * **Cuadrantes resultantes:**
    * *Cuadrante Superior Derecho (Alta Demanda + Alta Exposición Tecnológica):* Perfiles en acelerada reconversión y transformación digital (Desarrolladores, Científicos de Datos, Diseñadores UX).
    * *Cuadrante Inferior Derecho (Alta Demanda + Baja Exposición Tecnológica):* Perfiles presenciales de cuidado y campo críticos (Enfermería, Mantenimiento Eléctrico, Cirugía, Kinesiología).
    * *Cuadrante Superior Izquierdo (Baja Demanda + Alta Exposición Tecnológica):* Perfiles en riesgo de desplazamiento transaccional (Tareas secretariales y reservas tradicionales).
    * *Cuadrante Inferior Izquierdo (Baja Demanda + Baja Exposición):* Ocupaciones artesanales u operativas tradicionales.

---

### 5. Resumen de Estados HTTP y Manejo de Errores

| Código | Significado | Comportamiento esperado en UI |
| :--- | :--- | :--- |
| `200 OK` | Consulta exitosa | Renderizar gráfico o tabla de datos con sus tooltips metodológicos |
| `400 Bad Request` | Parámetros inválidos (ej. año fuera de rango) | Mostrar mensaje amigable de validación de filtro |
| `404 Not Found` | Recurso o código no encontrado | Mostrar pantalla de estado vacío con sugerencia de búsqueda |
| `500 Server Error` | Excepción no controlada | Mostrar mensaje de soporte técnico sin romper el layout |

