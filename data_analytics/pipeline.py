"""
Pipeline Principal de Data Analytics
Observatorio Predictivo de Tendencias Socioeconomicas, Laborales y Educativas (ARG, CHL, URY)
Programa InnovaLab

Orquesta la ejecucion secuencial:
  01. Ingesta de APIs y verificacion de fuentes
  02. Limpieza, armonizacion y exportacion
  03. Indicadores, proyecciones y visualizaciones
"""

import sys
import time
import argparse
from pathlib import Path

# Configurar codificacion UTF-8 para consola en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Asegurar que la carpeta data_analytics este en sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ingesta_01 import ejecutar_ingesta
from src.cleaning_02 import ejecutar_limpieza
from src.indicadores_03 import ejecutar_indicadores


def main():
    parser = argparse.ArgumentParser(description="Pipeline Automatizado de Data Analytics - Observatorio Predictivo")
    parser.add_argument(
        '--etapa',
        type=int,
        choices=[1, 2, 3],
        help='Ejecutar solo una etapa especifica (1: Ingesta, 2: Limpieza, 3: Indicadores). Por defecto ejecuta todas en orden.'
    )
    args = parser.parse_args()

    tiempo_inicio = time.time()
    print("\n" + "=" * 70)
    print("🚀 OBSERVATORIO PREDICTIVO · PIPELINE DE DATA ANALYTICS")
    print(f"Ruta base del proyecto: {BASE_DIR}")
    print("=" * 70 + "\n")

    try:
        if args.etapa is None or args.etapa == 1:
            t0 = time.time()
            ejecutar_ingesta(base_dir=BASE_DIR)
            print(f"⏱️ Tiempo Etapa 01: {round(time.time() - t0, 2)}s\n")

        if args.etapa is None or args.etapa == 2:
            t0 = time.time()
            ejecutar_limpieza(base_dir=BASE_DIR)
            print(f"⏱️ Tiempo Etapa 02: {round(time.time() - t0, 2)}s\n")

        if args.etapa is None or args.etapa == 3:
            t0 = time.time()
            ejecutar_indicadores(base_dir=BASE_DIR)
            print(f"⏱️ Tiempo Etapa 03: {round(time.time() - t0, 2)}s\n")

        tiempo_total = round(time.time() - tiempo_inicio, 2)
        print("=" * 70)
        print(f"✅ PIPELINE COMPLETADO EXITOSAMENTE EN {tiempo_total} SEGUNDOS.")
        print(f"Archivos y visualizaciones guardados en: {BASE_DIR / 'output'}")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n⚠️ ERROR DURANTE LA EJECUCION DEL PIPELINE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
