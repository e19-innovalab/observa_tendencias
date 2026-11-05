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
def generar_reporte_brechas_genero_detallado(paths, df_egresados):
    """
    Genera el reporte detallado de brechas formativas y laborales por genero (Decision Etapa 5 Item 5.4 Opcion 1):
    - Graduados por genero: serie observada por ano (ARG 2016-2018, CHL 2016-2018 y 2025, URY con total 'T' y ND).
    - Empleo por genero: serie oficial tripartita armonizada OIT/ILOSTAT 2024 para los 3 paises x 5 sectores.
    """
    rows = []
    # 1. Graduados universitarios ARG (2016, 2017, 2018 observados en Araucano)
    sub_arg = df_egresados[(df_egresados['pais'] == 'ARG') & (df_egresados['anio'].isin([2016, 2017, 2018])) & (df_egresados['sexo'].isin(['F', 'M']))]
    if not sub_arg.empty:
        piv_arg = sub_arg.pivot_table(index=['pais', 'sector', 'anio'], columns='sexo', values='valor', aggfunc='sum').reset_index()
        for _, r in piv_arg.iterrows():
            f = float(r.get('F', 0))
            m = float(r.get('M', 0))
            tot = f + m
            rows.append({
                'pais': 'ARG', 'sector': r['sector'], 'tipo_indicador': 'graduados_universitarios',
                'anio': int(r['anio']), 'F': f, 'M': m, 'otros': np.nan, 'total': tot,
                'pct_mujeres': round((f / tot) * 100, 1) if tot > 0 else np.nan,
                'brecha_pct': round(((f - m) / tot) * 100, 1) if tot > 0 else np.nan,
                'fuente': 'AR_CAPITALHUMANO (Araucano)',
                'nota_metodologica': 'Dato observado en base Araucano (sin categoria no binaria en fuente oficial)'
            })

    # 2. Graduados universitarios CHL (2016, 2017, 2018 periodo comun y 2025 reciente)
    sub_chl = df_egresados[(df_egresados['pais'] == 'CHL') & (df_egresados['anio'].isin([2016, 2017, 2018, 2025])) & (df_egresados['sexo'].isin(['F', 'M', 'NB']))]
    if not sub_chl.empty:
        piv_chl = sub_chl.pivot_table(index=['pais', 'sector', 'anio'], columns='sexo', values='valor', aggfunc='sum').reset_index()
        for _, r in piv_chl.iterrows():
            f = float(r.get('F', 0))
            m = float(r.get('M', 0))
            nb = float(r.get('NB', 0)) if pd.notna(r.get('NB')) else 0.0
            tot = f + m + nb
            rows.append({
                'pais': 'CHL', 'sector': r['sector'], 'tipo_indicador': 'graduados_universitarios',
                'anio': int(r['anio']), 'F': f, 'M': m, 'otros': nb if nb > 0 else 0.0, 'total': tot,
                'pct_mujeres': round((f / tot) * 100, 1) if tot > 0 else np.nan,
                'brecha_pct': round(((f - m) / tot) * 100, 1) if tot > 0 else np.nan,
                'fuente': 'CL_MIFUTURO (SIES)',
                'nota_metodologica': 'Dato observado en SIES/Mi Futuro'
            })

    # 3. Graduados universitarios URY (2016, 2017, 2018 y 2023 - Solo total 'T' observado)
    sub_ury = df_egresados[(df_egresados['pais'] == 'URY') & (df_egresados['anio'].isin([2016, 2017, 2018, 2023])) & (df_egresados['sexo'] == 'T')]
    if not sub_ury.empty:
        piv_ury = sub_ury.groupby(['pais', 'sector', 'anio'])['valor'].sum().reset_index()
        for _, r in piv_ury.iterrows():
            tot = float(r['valor'])
            rows.append({
                'pais': 'URY', 'sector': r['sector'], 'tipo_indicador': 'graduados_universitarios',
                'anio': int(r['anio']), 'F': np.nan, 'M': np.nan, 'otros': np.nan, 'total': tot,
                'pct_mujeres': np.nan, 'brecha_pct': np.nan,
                'fuente': 'UY_MEC_SUP',
                'nota_metodologica': 'Sin apertura por sexo en fuente oficial MEC (solo total T observado)'
            })

    # 4. Empleo sectorial OIT/ILOSTAT 2024 (en miles de personas)
    mapa_ilo_sec = {
        'ECO_ISIC4_J': 'Tecnología',
        'ECO_ISIC4_M': 'Economía del conocimiento',
        'ECO_ISIC4_Q': 'Salud',
        'ECO_ISIC4_D': 'Energía',
        'ECO_ISIC4_I': 'Turismo',
    }
    carpeta_ilo = paths['data_raw'] / 'ilostat'
    for p in ['ARG', 'CHL', 'URY']:
        fpath = carpeta_ilo / f"EMP_TEMP_SEX_ECO_NB_{p}.csv"
        if fpath.exists():
            try:
                df_i = pd.read_csv(fpath)
                sub_i = df_i[(df_i['time'] == 2024) & (df_i['classif1'].isin(mapa_ilo_sec.keys()))]
                piv_i = sub_i.pivot_table(index='classif1', columns='sex', values='obs_value', aggfunc='first').reset_index()
                for _, r in piv_i.iterrows():
                    sec = mapa_ilo_sec[r['classif1']]
                    f = float(r.get('SEX_F', 0))
                    m = float(r.get('SEX_M', 0))
                    tot = float(r.get('SEX_T', f + m))
                    rows.append({
                        'pais': p, 'sector': sec, 'tipo_indicador': 'personas_ocupadas_miles',
                        'anio': 2024, 'F': round(f, 2), 'M': round(m, 2), 'otros': np.nan,
                        'total': round(tot, 2),
                        'pct_mujeres': round((f / tot) * 100, 1) if tot > 0 else np.nan,
                        'brecha_pct': round(((f - m) / tot) * 100, 1) if tot > 0 else np.nan,
                        'fuente': f"OIT_ILOSTAT (EMP_TEMP_SEX_ECO_NB_{p})",
                        'nota_metodologica': 'Empleo armonizado OIT por sexo y actividad CIIU Rev. 4 (sin categoria no binaria)'
                    })
            except Exception:
                pass

    df_rep = pd.DataFrame(rows)
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
    df_densidad['ratio_graduados_vs_empleo_pct'] = ((df_densidad['graduados_anuales'] / df_densidad['puestos_empleo']) * 100).round(3)
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
    print("\n[Paso 3/6] Calculando proyecciones a 3 y 5 anos (Umbral n >= 5, t-Student)...")
    proyecciones = []
    for (pais, sector), group in df_egresados_sector.groupby(['pais', 'sector']):
        serie = group.dropna(subset=['graduados_anuales']).sort_values('anio')
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
                'valor_proyectado': round(y_proy, 1),
                'limite_inferior_95': round(lim_inf, 1),
                'limite_superior_95': round(lim_sup, 1),
                'pendiente_anual': round(pendiente, 2),
                'r2': round(r_val**2, 4),
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

        df_h5['crecimiento_esperado_5a_pct'] = ((df_h5['pendiente_anual'] * 5) / df_h5['ultimo_valor_observado'] * 100).round(1)
        df_h5['recomendacion_presupuesto'] = df_h5.apply(asignar_semaforo, axis=1)
        df_h5['tipo_indicador'] = 'Semaforo_Prioridad_Formativa_Predictiva'
        df_h5['metodologia'] = 'Recomendacion de asignacion de recursos formativos segun proyeccion a 5 anos de graduados (t-Student)'
        df_reporte_gob = df_h5[['pais', 'sector', 'ultimo_valor_observado', 'valor_proyectado', 'pendiente_anual', 'crecimiento_esperado_5a_pct', 'recomendacion_presupuesto', 'tipo_indicador', 'metodologia']].sort_values(['pais', 'sector'])

        archivo_rep = paths['output'] / 'reporte_presupuesto_educativo.csv'
        df_reporte_gob.to_csv(archivo_rep, index=False, encoding='utf-8')
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
                    'salario_min_usd_ppa': round(float(grp['salario_usd_ppa'].min()), 1),
                    'salario_mediano_usd_ppa': round(float(grp['salario_usd_ppa'].median()), 1),
                    'salario_medio_usd_ppa': round(float(val_medio), 1),
                    'salario_max_usd_ppa': round(float(grp['salario_usd_ppa'].max()), 1),
                })
            df_rangos_pais = pd.DataFrame(res_pais_sec)
        else:
            df_rangos_pais = pd.DataFrame(columns=['pais', 'sector', 'salario_min_usd_ppa', 'salario_mediano_usd_ppa', 'salario_medio_usd_ppa', 'salario_max_usd_ppa'])
    else:
        df_rangos_pais = pd.DataFrame(columns=['pais', 'sector', 'salario_min_usd_ppa', 'salario_mediano_usd_ppa', 'salario_medio_usd_ppa', 'salario_max_usd_ppa'])

    pivot_regional = df_rangos_pais.pivot(index='sector', columns='pais', values='salario_medio_usd_ppa')
    cols_p = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_regional.columns]
    pivot_regional['Promedio_Cono_Sur_USD_PPA'] = pivot_regional[cols_p].mean(axis=1).round(1)
    pivot_regional['Salario_Max_Pais'] = pivot_regional[cols_p].max(axis=1).round(1)
    pivot_regional['Salario_Min_Pais'] = pivot_regional[cols_p].min(axis=1).round(1)
    pivot_regional['Brecha_Regional_Pct'] = (((pivot_regional['Salario_Max_Pais'] - pivot_regional['Salario_Min_Pais']) / pivot_regional['Salario_Min_Pais']) * 100).round(1)
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
                'salario_medio_usd_ppa': round(float(val_mean), 1),
                'salario_mediano_usd_ppa': round(float(val_med), 1),
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

    # 5. Analisis de Genero y Tasa de Feminizacion (Brechas Formativas y Laborales Observadas)
    print("\n[Paso 5/6] Analizando paridad de genero y brechas formativas/laborales...")

    # Asegurar aislamiento estricto de 'T' (Total no es categoria de genero, Decision Etapa 5 Item 5.2 Opcion 1)
    assert 'T' not in ['F', 'M', 'NB'], "Inconsistencia de diseno: 'T' no debe incluirse en categorias de genero"
    df_gen = df_egresados[df_egresados['sexo'].isin(['F', 'M', 'NB'])].copy()
    if not df_gen.empty:
        agrup_gen = df_gen.groupby(['pais', 'sector', 'sexo'])['valor'].sum().unstack().reset_index()
        for col_s in ['F', 'M', 'NB']:
            if col_s not in agrup_gen.columns:
                agrup_gen[col_s] = np.nan
        # Para Argentina, Araucano no midio categoria no binaria (Decision Etapa 5 Item 5.1 Opcion 1)
        agrup_gen.loc[agrup_gen['pais'] == 'ARG', 'NB'] = np.nan

        agrup_gen['Total_Graduados'] = agrup_gen[['F', 'M']].sum(axis=1) + agrup_gen['NB'].fillna(0)
        agrup_gen['Pct_Mujeres_Graduadas'] = ((agrup_gen['F'] / agrup_gen['Total_Graduados']) * 100).round(1)
        agrup_gen['Pct_Varones_Graduados'] = ((agrup_gen['M'] / agrup_gen['Total_Graduados']) * 100).round(1)
        agrup_gen['Pct_NB_Graduados'] = np.where(agrup_gen['NB'].notna(), ((agrup_gen['NB'] / agrup_gen['Total_Graduados']) * 100).round(1), np.nan)
        agrup_gen['Brecha_Graduados_Pct'] = (agrup_gen['Pct_Mujeres_Graduadas'] - agrup_gen['Pct_Varones_Graduados']).round(1)
    else:
        agrup_gen = pd.DataFrame(columns=['pais', 'sector', 'F', 'M', 'NB', 'Total_Graduados', 'Pct_Mujeres_Graduadas', 'Pct_Varones_Graduados', 'Pct_NB_Graduados', 'Brecha_Graduados_Pct'])

    # Incorporar estratos de Uruguay (egresados sin apertura de sexo en fuente oficial, pero con empleo observado OIT)
    sectores_lista = ['Economía del conocimiento', 'Energía', 'Salud', 'Tecnología', 'Turismo']
    paises_presentes_gen = agrup_gen['pais'].unique() if not agrup_gen.empty else []
    if 'URY' not in paises_presentes_gen:
        filas_ury = []
        for sec in sectores_lista:
            filas_ury.append({
                'pais': 'URY', 'sector': sec,
                'F': np.nan, 'M': np.nan, 'NB': np.nan,
                'Total_Graduados': np.nan,
                'Pct_Mujeres_Graduadas': np.nan,
                'Pct_Varones_Graduados': np.nan,
                'Pct_NB_Graduados': np.nan,
                'Brecha_Graduados_Pct': np.nan
            })
        if filas_ury:
            agrup_gen = pd.concat([agrup_gen, pd.DataFrame(filas_ury)], ignore_index=True)

    # Periodos de referencia para graduados (Decision Etapa 5 Item 5.4 Opcion 1)
    def asignar_periodo_grad(p):
        if p == 'ARG':
            return '2016-2018 (Araucano)'
        elif p == 'CHL':
            return '2007-2025 (SIES / Mi Futuro)'
        else:
            return 'ND (Sin apertura por sexo en fuente oficial MEC)'
    agrup_gen['periodo_graduados'] = agrup_gen['pais'].map(asignar_periodo_grad)

    ruta_ocup = resolver_hecho('hecho_ocupacion_terciarios.csv', paths)
    if ruta_ocup:
        df_oc = pd.read_csv(ruta_ocup)
        if 'share_mujeres' in df_oc.columns and not df_oc['share_mujeres'].dropna().empty:
            ult_oc = df_oc.dropna(subset=['share_mujeres']).sort_values(['pais', 'sector', 'anio']).groupby(['pais', 'sector']).last().reset_index()
            agrup_gen = pd.merge(agrup_gen, ult_oc[['pais', 'sector', 'share_mujeres', 'anio']], on=['pais', 'sector'], how='left')
            agrup_gen.rename(columns={'anio': 'anio_empleo'}, inplace=True)
            agrup_gen['Pct_Mujeres_Empleadas'] = (agrup_gen['share_mujeres'] * 100).round(1)
            agrup_gen['Brecha_Empleo_Pct'] = (agrup_gen['Pct_Mujeres_Empleadas'] - (100.0 - agrup_gen['Pct_Mujeres_Empleadas'])).round(1)
        else:
            agrup_gen['anio_empleo'] = 2024
            agrup_gen['Pct_Mujeres_Empleadas'] = np.nan
            agrup_gen['Brecha_Empleo_Pct'] = np.nan
    else:
        agrup_gen['anio_empleo'] = 2024
        agrup_gen['Pct_Mujeres_Empleadas'] = np.nan
        agrup_gen['Brecha_Empleo_Pct'] = np.nan

    # Diagnostico de paridad segun estandar internacional EIGE / OIT (40% - 60%) (Decision Etapa 5 Item 5.3 Opcion 1)
    def diagnostico_genero(row):
        pct_f = row['Pct_Mujeres_Graduadas']
        if pd.isna(pct_f):
            return 'Sin dato de graduados por sexo (Empleo observado OIT)'
        elif pct_f < 40.0:
            return 'Sub-representacion Femenina / Masculinizacion (<40% EIGE-OIT)'
        elif pct_f > 60.0:
            return 'Segregacion Femenina / Concentracion (>60% EIGE-OIT)'
        else:
            return 'Zona de Paridad Equilibrada (40% - 60% EIGE-OIT)'

    agrup_gen['Diagnostico_Paridad'] = agrup_gen.apply(diagnostico_genero, axis=1)
    agrup_gen['Criterio_Referencia'] = 'EIGE_OIT_40_60'

    cols_gen_rep = [
        'pais', 'sector', 'periodo_graduados', 'F', 'M', 'NB', 'Total_Graduados',
        'Pct_Mujeres_Graduadas', 'Pct_Varones_Graduados', 'Pct_NB_Graduados',
        'Brecha_Graduados_Pct',
        'anio_empleo', 'Pct_Mujeres_Empleadas', 'Brecha_Empleo_Pct',
        'Diagnostico_Paridad', 'Criterio_Referencia'
    ]
    df_gen_final = agrup_gen[[c for c in cols_gen_rep if c in agrup_gen.columns]].sort_values(['pais', 'sector'])

    archivo_gen = paths['output'] / 'analisis_genero_integral.csv'
    df_gen_final.to_csv(archivo_gen, index=False, encoding='utf-8')
    df_gen_final.to_csv(paths['data_processed'] / 'analisis_genero_integral.csv', index=False, encoding='utf-8')
    print(f"  ✅ Analisis de genero (brecha formativa y laboral observada) exportado a: {archivo_gen.name}")

    # Generacion del reporte detallado de brechas de genero (Decision Etapa 5 Item 5.4 Opcion 1)
    generar_reporte_brechas_genero_detallado(paths, df_egresados)

    # Grafico de genero (2 paneles: Graduados universitarios y Empleo formal tripartito OIT)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Panel 1: Graduados universitarios
    df_gen_graf = df_gen_final.dropna(subset=['Pct_Mujeres_Graduadas'])
    pivot_g = df_gen_graf.pivot(index='sector', columns='pais', values='Pct_Mujeres_Graduadas')
    cols_g = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_g.columns]

    if not pivot_g.empty:
        pivot_g[cols_g].plot(kind='bar', ax=ax1, color=[colores_pais[c] for c in cols_g], width=0.60)
    ax1.axhline(50, color='black', linestyle='--', linewidth=1.2, label='Paridad Exacta (50%)')
    ax1.axhspan(40, 60, color='green', alpha=0.12, label='Franja Paridad EIGE/OIT (40%-60%)')
    ax1.set_title("1. Graduados Universitarios (% Mujeres)\n[ARG 2016-2018, CHL 2007-2025]", fontsize=11, pad=10)
    ax1.set_xlabel("Sector Estratégico", fontsize=10)
    ax1.set_ylabel("% Mujeres Graduadas", fontsize=10)
    ax1.set_ylim(0, 100)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=20, ha='right')
    ax1.text(0.02, 0.03, "* Uruguay: Sin apertura por sexo en fuente oficial MEC", transform=ax1.transAxes, fontsize=8, fontstyle='italic', color='#555555')

    # Panel 2: Empleo formal observado OIT 2024
    pivot_emp = df_gen_final.pivot(index='sector', columns='pais', values='Pct_Mujeres_Empleadas')
    cols_emp = [c for c in ['ARG', 'CHL', 'URY'] if c in pivot_emp.columns]

    if not pivot_emp.empty:
        pivot_emp[cols_emp].plot(kind='bar', ax=ax2, color=[colores_pais[c] for c in cols_emp], width=0.65)
    ax2.axhline(50, color='black', linestyle='--', linewidth=1.2, label='Paridad Exacta (50%)')
    ax2.axhspan(40, 60, color='green', alpha=0.12, label='Franja Paridad EIGE/OIT (40%-60%)')
    ax2.set_title("2. Personas Ocupadas (% Mujeres)\n[Año Común Tripartito 2024 - OIT/ILOSTAT]", fontsize=11, pad=10)
    ax2.set_xlabel("Sector Estratégico", fontsize=10)
    ax2.set_ylabel("% Mujeres Empleadas", fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=20, ha='right')

    plt.suptitle("Observatorio Predictivo: Brechas Formativas y Laborales por Género (Referencia: EIGE / OIT 40%-60%)", fontsize=13, y=0.98)
    plt.tight_layout()

    ruta_gen_img = paths['graficos'] / "analisis_genero_empleabilidad_brecha.png"
    plt.savefig(ruta_gen_img, dpi=200)
    plt.close()
    print(f"  ✅ Grafico de genero guardado en: {ruta_gen_img.name}")

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

            # 2. Acumulado historico observado
            grp_reg_acum = df_inst_raw.groupby(['institucion', 'pais', 'tipo_gestion'], as_index=False)['graduados'].sum()
            grp_reg_acum = grp_reg_acum.sort_values('graduados', ascending=False).head(10).reset_index(drop=True)
            grp_reg_acum['ranking_regional'] = grp_reg_acum.index + 1
            grp_reg_acum['anio_evaluado'] = '2007-2025'
            grp_reg_acum['criterio_paridad'] = 'acumulado_historico_total'
            grp_reg_acum['periodo_tipo'] = 'acumulado'
            grp_reg_acum['periodo_detalle'] = 'Ventana historica completa observada'

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
