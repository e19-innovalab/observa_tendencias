"""
Modulo 01: Ingesta Automatizada de Fuentes Oficiales
Observatorio Predictivo de Tendencias Socioeconomicas, Laborales y Educativas (ARG, CHL, URY)
"""

import os
import sys
import json
import time
import zipfile
import shutil
import datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def get_paths(base_dir=None):
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
    else:
        base_dir = Path(base_dir).resolve()

    data_raw = base_dir / 'data' / 'raw'
    data_processed = base_dir / 'data' / 'processed'
    output_dir = base_dir / 'output'

    for d in [data_raw, data_processed, output_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        'base': base_dir,
        'data_raw': data_raw,
        'data_processed': data_processed,
        'output': output_dir,
    }


def auto_descomprimir_zips(directorio_base):
    """
    Inspecciona recursivamente el directorio y descomprime de forma autonoma
    cualquier archivo .zip encontrado en su carpeta de origen.
    """
    if not directorio_base.exists():
        return
    zips_encontrados = list(directorio_base.glob('**/*.zip'))
    for zip_path in zips_encontrados:
        try:
            destino = zip_path.parent
            with zipfile.ZipFile(zip_path, 'r') as zf:
                miembros = [m for m in zf.namelist() if not m.startswith('__MACOSX') and not m.endswith('/')]
                faltantes = [m for m in miembros if not (destino / m).exists()]
                if faltantes:
                    print(f"[Auto-ZIP] Descomprimiendo '{zip_path.name}' en '{destino.name}/'...")
                    zf.extractall(path=destino)
                    print(f"  ✅ Extraidos {len(miembros)} archivos de '{zip_path.name}'.")
                else:
                    print(f"[Auto-ZIP] '{zip_path.name}' ya se encuentra descomprimido.")
        except Exception as e:
            print(f"⚠️ [Auto-ZIP] No se pudo descomprimir '{zip_path.name}': {e}")


def descargar_banco_mundial(indicadores, paises, anio_inicio, anio_fin, dir_raw):
    datos_consolidados = []
    carpeta_wb = dir_raw / 'banco_mundial'
    carpeta_wb.mkdir(parents=True, exist_ok=True)

    headers = {'User-Agent': 'ObservatorioPredictivo/1.0'}
    for ind_cod, desc in indicadores.items():
        registros_ind = []
        for p in paises:
            url = f"https://api.worldbank.org/v2/country/{p}/indicator/{ind_cod}"
            params = {'format': 'json', 'per_page': 1000, 'date': f"{anio_inicio}:{anio_fin}"}
            try:
                r = requests.get(url, params=params, headers=headers, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    if len(data) > 1 and data[1]:
                        for reg in data[1]:
                            val = reg.get('value')
                            if val is not None:
                                registros_ind.append({
                                    'fuente_id': 'WB',
                                    'indicador_codigo': ind_cod,
                                    'indicador_nombre': desc,
                                    'pais': reg['countryiso3code'],
                                    'anio': int(reg['date']),
                                    'valor': float(val),
                                    'unidad': 'USD_PPA' if 'PPA' in ind_cod else ('%' if 'ZS' in ind_cod else 'INDICE'),
                                    'es_observado': True
                                })
            except Exception as e:
                print(f"  ⚠️ [WB] {ind_cod} ({p}): Reintento omitido ({e})")
            time.sleep(0.1)

        if registros_ind:
            datos_consolidados.extend(registros_ind)
            with open(carpeta_wb / f"{ind_cod}.json", 'w', encoding='utf-8') as f:
                json.dump(registros_ind, f, ensure_ascii=False, indent=2)
            print(f"  ✅ [WB] {ind_cod} ({desc[:35]}...): {len(registros_ind)} registros.")
        else:
            print(f"  ⚠️ [WB] {ind_cod}: Sin datos en ventana {anio_inicio}-{anio_fin}.")

    df_wb = pd.DataFrame(datos_consolidados)
    return df_wb


def descargar_cepalstat(indicadores, paises, dir_raw):
    cepal_base = 'https://api-cepalstat.cepal.org/cepalstat/api/v1'
    carpeta_cepal = dir_raw / 'cepalstat'
    carpeta_cepal.mkdir(parents=True, exist_ok=True)

    filas_cepal = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for ind_id, desc in indicadores.items():
        url_dim = f"{cepal_base}/indicator/{ind_id}/dimensions"
        mapa_anios = {}
        try:
            r_dim = requests.get(url_dim, headers=headers, timeout=15)
            if r_dim.status_code == 200:
                for d in r_dim.json().get('body', {}).get('dimensions', []):
                    if 'year' in d.get('name', '').lower() or d.get('id') == 29117:
                        for m in d.get('members', []):
                            if str(m.get('name', '')).isdigit():
                                mapa_anios[m['id']] = int(m['name'])
        except Exception:
            pass

        url = f"{cepal_base}/indicator/{ind_id}/data?format=json&lang=es"
        try:
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code == 200:
                d = r.json()
                raw_data = d.get('body', {}).get('data', [])
                filtrados = [row for row in raw_data if row.get('iso3') in paises]

                for f in filtrados:
                    val = f.get('value')
                    anio_val = None
                    dim_yr = f.get('dim_29117')
                    if dim_yr in mapa_anios:
                        anio_val = mapa_anios[dim_yr]

                    if anio_val is None:
                        anio_cands = [f.get('dim_1401'), f.get('dim_29117'), f.get('year'), f.get('anio'), f.get('period')]
                        for c in anio_cands:
                            if c is not None and str(c).isdigit() and 2000 <= int(c) <= 2030:
                                anio_val = int(c)
                                break

                    if val is not None:
                        try:
                            filas_cepal.append({
                                'fuente_id': 'CEPALSTAT',
                                'indicador_id': ind_id,
                                'indicador_nombre': desc,
                                'pais': f.get('iso3'),
                                'anio': anio_val if anio_val is not None else np.nan,
                                'valor': float(val),
                                'es_observado': True
                            })
                        except (ValueError, TypeError):
                            pass

                with open(carpeta_cepal / f"cepal_{ind_id}.json", 'w', encoding='utf-8') as f_out:
                    json.dump(filtrados, f_out, ensure_ascii=False, indent=2)

                print(f"  ✅ [CEPALSTAT] Indicador {ind_id} ({desc[:32]}...): {len(filtrados)} registros.")
            else:
                print(f"  ⚠️ [CEPALSTAT] Indicador {ind_id}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ⚠️ [CEPALSTAT] Indicador {ind_id}: Error ({e})")
        time.sleep(0.2)

    df_cepal = pd.DataFrame(filas_cepal)
    return df_cepal


def descargar_ilostat_indicador(indicador_id, paises, dir_raw):
    carpeta_ilo = dir_raw / 'ilostat'
    carpeta_ilo.mkdir(parents=True, exist_ok=True)

    ind_clean = indicador_id.replace('DF_', '')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioPredictivo/1.0'}
    for p in paises:
        url = f"https://rplumber.ilo.org/data/indicator/?id={ind_clean}&ref_area={p}&format=.csv"
        try:
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code == 200 and len(r.text) > 80:
                archivo_salida = carpeta_ilo / f"{ind_clean}_{p}.csv"
                with open(archivo_salida, 'w', encoding='utf-8') as f:
                    f.write(r.text)
                print(f"  ✅ [ILOSTAT] {ind_clean} ({p}): OK ({len(r.text.splitlines())} lineas).")
            else:
                print(f"  [ILOSTAT] {ind_clean} ({p}): HTTP {r.status_code} (Serie no disponible por rplumber directo).")
        except Exception as e:
            print(f"  [ILOSTAT] {ind_clean} ({p}): Omitido ({e}).")


def descargar_spu_anuarios(dir_raw):
    """
    Intenta descargar conjuntos de datos abiertos de los Anuarios Estadisticos Universitarios SPU
    (Ministerio de Capital Humano / Datos Argentina) para anos faltantes (ej. 2019, 2018).
    Si los servidores oficiales se encuentran temporalmente inaccesibles (404/502), reporta
    el estado y continua con los anuarios consolidados ya existentes en el repositorio.
    """
    dir_arg = dir_raw / 'argentina'
    dir_arg.mkdir(parents=True, exist_ok=True)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ObservatorioPredictivo/1.0'}
    urls_candidatas = [
        ('2019', 'https://www.argentina.gob.ar/sites/default/files/anuario_csv_2019.zip'),
        ('2018', 'https://www.argentina.gob.ar/sites/default/files/anuario_csv_2018.zip'),
    ]

    for anio_tag, url in urls_candidatas:
        target_zip = dir_arg / f"anuario_csv_{anio_tag}.zip"
        if target_zip.exists():
            print(f"  ✅ [SPU Anuarios] Anuario {anio_tag} ya disponible en: {target_zip.name}")
            continue
        try:
            r = requests.get(url, headers=headers, timeout=10, stream=True)
            if r.status_code == 200 and int(r.headers.get('content-length', 0)) > 10000:
                with open(target_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"  ✅ [SPU Anuarios] Descargado anuario {anio_tag}: {target_zip.name}")
            else:
                print(f"  ℹ️ [SPU Anuarios] Anuario {anio_tag}: Endpoint oficial no disponible (HTTP {r.status_code}). Se utilizan anuarios locales consolidados.")
        except Exception as e:
            print(f"  ℹ️ [SPU Anuarios] Anuario {anio_tag}: Reintento omitido ({e}). Se utilizan anuarios locales consolidados.")


def descargar_indec_ipc(dir_raw):
    """
    Descarga la serie oficial observada de IPC Nacional del INDEC desde la API de Datos Abiertos
    de la Republica Argentina (serie 145.3_INGNACNAL_DICI_M_15, base dic-2016=100).
    Permite armonizar el IPC de Argentina con Chile y Uruguay sin lagunas ni NaN.
    """
    dir_arg = dir_raw / 'argentina'
    dir_arg.mkdir(parents=True, exist_ok=True)
    archivo_json = dir_arg / 'indec_ipc_nacional.json'
    archivo_csv = dir_arg / 'indec_ipc_nacional.csv'
    url = "https://apis.datos.gob.ar/series/api/series/?ids=145.3_INGNACNAL_DICI_M_15&limit=1000"
    headers = {'User-Agent': 'ObservatorioPredictivo/1.0'}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if 'data' in data and data['data']:
                with open(archivo_json, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                registros = []
                for fila in data['data']:
                    fecha_str = fila[0]
                    val = float(fila[1])
                    anio = int(fecha_str.split('-')[0])
                    registros.append({'pais': 'ARG', 'fecha': fecha_str, 'anio': anio, 'ipc_indec': val})
                df_indec = pd.DataFrame(registros)
                df_indec.to_csv(archivo_csv, index=False, encoding='utf-8')
                print(f"  ✅ [INDEC] IPC Nacional descargado: {len(df_indec)} meses ({df_indec['anio'].min()}-{df_indec['anio'].max()}).")
                return df_indec
    except Exception as e:
        print(f"  ⚠️ [INDEC] Error al consultar API de INDEC ({e}). Se utilizara cache local si existe.")

    if archivo_csv.exists():
        try:
            return pd.read_csv(archivo_csv)
        except Exception:
            pass
    elif archivo_json.exists():
        try:
            with open(archivo_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            registros = [{'pais': 'ARG', 'fecha': r[0], 'anio': int(r[0].split('-')[0]), 'ipc_indec': float(r[1])} for r in data.get('data', [])]
            return pd.DataFrame(registros)
        except Exception:
            pass
    return pd.DataFrame()


def inspeccionar_fuentes_locales(dir_raw):
    archivos_detectados = []

    def verificar(ruta_rel, pais, descripcion, obligatorio=True, patrones=None):
        nombre = Path(ruta_rel).name
        candidatos = [
            dir_raw / ruta_rel,
            dir_raw / pais.lower() / nombre,
            dir_raw / ('argentina' if pais == 'ARG' else ('chile' if pais == 'CHL' else 'uruguay')) / nombre,
        ]
        encontrado = None
        for c in candidatos:
            if c.exists():
                encontrado = c
                break

        if not encontrado and patrones:
            for pat in patrones:
                matches = list(dir_raw.glob(pat))
                if matches:
                    encontrado = matches[0]
                    break

        info = {
            'pais': pais,
            'descripcion': descripcion,
            'tipo': 'Obligatorio' if obligatorio else 'Complementario',
            'existe': encontrado is not None,
            'tamanio_mb': round(encontrado.stat().st_size / (1024 * 1024), 2) if encontrado else 0,
            'ruta': str(encontrado) if encontrado else f'No encontrado en {ruta_rel}'
        }
        archivos_detectados.append(info)
        if encontrado:
            print(f"  ✅ [{pais}] Encontrado: {encontrado.name} ({info['tamanio_mb']} MB)")
        else:
            estado_txt = "FALTANTE PRINCIPAL" if obligatorio else "OPCIONAL"
            print(f"  ⚠️ [{pais}] {descripcion}: {estado_txt}")

    print("\nVerificando Fuentes Locales en data/raw:")
    print("--- CHILE ---")
    verificar('chile/TITULADO_2007-2025_web_27_05_2026_E-1.xlsx', 'CHL', 'Titulados Mi Futuro (Historico)', True, ['**/TITULAD*.xlsx'])
    verificar('chile/Buscador_Empleabilidad_e_Ingresos_2024_2025_SIES.xlsx', 'CHL', 'SIES Empleabilidad e Ingresos', False, ['**/*Empleabilidad*SIES*.xlsx'])
    verificar('chile/Buscador_Estadisticas_por_carrera_2024_2025_SIES.xlsx', 'CHL', 'SIES Estadisticas por Carrera', False, ['**/*Estadisticas*carrera*SIES*.xlsx'])

    print("--- ARGENTINA ---")
    verificar('argentina/base_araucano_traducida.xlsx', 'ARG', 'Base SIU-Araucano Graduados', True, ['**/base_araucano*.csv', '**/base_araucano*.xlsx'])
    verificar('argentina/anuario_csv_2022.zip', 'ARG', 'SPU Anuarios Universitarios Oficiales', False, ['**/anuario_csv*.zip'])
    verificar('argentina/puestos_depto_priv_por_clae2.csv', 'ARG', 'CEP-XXI Puestos Privados por CLAE2', False, ['**/puestos*clae2*.csv'])
    verificar('argentina/w_mean_privado_mensual_por_clae2.csv', 'ARG', 'CEP-XXI Salario Medio Privado por CLAE2', False, ['**/w_mean*clae2*.csv'])
    verificar('argentina/w_median_privado_mensual_por_clae2.csv', 'ARG', 'CEP-XXI Salario Mediano Privado por CLAE2', False, ['**/w_median*clae2*.csv'])
    verificar('argentina/share_mujer_privado_mensual_por_clae2.csv', 'ARG', 'CEP-XXI Participacion Mujeres por CLAE2', False, ['**/share_mujer*clae2*.csv'])

    print("--- URUGUAY ---")
    verificar('uruguay/00._educ_superior_datos.csv', 'URY', 'Educacion Superior Uruguay (Egresados)', True, ['**/*educ_superior_datos*.csv'])
    verificar('uruguay/Anuario Estadístico de Educación 2024.xlsx', 'URY', 'MEC Anuario Estadistico de Educacion', False, ['**/*Anuario*Educaci*.xlsx'])
    verificar('uruguay/10235_distribucion_porcentual_de_las_personas_ocupadas_segun_sexo_por_rama_de_actividad_en_ocupa.csv', 'URY', 'INE Uruguay Empleo por Sexo y Rama', False, ['**/*distribucion*ocupadas*sexo*.csv'])

    print("--- REGIONAL / ILOSTAT ---")
    for p in ['ARG', 'CHL', 'URY']:
        verificar(f'ilostat/EAR_EMTA_SEX_ECO_NB_{p}.csv', p, f'ILOSTAT Salarios Medios por Rama y Sexo ({p})', False, [f'**/EAR_EMTA_SEX_ECO_NB_{p}.csv'])

    return pd.DataFrame(archivos_detectados)


def ejecutar_ingesta(base_dir=None):
    """
    Punto de entrada principal para la Ingesta Automatizada.
    """
    paths = get_paths(base_dir)
    print("=" * 65)
    print("INICIANDO ETAPA 01: INGESTA DE FUENTES OFICIALES")
    print(f"Ruta Base: {paths['base']}")
    print(f"Ruta Raw:  {paths['data_raw']}")
    print("=" * 65)

    # 1. Descomprimir zips recursivamente en data_raw
    print("\n[Paso 1/4] Descompresion de archivos ZIP...")
    auto_descomprimir_zips(paths['data_raw'])

    # 2. Ingesta de APIs Oficiales
    paises_iso3 = ['ARG', 'CHL', 'URY']
    anio_desde = 2010
    anio_hasta = dt.date.today().year

    wb_indicadores = {
        'PA.NUS.PPP':     'Factor PPA PIB (LCU por USD internacional)',
        'PA.NUS.PRVT.PP': 'Factor PPA consumo privado (LCU por USD internacional)',
        'FP.CPI.TOTL':    'IPC (Indice de precios base 2010)',
        'SL.UEM.TOTL.ZS': 'Desempleo total (% PEA)',
        'SL.UEM.ADVN.ZS': 'Desempleo con educacion avanzada (% PEA terciaria)'
    }

    print("\n[Paso 2/4] Consumo de APIs Oficiales...")
    # A. Banco Mundial
    print("  • Consultando API Banco Mundial...")
    df_wb = descargar_banco_mundial(wb_indicadores, paises_iso3, anio_desde, anio_hasta, paths['data_raw'])
    if not df_wb.empty:
        archivo_wb = paths['data_raw'] / 'wb_macro_indicadores.csv'
        df_wb.to_csv(archivo_wb, index=False, encoding='utf-8')
        print(f"  ✅ Banco Mundial consolidado en: {archivo_wb.name} ({len(df_wb)} filas)")

    # B. CEPALSTAT
    cepal_indicadores = {
        99:   'Tasa bruta de matricula terciaria (% por sexo)',
        127:  'Tasa de desocupacion por sexo (%)',
        5701: 'Personas 18-24 anos cursando estudios superiores (%)'
    }
    print("  • Consultando API CEPALSTAT...")
    df_cepal = descargar_cepalstat(cepal_indicadores, paises_iso3, paths['data_raw'])
    if not df_cepal.empty:
        archivo_cepal = paths['data_raw'] / 'cepalstat_indicadores.csv'
        df_cepal.to_csv(archivo_cepal, index=False, encoding='utf-8')
        print(f"  ✅ CEPALSTAT consolidado en: {archivo_cepal.name} ({len(df_cepal)} filas)")

    # C. ILOSTAT
    print("  • Consultando API ILOSTAT...")
    descargar_ilostat_indicador('EAP_TEAP_SEX_AGE_EDU_NB', paises_iso3, paths['data_raw'])
    descargar_ilostat_indicador('EAR_EMTA_SEX_ECO_NB', paises_iso3, paths['data_raw'])
    descargar_ilostat_indicador('EMP_TEMP_SEX_ECO_NB', paises_iso3, paths['data_raw'])

    # D. SPU Anuarios (Argentina - descarga de paquetes abiertos complementarios)
    print("  • Verificando paquetes abiertos SPU Anuarios...")
    descargar_spu_anuarios(paths['data_raw'])

    # E. INDEC IPC Nacional (Argentina - serie oficial observada)
    print("  • Consultando API INDEC (IPC Nacional Argentina)...")
    descargar_indec_ipc(paths['data_raw'])

    # 3. Inspeccionar fuentes manuales
    print("\n[Paso 3/4] Inspeccion de archivos manuales y locales...")
    df_estado = inspeccionar_fuentes_locales(paths['data_raw'])

    # 4. Generar reporte consolidado de ingesta
    print("\n[Paso 4/4] Exportando resumen de ingesta...")
    ruta_resumen = paths['output'] / 'resumen_ingesta.csv'
    df_estado.to_csv(ruta_resumen, index=False, encoding='utf-8')
    # Guardar copia en data_processed
    df_estado.to_csv(paths['data_processed'] / 'resumen_ingesta.csv', index=False, encoding='utf-8')
    print(f"  ✅ Resumen de ingesta exportado exitosamente a: {ruta_resumen}")

    print("\n✅ ETAPA 01 (INGESTA) COMPLETADA CON EXITO.\n")
    return {
        'df_wb': df_wb,
        'df_cepal': df_cepal,
        'df_estado': df_estado
    }


if __name__ == '__main__':
    ejecutar_ingesta()
