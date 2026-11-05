"""
Paquete Data Analytics - Observatorio Predictivo de Tendencias
Modulos de procesamiento, limpieza e indicadores socioeconomicos.
"""

from .ingesta_01 import ejecutar_ingesta
from .cleaning_02 import ejecutar_limpieza
from .indicadores_03 import ejecutar_indicadores


def ejecutar_todo(base_dir=None):
    """
    Ejecuta el flujo secuencial completo de los 3 modulos (01 -> 02 -> 03).
    """
    print("\n>>> EJECUTANDO PIPELINE COMPLETO DE DATA ANALYTICS <<<\n")
    res_ingesta = ejecutar_ingesta(base_dir=base_dir)
    res_limpieza = ejecutar_limpieza(base_dir=base_dir)
    res_indicadores = ejecutar_indicadores(base_dir=base_dir)

    print("\n" + "=" * 65)
    print("✅ FLUJO COMPLETO FINALIZADO EXITOSAMENTE.")
    print("=" * 65 + "\n")
    return {
        'ingesta': res_ingesta,
        'limpieza': res_limpieza,
        'indicadores': res_indicadores,
    }


__all__ = [
    'ejecutar_ingesta',
    'ejecutar_limpieza',
    'ejecutar_indicadores',
    'ejecutar_todo',
]


if __name__ == '__main__':
    ejecutar_todo()
