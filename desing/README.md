# Estado y Documentación - Equipo de Diseño UX/UI

Este espacio resume las decisiones de diseño, herramientas de trabajo, la organización del espacio colaborativo y el estado actual del desarrollo de interfaz para el proyecto.

---

## Accesos Rápidos y Recursos Principales

* **Espacio Colaborativo Centralizado:** [Tablero de Miro](https://miro.com/app/board/uXjVHI5DvM=/)
* **Archivo de Diseño UI:** [Figma Colaborativo](https://www.figma.com/design/W3S2E5N9MKzAYEp90N9QhP/Gisella-Franco-s-team-library?node-id=3316-2&t=Rxj6O52WH7h4wmnc-1) | [Prototipo Navegable (wireframes)](https://www.figma.com/proto/W3S2E5N9MKzAYEp90N9QhP/Gisella-Franco-s-team-library?node-id=3364-1721&p=f&t=aN25UvDngecOjWQS-1&scaling=min-zoom&content-scaling=fixed&page-id=3316%3A2&starting-point-node-id=3364%3A1721)
* **Repositorio de Activos Exportados:** [Carpeta Google Drive - Diseño UX/UI](https://drive.google.com/drive/folders/1wFV2P4Krug6KoGZszjzpO06Nq6ueMoUx?usp=sharing)  
  *(Organizado en carpetas: Diagramas de flujo, Recursos gráficos, Sitemaps y Wireframes)*

---

## Espacio Colaborativo Centralizado (Miro)

El tablero de Miro funciona como la **fuente de verdad principal y centralizada** para el equipo de UX/UI. En él se documenta todo el proceso de diseño, capturas de investigación, referencias visuales, wireframes de Figma y espacios de interacción interdisciplinaria.

### Estructura y Organización del Tablero

| Etapa / Columna | Subsecciones | Contenido y Propósito |
| :--- | :--- | :--- |
| **Investigación** | Contexto, Usuarios, Datos, Future Scope, Referencias | Análisis del proyecto, definición de arquetipos de usuario, escalabilidad y referencias visuales. |
| **Estructura** | Funcionalidades, Vistas / Sitemaps, Arquitectura de Información, Flujos | Mapa de sitio, jerarquía de navegación y diagramación de flujos de usuario. |
| **Diseño** | Wireframes, UI / Diseño visual, Componentes, Estados | Maquetación en baja/media fidelidad, exploración gráfica, librería de componentes y estados de interacción. |
| **Entregables** | Diseños finales, Prototipo, UI Kit / Design System, Especificaciones | Vistas definitivas, prototipo interactivo navegable y documentación para desarrollo. |
| **Feedback** | Frontend, Backend, Data Analytics, Testers | Espacio dedicado para que cada rol técnico deje comentarios, dudas o revisiones sobre los avances. |

---

## 1. Fase de Investigación y Descubrimiento (Research & Discovery)

La fase de investigación y descubrimiento combina el análisis crítico, la empatía con el usuario y la toma de decisiones del equipo de UX/UI, apoyándose en herramientas de Inteligencia Artificial como **aceleradores metodológicos** para procesar información y explorar alternativas.

### Criterio Humano y Análisis UX
* **Análisis Crítico y Evaluación:** Selección, validación y filtrado de requerimientos según las necesidades reales del proyecto y la viabilidad del producto.
* **Toma de Decisiones de Diseño:** Definición de la estrategia de la experiencia de usuario, priorización de funcionalidades y curaduría visual.
* **Síntesis de Hallazgos:** Interpretación de los datos para transformar descubrimientos en decisiones de arquitectura de información e interfaz.

### Herramientas de Apoyo Asistidas por IA
* **Investigación y Benchmarking:** ChatGPT, Gemini, Claude y Google AI Studio para explorar referencias, agilizar el análisis comparativo y estructurar hipótesis iniciales.
* **Gestión de Fuentes e Insights:** NotebookLM para sintetizar documentación de contexto e investigar perfiles de usuario.
* **Exploración Visual y Conceptual:** Stitch by Google para pruebas iniciales de conceptos gráficos.

> **Enfoque de trabajo:** Las herramientas de IA se emplean únicamente como asistentes de exploración e investigación; toda la validación, estructuración final y diseño responde al criterio técnico y estratégico del equipo de UX/UI.

---

## 2. Arquitectura de Información y Estructura

El diseño de la arquitectura de información se abordó mediante una metodología estructurada, alineando los requerimientos del negocio con la experiencia de usuario y la escalabilidad del sistema.

### Aspectos clave de la estructura:

* **Experiencia de Descubrimiento (Onboarding):** Diagramación de la narrativa visual y de contenido en la zona pública para comunicar la propuesta de valor del Observatorio y facilitar el acceso a la plataforma.
* **Gestión de Accesos y Roles:** Modelado de la estructura de navegación diferenciada entre vistas públicas de consulta general y paneles privados orientados a análisis avanzado y administración del sistema.
* **Modelado de Módulos y Taxonomía de Datos:** Definición conceptual de las pantallas clave (*Panorama Regional, Tendencias, Ocupaciones, Habilidades y Alertas*), estableciendo la jerarquía de filtros, la organización de métricas socioeconómicas/laborales y la estructura para la gestión de fuentes de datos.

---

## 3. Diseño de Interfaz (UI) y Prototipado

Se trabaja en la maquetación progresiva de pantallas, componentes y prototipos navegables.

### Estado de Desarrollo de Vistas

#### Navegación Pública
| Vista / Módulo | Wireframes | Diseño Final |
| :--- | :---: | :---: |
| Landing Page | 🟢 `COMPLETADO` | ⚪ `PENDIENTE` |
| Iniciar sesión *(Login)* | 🟢 `COMPLETADO` | ⚪ `PENDIENTE` |

#### Navegación Privada
| Vista / Módulo | Wireframes | Diseño Final |
| :--- | :---: | :---: |
| Inicio *(Dashboard principal)* | 🟢 `COMPLETADO` | ⚪ `PENDIENTE` |
| Panorama regional | 🟢 `COMPLETADO` | ⚪ `PENDIENTE` |
| Tendencias | 🟢 `COMPLETADO` | ⚪ `PENDIENTE` |
| Ocupaciones | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| Ocupaciones | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| └─ *Detalle de Ocupación* | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| Habilidades | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| Alertas | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| Gestión / Administración | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| ├─ *Gestión de Usuarios* | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |
| └─ *Gestión de Datos* | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |

#### Sistema e Identidad Visual
| Elemento / Recursos UI | Definición Base | Diseño Final |
| :--- | :---: | :---: |
| Paleta de colores, Logo e Identidad definitiva | 🟡 `EN PROCESO` | ⚪ `PENDIENTE` |
| Componentes del UI Kit | 🟡 `EN PROCESO` | ⚪ `PENDIENTE` |
| Estados de interacción *(Hover, Active, Disabled, etc.)* | ⚪ `PENDIENTE` | ⚪ `PENDIENTE` |

---

## 4. Exploración Técnica y Material de Consulta

Como aporte preliminar para analizar la integración entre UI y desarrollo:

* Se exploró la viabilidad de utilizar datos reales en lugar de datos estáticos en el código de muestra.
* Se adjunta un informe y propuesta de modelo de datos sujeto a revisión del equipo Backend.
* **Recursos:** [Código Fuente](https://drive.google.com/file/d/1yEEEiJ4z4CFTyixCQ39Yqh_OzqwNldTN/view) | [Guía de instalación del Stack](https://drive.google.com/file/d/119YQlvfqwdOUVYIo6i8qCeh42nulZ0yq/view)
