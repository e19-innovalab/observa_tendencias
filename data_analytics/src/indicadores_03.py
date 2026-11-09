"""
Modulo 03: Analisis de Indicadores, Brechas y Proyecciones Predictivas
Observatorio Predictivo de Tendencias Socioeconomicas, Laborales y Educativas (ARG, CHL, URY)
"""

import os
import sys
import datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Modo no interactivo para entornos de pipeline
import matplotlib.pyplot as plt
from scipy import stats
from matplotlib.patches import Patch

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
    graficos_dir = output_dir / 'graficos'

    for d in [data_processed, output_dir, graficos_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        'base': base_dir,
        'data_raw': data_raw,
        'data_processed': data_processed,
        'output': output_dir,
        'graficos': graficos_dir,
    }


def resolver_hecho(nombre_archivo, paths):
    candidatos = [
        paths['output'] / nombre_archivo,
        paths['data_processed'] / nombre_archivo,
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def obtener_graduados_totales_por_genero(paths, df_egresados=None):
    """
    Carga la tabla normalizada graduados_totales_genero_limpio.csv generada en cleaning_02.py.
    Si no existe aun en disco, invoca procesar_graduados_totales_genero de cleaning_02.py.
    """
    ruta_limpia = resolver_hecho('graduados_totales_genero_limpio.csv', paths)
    if ruta_limpia is None or not ruta_limpia.exists():
        from cleaning_02 import procesar_graduados_totales_genero
        df_tot = procesar_graduados_totales_genero(paths)
    else:
        df_tot = pd.read_csv(ruta_limpia)

    for col in ['F', 'M', 'NB', 'total', 'pct_mujeres', 'pct_varones', 'pct_nb', 'brecha_pct']:
        if col in df_tot.columns:
            df_tot[col] = pd.to_numeric(df_tot[col], errors='coerce').round(2)
    return df_tot.sort_values(['pais', 'anio']).reset_index(drop=True)


def obtener_empleo_sectorial_por_genero(paths):
    """
    Carga la tabla normalizada ilostat_empleo_sectorial_limpio.csv generada en cleaning_02.py.
    """
    ruta_limpia = resolver_hecho('ilostat_empleo_sectorial_limpio.csv', paths)
    if ruta_limpia is None or not ruta_limpia.exists():
        from cleaning_02 import procesar_ilostat_empleo
        procesar_ilostat_empleo(paths)
        ruta_limpia = resolver_hecho('ilostat_empleo_sectorial_limpio.csv', paths)
    if ruta_limpia and ruta_limpia.exists():
        df_emp = pd.read_csv(ruta_limpia)
        for col in ['F', 'M', 'NB', 'total', 'pct_mujeres', 'pct_varones', 'brecha_pct']:
            if col in df_emp.columns:
                df_emp[col] = pd.to_numeric(df_emp[col], errors='coerce').round(2)
        return df_emp
    return pd.DataFrame()


def obtener_ocupados_educ_superior_por_genero(paths):
    """
    Carga la tabla normalizada ilostat_ocupados_educ_superior_limpio.csv generada en cleaning_02.py
    (personas ocupadas con Educacion Superior EDU_AGGREGATE_ADV por sector y sexo).
    """
    ruta_limpia = resolver_hecho('ilostat_ocupados_educ_superior_limpio.csv', paths)
    if ruta_limpia is None or not ruta_limpia.exists():
        from cleaning_02 import procesar_ilostat_empleo_educ_superior
        df_edu = procesar_ilostat_empleo_educ_superior(paths)
    else:
        df_edu = pd.read_csv(ruta_limpia)

    for col in ['F', 'M', 'NB', 'total', 'pct_mujeres', 'pct_varones', 'brecha_pct']:
        if col in df_edu.columns:
            df_edu[col] = pd.to_numeric(df_edu[col], errors='coerce').round(2)
    return df_edu


def generar_reporte_brechas_genero_detallado(paths, df_egresados):
    """
    Genera el reporte detallado de brechas formativas y laborales por genero con las 3 dimensiones
    normalizadas a 2 decimales:
    1. graduados_universitarios_total: Total Universitario por genero en ventana comun 2020-2024 (SPU, SIES, MEC).
    2. personas_ocupadas_miles: Empleo total por genero y sector en ano comun 2024 (OIT/ILOSTAT EMP_TEMP_SEX_ECO_NB).
    3. ocupados_educ_superior_miles: Ocupados con Educacion Superior por genero y sector en ano comun 2024 (OIT/ILOSTAT EMP_TEMP_SEX_ECO_EDU_NB).
    """
    rows = []

    # 1. Graduados universitarios en TOTAL (2020-2024)
    df_grad_tot = obtener_graduados_totales_por_genero(paths, df_egresados)
    for _, r in df_grad_tot.iterrows():
        rows.append({
            'pais': r['pais'],
            'sector': 'Total Universitario',
            'tipo_indicador': 'graduados_universitarios_total',
            'anio': int(r['anio']),
            'F': round(float(r['F']), 2),
            'M': round(float(r['M']), 2),
            'otros': round(float(r['NB']), 2) if pd.notna(r['NB']) else np.nan,
            'total': round(float(r['total']), 2),
            'pct_mujeres': round(float(r['pct_mujeres']), 2),
            'brecha_pct': round(float(r['brecha_pct']), 2),
            'fuente': r['fuente'],
            'nota_metodologica': r['nota_metodologica']
        })

    # 2. Empleo sectorial total OIT/ILOSTAT 2024 (en miles de personas)
    df_emp_sec = obtener_empleo_sectorial_por_genero(paths)
    if not df_emp_sec.empty:
        sub_emp_24 = df_emp_sec[df_emp_sec['anio'] == 2024]
        for _, r in sub_emp_24.iterrows():
            rows.append({
                'pais': r['pais'],
                'sector': r['sector'],
                'tipo_indicador': 'personas_ocupadas_miles',
                'anio': int(r['anio']),
                'F': round(float(r['F']), 2),
                'M': round(float(r['M']), 2),
                'otros': np.nan,
                'total': round(float(r['total']), 2),
                'pct_mujeres': round(float(r['pct_mujeres']), 2),
                'brecha_pct': round(float(r['brecha_pct']), 2),
                'fuente': r['fuente'],
                'nota_metodologica': r['nota_metodologica']
            })

    # 3. Ocupados con Educacion Superior por sector OIT/ILOSTAT 2024 (en miles de personas)
    df_edu_sec = obtener_ocupados_educ_superior_por_genero(paths)
    if not df_edu_sec.empty:
        sub_edu_24 = df_edu_sec[df_edu_sec['anio'] == 2024]
        for _, r in sub_edu_24.iterrows():
            rows.append({
                'pais': r['pais'],
                'sector': r['sector'],
                'tipo_indicador': 'ocupados_educ_superior_miles',
                'anio': int(r['anio']),
                'F': round(float(r['F']), 2),
                'M': round(float(r['M']), 2),
                'otros': np.nan,
                'total': round(float(r['total']), 2),
                'pct_mujeres': round(float(r['pct_mujeres']), 2),
                'brecha_pct': round(float(r['brecha_pct']), 2),
                'fuente': r['fuente'],
                'nota_metodologica': r['nota_metodologica']
            })

    df_rep = pd.DataFrame(rows)
    for col in ['F', 'M', 'otros', 'total', 'pct_mujeres', 'brecha_pct']:
        if col in df_rep.columns:
            df_rep[col] = pd.to_numeric(df_rep[col], errors='coerce').round(2)

    fout_proc = paths['data_processed'] / 'reporte_brechas_genero_detallado.csv'
    fout_out = paths['output'] / 'reporte_brechas_genero_detallado.csv'
    df_rep.to_csv(fout_proc, index=False, encoding='utf-8')
    df_rep.to_csv(fout_out, index=False, encoding='utf-8')
    print(f"  ✅ Reporte detallado de brechas de genero exportado ({len(df_rep)} filas): {fout_out.name}")
    return df_rep


def generar_reporte_densidad_profesional(paths, df_egresados_sector):
    """
    Decision Etapa 6 Item 6.4 (Opcion A):
    Cruza la oferta observada de graduados anuales con la demanda laboral observada de personas
    ocupadas (OIT/ILOSTAT) para los anos comunes, calculando la Tasa de Densidad Profesional / Renovacion
    (Graduados por cada 1.000 personas ocupadas en el sector).
    """
    ruta_ocup = resolver_hecho('hecho_ocupacion_terciarios.csv', paths)
    if not ruta_ocup or not ruta_ocup.exists():
        print("  ⚠️ hecho_ocupacion_terciarios.csv no encontrado para cruce de densidad profesional.")
        return None

    df_oc = pd.read_csv(ruta_ocup)
    df_emp = df_oc[df_oc['puestos_empleo'].notna() & (df_oc['fuente_id'] == 'OIT_ILOSTAT')][['pais', 'sector', 'anio', 'puestos_empleo']].copy()
    if df_emp.empty:
        print("  ⚠️ Sin datos de puestos_empleo OIT para calcular densidad profesional.")
        return None

    df_densidad = pd.merge(
        df_egresados_sector[['pais', 'sector', 'anio', 'graduados_anuales']],
        df_emp,
        on=['pais', 'sector', 'anio'],
        how='inner'
    )
    df_densidad['graduados_por_mil_ocupados'] = ((df_densidad['graduados_anuales'] / df_densidad['puestos_empleo']) * 1000).round(2)
    df_densidad['ratio_graduados_vs_empleo_pct'] = ((df_densidad['graduados_anuales'] / df_densidad['puestos_empleo']) * 100).round(2)
    df_densidad['fuente_graduados'] = df_densidad['pais'].map({'ARG': 'Araucano_SPU', 'CHL': 'SIES_MiFuturo', 'URY': 'MEC_Superior'})
    df_densidad['fuente_empleo'] = 'OIT_ILOSTAT_EMP_TEMP_SEX_ECO_NB'
    df_densidad['concepto'] = 'Graduados anuales observados por cada 1.000 personas ocupadas en el sector (Presion formativa / Renovacion de talento)'

    df_densidad = df_densidad.sort_values(['pais', 'sector', 'anio'])
    archivo_dens = paths['output'] / 'reporte_densidad_profesional_sector.csv'
    df_densidad.to_csv(archivo_dens, index=False, encoding='utf-8')
    df_densidad.to_csv(paths['data_processed'] / 'reporte_densidad_profesional_sector.csv', index=False, encoding='utf-8')
    print(f"  ✅ Reporte de densidad profesional (formacion vs puestos de trabajo) guardado en: {archivo_dens.name} ({len(df_densidad)} registros cruzados).")
    return df_densidad


def verificar_matriz_reportes_3x5(paths):
    """
    Decision Etapa 6 Item 6.5:
    Audita que los reportes sectoriales consolidados contengan la matriz completa 3 paises x 5 sectores (15 estratos).
    """
    reportes_a_verificar = [
        ('indicadores_interanuales_zscore.csv', 'pais', 'sector'),
        ('proyecciones_oferta_demanda.csv', 'pais', 'sector'),
        ('reporte_presupuesto_educativo.csv', 'pais', 'sector'),
        ('analisis_genero_integral.csv', 'pais', 'sector'),
        ('reporte_salarios_detalle_local.csv', 'pais', 'sector'),
        ('reporte_densidad_profesional_sector.csv', 'pais', 'sector')
    ]
    print("\n[Verificacion Matriz 3x5] Auditando reportes sectoriales...")
    for nombre_rep, col_p, col_s in reportes_a_verificar:
        ruta = paths['output'] / nombre_rep
        if ruta.exists():
            df = pd.read_csv(ruta)
            paises = sorted(df[col_p].dropna().unique())
            sectores = sorted(df[col_s].dropna().unique())
            n_estratos = len(df.drop_duplicates(subset=[col_p, col_s]))
            print(f"  • {nombre_rep}: {len(paises)} paises ({paises}), {len(sectores)} sectores. Estratos unicos: {n_estratos}")
            if len(paises) < 3 or len(sectores) < 5:
                print(f"    ⚠️ Advertencia: {nombre_rep} no cubre integralmente los 3 paises o 5 sectores.")
        else:
            print(f"  • {nombre_rep}: No encontrado.")


def ejecutar_indicadores(base_dir=None):
    """
    Punto de entrada principal para el Calculo de Indicadores y Proyecciones.
    """
    paths = get_paths(base_dir)
    print("=" * 65)
    print("INICIANDO ETAPA 03: INDICADORES, BRECHAS Y PROYECCIONES")
    print(f"Ruta Base:     {paths['base']}")
    print(f"Ruta Output:   {paths['output']}")
    print(f"Ruta Graficos: {paths['graficos']}")
    print("=" * 65)

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.size'] = 10

    # 1. Carga de Hechos Consolidados
    print("\n[Paso 1/6] Cargando datos consolidados...")
    ruta_egresados = resolver_hecho('hecho_egresados.csv', paths)
    if not ruta_egresados:
        raise FileNotFoundError("⚠️ No se encontro hecho_egresados.csv. Ejecuta primero la Etapa 02.")

    df_egresados = pd.read_csv(ruta_egresados)
    paises_presentes = list(df_egresados['pais'].unique())
    print(f"  ✅ Hecho egresados cargado: {len(df_egresados):,} filas. Paises: {paises_presentes}")

    partes_sector = []
    for p in paises_presentes:
        sub_p = df_egresados[df_egresados['pais'] == p]
        if (sub_p['sexo'] == 'T').any():
            sub_t = sub_p[sub_p['sexo'] == 'T']
        else:
            sub_t = sub_p
        agrupado = (sub_t.groupby(['pais', 'sector', 'anio'])['valor']
                    .sum().reset_index().rename(columns={'valor': 'graduados_anuales'}))
        partes_sector.append(agrupado)

    df_egresados_sector = pd.concat(partes_sector, ignore_index=True)

    # 2. Variacion Interanual y Z-Score
    print("\n[Paso 2/6] Calculando variacion interanual y Z-scores...")
    df_egresados_sector = df_egresados_sector.sort_values(['pais', 'sector', 'anio'])

    # Validacion estricta de consecutividad temporal (Decision Etapa 6 Item 6.2):
    # Si anio - anio_lag != 1 (ej. Argentina 2020 vs 2018 por vacancia 2019), se deja vacio (NaN) y se informa
    df_egresados_sector['anio_lag1'] = df_egresados_sector.groupby(['pais', 'sector'])['anio'].shift(1)
    df_egresados_sector['es_consecutivo'] = (df_egresados_sector['anio'] - df_egresados_sector['anio_lag1']) == 1

    df_egresados_sector['graduados_lag1'] = np.where(
        df_egresados_sector['es_consecutivo'],
        df_egresados_sector.groupby(['pais', 'sector'])['graduados_anuales'].shift(1),
        np.nan
    )
    df_egresados_sector['var_pct_anual'] = np.where(
        df_egresados_sector['es_consecutivo'],
        ((df_egresados_sector['graduados_anuales'] - df_egresados_sector['graduados_lag1']) / df_egresados_sector['graduados_lag1']) * 100,
        np.nan
    )
    df_egresados_sector['nota_consecutividad'] = np.where(
        df_egresados_sector['es_consecutivo'],
        'Ano consecutivo observado',
        np.where(df_egresados_sector['anio_lag1'].isna(), 'Inicio de serie historica', 'Ano anterior no observado (salto temporal sin 2019)')
    )

    media_var = df_egresados_sector.groupby(['pais', 'sector'])['var_pct_anual'].transform('mean')
    std_var = df_egresados_sector.groupby(['pais', 'sector'])['var_pct_anual'].transform('std')
    df_indicadores = df_egresados_sector.copy()
    df_indicadores['zscore_dinamismo'] = np.where(std_var > 0, (df_indicadores['var_pct_anual'] - media_var) / std_var, np.nan)
    df_indicadores['var_pct_anual'] = df_indicadores['var_pct_anual'].round(2)
    df_indicadores['zscore_dinamismo'] = df_indicadores['zscore_dinamismo'].round(2)

    # Decision Etapa 6 Item 6.1: Umbral paritario homogeneo |Z| >= 1.4 (o 1.5 redondeado) para series de tamano moderado/corto
    umbral_z = 1.4
    df_indicadores['umbral_z_aplicado'] = umbral_z
    df_indicadores['es_desvio_significativo'] = df_indicadores['zscore_dinamismo'].abs() >= umbral_z

    def clasificar_dinamismo_z(z):
        if pd.isna(z):
            return 'Sin dispersion historica suficiente o ano no consecutivo'
        elif z >= umbral_z:
            return f'Expansion atipica (|Z| >= {umbral_z})'
        elif z <= -umbral_z:
            return f'Contraccion atipica (|Z| >= {umbral_z})'
        else:
            return f'Variacion normal (|Z| < {umbral_z})'

    df_indicadores['clasificacion_dinamismo'] = df_indicadores['zscore_dinamismo'].apply(clasificar_dinamismo_z)

    archivo_ind = paths['output'] / 'indicadores_interanuales_zscore.csv'
    df_indicadores.to_csv(archivo_ind, index=False, encoding='utf-8')
    df_indicadores.to_csv(paths['data_processed'] / 'indicadores_interanuales_zscore.csv', index=False, encoding='utf-8')
    print(f"  ✅ Indicadores interanuales y Z-score guardados en: {archivo_ind.name} (Umbral |Z| >= {umbral_z} aplicado con paridad tripartita)")

    # 3. Modelos Predictivos a 3 y 5 Anos con IC 95% (t-Student n-2 gl)
    print("\n[Paso 3/6] Calculando proyecciones a 3 y 5 anos (Umbral n >= 5, t-Student, ventana estructural reciente)...")
    proyecciones = []
    for (pais, sector), group in df_egresados_sector.groupby(['pais', 'sector']):
        serie_completa = group.dropna(subset=['graduados_anuales']).sort_values('anio')
        # Acotar a la decada estructural reciente (>= 2015 para CHL, >= 2014 para ARG/URY) evitando sesgo de expansion inicial 2007-2014
        anio_corte = 2015 if pais == 'CHL' else 2014
        serie = serie_completa[serie_completa['anio'] >= anio_corte].copy()
        if len(serie) < 5:
            serie = serie_completa.copy()
        n_puntos = len(serie)

        # Decision D7 (Aprobado): Umbral estricto de minimo 5 puntos anuales continuos
        if n_puntos < 5:
            print(f"  ⚠️ [{pais}] {sector}: Serie historica de {n_puntos} anos observados < 5. Rotulada como no proyectable.")
            ultimo_anio = int(serie['anio'].max()) if not serie.empty else np.nan
            ultimo_val = serie['graduados_anuales'].iloc[-1] if not serie.empty else np.nan
            for horizonte in [3, 5]:
                proyecciones.append({
                    'pais': pais,
                    'sector': sector,
                    'ultimo_anio_observado': ultimo_anio,
                    'ultimo_valor_observado': ultimo_val,
                    'horizonte_anios': horizonte,
                    'anio_proyectado': ultimo_anio + horizonte if pd.notna(ultimo_anio) else np.nan,
                    'valor_proyectado': np.nan,
                    'limite_inferior_95': np.nan,
                    'limite_superior_95': np.nan,
                    'pendiente_anual': np.nan,
                    'r2': np.nan,
                    'n_puntos_base': n_puntos,
                    'modelo': 'No proyectable',
                    'advertencia_tendencia': f"No proyectable: serie historica insuficiente ({n_puntos} anos observados < umbral minimo de 5 anos)"
                })
            continue

        x = serie['anio'].values
        y = serie['graduados_anuales'].values

        res = stats.linregress(x, y)
        pendiente, intercepto, r_val = res.slope, res.intercept, res.rvalue

        y_pred_hist = intercepto + pendiente * x
        residuos = y - y_pred_hist
        s_err_reg = np.sqrt(np.sum(residuos**2) / (n_puntos - 2))

        # Distribucion t-Student con n - 2 grados de libertad
        t_crit = float(stats.t.ppf(0.975, df=n_puntos - 2))

        ultimo_anio = int(x.max())
        for horizonte in [3, 5]:
            anio_proy = ultimo_anio + horizonte
            y_proy = intercepto + pendiente * anio_proy

            se_proy = s_err_reg * np.sqrt(1 + (1 / n_puntos) + ((anio_proy - np.mean(x))**2 / np.sum((x - np.mean(x))**2)))
            margen = t_crit * se_proy
            lim_inf = y_proy - margen
            lim_sup = y_proy + margen

            advertencias = []
            if y_proy < 0:
                advertencias.append("Alerta: proyeccion negativa por tendencia decreciente")
            if lim_inf < 0:
                advertencias.append("Alerta: limite inferior negativo por amplitud de intervalo o tendencia decreciente")
            advertencia_txt = " | ".join(advertencias) if advertencias else "Sin advertencias"

            proyecciones.append({
                'pais': pais,
                'sector': sector,
                'ultimo_anio_observado': ultimo_anio,
                'ultimo_valor_observado': y[-1],
                'horizonte_anios': horizonte,
                'anio_proyectado': anio_proy,
                'valor_proyectado': round(y_proy, 2),
                'limite_inferior_95': round(lim_inf, 2),
                'limite_superior_95': round(lim_sup, 2),
                'pendiente_anual': round(pendiente, 2),
                'r2': round(r_val**2, 2),
                'n_puntos_base': n_puntos,
                'modelo': f'Tendencia lineal con IC 95% (t-Student {n_puntos - 2} gl)',
                'advertencia_tendencia': advertencia_txt
            })

    df_proyecciones = pd.DataFrame(proyecciones)
    archivo_proy = paths['output'] / 'proyecciones_oferta_demanda.csv'
    df_proyecciones.to_csv(archivo_proy, index=False, encoding='utf-8')
    df_proyecciones.to_csv(paths['data_processed'] / 'proyecciones_oferta_demanda.csv', index=False, encoding='utf-8')

    # Decision Etapa 6 Item 6.4 (Opcion A): Nombre explicito de oferta formativa
    archivo_proy_grad = paths['output'] / 'proyecciones_graduados_sector.csv'
    df_proyecciones.to_csv(archivo_proy_grad, index=False, encoding='utf-8')
    df_proyecciones.to_csv(paths['data_processed'] / 'proyecciones_graduados_sector.csv', index=False, encoding='utf-8')
    print(f"  ✅ Proyecciones exportadas a: {archivo_proy_grad.name} y {archivo_proy.name} ({len(df_proyecciones)} estimaciones).")

    # Semaforo presupuestario (sobre sectores proyectables)
    df_proy_validas = df_proyecciones.dropna(subset=['valor_proyectado'])
    if not df_proy_validas.empty:
        df_h5 = df_proy_validas[df_proy_validas['horizonte_anios'] == 5].copy()

        def asignar_semaforo(row):
            p = row['pendiente_anual']
            val_obs = row['ultimo_valor_observado']
            crec_relativo = (p * 5) / val_obs if val_obs > 0 else 0
            if crec_relativo < 0.05:
                return 'ALTA PRIORIDAD (Mayor Presupuesto / Cuello de Botella)'
            elif crec_relativo < 0.20:
                return 'MEDIA PRIORIDAD (Equilibrio / Monitoreo)'
            else:
                return 'BAJA PRIORIDAD (Oferta en Expansión)'

        df_h5['crecimiento_esperado_5a_pct'] = ((df_h5['pendiente_anual'] * 5) / df_h5['ultimo_valor_observado'] * 100).round(2)
        df_h5['recomendacion_presupuesto'] = df_h5.apply(asignar_semaforo, axis=1)
        df_h5['tipo_indicador'] = 'Semaforo_Prioridad_Formativa_Predictiva'
        df_h5['metodologia'] = 'Recomendacion de asignacion de recursos formativos segun proyeccion a 5 anos de graduados (t-Student)'
        df_reporte_gob = df_h5[['pais', 'sector', 'ultimo_valor_observado', 'valor_proyectado', 'pendiente_anual', 'crecimiento_esperado_5a_pct', 'recomendacion_presupuesto', 'tipo_indicador', 'metodologia']].sort_values(['pais', 'sector'])

        archivo_rep = paths['output'] / 'reporte_presupuesto_educativo.csv'
        df_reporte_gob.to_csv(archivo_rep, index=False, encoding='utf-8')
        df_reporte_gob.to_csv(paths['data_processed'] / 'reporte_presupuesto_educativo.csv', index=False, encoding='utf-8')
        print(f"  ✅ Reporte de recomendacion presupuestaria guardado en: {archivo_rep.name}")

    # Graficos de proyecciones
    for p in paises_presentes:
        df_p = df_egresados_sector[df_egresados_sector['pais'] == p]
        df_proy_p = df_proyecciones[(df_proyecciones['pais'] == p) & (df_proyecciones['valor_proyectado'].notna())] if not df_proyecciones.empty else pd.DataFrame()

        plt.figure(figsize=(10, 6))
        sectores = df_p['sector'].unique()
        colores = plt.cm.tab10(np.linspace(0, 1, len(sectores)))

        for sec, col in zip(sectores, colores):
            sub = df_p[df_p['sector'] == sec].sort_values('anio')
            plt.plot(sub['anio'], sub['graduados_anuales'], marker='o', label=sec, color=col, linewidth=2)

            if not df_proy_p.empty:
                sub_proy = df_proy_p[df_proy_p['sector'] == sec].sort_values('anio_proyectado')
                if not sub_proy.empty and len(sub) > 0:
                    x_proy = [sub['anio'].max()] + list(sub_proy['anio_proyectado'])
                    y_proy = [sub['graduados_anuales'].iloc[-1]] + list(sub_proy['valor_proyectado'])
                    plt.plot(x_proy, y_proy, linestyle='--', color=col, alpha=0.8)
                    plt.fill_between(sub_proy['anio_proyectado'],
                                     sub_proy['limite_inferior_95'],
                                     sub_proy['limite_superior_95'],
                                     color=col, alpha=0.15)

        plt.title(f"Observatorio Predictivo: Flujo de Graduados y Proyecciones a 5 Anos ({p})", fontsize=12, pad=12)
        plt.xlabel("Ano Calendario", fontsize=10)
        plt.ylabel("Graduados / Egresados Anuales", fontsize=10)
        plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
        plt.tight_layout()

        ruta_img = paths['graficos'] / f"proyeccion_graduados_{p}.png"
        plt.savefig(ruta_img, dpi=200)
        plt.close()
        print(f"  ✅ Grafico generado: {ruta_img.name}")

    # 4. Comparativa Salarial Regional Multipais (Tanda 5: OIT ILOSTAT 2024 - Decision T5.1 Opcion B y T5.2 Opcion B)
    print("\n[Paso 4/6] Analizando salarios homologados y brechas regionales (OIT 2024 tripartito)...")
    ruta_salarios = resolver_hecho('hecho_salario.csv', paths)
    if ruta_salarios:
        df_sal = pd.read_csv(ruta_salarios)
    else:
        df_sal = pd.DataFrame()

    if not df_sal.empty and 'salario_usd_ppa' in df_sal.columns:
        # Filtrar serie armonizada OIT_ILOSTAT para ventana comun estricta 2024 con sexo 'T' (Total ambos sexos)
        df_sal_ilo_2024 = df_sal[
            (df_sal['fuente_id'] == 'OIT_ILOSTAT') &
            (df_sal['sexo'] == 'T') &
            (df_sal['anio'] == 2024) &
            (df_sal['salario_usd_ppa'].notna())
        ].copy()

        if not df_sal_ilo_2024.empty:
            res_pais_sec = []
            for (pais, sector), grp in df_sal_ilo_2024.groupby(['pais', 'sector']):
                val_medio = grp['salario_usd_ppa'].mean()
                res_pais_sec.append({
                    'pais': pais, 'sector': sector,
                    'salario_min_usd_ppa': round(float(grp['salario_usd_ppa'].min()), 2),
                    'salario_mediano_usd_ppa': round(float(grp['salario_usd_ppa'].median()), 2),
                    'salario_medio_usd_ppa': round(float(val_medio), 2),
                    'salario_max_usd_ppa': round(float(grp['salario_usd_ppa'].max()), 2),
                })
            df_rangos_pais = pd.DataFrame(res_pais_sec)
        else:
            df_rangos_pais = pd.DataFrame(columns=['pais', 'sector', 'salario_min_usd_ppa', 'salario_mediano_usd_ppa', 'salario_medio_usd_ppa', 'salario_max_usd_ppa'])
    else:
        df_rangos_pais = pd.DataFrame(columns=['pais', 'sector', 'salario_min_usd_ppa', 'salario_mediano_usd_ppa', 'salario_medio_usd_ppa', 'salario_max_usd_ppa'])

    pivot_regional = df_rangos_pais.pivot(index='sector', columns='pais', values='salario_medio_usd_ppa')
    cols_p = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_regional.columns]
    pivot_regional['Promedio_Cono_Sur_USD_PPA'] = pivot_regional[cols_p].mean(axis=1).round(2)
    pivot_regional['Salario_Max_Pais'] = pivot_regional[cols_p].max(axis=1).round(2)
    pivot_regional['Salario_Min_Pais'] = pivot_regional[cols_p].min(axis=1).round(2)
    pivot_regional['Brecha_Regional_Pct'] = (((pivot_regional['Salario_Max_Pais'] - pivot_regional['Salario_Min_Pais']) / pivot_regional['Salario_Min_Pais']) * 100).round(2)
    pivot_regional['Pais_Lider_Salarial'] = pivot_regional[cols_p].idxmax(axis=1)
    pivot_regional['metodo_ppa'] = 'PPA_PIB_PA.NUS.PPP'
    pivot_regional['anio_evaluado'] = 2024
    pivot_regional['fuente_referencia'] = 'OIT_ILOSTAT_EAR_EMTA_SEX_ECO_NB'
    pivot_regional['nota_metodologica'] = 'Comparativa regional tripartita homogenea 2024 en USD PPA del PIB (PA.NUS.PPP del Banco Mundial).'

    archivo_rep_regional = paths['output'] / 'reporte_brecha_salarial_regional.csv'
    pivot_regional.reset_index().to_csv(archivo_rep_regional, index=False, encoding='utf-8')
    pivot_regional.reset_index().to_csv(paths['data_processed'] / 'reporte_brecha_salarial_regional.csv', index=False, encoding='utf-8')
    print(f"  ✅ Reporte de brecha salarial regional (OIT 2024 tripartito) guardado en: {archivo_rep_regional.name}")

    # Reporte complementario de fuentes locales de alta especificidad (CEP-XXI y SIES)
    df_sal_local = df_sal[df_sal['fuente_id'].isin(['AR_CEPXXI', 'CL_SIES']) & df_sal['salario_usd_ppa'].notna()].copy()
    if not df_sal_local.empty:
        max_anios_loc = df_sal_local.groupby(['pais', 'sector'])['anio'].max().reset_index()
        df_sal_loc_rec = pd.merge(df_sal_local, max_anios_loc, on=['pais', 'sector', 'anio'], how='inner')
        res_loc = []
        for (pais, sector), grp in df_sal_loc_rec.groupby(['pais', 'sector']):
            fuente = grp['fuente_id'].iloc[0]
            val_mean = grp['salario_usd_ppa'].mean()
            val_med = grp['salario_usd_ppa'].median()
            tipo_sal = 'salario_formal_registrado' if fuente == 'AR_CEPXXI' else 'ingreso_1er_anio'
            concepto = 'Salario medio mensual asalariados formales registrados (CEP-XXI)' if fuente == 'AR_CEPXXI' else 'Ingreso promedio bruto mensual 1er ano de egreso (SIES)'
            res_loc.append({
                'pais': pais, 'fuente_id': fuente, 'sector': sector,
                'anio_observado': int(grp['anio'].iloc[0]),
                'salario_medio_usd_ppa': round(float(val_mean), 2),
                'salario_mediano_usd_ppa': round(float(val_med), 2),
                'tipo_salario': tipo_sal,
                'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                'concepto_salario': concepto,
                'n_registros_programas': len(grp),
                'nota_uruguay': 'Uruguay no cuenta con observatorio universitario de salarios por carrera; cubierto a nivel sectorial en reporte_brecha_salarial_regional.csv'
            })
        df_rep_local = pd.DataFrame(res_loc).sort_values(['pais', 'sector'])

        # Decision Etapa 6 Item 6.5 (Opcion 1): Incorporar formalmente a Uruguay con valores de salario vacios (NaN) y advertencia explicita
        sectores_cinco = ['Economía del conocimiento', 'Energía', 'Salud', 'Tecnología', 'Turismo']
        filas_ury_sal = []
        for sec in sectores_cinco:
            filas_ury_sal.append({
                'pais': 'URY',
                'fuente_id': 'Sin dato observado',
                'sector': sec,
                'anio_observado': np.nan,
                'salario_medio_usd_ppa': np.nan,
                'salario_mediano_usd_ppa': np.nan,
                'tipo_salario': 'Sin observatorio local',
                'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                'concepto_salario': 'Sin dato observado (Uruguay no publica observatorio de salarios universitarios locales por programa)',
                'n_registros_programas': 0,
                'nota_uruguay': 'Sin dato observado a nivel de carrera; cubierto a nivel sectorial paritario 2024 en reporte_brecha_salarial_regional.csv'
            })
        df_rep_local = pd.concat([df_rep_local, pd.DataFrame(filas_ury_sal)], ignore_index=True).sort_values(['pais', 'sector'])

        archivo_rep_local = paths['output'] / 'reporte_salarios_detalle_local.csv'
        df_rep_local.to_csv(archivo_rep_local, index=False, encoding='utf-8')
        df_rep_local.to_csv(paths['data_processed'] / 'reporte_salarios_detalle_local.csv', index=False, encoding='utf-8')
        print(f"  ✅ Reporte complementario de salarios locales guardado en: {archivo_rep_local.name} (15 filas, Uruguay incorporado con celdas vacias observadas)")

    # Grafico de brecha salarial
    fig, ax = plt.subplots(figsize=(14, 6))
    ancho_barra = 0.26
    sectores_graf = list(pivot_regional.index)
    x_pos = np.arange(len(sectores_graf))
    colores_pais = {'ARG': '#74ACDF', 'CHL': '#D52B1E', 'URY': '#0038A8'}
    etiquetas_pais = {'ARG': 'Argentina (OIT / ILOSTAT 2024)', 'CHL': 'Chile (OIT / ILOSTAT 2024)', 'URY': 'Uruguay (OIT / ILOSTAT 2024)'}

    for i, p_cod in enumerate(cols_p):
        valores = pivot_regional[p_cod].values
        offset = (i - (len(cols_p) - 1) / 2) * ancho_barra
        rects = ax.bar(x_pos + offset, valores, ancho_barra, label=etiquetas_pais.get(p_cod, p_cod),
                       color=colores_pais.get(p_cod, 'gray'), alpha=0.9)
        for rect in rects:
            alt = rect.get_height()
            if not np.isnan(alt) and alt > 0:
                ax.text(rect.get_x() + rect.get_width() / 2., alt + 35,
                        f"${int(alt):,}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    ax.set_title("Comparativa Salarial Regional en el Cono Sur por Sector (USD PPA del PIB 2024 - OIT/ILOSTAT)", fontsize=12, pad=15)
    ax.set_ylabel("Ingreso Mensual en USD PPA", fontsize=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(sectores_graf, fontsize=10, rotation=10)
    max_val = float(pivot_regional[cols_p].max().max()) if cols_p and not pivot_regional[cols_p].empty else 1000.0
    ax.set_ylim(0, (max_val if pd.notna(max_val) and max_val > 0 else 1000.0) * 1.18)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    ax.legend(frameon=True, loc='upper right')
    plt.tight_layout()

    ruta_img_sal = paths['graficos'] / 'brecha_salarial_regional_multipais.png'
    plt.savefig(ruta_img_sal, dpi=200)
    plt.close()
    print(f"  ✅ Grafico salarial regional guardado en: {ruta_img_sal.name}")

    # 5. Analisis de Genero y Tasa de Feminizacion (3 Dimensiones: Graduadas en Total 2020-2024, Empleo Sectorial 2024 y Ocupadas con Educ. Superior 2024)
    print("\n[Paso 5/6] Analizando paridad de genero (Graduadas en Total 2020-2024, Empleo Sectorial y Educ. Superior OIT 2024)...")

    # Asegurar aislamiento estricto de 'T' (Total no es categoria de genero, Decision Etapa 5 Item 5.2 Opcion 1)
    assert 'T' not in ['F', 'M', 'NB'], "Inconsistencia de diseno: 'T' no debe incluirse en categorias de genero"

    df_grad_tot = obtener_graduados_totales_por_genero(paths, df_egresados)
    df_emp_sec_limpio = obtener_empleo_sectorial_por_genero(paths)
    df_edu_sec_limpio = obtener_ocupados_educ_superior_por_genero(paths)
    sectores_lista = ['Economía del conocimiento', 'Energía', 'Salud', 'Tecnología', 'Turismo']

    def diagnostico_paridad_val(pct_f):
        if pd.isna(pct_f):
            return 'Sin dato observado'
        elif pct_f < 40.0:
            return 'Sub-representacion Femenina / Masculinizacion (<40% EIGE-OIT)'
        elif pct_f > 60.0:
            return 'Segregacion Femenina / Concentracion (>60% EIGE-OIT)'
        else:
            return 'Zona de Paridad Equilibrada (40% - 60% EIGE-OIT)'

    filas_gen = []
    # A. Filas de Total Universitario por pais en el periodo comun tripartito 2020-2024 (SPU, SIES, MEC)
    for p in ['ARG', 'CHL', 'URY']:
        sub_p = df_grad_tot[df_grad_tot['pais'] == p]
        f_sum = round(float(sub_p['F'].sum()), 2) if not sub_p.empty else np.nan
        m_sum = round(float(sub_p['M'].sum()), 2) if not sub_p.empty else np.nan
        nb_sum = round(float(sub_p['NB'].dropna().sum()), 2) if (not sub_p.empty and sub_p['NB'].notna().any()) else (0.0 if p == 'CHL' else np.nan)
        tot_g = round(f_sum + m_sum + (nb_sum if pd.notna(nb_sum) else 0.0), 2) if pd.notna(f_sum) else np.nan
        pct_f_g = round((f_sum / tot_g) * 100.0, 2) if (pd.notna(tot_g) and tot_g > 0) else np.nan
        pct_m_g = round((m_sum / tot_g) * 100.0, 2) if (pd.notna(tot_g) and tot_g > 0) else np.nan
        pct_nb_g = round((nb_sum / tot_g) * 100.0, 2) if (pd.notna(nb_sum) and pd.notna(tot_g) and tot_g > 0 and nb_sum > 0) else (0.0 if p == 'CHL' else np.nan)
        brecha_g = round(pct_f_g - pct_m_g, 2) if pd.notna(pct_f_g) else np.nan

        # Empleo ponderado en los 5 sectores estrategicos (OIT 2024) para la fila resumen
        pct_emp_tot = np.nan
        brecha_emp_tot = np.nan
        anio_emp_tot = 2024
        if not df_emp_sec_limpio.empty:
            oc_p = df_emp_sec_limpio[(df_emp_sec_limpio['pais'] == p) & (df_emp_sec_limpio['anio'] == 2024)]
            if not oc_p.empty and oc_p['total'].sum() > 0:
                pct_emp_tot = round(float((oc_p['F'].sum() / oc_p['total'].sum()) * 100.0), 2)
                brecha_emp_tot = round(pct_emp_tot - (100.0 - pct_emp_tot), 2)

        filas_gen.append({
            'pais': p,
            'sector': 'Total Universitario',
            'periodo_graduados': '2020-2024 (Ventana Común Tripartita SPU/SIES/MEC)',
            'F': f_sum,
            'M': m_sum,
            'NB': nb_sum,
            'Total_Graduados': tot_g,
            'Pct_Mujeres_Graduadas': pct_f_g,
            'Pct_Varones_Graduados': pct_m_g,
            'Pct_NB_Graduados': pct_nb_g,
            'Brecha_Graduados_Pct': brecha_g,
            'anio_empleo': anio_emp_tot,
            'Pct_Mujeres_Empleadas': pct_emp_tot,
            'Brecha_Empleo_Pct': brecha_emp_tot,
            'Diagnostico_Paridad': diagnostico_paridad_val(pct_f_g),
            'Criterio_Referencia': 'EIGE_OIT_40_60'
        })

    # B. Filas por Sector Estrategico (Año Comun 2024 OIT/ILOSTAT: Ocupados con Educ. Superior vs Empleo Total del Sector)
    for p in ['ARG', 'CHL', 'URY']:
        for sec in sectores_lista:
            f_edu, m_edu, tot_edu = np.nan, np.nan, np.nan
            pct_f_edu, pct_m_edu, brecha_edu = np.nan, np.nan, np.nan
            if not df_edu_sec_limpio.empty:
                ed_ps = df_edu_sec_limpio[(df_edu_sec_limpio['pais'] == p) & (df_edu_sec_limpio['sector'] == sec) & (df_edu_sec_limpio['anio'] == 2024)]
                if not ed_ps.empty:
                    r_ed = ed_ps.iloc[0]
                    f_edu = round(float(r_ed['F']), 2)
                    m_edu = round(float(r_ed['M']), 2)
                    tot_edu = round(float(r_ed['total']), 2)
                    pct_f_edu = round(float(r_ed['pct_mujeres']), 2)
                    pct_m_edu = round(float(r_ed['pct_varones']), 2)
                    brecha_edu = round(float(r_ed['brecha_pct']), 2)

            pct_emp = np.nan
            brecha_emp = np.nan
            anio_emp = 2024
            if not df_emp_sec_limpio.empty:
                oc_ps = df_emp_sec_limpio[(df_emp_sec_limpio['pais'] == p) & (df_emp_sec_limpio['sector'] == sec) & (df_emp_sec_limpio['anio'] == 2024)]
                if not oc_ps.empty:
                    r_oc = oc_ps.iloc[0]
                    pct_emp = round(float(r_oc['pct_mujeres']), 2)
                    brecha_emp = round(float(r_oc['brecha_pct']), 2)

            filas_gen.append({
                'pais': p,
                'sector': sec,
                'periodo_graduados': '2024 (Ocupados Educ. Superior OIT en miles)',
                'F': f_edu,
                'M': m_edu,
                'NB': np.nan,
                'Total_Graduados': tot_edu,
                'Pct_Mujeres_Graduadas': pct_f_edu,
                'Pct_Varones_Graduados': pct_m_edu,
                'Pct_NB_Graduados': np.nan,
                'Brecha_Graduados_Pct': brecha_edu,
                'anio_empleo': anio_emp,
                'Pct_Mujeres_Empleadas': pct_emp,
                'Brecha_Empleo_Pct': brecha_emp,
                'Diagnostico_Paridad': diagnostico_paridad_val(pct_f_edu if pd.notna(pct_f_edu) else pct_emp),
                'Criterio_Referencia': 'EIGE_OIT_40_60'
            })

    cols_gen_rep = [
        'pais', 'sector', 'periodo_graduados', 'F', 'M', 'NB', 'Total_Graduados',
        'Pct_Mujeres_Graduadas', 'Pct_Varones_Graduados', 'Pct_NB_Graduados',
        'Brecha_Graduados_Pct',
        'anio_empleo', 'Pct_Mujeres_Empleadas', 'Brecha_Empleo_Pct',
        'Diagnostico_Paridad', 'Criterio_Referencia'
    ]
    df_gen_final = pd.DataFrame(filas_gen)[cols_gen_rep]
    for col_f in ['F', 'M', 'NB', 'Total_Graduados', 'Pct_Mujeres_Graduadas', 'Pct_Varones_Graduados', 'Pct_NB_Graduados', 'Brecha_Graduados_Pct', 'Pct_Mujeres_Empleadas', 'Brecha_Empleo_Pct']:
        df_gen_final[col_f] = pd.to_numeric(df_gen_final[col_f], errors='coerce').round(2)

    archivo_gen = paths['output'] / 'analisis_genero_integral.csv'
    df_gen_final.to_csv(archivo_gen, index=False, encoding='utf-8')
    df_gen_final.to_csv(paths['data_processed'] / 'analisis_genero_integral.csv', index=False, encoding='utf-8')
    print(f"  ✅ Analisis de genero (Total Universitario 2020-2024, Empleo Sectorial y Educ. Superior 2024) exportado a: {archivo_gen.name}")

    # Generacion del reporte detallado de brechas de genero
    generar_reporte_brechas_genero_detallado(paths, df_egresados)

    # Grafico de genero (3 paneles: 1. Graduados universitarios en TOTAL 2020-2024, 2. Empleo Total por Sector OIT 2024, 3. Ocupados con Educ. Superior por Sector OIT 2024)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(22, 6.5))

    # Panel 1: Graduados universitarios en TOTAL (% Mujeres) en el periodo comun 2020-2024 + Acumulado 2020-2024
    df_graf_tot = df_grad_tot[['pais', 'anio', 'pct_mujeres']].copy()
    df_graf_tot['periodo'] = df_graf_tot['anio'].astype(str)
    filas_acum = []
    for _, r_tot in df_gen_final[df_gen_final['sector'] == 'Total Universitario'].iterrows():
        filas_acum.append({
            'pais': r_tot['pais'],
            'anio': 9999,
            'pct_mujeres': r_tot['Pct_Mujeres_Graduadas'],
            'periodo': 'Total\n2020-2024'
        })
    df_graf_tot = pd.concat([df_graf_tot, pd.DataFrame(filas_acum)], ignore_index=True)
    orden_periodos = ['2020', '2021', '2022', '2023', '2024', 'Total\n2020-2024']
    pivot_g = df_graf_tot.pivot(index='periodo', columns='pais', values='pct_mujeres').reindex(orden_periodos)
    cols_g = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_g.columns]

    if not pivot_g.empty:
        pivot_g[cols_g].plot(kind='bar', ax=ax1, color=[colores_pais[c] for c in cols_g], width=0.68)
    ax1.axhline(50, color='black', linestyle='--', linewidth=1.2, label='Paridad Exacta (50%)')
    ax1.axhspan(40, 60, color='green', alpha=0.12, label='Franja Paridad EIGE/OIT (40%-60%)')
    ax1.set_title("1. Graduados Universitarios en Total (% Mujeres)\n[Ventana Común Tripartita 2020-2024 - SPU / SIES / MEC]", fontsize=10.5, pad=10)
    ax1.set_xlabel("Año Común Observado (Total Nacional por Sexo)", fontsize=9.5)
    ax1.set_ylabel("% Mujeres Graduadas (Total Universitario)", fontsize=10)
    ax1.set_ylim(0, 100)
    ax1.legend(loc='upper left', fontsize=8.5)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=0, ha='center')

    # Panel 2: Empleo total observado OIT 2024 por sector
    df_emp_sec = df_gen_final[df_gen_final['sector'].isin(sectores_lista)]
    pivot_emp = df_emp_sec.pivot(index='sector', columns='pais', values='Pct_Mujeres_Empleadas').reindex(sectores_lista)
    cols_emp = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_emp.columns]

    if not pivot_emp.empty:
        pivot_emp[cols_emp].plot(kind='bar', ax=ax2, color=[colores_pais[c] for c in cols_emp], width=0.65)
    ax2.axhline(50, color='black', linestyle='--', linewidth=1.2, label='Paridad Exacta (50%)')
    ax2.axhspan(40, 60, color='green', alpha=0.12, label='Franja Paridad EIGE/OIT (40%-60%)')
    ax2.set_title("2. Personas Ocupadas por Sector (% Mujeres)\n[Año Común Tripartito 2024 - OIT / ILOSTAT]", fontsize=10.5, pad=10)
    ax2.set_xlabel("Sector Estratégico (Empleo Total)", fontsize=9.5)
    ax2.set_ylabel("% Mujeres Empleadas (Total Sector)", fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left', fontsize=8.5)
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=20, ha='right')

    # Panel 3: Personas ocupadas con Educacion Superior OIT 2024 por sector
    pivot_edu = df_emp_sec.pivot(index='sector', columns='pais', values='Pct_Mujeres_Graduadas').reindex(sectores_lista)
    cols_edu = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_edu.columns]

    if not pivot_edu.empty:
        pivot_edu[cols_edu].plot(kind='bar', ax=ax3, color=[colores_pais[c] for c in cols_edu], width=0.65)
    ax3.axhline(50, color='black', linestyle='--', linewidth=1.2, label='Paridad Exacta (50%)')
    ax3.axhspan(40, 60, color='green', alpha=0.12, label='Franja Paridad EIGE/OIT (40%-60%)')
    ax3.set_title("3. Ocupados con Educación Superior por Sector (% Mujeres)\n[Año Común Tripartito 2024 - OIT / ILOSTAT]", fontsize=10.5, pad=10)
    ax3.set_xlabel("Sector Estratégico (Nivel Terciario / Universitario)", fontsize=9.5)
    ax3.set_ylabel("% Mujeres con Educación Superior", fontsize=10)
    ax3.set_ylim(0, 100)
    ax3.legend(loc='upper left', fontsize=8.5)
    ax3.set_xticklabels(ax3.get_xticklabels(), rotation=20, ha='right')

    plt.suptitle("Observatorio Predictivo: Brechas Formativas (Total Universitario), Laborales y de Profesionales por Género (EIGE / OIT 40%-60%)", fontsize=13, y=0.98)
    plt.tight_layout()

    ruta_gen_img = paths['graficos'] / "analisis_genero_empleabilidad_brecha.png"
    plt.savefig(ruta_gen_img, dpi=200)
    plt.close()
    print(f"  ✅ Grafico de genero (3 paneles) guardado en: {ruta_gen_img.name}")

    # 6. Rankings Universitarios (Tanda 4: 100% datos observados)
    print("\n[Paso 6/6] Construyendo rankings universitarios regionales y nacionales (datos 100% observados)...")
    ruta_hecho_inst = resolver_hecho('hecho_instituciones_egresados.csv', paths)
    df_top_regional = pd.DataFrame()
    df_univ_todos = pd.DataFrame()

    if ruta_hecho_inst and ruta_hecho_inst.exists():
        df_inst_raw = pd.read_csv(ruta_hecho_inst)
        if not df_inst_raw.empty:
            ult_anios = df_inst_raw.groupby('pais')['anio'].max().to_dict()

            # --- A. RANKING REGIONAL CONJUNTO (Top 10 - Ano comun 2022) ---
            # Decision Etapa 2 Item 2.3: evaluacion estricta sobre el ultimo ano comun tripartito (2022)
            anio_comun_regional = 2022
            df_inst_2022 = df_inst_raw[df_inst_raw['anio'] == anio_comun_regional]
            grp_reg_anual = df_inst_2022.groupby(['institucion', 'pais', 'tipo_gestion'], as_index=False)['graduados'].sum()
            grp_reg_anual = grp_reg_anual.sort_values('graduados', ascending=False).head(10).reset_index(drop=True)
            grp_reg_anual['ranking_regional'] = grp_reg_anual.index + 1
            grp_reg_anual['anio_evaluado'] = anio_comun_regional
            grp_reg_anual['criterio_paridad'] = 'ultimo_anio_comun_tripartito'
            grp_reg_anual['periodo_tipo'] = 'anual_comun'
            grp_reg_anual['periodo_detalle'] = f"Ano {anio_comun_regional} (Ultimo ano comun observado ARG, CHL, URY)"

            # 2. Acumulado trienal en ventana comun tripartita observada (2020-2022)
            df_inst_comun_3a = df_inst_raw[df_inst_raw['anio'].isin([2020, 2021, 2022])]
            grp_reg_acum = df_inst_comun_3a.groupby(['institucion', 'pais', 'tipo_gestion'], as_index=False)['graduados'].sum()
            grp_reg_acum = grp_reg_acum.sort_values('graduados', ascending=False).head(10).reset_index(drop=True)
            grp_reg_acum['ranking_regional'] = grp_reg_acum.index + 1
            grp_reg_acum['anio_evaluado'] = '2020-2022'
            grp_reg_acum['criterio_paridad'] = 'acumulado_ventana_comun_tripartita'
            grp_reg_acum['periodo_tipo'] = 'acumulado'
            grp_reg_acum['periodo_detalle'] = 'Acumulado ventana comun tripartita 2020-2022 (ARG, CHL, URY en los 5 sectores)'

            df_top_regional = pd.concat([grp_reg_anual, grp_reg_acum], ignore_index=True)
            archivo_reg = paths['output'] / 'ranking_universidades_regional.csv'
            df_top_regional.to_csv(archivo_reg, index=False, encoding='utf-8')
            df_top_regional.to_csv(paths['data_processed'] / 'ranking_universidades_regional.csv', index=False, encoding='utf-8')
            print(f"  ✅ Ranking regional exportado a: {archivo_reg.name} (Ano comun {anio_comun_regional} tripartito garantizado)")

            # Grafico de Ranking Regional (Top 10 en ano comun 2022)
            plt.figure(figsize=(12, 6))
            sub_g_reg = grp_reg_anual.sort_values('graduados', ascending=True)
            colores_inst = [colores_pais.get(p, '#333333') for p in sub_g_reg['pais']]
            plt.barh(sub_g_reg['institucion'], sub_g_reg['graduados'], color=colores_inst, alpha=0.88)
            for idx, val in enumerate(sub_g_reg['graduados']):
                plt.text(val + max(sub_g_reg['graduados']) * 0.01, idx, f"{int(val):,}", va='center', fontsize=9, fontweight='bold')
            plt.title(f"Top 10 Regional de Universidades con Mas Graduados - Ano Comun {anio_comun_regional} (ARG, CHL, URY)", fontsize=12, pad=12)
            plt.xlabel("Graduados Anuales Observados", fontsize=10)
            plt.xlim(0, max(sub_g_reg['graduados']) * 1.15)
            legend_elements = [
                Patch(facecolor='#74ACDF', label='Argentina (SPU 2022)'),
                Patch(facecolor='#D52B1E', label='Chile (Mi Futuro 2022)'),
                Patch(facecolor='#0038A8', label='Uruguay (UdelaR / MEC 2022)')
            ]
            plt.legend(handles=legend_elements, loc='lower right', frameon=True)
            plt.tight_layout()
            ruta_reg_img = paths['graficos'] / 'ranking_universidades_regional_2022.png'
            plt.savefig(ruta_reg_img, dpi=200)
            plt.close()
            print(f"  ✅ Grafico de ranking regional guardado en: {ruta_reg_img.name}")

            # --- B. RANKING NACIONAL POR PAIS (Ano mas actual por pais: ARG 2022, CHL 2025, URY 2024) ---
            recs_nac = []
            for p in ['ARG', 'CHL', 'URY']:
                df_p = df_inst_raw[df_inst_raw['pais'] == p]
                if df_p.empty:
                    continue

                anio_reciente_p = int(df_p['anio'].max())
                df_sub_reciente = df_p[df_p['anio'] == anio_reciente_p]

                for p_tipo, df_sub_p, p_det, a_eval in [
                    ('anual_reciente', df_sub_reciente, f"Ano {anio_reciente_p} (Mas reciente observado {p})", anio_reciente_p),
                    ('acumulado', df_p, f"Ventana historica completa ({df_p['anio'].min()}-{df_p['anio'].max()})", f"{df_p['anio'].min()}-{df_p['anio'].max()}")
                ]:
                    grp_p = df_sub_p.groupby(['institucion', 'tipo_gestion'], as_index=False)['graduados'].sum()
                    n_inst = len(grp_p)
                    # Decision Etapa 4 Item 4.3: Excluir pais con 10 o menos universidades / Uruguay del ranking de menos graduados
                    es_pequeno = (n_inst <= 10) or (p == 'URY')

                    # 1. Mas graduados (descendente)
                    grp_desc = grp_p.sort_values('graduados', ascending=False).copy()
                    if not es_pequeno:
                        grp_desc = grp_desc.head(10)
                    grp_desc = grp_desc.reset_index(drop=True)
                    grp_desc['ranking_nacional'] = grp_desc.index + 1
                    grp_desc['tipo_ranking'] = 'mas_graduados'
                    grp_desc['pais'] = p
                    grp_desc['anio_evaluado'] = a_eval
                    grp_desc['periodo_tipo'] = p_tipo
                    grp_desc['periodo_detalle'] = p_det
                    grp_desc['total_instituciones_pais'] = n_inst
                    grp_desc['cobertura'] = 'totalidad_instituciones_existentes' if es_pequeno else 'top_10'
                    recs_nac.append(grp_desc)

                    # 2. Menos graduados (ascendente) - Excluir pais con 10 o menos instituciones (ej. Uruguay) segun condicion de diseno (Item 4.3)
                    if not es_pequeno and p != 'URY':
                        grp_asc = grp_p.sort_values('graduados', ascending=True).head(10).reset_index(drop=True)
                        grp_asc['ranking_nacional'] = grp_asc.index + 1
                        grp_asc['tipo_ranking'] = 'menos_graduados'
                        grp_asc['pais'] = p
                        grp_asc['anio_evaluado'] = a_eval
                        grp_asc['periodo_tipo'] = p_tipo
                        grp_asc['periodo_detalle'] = p_det
                        grp_asc['total_instituciones_pais'] = n_inst
                        grp_asc['cobertura'] = 'bottom_10'
                        recs_nac.append(grp_asc)

            df_univ_todos = pd.concat(recs_nac, ignore_index=True)
            archivo_nac = paths['output'] / 'ranking_universidades_nacional.csv'
            df_univ_todos.to_csv(archivo_nac, index=False, encoding='utf-8')
            df_univ_todos.to_csv(paths['data_processed'] / 'ranking_universidades_nacional.csv', index=False, encoding='utf-8')
            print(f"  ✅ Ranking nacional exportado a: {archivo_nac.name} ({len(df_univ_todos)} registros, anos mas recientes por pais asentados)")
    else:
        print("  ⚠️ hecho_instituciones_egresados.csv no encontrado.")

    # 7. Grafico de contexto: Desempleo con educacion terciaria vs general (Banco Mundial)
    ruta_contexto = paths['output'] / 'reporte_contexto_educativo_laboral.csv'
    if ruta_contexto.exists():
        try:
            df_ctx = pd.read_csv(ruta_contexto)
            df_ctx_rec = df_ctx[df_ctx['anio'] == 2024]
            if not df_ctx_rec.empty and df_ctx_rec['tasa_desempleo_educ_terciaria_pct'].notna().any():
                plt.figure(figsize=(10, 5))
                paises_orden = [p for p in ['ARG', 'CHL', 'URY'] if p in df_ctx_rec['pais'].values]
                sub_c = df_ctx_rec.set_index('pais').loc[paises_orden].reset_index()

                x = np.arange(len(paises_orden))
                width = 0.35

                plt.bar(x - width/2, sub_c['tasa_desempleo_general_pct'], width, label='Desempleo General (% PEA)', color='#5C6F84', alpha=0.9)
                plt.bar(x + width/2, sub_c['tasa_desempleo_educ_terciaria_pct'], width, label='Desempleo c/ Educación Superior (%)', color='#2E7D32', alpha=0.9)

                for i, row in sub_c.iterrows():
                    val_tot = row['tasa_desempleo_general_pct']
                    val_adv = row['tasa_desempleo_educ_terciaria_pct']
                    if pd.notna(val_tot):
                        plt.text(i - width/2, val_tot + 0.15, f"{val_tot:.1f}%", ha='center', fontsize=9, fontweight='bold')
                    if pd.notna(val_adv):
                        plt.text(i + width/2, val_adv + 0.15, f"{val_adv:.1f}%", ha='center', fontsize=9, fontweight='bold')

                plt.title("Efecto Protector de la Educación Superior: Desempleo Total vs. Graduados Superiores (2024)", fontsize=12, pad=12)
                plt.ylabel("Tasa de Desempleo (%)", fontsize=10)
                plt.xticks(x, ['Argentina (ARG)', 'Chile (CHL)', 'Uruguay (URY)'], fontsize=10)
                max_y = max(sub_c['tasa_desempleo_general_pct'].max(), sub_c['tasa_desempleo_educ_terciaria_pct'].max())
                plt.ylim(0, max_y * 1.25)
                plt.legend(frameon=True, loc='upper right')
                plt.tight_layout()
                ruta_ctx_img = paths['graficos'] / 'desempleo_educacion_superior_regional.png'
                plt.savefig(ruta_ctx_img, dpi=200)
                plt.close()
                print(f"  ✅ Grafico de desempleo y educacion superior guardado en: {ruta_ctx_img.name}")
        except Exception as e_ctx:
            print(f"  ⚠️ Error generando grafico de desempleo terciario: {e_ctx}")

    # 8. Reporte de Densidad Profesional (Oferta vs Puestos de Trabajo - Decision Etapa 6 Item 6.4 Opcion A)
    print("\n[Paso 7/7] Generando reporte de densidad profesional y cruce formacion-empleo...")
    generar_reporte_densidad_profesional(paths, df_egresados_sector)

    # 9. Verificacion estructural de la matriz paritaria 3 paises x 5 sectores (Item 6.5)
    verificar_matriz_reportes_3x5(paths)

    print("\n✅ ETAPA 03 (INDICADORES Y PROYECCIONES) COMPLETADA CON EXITO.\n")
    return {
        'df_indicadores': df_indicadores,
        'df_proyecciones': df_proyecciones,
        'df_top_regional': df_top_regional,
        'df_univ_todos': df_univ_todos
    }


if __name__ == '__main__':
    ejecutar_indicadores()
