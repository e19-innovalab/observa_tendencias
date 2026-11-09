# Cruce de fuentes con los datos de Noelia

Compara la carpeta `raw-noelia` (datos de `data_analytics`) con los archivos y las APIs del
backend, y deja una versión limpia en `data/processed/consolidado_fuentes/`.

**Estado:** este cruce fue una comparación puntual. `data/scripts/build_consolidado_fuentes.py` y
los CSV de `consolidado_fuentes/` quedan como registro local (no se suben al repositorio) y la aplicación no los lee. Los egresados
por universidad se cargan aparte, desde las páginas oficiales (sección siguiente), por ahora **solo
en la base local**.

## Egresados por universidad en la aplicación

La fuente `universidades_egresados` (`app/datasets/universities.py`) se revisa una vez por mes con
`python -m app.jobs.run --source universidades_egresados`. Lee los enlaces en las páginas oficiales
y descarga los archivos solo si cambió algún enlace. Carga `hecho_instituciones_egresados`,
`ranking_universidades_nacional` y `ranking_universidades_regional` (migración 0025), y la API los
entrega en `GET /graduates/universities` y `GET /graduates/universities/ranking`.

- **Controles:** si un archivo cambia de formato o las sumas por institución no coinciden con los
  totales publicados, no se carga nada y queda una alerta.
- **Historial:** los valores que cambian o desaparecen quedan en `data_revisions`. Los rankings se
  derivan de esos valores y se recalculan en cada carga.
- **Nombres:** `config/reference/universidades_nombres.yaml` une cada nombre publicado con su nombre
  normalizado. Un nombre nuevo se carga como viene y la corrida queda en `partial` con el aviso.
- **Una fuente por institución:** para UdelaR se carga su propia serie, no la cifra preliminar del
  MEC, para no contar dos veces.
- **Ranking regional:** usa el último año con datos de los tres países, calculado en cada carga.

| Datos | Archivo | Página oficial |
|---|---|---|
| Argentina 2014-2024 | `adelanto_anuario_24_14-08.zip` | [Anuarios, DIU](https://www.argentina.gob.ar/educacion/universidades/informacion/publicaciones/anuarios) |
| Argentina 2012-2013 | `anuario_csv_2022.zip` | [Anuarios, DIU](https://www.argentina.gob.ar/educacion/universidades/informacion/publicaciones/anuarios) |
| Chile | `TITULADO_2007-<año>_web_*.xlsx` | Mi Futuro, según `config/datasets/mifuturo_titulados.yaml` |
| Uruguay | Anuarios del MEC, uno por año desde 2020 | gub.uy, según `config/datasets/mec_uy_egresados_grado.yaml` |
| UdelaR | `1.Serie-Egresos-totales-Grado-por-Servicio-2000-<año>.ods` | [Planeamiento de la Udelar](https://planeamiento.udelar.edu.uy/portal/egresados/egresados-de-grado/) |

## Archivos de salida

| Archivo | Contenido |
|---|---|
| `inventario_fuentes.csv` | Los 18 archivos de datos, con hash, estado y decisión |
| `egresados_argentina_total.csv` | Anuario contra CTI, año por año, 2012-2024 |
| `egresados_por_universidad.csv` | Egresados por institución y año, en los 3 países |
| `universidades_mas_egresados.csv` | Top 10 regional 2022 y top 10 de cada país en su último año |
| `laboral_argentina_clae2.csv` | Puestos, salario medio y mediano y participación femenina por rama, mensual, 2007-2023 |
| `empleabilidad_chile_carrera.csv`, `empleabilidad_chile_institucion.csv` | Buscadores de SIES, con las columnas publicadas |
| `controles.csv` | Cada suma contra el total que publica la fuente |

## Criterios

- **Argentina, egresados de pregrado y grado:** el anuario del DIU. Adelanto 2024, cuadros 2.1.4 y
  2.2.4, para 2014-2024; anuario 2022 para 2012-2013. En los años en común, los dos anuarios dan lo mismo.
- **Archivo CTI:** queda como comparación. Da 17 % a 19 % menos que el anuario en 2016-2019 y 2021,
  sobre todo en pregrado. Falta preguntar al DIU o a CTI por qué. Esos años no se corrigieron en la base.
- **Chile:** Mi Futuro, solo universidades y nivel Pregrado.
- **Uruguay:** cada año sale del anuario MEC de ese año. Para UdelaR manda su propia serie, porque
  el MEC publica un dato preliminar; el del MEC se conserva con `es_principal = False`.
- **Sin datos:** `-`, `s/d`, `s/i`, `n/a` y `-99` quedan vacíos, nunca en cero.
- **Nombres:** como los publica cada fuente. No hay una tabla que unifique instituciones.

## Lo que no se consolidó

- **`00._educ_superior_datos.csv`:** es el archivo CTI/SPU de Argentina (2014-2023). En una versión inicial figuraba en Uruguay; en la versión actual de `data_analytics` (`cleaning_02.py`, `fuentes.yaml` y `README.md`) ya fue reubicado en Argentina y para Uruguay se integraron los 5 Anuarios Estadísticos de Educación del MEC (2020-2024) junto con la serie histórica de UdelaR (2000-2024).
- **`base_araucano_traducida.xlsx`:** son microdatos individuales (id, año de nacimiento, salario),
  de origen sin confirmar. No es un censo: en 2018 tiene unos 100.000 egresados de pregrado y grado,
  contra 132.744 del anuario.
- **`10235_….csv` (INE Uruguay):** cubre 2012-2017 en porcentajes, y `fuentes.yaml` ya lo descarta.
- **Copias de archivos que ya teníamos:** `TITULADO`, Anuario MEC 2024 y LinkedIn.

## Limitaciones

- **Universidades con más egresados:** mide tamaño, no calidad. Pregrado y grado no son exactamente
  lo mismo en los 3 países.
- **Saltos en los datos publicados:** se dejaron tal cual. Por ejemplo, Rosario pasa de 10.301 (2022)
  a 3.687 (2023), y Buenos Aires de 18.936 (2021) a 25.970 (2022).
- **Adelanto 2024:** es parcial y puede corregirse.
- **`puestos_informados`:** suma solo los departamentos con dato. CEP-XXI suprime celdas (`-99`), así
  que es un piso; `departamentos_suprimidos` dice cuántas faltan.
- **Buscadores de SIES:** falta confirmar de dónde se descargaron. Los encabezados dicen "cohortes
  2018 a 2022", pero las columnas dicen 2019 a 2023; hay que aclararlo antes de usarlos.
