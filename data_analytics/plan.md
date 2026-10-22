# Plan de Trabajo - Data Analytics
## Observatorio Predictivo de Tendencias Socioeconómicas, Laborales y Educativas
**Alcance Regional:** Argentina, Uruguay y Chile  
**Programa:** InnovaLab  
**Rol:** Data Analytics  

---

## 📌 Protocolo de Trabajo y Uso de este Plan
1. **Implementación secuencial:** Se ejecuta estrictamente **una sola etapa a la vez**.
2. **Actualización continua:** Al finalizar cada etapa, se actualizará este archivo con el estado, detalle de lo implementado y el contexto relevante para la etapa siguiente.
3. **Control y aprobación:** No se realizarán modificaciones estructurales ni de código sin notificar previamente al usuario y esperar su aprobación explícita.
4. **Pausa en pasos manuales:** Cuando una etapa requiera una acción manual del usuario (por ejemplo, la Etapa 2 de subida de datasets), el asistente se detendrá e informará al usuario antes de continuar.

---

## ⚖️ Condiciones Básicas Obligatorias del Proyecto
*Todas las etapas, scripts, transformaciones e indicadores deben respetar sin excepción:*

* **3 Países a comparar:** Argentina, Uruguay y Chile.
* **5 Sectores estratégicos:**
  1. Tecnología
  2. Economía del conocimiento
  3. Salud
  4. Energía
  5. Turismo
* **5 Ocupaciones por sector en común:**
  * Deben ser ocupaciones/carreras homologadas y presentes en los 3 países.
  * Unificación preferente bajo codificación/nomenclatura regional estándar (ej. CIUO-08 / ISCO-08).
* **100% Datos observados:**
  * Estrictamente prohibido el uso de sustituciones, interpolaciones arbitrarias o imputaciones sintéticas/calculadas.
* **Origen de datos:**
  * Obtenidos exclusivamente mediante APIs oficiales o datasets descargados de las fuentes oficiales listadas en la ingesta.
* **Aislamiento e independencia del módulo:**
  * Todos los recursos, datos y salidas deben pertenecer exclusivamente a la rama/directorio `data_analytics/`.
  * No leer datos de backend ni depositar resultados en carpetas de backend.
* **Paridad estricta en comparativas:**
  * Mismo horizonte temporal (misma cantidad de años analizados por país).
  * Mismas ocupaciones y carreras comparables.
  * Salarios convertidos y homologados a **USD PPA (Paridad de Poder Adquisitivo)**.
* **Estilo y formato de código:**
  * No incluir emojis en el código fuente, excepto advertencias (⚠️) o verificaciones (✅).
* **Indicadores obligatorios a generar y comparar (entre los 3 países y los 5 sectores):**
  1. **Cantidad de graduados** por sector y país.
  2. **Estimaciones salariales** por sector y por país.
  3. **Brecha salarial** entre sectores y países.
  4. **Top 10 de universidades con más graduados:** a nivel regional y por país (si un país cuenta con menos de 10 universidades, mostrar el total disponible).
  5. **Top 10 descendente de universidades con menos graduados por país** (excluir países que tengan 10 o menos universidades).
  6. **Brecha de género (laboral y/o de graduados) por sector y país**, unificando categorías:
     * **F**: "femenino", "mujer", "M".
     * **M**: "masculino", "varón", "hombre", "H".
     * **Tercera opción**: "no binario", "indefinido", "otros".
  7. **Tasas de crecimiento interanual y Z-scores**.
  8. **Proyecciones de tendencia** por sector y ocupación.

---

## 🗺️ Mapa de Etapas

| Etapa | Descripción | Tipo | Estado |
| :---: | :--- | :---: | :---: |
| **Etapa 1** | Armar estructura prolija en `data_analytics/`: carpetas `data/raw/`, `data/processed/`, `output/` y `src/`. | Automatizada | ✅ Completada |
| **Etapa 2** | Subida manual de datasets a `data/raw/` (ARG, CHL, URY) e incorporación de scraping `linkedin_jobs/`. | 👤 Manual + Ajuste | ✅ Completada |
| **Etapa 3** | Agregar `.gitignore` en `data_analytics/` para evitar subir datasets a GitHub. | Automatizada | ✅ Completada |
| **Etapa 4** | Migrar cuadernos a módulos `.py` en `src/`, con `__init__.py` y `pipeline.py` (01 ➔ 02 ➔ 03), guardando en `data/processed/` y `output/`. | Automatizada | ✅ Completada |
| **Etapa 5** | Agregar `README.md` actualizado en `data_analytics/` (paso a paso, requisitos, estructura, ejecución y pipeline). | Automatizada | ✅ Completada |
| **Etapa 6** | Sugerir en `README.md` fuentes oficiales a incorporar y mejoras al código para métricas observadas reales. | Automatizada | ✅ Completada |
| **Etapa 7** | Eliminar la carpeta `cuadernos/` una vez validada y aprobada la versión `.py` en `src/`. | Automatizada | ✅ Completada |

---

## 📝 Registro de Avance y Contexto entre Etapas

### Estado Actual:
* **Todas las etapas (1 a 7) Completadas al 100%**:
  * Estructura organizada, datasets cargados y protegidos por `.gitignore`.
  * Código modular migrado, probado y validado end-to-end (`pipeline.py`, `src/ingesta_01.py`, `src/cleaning_02.py`, `src/indicadores_03.py`, `src/__init__.py`).
  * Carpeta transitoria `cuadernos/` eliminada de forma segura tras verificar la paridad funcional estricta.
  * `README.md` y `requirements.txt` actualizados con documentación de uso, sugerencias de fuentes oficiales y hoja de ruta en 4 fases.
* **Estado del Módulo:** 100% operativo, autónomo y reproducible en local.

### Bitácora de Etapas:

#### ✅ Etapa 1: Estructura de directorios en `data_analytics`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se crearon los directorios base para la organización del proyecto (`fuentes/`, `output/`, `src/`).

#### ✅ Etapa 2: Carga de datasets, reconfiguración a `data/` e incorporación de `linkedin_jobs`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se reconfiguró la carpeta `fuentes/` transformándola a la convención estándar `data/raw/` y creando `data/processed/`.
  * Se trasladaron e inspeccionaron todos los datasets cargados por el usuario para los tres países (Argentina, Chile y Uruguay).
  * Se importó desde backend la carpeta `linkedin_jobs/` a `data/raw/linkedin_jobs/`.
  * Se eliminó la carpeta transitoria `fuentes/`.

#### ✅ Etapa 3: Creación y verificación de `.gitignore`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se creó el archivo `data_analytics/.gitignore` protegiendo datasets masivos, formatos binarios y cachés.
  * Se verificó mediante `git status -u` que no se filtran archivos masivos al control de versiones.

#### ✅ Etapa 4: Migración modular a `src/` y orquestación con `pipeline.py`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se crearon los módulos Python manteniendo el 100% de la lógica y funciones de los cuadernos de Colab, adaptando rutas a la arquitectura local y eliminando dependencias de Google Drive (`src/ingesta_01.py`, `src/cleaning_02.py`, `src/indicadores_03.py`, `src/__init__.py` y `pipeline.py`).
  * Se ejecutó el pipeline completo de manera exitosa: 21 datasets consolidados exportados a `data_analytics/output/` y 7 gráficos de alta resolución guardados en `data_analytics/output/graficos/`.

#### ✅ Etapa 5: Documentación técnica y guía de ejecución en `README.md`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se creó el archivo `data_analytics/requirements.txt` con las dependencias requeridas (`pandas`, `numpy`, `requests`, `scipy`, `matplotlib`, `openpyxl`, `odfpy`).
  * Se redactó el archivo `data_analytics/README.md` con la arquitectura, guía de uso, detalle de módulos y catálogo de entregables.

#### ✅ Etapa 6: Sugerencias de fuentes oficiales y mejoras técnicas en `README.md`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se incorporaron en `data_analytics/README.md` dos secciones estratégicas:
    * **Sección 7 (Fuentes Oficiales Adicionales Sugeridas):** EPH del INDEC (Argentina) para salarios por ocupación CIUO, microdatos ECH del INE (Uruguay) para series temporales continuas observadas, base completa de empleabilidad SIES y ENE/SENCE (Chile), y explotación de `linkedin_jobs/` para demandas en tiempo cercano al real.
    * **Sección 8 (Hoja de Ruta de Mejoras Técnicas en 4 Fases):** Fase 1 (Homologación CIUO-08 a 4 dígitos para 5 ocupaciones por sector), Fase 2 (Ingestor y ponderador muestral de microdatos), Fase 3 (NLP y minería de texto sobre avisos de LinkedIn) y Fase 4 (Modelos ARIMA / series de tiempo robustas para series >5 años).

#### ✅ Etapa 7: Eliminación de la carpeta obsoleta `cuadernos/`
* **Fecha de ejecución:** 2026-10-22
* **Acciones realizadas:**
  * Se realizó la comparación y verificación minuciosa entre `cuadernos/` y `src/`, comprobando la preservación del 100% de las funcionalidades, diccionarios clasificadores, fórmulas matemáticas y entregables canónicos.
  * Se probó la ejecución completa e individual de los módulos en `src/` y de `pipeline.py`.
  * Se eliminó de manera segura y definitiva el directorio `data_analytics/cuadernos/`.
  * El módulo de Data Analytics queda limpio, profesionalizado y operando exclusivamente mediante código Python estándar.
