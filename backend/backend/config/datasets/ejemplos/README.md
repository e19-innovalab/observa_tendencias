# Archivos de ejemplo para la carga manual

Sirven para probar la revisión de la plantilla genérica (Administración → Datos → Cargar). Se
descargan desde la pantalla o con `GET /api/v1/datasets/profiles/plantilla_generica/examples/{nombre}`.

- `ejemplo_valido.csv`: desocupación y tasa de actividad anual de Argentina, Chile y Uruguay,
  2022–2024. Son valores **reales de ILOSTAT y del Banco Mundial**, copiados de la base el
  2026-11-01. Pasa la revisión
  y muestra el aviso de que esos valores ya existen en una fuente oficial. No hace falta cargarlo.
- `ejemplo_con_errores.csv`: el mismo archivo con errores puestos a propósito: país fuera del
  catálogo (BRA, PER), indicador inexistente, período ilegible, frecuencia inválida, valor con «%»,
  valor vacío y ocupación CIUO inexistente. Se rechaza y muestra los errores agrupados.
