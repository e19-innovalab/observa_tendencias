# Búsqueda por significado (prototipo)

Prueba si un modelo chico puede convertir lo que escribe una persona ("colectivero", "programador de apps") en un código CIUO-08, para usarlo cuando el buscador de la app no encuentra nada. **Todavía no forma parte de la app.** No toca la base de datos ni los servidores.

## Cómo funciona

1. `build_data.py` junta todos los nombres en español de cada grupo CIUO-08:
   - el título oficial y la lista "incluye" de `config/reference/isco08_occupations.yaml`;
   - los nombres de ESCO de cada ocupación del grupo: el nombre preferido y los alternativos;
   - los nombres locales de `config/reference/ocupaciones_nombres_locales.yaml`: palabras de Argentina, Chile y Uruguay que ESCO no tiene (colectivero, gasfíter, patovica…).

   La URL de ESCO sale de `config/sources.yaml`. Las respuestas de ESCO quedan guardadas en `data/esco_raw/`, así que volver a correrlo no repite pedidos.
2. `evaluate.py` mide, sobre las búsquedas de `testset.yaml`, cuántas veces el código correcto aparece primero o entre los primeros 3 o 5. Compara:
   - `lexical_ciuo`: la regla del buscador actual sobre los títulos CIUO. Es lo que la app encuentra hoy.
   - `lexical_all`: la misma regla sobre todos los nombres (CIUO + ESCO). No usa ningún modelo.
   - los modelos multilingües de `config.yaml`, que buscan por significado.
   - el modelo entrenado, si existe `models/occupation-match-es`.

   Por defecto oculta del índice los nombres iguales a una frase de prueba, así el puntaje mide palabras no vistas. `--with-test-phrases` muestra lo que respondería la app con la lista completa. Cada corrida queda en `results/` con fecha; no se borran las anteriores.
3. `train.py` ajusta un modelo con pares (nombre → título CIUO del mismo grupo). Nunca entrena con:
   - las frases de `testset.yaml`;
   - un 10 % de los códigos, elegidos al azar y guardados en `holdout.json`.

## Uso

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python build_data.py     # ~15 min la primera vez (ESCO)
.venv/bin/python evaluate.py       # o: evaluate.py --only lexical e5-small
```

### Entrenar en otra máquina (GPU NVIDIA)

1. Copiar esta carpeta, incluida `data/labels_es.jsonl` (no hace falta `data/esco_raw/`).
2. Instalar PyTorch con CUDA ([pytorch.org](https://pytorch.org/get-started/locally/)) y después `pip install -r requirements.txt`.
3. Correr `python train.py`. Con una RTX 3080 debería tardar menos de una hora.
4. Traer de vuelta la carpeta `models/occupation-match-es/` y correr `evaluate.py`.

## Configuración

Todo está en `config.yaml`: rutas, modelos a comparar, valores de k y parámetros de entrenamiento. `data/`, `models/` y `.venv/` no van a git.

## Estado

- `testset.yaml`: revisado y aprobado (Paula Vergara, 2026-11-01) contra ISCO-08 Vol. 1 (OIT). Si ESCO asigna otro grupo a la misma palabra, manda ISCO-08.
- `config/reference/ocupaciones_nombres_locales.yaml` (antes `local_names.yaml` en esta carpeta; la usa también la app): revisado y aprobado (Paula Vergara, 2026-11-01) contra ISCO-08 Vol. 1 (OIT). 251 entradas; las 22 que tenían dudas se corrigieron en la revisión.
- Primera medición (2026-11-01, 86 búsquedas): buscador actual 23 % de aciertos en primer lugar; mismo buscador con nombres ESCO 49 %; `multilingual-e5-base` sin entrenar 64 % en primer lugar y 81 % entre los primeros 5. La mayoría de los errores son palabras locales que ESCO no tiene (colectivero, gasfíter, patovica…).
- Segunda medición (2026-11-01, con `local_names.yaml`). Frases de prueba ocultas: `multilingual-e5-base` acierta 62 % en primer lugar, 79 % entre los primeros 3 y 88 % entre los primeros 5. Con la lista completa (lo que vería la app): 86 % / 98 % / 100 %. El mismo buscador actual sobre todos los nombres, sin modelo: 72 % en primer lugar.
