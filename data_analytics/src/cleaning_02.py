"""
Modulo 02: Limpieza, Normalizacion y Exportacion de Tablas
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
import re
import unicodedata

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
        except Exception as e:
            print(f"⚠️ [Auto-ZIP] No se pudo descomprimir '{zip_path.name}': {e}")


def resolver_ruta_archivo(ruta_relativa, data_raw, data_processed, patrones=None):
    nombre = Path(ruta_relativa).name
    candidatos = [
        data_raw / ruta_relativa,
        data_raw / nombre,
        data_raw / 'argentina' / nombre,
        data_raw / 'chile' / nombre,
        data_raw / 'uruguay' / nombre,
        data_raw / 'linkedin_jobs' / nombre,
        data_processed / nombre,
    ]
    for c in candidatos:
        if c.exists():
            return c

    # Busqueda por patrones alternativos
    pats = list(patrones or [])
    pats.extend([f"**/{nombre}", f"*{nombre}*"])
    for d in [data_raw, data_processed]:
        if d.exists():
            for patron in pats:
                try:
                    matches = list(d.glob(patron))
                    if matches:
                        return matches[0]
                except Exception:
                    pass
    return None


# ==============================================================================
# Diccionarios Maestros y Clasificadores CINE/CIIU
# ==============================================================================

SECTORES_CIIU = {
    'Tecnología':                ['61', '62', '63'],
    'Economía del conocimiento': ['70', '71', '72', '73', '74'],
    'Salud':                     ['86', '87'],
    'Energía':                   ['05', '06', '07', '08', '09', '19', '35'],
    'Turismo':                   ['55', '56', '79'],
}

CLAE2_A_SECTOR = {}
for sec, claes in SECTORES_CIIU.items():
    for c in claes:
        CLAE2_A_SECTOR[c] = sec

DISCIPLINA_ID_A_SECTOR = {
    '10': ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613'),
    '19': ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613'),
    '22': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
    '1':  ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
    '13': ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211'),
    '35': ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542'),
    '5':  ('SAL01', 'Medicina', 'Salud', '0912'),
    '17': ('SAL05', 'Nutrición / bioquímica', 'Salud', '0915'),
    '18': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
    '25': ('SAL02', 'Enfermería / salud pública', 'Salud', '0913'),
    '29': ('SAL03', 'Odontología', 'Salud', '0911'),
    '31': ('SAL02', 'Enfermería / sanidad', 'Salud', '0913'),
    '2':  ('ENE01', 'Ingeniería eléctrica / mecánica', 'Energía', '0713'),
    '21': ('ENE03', 'Ingeniería mecánica / industrial', 'Energía', '0715'),
    '23': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
    '30': ('ENE01', 'Ingeniería eléctrica / física', 'Energía', '0713'),
    '32': ('ENE02', 'Ingeniería química', 'Energía', '0711'),
}

DISCIPLINA_TEXT_A_SECTOR = {
    'informatica': ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613'),
    'computacion': ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613'),
    'ciencias de la informacion': ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613'),
    'ciencias de la informacion y de la comunicacion': ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613'),
    'programacion': ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613'),
    'sistemas': ('TEC02', 'Licenciatura en sistemas / ciencias de la computación', 'Tecnología', '0613'),
    'telecomunicaciones': ('TEC03', 'Ingeniería en telecomunicaciones', 'Tecnología', '0714'),
    'electronica': ('TEC04', 'Ingeniería electrónica', 'Tecnología', '0714'),
    'demografia y geografia': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
    'turismo': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
    'geografia': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
    'hoteleria': ('TUR02', 'Hotelería / administración hotelera', 'Turismo', '1013'),
    'gastronomia': ('TUR03', 'Gastronomía', 'Turismo', '1013'),
    'economia y administracion': ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
    'administracion': ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
    'arquitectura y diseno': ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211'),
    'diseno': ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211'),
    'estadistica': ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542'),
    'marketing': ('EDC04', 'Marketing / publicidad', 'Economía del conocimiento', '0414'),
    'medicina': ('SAL01', 'Medicina', 'Salud', '0912'),
    'paramedicas y auxiliares de la medicina': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
    'paramedicas': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
    'enfermeria': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
    'odontologia': ('SAL03', 'Odontología', 'Salud', '0911'),
    'bioquimica y farmacia': ('SAL05', 'Nutrición / bioquímica', 'Salud', '0915'),
    'salud publica': ('SAL02', 'Enfermería / salud pública', 'Salud', '0913'),
    'sanidad': ('SAL02', 'Enfermería / sanidad', 'Salud', '0913'),
    'nutricion': ('SAL05', 'Nutrición / bioquímica', 'Salud', '0915'),
    'kinesiologia': ('SAL04', 'Kinesiología / fisioterapia', 'Salud', '0915'),
    'ingenieria': ('ENE01', 'Ingeniería eléctrica / mecánica', 'Energía', '0713'),
    'industrias': ('ENE03', 'Ingeniería mecánica / industrial', 'Energía', '0715'),
    'ciencias del suelo': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
    'ingenieria electrica': ('ENE01', 'Ingeniería eléctrica', 'Energía', '0713'),
    'ingenieria quimica': ('ENE02', 'Ingeniería química', 'Energía', '0711'),
    'ingenieria mecanica': ('ENE03', 'Ingeniería mecánica', 'Energía', '0715'),
    'geologia': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
    'mineria': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
    'petroleo': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
}

CARRERAS_OBJETIVO = [
    ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613', 'grado',
     [r'ingenier.*(informatic|computacion|sistemas)', r'ciencias de la computacion', r'civil en informatica', r'civil en computacion']),
    ('TEC02', 'Licenciatura en sistemas / ciencias de la computación', 'Tecnología', '0613', 'grado',
     [r'licenciatur.*(sistemas|computacion|informatica)']),
    ('TEC03', 'Ingeniería en telecomunicaciones', 'Tecnología', '0714', 'grado',
     [r'ingenier.*telecomunicacion', r'civil en telecomunicacion']),
    ('TEC04', 'Ingeniería electrónica', 'Tecnología', '0714', 'grado',
     [r'ingenier.*electronic', r'civil electronic']),
    ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613', 'tecnico',
     [r'tecnic.*(programacion|software|analista|computacion|informatica|desarrollo)', r'analista programador', r'analista de sistemas']),
    ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542', 'grado',
     [r'estadistic', r'datos', r'data science']),
    ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211', 'ambos',
     [r'diseno.*(grafico|multimedia|digital|visual|ux|ui)', r'multimedia', r'animacion digital']),
    ('EDC03', 'Ingeniería industrial', 'Economía del conocimiento', '0715', 'grado',
     [r'ingenier.*industrial', r'civil industrial']),
    ('EDC04', 'Marketing / publicidad', 'Economía del conocimiento', '0414', 'ambos',
     [r'marketing', r'comercializacion', r'publicidad', r'mercadotecnia']),
    ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413', 'grado',
     [r'administracion', r'ingenier.*comercial', r'negocios', r'comercial']),
    ('SAL01', 'Medicina', 'Salud', '0912', 'grado',
     [r'medicina(?!.*(veterinar|legal))', r'medico cirujano']),
    ('SAL02', 'Enfermería', 'Salud', '0913', 'ambos',
     [r'enfermer']),
    ('SAL03', 'Odontología', 'Salud', '0911', 'grado',
     [r'odontolog', r'cirujano dentista']),
    ('SAL04', 'Kinesiología / fisioterapia', 'Salud', '0915', 'grado',
     [r'kinesiolog', r'fisioterap']),
    ('SAL05', 'Nutrición', 'Salud', '0915', 'grado',
     [r'nutricion', r'dietetic']),
    ('ENE01', 'Ingeniería eléctrica', 'Energía', '0713', 'grado',
     [r'ingenier.*(electric|electrotecnic)', r'civil electric']),
    ('ENE02', 'Ingeniería química', 'Energía', '0711', 'grado',
     [r'ingenier.*quimic', r'civil quimic', r'quimic.*industr']),
    ('ENE03', 'Ingeniería mecánica', 'Energía', '0715', 'grado',
     [r'ingenier.*(mecanic|electromecanic)', r'civil mecanic']),
    ('ENE04', 'Geología / ingeniería en minas', 'Energía', '0724', 'grado',
     [r'geolog', r'ingenier.*(minas|mineri|petroleo)', r'ciencias.*suelo']),
    ('ENE05', 'Técnico/ingeniería en energías renovables', 'Energía', '0713', 'ambos',
     [r'energ.*renovable', r'solar', r'eolic', r'hidrogeno']),
    ('TUR01', 'Licenciatura en turismo', 'Turismo', '1015', 'grado',
     [r'turismo', r'ecoturismo']),
    ('TUR02', 'Hotelería / administración hotelera', 'Turismo', '1013', 'ambos',
     [r'hoteler']),
    ('TUR03', 'Gastronomía', 'Turismo', '1013', 'tecnico',
     [r'gastronom', r'cocina', r'culinari']),
    ('TUR04', 'Guía de turismo', 'Turismo', '1015', 'tecnico',
     [r'guia.*turism']),
    ('TUR05', 'Gestión de eventos', 'Turismo', '1015', 'ambos',
     [r'eventos']),
]

PATRONES_CARRERA = [(cid, c_nom, sec, cine, niv_esp, [re.compile(p, re.IGNORECASE) for p in pats])
                    for cid, c_nom, sec, cine, niv_esp, pats in CARRERAS_OBJETIVO]

MAPA_DISCIPLINAS_URY = {
    'Informática': ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613'),
    'Ciencias de la Información y de la Comunicación': ('TEC05', 'Técnico en programación / desarrollo de software', 'Tecnología', '0613'),
    'Economía y Administración': ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
    'Estadística': ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542'),
    'Arquitectura y Diseño': ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211'),
    'Medicina': ('SAL01', 'Medicina', 'Salud', '0912'),
    'Paramédicas y Auxiliares de la Medicina': ('SAL02', 'Enfermería', 'Salud', '0913'),
    'Odontología': ('SAL03', 'Odontología', 'Salud', '0911'),
    'Bioquímica y Farmacia': ('SAL05', 'Nutrición', 'Salud', '0915'),
    'Salud Pública': ('SAL02', 'Enfermería', 'Salud', '0913'),
    'Sanidad': ('SAL02', 'Enfermería', 'Salud', '0913'),
    'Ciencias del Suelo': ('ENE04', 'Geología / ingeniería en minas', 'Energía', '0724'),
    'Industrias': ('ENE03', 'Ingeniería mecánica', 'Energía', '0715'),
    'Ingeniería': ('ENE01', 'Ingeniería eléctrica', 'Energía', '0713'),
    'Demografía y Geografía': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
}


def normalizar_texto(texto):
    if pd.isna(texto) or texto is None:
        return ''
    s = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def clasificar_titulo(nombre_carrera, nivel_dato=None):
    norm = normalizar_texto(nombre_carrera)
    es_tecnico = (nivel_dato == 'tecnico') or any(k in norm for k in ['tecnic', 'tecnicatura', 'asistente', 'auxiliar', 'laboratorista', 'analista programador'])

    for cid, c_nom, sec, cine, niv_esp, regex_list in PATRONES_CARRERA:
        if es_tecnico and niv_esp == 'grado':
            continue
        if nivel_dato == 'grado' and niv_esp == 'tecnico':
            continue
        # Exclusiones de seguridad para carreras universitarias
        if cid == 'SAL03' and any(k in norm for k in ['tecnic', 'asistente', 'auxiliar', 'laboratorista']):
            continue
        if cid in ['ENE01', 'ENE02', 'ENE03', 'TEC01', 'TEC03', 'TEC04'] and any(k in norm for k in ['tecnic', 'asistente', 'auxiliar']):
            continue
        if any(r.search(norm) for r in regex_list):
            return cid, c_nom, sec, cine
    return None


def clasificar_disciplina_o_titulo(val, nivel_dato=None):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    s_clean = re.sub(r'\.0$', '', s)
    if s_clean in DISCIPLINA_ID_A_SECTOR:
        return DISCIPLINA_ID_A_SECTOR[s_clean]
    norm = normalizar_texto(s)
    if norm in DISCIPLINA_TEXT_A_SECTOR:
        return DISCIPLINA_TEXT_A_SECTOR[norm]
    for k, v in DISCIPLINA_TEXT_A_SECTOR.items():
        if k in norm:
            return v
    return clasificar_titulo(s, nivel_dato=nivel_dato)


def inferir_nivel(carrera, tipo_inst=''):
    c_norm = normalizar_texto(carrera)
    i_norm = normalizar_texto(tipo_inst)
    if any(k in c_norm for k in ['magister', 'master', 'doctor', 'posgrado', 'postgrado', 'especializacion']):
        return 'posgrado'
    if any(k in c_norm for k in ['tecnic', 'tecnicatura', 'asistente', 'auxiliar', 'analista programador']):
        return 'tecnico'
    if 'cft' in i_norm or 'centro de formacion tecnica' in i_norm:
        return 'tecnico'
    if 'instituto profesional' in i_norm:
        return 'tecnico' if 'tecnic' in c_norm else 'grado'
    return 'grado'


def inferir_gestion(institucion, clasificacion=''):
    texto = normalizar_texto(f"{institucion} {clasificacion}")
    if any(k in texto for k in ['estatal', 'publica', 'nacional', 'cruch']):
        return 'publica'
    if any(k in texto for k in ['privada', 'particular']):
        return 'privada'
    return 'NS'


# ==============================================================================
# Procesadores por País
# ==============================================================================

def procesar_chile(paths, force_rebuild=False):
    cache_chile = paths['data_processed'] / 'chile_egresados_cache.csv'
    if not force_rebuild and cache_chile.exists():
        df_c = pd.read_csv(cache_chile)
        if len(df_c) > 0 and 'institucion' in df_c.columns:
            print(f"  ✅ Cargando Chile desde cache: {cache_chile.name} ({len(df_c):,} filas)")
            return df_c

    ruta_chile = resolver_ruta_archivo('chile/TITULADO_2007-2025_web_27_05_2026_E-1.xlsx',
                                        paths['data_raw'], paths['data_processed'], ['**/TITULAD*.xlsx'])
    if not ruta_chile:
        print("  ⚠️ Archivo de Chile Mi Futuro no encontrado.")
        return pd.DataFrame()

    print(f"  • Leyendo Excel de Chile: {ruta_chile.name}...")
    df_raw = pd.read_excel(ruta_chile, sheet_name=0)

    cols = df_raw.columns
    col_anio = cols[0]
    col_total = cols[1]
    col_mujeres = cols[2]
    col_hombres = cols[3]
    col_nb = cols[4] if len(cols) > 4 else None
    col_gestion = cols[7] if len(cols) > 7 else cols[1]
    col_inst = cols[9] if len(cols) > 9 else cols[0]
    col_carrera = cols[14] if len(cols) > 14 else [c for c in cols if 'carrera' in str(c).lower()][0]

    df_sub = pd.DataFrame({
        'anio_raw': df_raw[col_anio],
        'total': pd.to_numeric(df_raw[col_total], errors='coerce').fillna(0),
        'mujeres': pd.to_numeric(df_raw[col_mujeres], errors='coerce').fillna(0),
        'hombres': pd.to_numeric(df_raw[col_hombres], errors='coerce').fillna(0),
        'nb_indefinido': pd.to_numeric(df_raw[col_nb], errors='coerce').fillna(0) if col_nb is not None else 0,
        'carrera_origen': df_raw[col_carrera].astype(str),
        'institucion': df_raw[col_inst].astype(str).str.strip(),
        'gestion_raw': df_raw[col_gestion].astype(str)
    })

    df_sub['anio'] = df_sub['anio_raw'].astype(str).str.extract(r'(\d{4})')[0].astype(float)
    df_sub = df_sub.dropna(subset=['anio'])
    df_sub['anio'] = df_sub['anio'].astype(int)

    df_sub['nivel'] = [inferir_nivel(c, i) for c, i in zip(df_sub['carrera_origen'], df_sub['institucion'])]
    df_sub['tipo_gestion'] = [inferir_gestion(i, g) for i, g in zip(df_sub['institucion'], df_sub['gestion_raw'])]

    # Mapeo considerando el nivel educativo observado
    mapas = [clasificar_titulo(c, niv) for c, niv in zip(df_sub['carrera_origen'], df_sub['nivel'])]
    df_sub['carrera_id'] = [m[0] if m else np.nan for m in mapas]
    df_sub['carrera_objetivo'] = [m[1] if m else np.nan for m in mapas]
    df_sub['sector'] = [m[2] if m else np.nan for m in mapas]
    df_sub['cine_f_codigo'] = [m[3] if m else np.nan for m in mapas]

    df_matcheadas = df_sub.dropna(subset=['carrera_id']).copy()
    print(f"    Filas vinculadas a carreras objetivo (Chile): {len(df_matcheadas):,} de {len(df_sub):,}")

    id_vars = ['institucion', 'carrera_id', 'carrera_objetivo', 'sector', 'cine_f_codigo', 'anio', 'nivel', 'tipo_gestion']
    df_melt = pd.melt(df_matcheadas, id_vars=id_vars, value_vars=['total', 'mujeres', 'hombres', 'nb_indefinido'],
                      var_name='sexo_raw', value_name='valor')

    df_melt['sexo'] = df_melt['sexo_raw'].map({'total': 'T', 'mujeres': 'F', 'hombres': 'M', 'nb_indefinido': 'NB'})
    df_melt['pais'] = 'CHL'
    df_melt['fuente_id'] = 'CL_MIFUTURO'
    df_melt['nivel_granularidad'] = 'carrera'
    df_melt['calidad'] = 'alta'
    df_melt['marca_quiebre_serie'] = ''
    df_melt['n_muestral'] = np.nan
    df_melt['es_observado'] = pd.notna(df_melt['valor'])

    df_chl_egresados = df_melt[df_melt['valor'] > 0].copy()
    df_chl_egresados.to_csv(cache_chile, index=False, encoding='utf-8')
    print(f"  ✅ Cache de Chile generado: {len(df_chl_egresados):,} registros procesados.")
    return df_chl_egresados


def procesar_chile_sies(paths, force_rebuild=False):
    cache_sies = paths['data_processed'] / 'chile_sies_cache.csv'
    if not force_rebuild and cache_sies.exists():
        df_s = pd.read_csv(cache_sies)
        print(f"  ✅ Cargando SIES Chile desde cache: {cache_sies.name} ({len(df_s):,} filas)")
        return df_s

    ruta_sies = resolver_ruta_archivo('chile/Buscador_Estadisticas_por_carrera_2024_2025_SIES.xlsx',
                                      paths['data_raw'], paths['data_processed'],
                                      ['**/*Estadisticas*carrera*SIES*.xlsx', '**/*Empleabilidad*SIES*.xlsx'])
    if not ruta_sies:
        print("  [SIES Chile] Archivo complementario no encontrado. Continuando.")
        return pd.DataFrame()

    print(f"  • Leyendo archivo SIES Chile (encabezado doble): {ruta_sies.name}...")
    df_raw = pd.read_excel(ruta_sies, header=[0, 1])

    tipo_inst = df_raw.iloc[:, 2].astype(str).str.strip()
    carr = df_raw.iloc[:, 3].astype(str).str.strip()
    ing_1 = pd.to_numeric(df_raw.iloc[:, 4], errors='coerce')
    ing_4 = pd.to_numeric(df_raw.iloc[:, 7], errors='coerce')
    emp_1 = pd.to_numeric(df_raw.iloc[:, 24], errors='coerce')
    emp_2 = pd.to_numeric(df_raw.iloc[:, 25], errors='coerce')

    df_sies = pd.DataFrame({
        'carrera_origen': carr,
        'tipo_institucion': tipo_inst,
        'ingreso_1er_anio_clp': ing_1.round(2),
        'ingreso_4to_anio_clp': ing_4.round(2),
        'salario_clp': ing_1.round(2),  # Etapa 3 Item 3.7: ingreso al 1er año de egreso (inserción laboral inicial)
        'empleabilidad_1er_anio': emp_1.round(4),
        'empleabilidad_2do_anio': emp_2.round(4)
    })

    # Determinar nivel educativo
    niveles = []
    for _, r in df_sies.iterrows():
        c_n = normalizar_texto(r['carrera_origen'])
        i_n = normalizar_texto(r['tipo_institucion'])
        if 'tecnic' in c_n or 'asistente' in c_n or 'cft' in i_n or 'centro de formacion tecnica' in i_n:
            niveles.append('tecnico')
        elif 'instituto profesional' in i_n:
            niveles.append('tecnico' if 'tecnic' in c_n else 'grado')
        else:
            niveles.append('grado')
    df_sies['nivel'] = niveles

    # Mapear a carreras objetivo respetando nivel educativo (prohibido mapear tecnicos a ingenierias)
    mapas = [clasificar_titulo(c, niv) for c, niv in zip(df_sies['carrera_origen'], df_sies['nivel'])]
    df_sies['carrera_id'] = [m[0] if m else np.nan for m in mapas]
    df_sies['carrera_objetivo'] = [m[1] if m else np.nan for m in mapas]
    df_sies['sector'] = [m[2] if m else np.nan for m in mapas]
    df_sies['cine_f_codigo'] = [m[3] if m else np.nan for m in mapas]

    # Validacion contra casos testigo de SIES
    dental_mask = df_sies['carrera_origen'].str.contains('Dental', case=False)
    cft_mask = df_sies['tipo_institucion'].str.contains('Formación Técnica|CFT', case=False)
    test_dental = df_sies[dental_mask & cft_mask]
    if not test_dental.empty:
        r_d = test_dental.iloc[0]
        print(f"    [Caso Testigo SIES] Técnico Dental CFT: Nivel={r_d['nivel']}, CarreraID={r_d['carrera_id']}, Salario 1er={r_d['salario_clp']:,.0f} CLP, Emp 1er={r_d['empleabilidad_1er_anio']:.3f}, Emp 2do={r_d['empleabilidad_2do_anio']:.3f}")

    ind_mask = df_sies['carrera_origen'].str.contains('Ingeniería Industrial', case=False)
    ip_mask = df_sies['tipo_institucion'].str.contains('Institutos Profesionales|IP', case=False)
    test_ind = df_sies[ind_mask & ip_mask]
    if not test_ind.empty:
        r_i = test_ind.iloc[0]
        print(f"    [Caso Testigo SIES] Ingeniería Industrial IP: Nivel={r_i['nivel']}, CarreraID={r_i['carrera_id']}, Salario 1er={r_i['salario_clp']:,.0f} CLP, Emp 1er={r_i['empleabilidad_1er_anio']:.3f}, Emp 2do={r_i['empleabilidad_2do_anio']:.3f}")

    df_sies = df_sies.dropna(subset=['carrera_id']).copy()
    df_sies['pais'] = 'CHL'
    df_sies['fuente_id'] = 'CL_SIES'
    df_sies['anio'] = 2024
    df_sies['es_observado'] = pd.notna(df_sies['salario_clp']) | pd.notna(df_sies['empleabilidad_1er_anio']) | pd.notna(df_sies['empleabilidad_2do_anio'])

    df_sies.to_csv(cache_sies, index=False, encoding='utf-8')
    print(f"  ✅ SIES Chile procesado: {len(df_sies):,} carreras vinculadas a sectores estrategicos.")
    return df_sies


def procesar_argentina(paths, force_rebuild=False):
    cache_arg = paths['data_processed'] / 'argentina_egresados_cache.csv'

    # Verificar si existe cache
    if not force_rebuild and cache_arg.exists():
        try:
            df_c = pd.read_csv(cache_arg)
            sectores_en_cache = set(df_c['sector'].dropna().unique())
            anios_en_cache = df_c['anio'].dropna().unique()
            if len(df_c) > 50 and len(sectores_en_cache) >= 5 and len(anios_en_cache) >= 5 and 'institucion' in df_c.columns:
                print(f"  ✅ Cargando Argentina desde cache verificado: {cache_arg.name} ({len(df_c):,} filas, {len(anios_en_cache)} anos: {sorted(anios_en_cache)})")
                return df_c
        except Exception as e:
            print(f"  [Cache AR] Leyendo fuente cruda ({e})...")

    ruta_arg = resolver_ruta_archivo('argentina/base_araucano_traducida.xlsx',
                                     paths['data_raw'], paths['data_processed'],
                                     ['**/base_araucano*.xlsx', '**/base_araucano*.csv'])
    if not ruta_arg:
        print("  ⚠️ Archivo fuente de Argentina no encontrado.")
        return pd.DataFrame()

    print(f"  • Procesando base de Argentina desde: {ruta_arg.name}...")
    if str(ruta_arg).endswith('.csv'):
        df_raw = pd.read_csv(ruta_arg, low_memory=False)
    else:
        df_raw = pd.read_excel(ruta_arg)

    cols = list(df_raw.columns)
    cols_clean = {c: str(c).lower().strip() for c in cols}

    col_anio = None
    if 'anioegreso' in cols_clean.values():
        for c, cl in cols_clean.items():
            if cl == 'anioegreso':
                col_anio = c
                break
    if not col_anio:
        for c, cl in cols_clean.items():
            if cl in ['anio', 'ano', 'periodo']:
                col_anio = c
                break
    col_anio = col_anio or cols[0]

    col_clasif = None
    for c, cl in cols_clean.items():
        if cl in ['disciplina_id', 'cod_disciplina', 'id_disciplina']:
            col_clasif = c
            break
    if not col_clasif:
        for c, cl in cols_clean.items():
            if any(k in cl for k in ['carrera', 'titulo', 'disciplina', 'denominacion', 'nombre']) and not any(k in cl for k in ['id_', 'cod_']):
                col_clasif = c
                break

    if 'id' in cols_clean.values():
        col_id = [c for c, cl in cols_clean.items() if cl == 'id'][0]
        df_raw = df_raw.drop_duplicates(subset=[col_id]).copy()

    df_raw['mapeo'] = df_raw[col_clasif].apply(clasificar_disciplina_o_titulo)
    df_matcheadas = df_raw.dropna(subset=['mapeo']).copy()

    df_matcheadas['carrera_id'] = df_matcheadas['mapeo'].apply(lambda m: m[0])
    df_matcheadas['carrera_objetivo'] = df_matcheadas['mapeo'].apply(lambda m: m[1])
    df_matcheadas['sector'] = df_matcheadas['mapeo'].apply(lambda m: m[2])
    df_matcheadas['cine_f_codigo'] = df_matcheadas['mapeo'].apply(lambda m: m[3])
    df_matcheadas['anio'] = pd.to_numeric(df_matcheadas[col_anio].astype(str).str.extract(r'(\d{4})')[0], errors='coerce').fillna(0).astype(int)
    df_matcheadas = df_matcheadas[df_matcheadas['anio'] >= 2000]
    df_matcheadas['pais'] = 'ARG'
    df_matcheadas['fuente_id'] = 'AR_CAPITALHUMANO'
    df_matcheadas['institucion'] = 'Sin dato observado'
    df_matcheadas['nivel'] = df_matcheadas['carrera_id'].map(lambda cid: 'tecnico' if cid == 'TEC05' or 'tecnic' in str(cid).lower() else 'grado')
    if 'gestion' in df_matcheadas.columns:
        df_matcheadas['tipo_gestion'] = df_matcheadas['gestion'].astype(str).str.lower().apply(
            lambda g: 'privada' if 'privad' in g else ('publica' if ('estatal' in g or 'pub' in g) else 'NS')
        )
    else:
        df_matcheadas['tipo_gestion'] = 'publica'

    if 'genero' in df_matcheadas.columns:
        df_matcheadas['sexo'] = df_matcheadas['genero'].astype(str).str.lower().apply(
            lambda s: 'F' if ('muj' in s or s == 'f') else ('M' if ('var' in s or 'hom' in s or s == 'm') else 'NS')
        )
    else:
        df_matcheadas['sexo'] = 'T'

    df_matcheadas['valor'] = 1.0

    cols_group = ['pais', 'fuente_id', 'institucion', 'carrera_id', 'carrera_objetivo', 'sector', 'cine_f_codigo',
                  'anio', 'nivel', 'tipo_gestion', 'sexo']
    df_arg_final = df_matcheadas.groupby(cols_group, as_index=False, dropna=False)['valor'].sum()
    df_arg_final['nivel_granularidad'] = 'carrera'
    df_arg_final['calidad'] = 'alta'
    df_arg_final['marca_quiebre_serie'] = ''
    df_arg_final['n_muestral'] = np.nan
    df_arg_final['es_observado'] = pd.notna(df_arg_final['valor'])

    # Generar registros consolidados sexo='T' para el trinomio de Araucano
    cols_tot = ['pais', 'fuente_id', 'institucion', 'carrera_id', 'carrera_objetivo', 'sector', 'cine_f_codigo',
                'anio', 'nivel', 'tipo_gestion', 'nivel_granularidad', 'calidad', 'marca_quiebre_serie',
                'n_muestral', 'es_observado']
    df_arg_tot = df_arg_final.groupby(cols_tot, as_index=False, dropna=False)['valor'].sum()
    df_arg_tot['sexo'] = 'T'
    df_arg_final = pd.concat([df_arg_final, df_arg_tot], ignore_index=True)

    # Integracion de Anuarios SPU 2020-2022 (Decision Etapa 2 Item 2.1 Opcion 1)
    col_map_spu = {
        'e_informatica': ('TEC01', 'Ingeniería en informática / computación', 'Tecnología', '0613'),
        'e_ing': ('ENE01', 'Ingeniería eléctrica / mecánica', 'Energía', '0713'),
        'e_industrias': ('ENE03', 'Ingeniería mecánica / industrial', 'Energía', '0715'),
        'e_suelo': ('ENE04', 'Geología / minería / suelo', 'Energía', '0724'),
        'e_medicina': ('SAL01', 'Medicina', 'Salud', '0912'),
        'e_odontologia': ('SAL03', 'Odontología', 'Salud', '0911'),
        'e_paramedicas_auxiliares': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
        'e_paramedico_auxiliares': ('SAL02', 'Enfermería / paramédicas', 'Salud', '0913'),
        'e_salud_publica': ('SAL02', 'Enfermería / salud pública', 'Salud', '0913'),
        'e_sanidad': ('SAL02', 'Enfermería / sanidad', 'Salud', '0913'),
        'e_bioquimica_farmacia': ('SAL05', 'Nutrición / bioquímica', 'Salud', '0915'),
        'e_estadistica': ('EDC01', 'Estadística / ciencia de datos', 'Economía del conocimiento', '0542'),
        'e_economia_administracion': ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
        'e_economia': ('EDC05', 'Administración / ingeniería comercial', 'Economía del conocimiento', '0413'),
        'e_arquitectura_disenio': ('EDC02', 'Diseño gráfico / multimedia / UX-UI', 'Economía del conocimiento', '0211'),
        'e_demografia_geografia': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015'),
        'e_dg': ('TUR01', 'Licenciatura en turismo / geografía', 'Turismo', '1015')
    }

    dir_arg = paths['data_raw'] / 'argentina'
    spu_filas = []
    for yr in ['2020', '2021', '2022']:
        for tipo, cap in [('publica', 'Capitulo 2 Pregrado Grado Estatal'), ('privada', 'Capitulo 2 Pregrado Grado Privado')]:
            folder = dir_arg / f"Anuario {yr}" / cap
            if not folder.exists():
                continue
            for p in folder.glob("*.csv"):
                try:
                    df_p = pd.read_csv(p, sep='|', encoding='latin-1')
                    if 'nombre_corto' not in df_p.columns:
                        continue
                    cols_present = [c for c in col_map_spu if c in df_p.columns]
                    if not cols_present:
                        continue
                    for _, r in df_p.iterrows():
                        inst = str(r['nombre_corto']).strip()
                        if 'Total' in inst or inst == '' or inst == 'nan':
                            continue
                        for col in cols_present:
                            val = pd.to_numeric(r[col], errors='coerce')
                            if pd.notna(val) and val > 0:
                                cid, cnom, sec, cine = col_map_spu[col]
                                spu_filas.append({
                                    'pais': 'ARG',
                                    'fuente_id': 'AR_SPU_ANUARIO',
                                    'institucion': 'Sin dato observado',
                                    'carrera_id': cid,
                                    'carrera_objetivo': cnom,
                                    'sector': sec,
                                    'cine_f_codigo': cine,
                                    'anio': int(yr),
                                    'nivel': 'grado',
                                    'tipo_gestion': tipo,
                                    'sexo': 'T',
                                    'valor': float(val),
                                    'nivel_granularidad': 'disciplina',
                                    'calidad': 'alta',
                                    'marca_quiebre_serie': '',
                                    'n_muestral': np.nan,
                                    'es_observado': True
                                })
                except Exception:
                    pass

    if spu_filas:
        df_spu = pd.DataFrame(spu_filas)
        cols_spu_grp = ['pais', 'fuente_id', 'institucion', 'carrera_id', 'carrera_objetivo', 'sector', 'cine_f_codigo',
                        'anio', 'nivel', 'tipo_gestion', 'sexo', 'nivel_granularidad', 'calidad', 'marca_quiebre_serie',
                        'n_muestral', 'es_observado']
        df_spu_agrup = df_spu.groupby(cols_spu_grp, as_index=False, dropna=False)['valor'].sum()
        df_arg_final = pd.concat([df_arg_final, df_spu_agrup], ignore_index=True)
        print(f"    • Incorporados {len(df_spu_agrup):,} registros de Anuarios SPU 2020-2022 (Total anos AR: {sorted(df_arg_final['anio'].unique())}).")

    df_arg_final.to_csv(cache_arg, index=False, encoding='utf-8')
    print(f"  ✅ Base de Argentina procesada exitosamente ({len(df_arg_final):,} filas agrupadas).")
    return df_arg_final


def procesar_argentina_laboral(paths, force_rebuild=False):
    cache_lab = paths['data_processed'] / 'argentina_laboral_cache.csv'
    if not force_rebuild and cache_lab.exists():
        try:
            df_l = pd.read_csv(cache_lab)
            if len(df_l) > 0 and 'meses_observados' in df_l.columns:
                print(f"  ✅ Cargando Mercado Laboral Argentina desde cache verificado: {cache_lab.name} ({len(df_l):,} filas)")
                return df_l
        except Exception:
            pass

    ruta_puestos_nac = resolver_ruta_archivo('argentina/puestos_privados_mensual_por_clae2.csv', paths['data_raw'], paths['data_processed'], ['**/puestos_privados*.csv'])
    ruta_puestos_dep = resolver_ruta_archivo('argentina/puestos_depto_priv_por_clae2.csv', paths['data_raw'], paths['data_processed'], ['**/puestos*clae2*.csv'])
    ruta_wmean = resolver_ruta_archivo('argentina/w_mean_privado_mensual_por_clae2.csv', paths['data_raw'], paths['data_processed'], ['**/w_mean*clae2*.csv'])
    ruta_wmedian = resolver_ruta_archivo('argentina/w_median_privado_mensual_por_clae2.csv', paths['data_raw'], paths['data_processed'], ['**/w_median*clae2*.csv'])
    ruta_mujer = resolver_ruta_archivo('argentina/share_mujer_privado_mensual_por_clae2.csv', paths['data_raw'], paths['data_processed'], ['**/share_mujer*clae2*.csv'])

    if not ruta_wmean:
        print("  ⚠️ Archivos de salarios CEP-XXI no encontrados. Continuando sin series salariales AR.")
        return pd.DataFrame()

    print("  • Procesando series salariales y de empleo CEP-XXI de Argentina (Ponderación por puestos observados)...")

    # 1. Puestos de empleo (priorizar serie nacional continua 2007-2023)
    df_pst_anual = pd.DataFrame()
    if ruta_puestos_nac and ruta_puestos_nac.exists():
        print(f"    • Usando base nacional de puestos: {ruta_puestos_nac.name}")
        df_p_raw = pd.read_csv(ruta_puestos_nac)
        df_p_raw['puestos'] = df_p_raw['puestos'].replace(-99, np.nan)
        df_p_raw['fecha_dt'] = pd.to_datetime(df_p_raw['fecha'])
        df_p_raw['anio'] = df_p_raw['fecha_dt'].dt.year
        df_p_raw['clae2_str'] = df_p_raw['clae2'].astype(str).str.strip().str.zfill(2)
        df_pst_anual = df_p_raw.groupby(['clae2_str', 'anio'], as_index=False).agg(
            puestos=('puestos', 'mean'),
            meses_puestos=('fecha', 'count')
        )
    elif ruta_puestos_dep and ruta_puestos_dep.exists():
        print(f"    • Usando base departamental de puestos agregada: {ruta_puestos_dep.name}")
        df_p_raw = pd.read_csv(ruta_puestos_dep)
        df_p_raw['puestos'] = df_p_raw['puestos'].replace(-99, np.nan)
        df_p_raw['fecha_dt'] = pd.to_datetime(df_p_raw['fecha'])
        df_p_raw['anio'] = df_p_raw['fecha_dt'].dt.year
        df_p_raw['clae2_str'] = df_p_raw['clae2'].astype(str).str.strip().str.zfill(2)
        df_mes = df_p_raw.groupby(['clae2_str', 'anio', 'fecha_dt'], as_index=False)['puestos'].sum()
        df_pst_anual = df_mes.groupby(['clae2_str', 'anio'], as_index=False).agg(
            puestos=('puestos', 'mean'),
            meses_puestos=('fecha_dt', 'count')
        )

    # 2. Salario medio mensual
    df_wm = pd.read_csv(ruta_wmean)
    df_wm['w_mean'] = df_wm['w_mean'].replace(-99, np.nan)
    df_wm['fecha_dt'] = pd.to_datetime(df_wm['fecha'])
    df_wm['anio'] = df_wm['fecha_dt'].dt.year
    df_wm['clae2_str'] = df_wm['clae2'].astype(str).str.strip().str.zfill(2)
    df_wm_anual = df_wm.groupby(['clae2_str', 'anio'], as_index=False).agg(
        w_mean=('w_mean', 'mean'),
        meses_wmean=('fecha', 'count')
    )

    # 3. Salario mediano mensual
    df_wmed_anual = pd.DataFrame()
    if ruta_wmedian and ruta_wmedian.exists():
        df_wmed = pd.read_csv(ruta_wmedian)
        df_wmed['w_median'] = df_wmed['w_median'].replace(-99, np.nan)
        df_wmed['fecha_dt'] = pd.to_datetime(df_wmed['fecha'])
        df_wmed['anio'] = df_wmed['fecha_dt'].dt.year
        df_wmed['clae2_str'] = df_wmed['clae2'].astype(str).str.strip().str.zfill(2)
        df_wmed_anual = df_wmed.groupby(['clae2_str', 'anio'], as_index=False).agg(
            w_median=('w_median', 'mean')
        )

    # 4. Participacion femenina mensual
    df_muj_anual = pd.DataFrame()
    if ruta_mujer and ruta_mujer.exists():
        df_muj = pd.read_csv(ruta_mujer)
        df_muj['share_mujer'] = df_muj['share_mujer'].replace(-99, np.nan)
        df_muj['fecha_dt'] = pd.to_datetime(df_muj['fecha'])
        df_muj['anio'] = df_muj['fecha_dt'].dt.year
        df_muj['clae2_str'] = df_muj['clae2'].astype(str).str.strip().str.zfill(2)
        df_muj_anual = df_muj.groupby(['clae2_str', 'anio'], as_index=False).agg(
            share_mujer=('share_mujer', 'mean')
        )

    # Unir a nivel rama (CLAE2) y año
    df_clae2 = pd.merge(df_wm_anual, df_pst_anual, on=['clae2_str', 'anio'], how='outer')
    if not df_wmed_anual.empty:
        df_clae2 = pd.merge(df_clae2, df_wmed_anual, on=['clae2_str', 'anio'], how='outer')
    if not df_muj_anual.empty:
        df_clae2 = pd.merge(df_clae2, df_muj_anual, on=['clae2_str', 'anio'], how='outer')

    df_clae2['sector'] = df_clae2['clae2_str'].map(CLAE2_A_SECTOR)
    df_sec_clae = df_clae2.dropna(subset=['sector']).copy()

    # 5. Agregacion sectorial ponderada por puestos (Decisiones D2 y D3)
    registros_sector = []
    for (sec, anio), grp in df_sec_clae.groupby(['sector', 'anio']):
        puestos_tot = grp['puestos'].sum(min_count=1)
        val_puestos = grp['puestos'].fillna(0)
        sum_puestos = val_puestos.sum()

        if sum_puestos > 0 and grp['w_mean'].notna().any():
            valid_wm = grp.dropna(subset=['w_mean', 'puestos'])
            if not valid_wm.empty and valid_wm['puestos'].sum() > 0:
                w_mean_pond = (valid_wm['w_mean'] * valid_wm['puestos']).sum() / valid_wm['puestos'].sum()
            else:
                w_mean_pond = grp['w_mean'].mean()
        else:
            w_mean_pond = grp['w_mean'].mean()

        if sum_puestos > 0 and 'w_median' in grp.columns and grp['w_median'].notna().any():
            valid_wmed = grp.dropna(subset=['w_median', 'puestos'])
            if not valid_wmed.empty and valid_wmed['puestos'].sum() > 0:
                w_median_pond = (valid_wmed['w_median'] * valid_wmed['puestos']).sum() / valid_wmed['puestos'].sum()
            else:
                w_median_pond = grp['w_median'].mean()
        else:
            w_median_pond = grp['w_median'].mean() if 'w_median' in grp.columns else np.nan

        if sum_puestos > 0 and 'share_mujer' in grp.columns and grp['share_mujer'].notna().any():
            valid_muj = grp.dropna(subset=['share_mujer', 'puestos'])
            if not valid_muj.empty and valid_muj['puestos'].sum() > 0:
                share_muj_pond = (valid_muj['share_mujer'] * valid_muj['puestos']).sum() / valid_muj['puestos'].sum()
            else:
                share_muj_pond = grp['share_mujer'].mean()
        else:
            share_muj_pond = grp['share_mujer'].mean() if 'share_mujer' in grp.columns else np.nan

        meses_max = grp['meses_wmean'].max() if 'meses_wmean' in grp.columns else (grp['meses_puestos'].max() if 'meses_puestos' in grp.columns else 12)
        meses_val = int(meses_max) if pd.notna(meses_max) else 12

        registros_sector.append({
            'sector': sec,
            'anio': int(anio),
            'w_mean': round(float(w_mean_pond), 2) if pd.notna(w_mean_pond) else np.nan,
            'w_median': round(float(w_median_pond), 2) if pd.notna(w_median_pond) else np.nan,
            'share_mujer': round(float(share_muj_pond), 4) if pd.notna(share_muj_pond) else np.nan,
            'puestos': round(float(puestos_tot), 1) if pd.notna(puestos_tot) else np.nan,
            'meses_observados': meses_val,
            'cobertura_meses': f"{meses_val}/12",
            'metodo_ponderacion': 'ponderado_por_puestos' if sum_puestos > 0 else 'promedio_simple'
        })

    df_wm_sec = pd.DataFrame(registros_sector)
    df_wm_sec['pais'] = 'ARG'
    df_wm_sec['fuente_id'] = 'AR_CEPXXI'
    df_wm_sec['es_observado'] = pd.notna(df_wm_sec.get('w_mean')) | pd.notna(df_wm_sec.get('puestos'))

    df_wm_sec.to_csv(cache_lab, index=False, encoding='utf-8')
    print(f"  ✅ Datos laborales de Argentina consolidados: {len(df_wm_sec)} filas sector/ano (Ponderacion por puestos aplicada).")
    return df_wm_sec


def procesar_uruguay(paths, force_rebuild=False):
    cache_ury = paths['data_processed'] / 'uruguay_egresados_cache.csv'
    if not force_rebuild and cache_ury.exists():
        try:
            df_u = pd.read_csv(cache_ury)
            if len(df_u) > 0 and 'Turismo' in df_u['sector'].unique() and (df_u['valor'] % 1 == 0).all() and 'institucion' in df_u.columns:
                print(f"  ✅ Cargando Uruguay desde cache verificado: {cache_ury.name} ({len(df_u):,} filas)")
                return df_u
        except Exception:
            pass

    ruta_ury = resolver_ruta_archivo('uruguay/00._educ_superior_datos.csv',
                                     paths['data_raw'], paths['data_processed'],
                                     ['**/*educ_superior_datos*.csv'])
    if not ruta_ury:
        print("  ⚠️ Archivo de Uruguay Educacion Superior no encontrado.")
        return pd.DataFrame()

    print(f"  • Leyendo Educacion Superior de Uruguay: {ruta_ury.name} (separador miles con punto)...")
    df_raw = None
    for enc in ['latin-1', 'cp1252', 'utf-8']:
        try:
            df_try = pd.read_csv(ruta_ury, sep=';', thousands='.', encoding=enc)
            if len(df_try.columns) > 3:
                df_raw = df_try
                break
        except Exception:
            continue

    if df_raw is None:
        print("  ⚠️ No se pudo decodificar el archivo de Uruguay.")
        return pd.DataFrame()

    df_egr = df_raw[df_raw['TIPO_ALUMNO'].astype(str).str.strip().str.upper() == 'EGRESADOS'].copy()
    if 'U_MED' in df_egr.columns:
        df_egr = df_egr[df_egr['U_MED'].astype(str).str.strip() == 'Cantidad de personas']

    df_egr['mapeo'] = df_egr['DISCIP_ESPECIF'].astype(str).str.strip().map(MAPA_DISCIPLINAS_URY)
    df_matcheadas = df_egr.dropna(subset=['mapeo']).copy()

    df_matcheadas['carrera_id'] = df_matcheadas['mapeo'].apply(lambda m: m[0])
    df_matcheadas['carrera_objetivo'] = df_matcheadas['mapeo'].apply(lambda m: m[1])
    df_matcheadas['sector'] = df_matcheadas['mapeo'].apply(lambda m: m[2])
    df_matcheadas['cine_f_codigo'] = df_matcheadas['mapeo'].apply(lambda m: m[3])

    df_matcheadas['pais'] = 'URY'
    df_matcheadas['fuente_id'] = 'UY_MEC_SUP'
    df_matcheadas['institucion'] = 'Sin dato observado'
    df_matcheadas['anio'] = pd.to_numeric(df_matcheadas['ANIO'], errors='coerce').fillna(0).astype(int)
    df_matcheadas['valor'] = pd.to_numeric(df_matcheadas['VALOR'], errors='coerce').fillna(0).round().astype(int)

    df_matcheadas['tipo_gestion'] = df_matcheadas['TIPO_UNIV'].astype(str).str.lower().apply(
        lambda g: 'privada' if 'privad' in g else ('publica' if ('pub' in g or 'púb' in g) else 'NS')
    )
    df_matcheadas['nivel'] = df_matcheadas['NIVEL_ACADEM'].astype(str).str.lower().apply(
        lambda n: 'posgrado' if 'pos' in n else ('tecnico' if 'pre' in n else 'grado')
    )

    df_matcheadas['sexo'] = 'T'
    df_matcheadas['nivel_granularidad'] = 'carrera'
    df_matcheadas['calidad'] = 'alta'
    df_matcheadas['marca_quiebre_serie'] = ''
    df_matcheadas['n_muestral'] = np.nan
    df_matcheadas['es_observado'] = pd.notna(df_matcheadas['valor']) & (df_matcheadas['valor'] > 0)

    cols_group = ['pais', 'fuente_id', 'institucion', 'carrera_id', 'carrera_objetivo', 'sector', 'cine_f_codigo',
                  'anio', 'nivel', 'tipo_gestion', 'nivel_granularidad', 'calidad', 'marca_quiebre_serie',
                  'n_muestral', 'es_observado', 'sexo']
    df_ury_final = df_matcheadas.groupby(cols_group, as_index=False, dropna=False)['valor'].sum()
    df_ury_final = df_ury_final[df_ury_final['valor'] > 0]
    df_ury_final.to_csv(cache_ury, index=False, encoding='utf-8')

    print(f"  ✅ [Uruguay] Egresados normalizados: {len(df_ury_final):,} registros consolidados (2014-2023, valores enteros observados).")
    return df_ury_final


def normalizar_nombre_institucion(nombre: str, pais: str) -> str:
    """
    Normaliza el nombre de instituciones universitarias (Decision Etapa 4 Item 4.1):
    - Mayusculas y minusculas formales (Title Case) con excepciones de enlace.
    - Preserva y corrige tildes y caracteres ortograficos en UTF-8.
    - Remueve notas aclaratorias de convenios entre parentesis y asteriscos.
    - Expande abreviaturas institucionales y resuelve siglas oficiales.
    - Unifica duplicados conocidos (ej. UdelaR).
    """
    if not isinstance(nombre, str) or not nombre.strip():
        return ""
    n = nombre.strip()

    if pais == 'CHL':
        # Correccion de caracteres especiales / encoding
        n = n.replace('IBAEZ', 'IBÁÑEZ').replace('IBAÑEZ', 'IBÁÑEZ').replace('VIA DEL MAR', 'VIÑA DEL MAR')
        # Limpieza de notas de convenio entre parentesis y asteriscos (ej. ARCIS, Pacifico, UNICYT)
        n = re.sub(r'\s*\(\s*\*.*?convenio.*?\)', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\s*\(\s*\*.*?\)', '', n, flags=re.IGNORECASE)
        n = n.strip()
        map_chl = {
            'UNIVERSIDAD ADOLFO IBÁÑEZ': 'Universidad Adolfo Ibáñez',
            'UNIVERSIDAD DE VIÑA DEL MAR': 'Universidad de Viña del Mar',
            'UNIVERSIDAD DE ARTE Y CIENCIAS SOCIALES ARCIS': 'Universidad de Arte y Ciencias Sociales (ARCIS)',
            'UNIVERSIDAD DEL PACIFICO': 'Universidad del Pacífico',
            'UNIVERSIDAD IBEROAMERICANA DE CIENCIAS Y TECNOLOGIA, UNICYT': 'Universidad Iberoamericana de Ciencias y Tecnología (UNICYT)',
            'UNIVERSIDAD TECNOLOGICA DE CHILE INACAP': 'Universidad Tecnológica de Chile INACAP',
            'PONTIFICIA UNIVERSIDAD CATOLICA DE CHILE': 'Pontificia Universidad Católica de Chile',
            'UNIVERSIDAD ANDRES BELLO': 'Universidad Andrés Bello',
            'UNIVERSIDAD DE CHILE': 'Universidad de Chile',
            'UNIVERSIDAD DE SANTIAGO DE CHILE': 'Universidad de Santiago de Chile',
            'UNIVERSIDAD SAN SEBASTIAN': 'Universidad San Sebastián',
            'UNIVERSIDAD DEL DESARROLLO': 'Universidad del Desarrollo',
            'UNIVERSIDAD AUTONOMA DE CHILE': 'Universidad Autónoma de Chile',
            'UNIVERSIDAD DE LAS AMERICAS': 'Universidad de Las Américas',
            'UNIVERSIDAD SANTO TOMAS': 'Universidad Santo Tomás',
            'UNIVERSIDAD DE CONCEPCION': 'Universidad de Concepción',
            'UNIVERSIDAD MAYOR': 'Universidad Mayor',
            'PONTIFICIA UNIVERSIDAD CATOLICA DE VALPARAISO': 'Pontificia Universidad Católica de Valparaíso',
            'UNIVERSIDAD CENTRAL DE CHILE': 'Universidad Central de Chile',
            'UNIVERSIDAD CATOLICA DEL NORTE': 'Universidad Católica del Norte',
            'UNIVERSIDAD CATOLICA DEL MAULE': 'Universidad Católica del Maule',
            'UNIVERSIDAD CATOLICA DE LA SANTISIMA CONCEPCION': 'Universidad Católica de la Santísima Concepción',
            'UNIVERSIDAD CATOLICA DE TEMUCO': 'Universidad Católica de Temuco',
            'UNIVERSIDAD DE VALPARAISO': 'Universidad de Valparaíso',
            'UNIVERSIDAD DE LA FRONTERA': 'Universidad de La Frontera',
            'UNIVERSIDAD AUSTRAL DE CHILE': 'Universidad Austral de Chile',
            'UNIVERSIDAD DE TARAPACA': 'Universidad de Tarapacá',
            'UNIVERSIDAD DE ANTOFAGASTA': 'Universidad de Antofagasta',
            'UNIVERSIDAD DE ATACAMA': 'Universidad de Atacama',
            'UNIVERSIDAD DE LA SERENA': 'Universidad de La Serena',
            'UNIVERSIDAD DE PLAYA ANCHA DE CIENCIAS DE LA EDUCACION': 'Universidad de Playa Ancha',
            'UNIVERSIDAD DEL BIO-BIO': 'Universidad del Bío-Bío',
            'UNIVERSIDAD DE LOS LAGOS': 'Universidad de Los Lagos',
            'UNIVERSIDAD DE MAGALLANES': 'Universidad de Magallanes',
            'UNIVERSIDAD DE TALCA': 'Universidad de Talca',
            'UNIVERSIDAD DE O\'HIGGINS': 'Universidad de O\'Higgins',
            'UNIVERSIDAD DE AYSEN': 'Universidad de Aysén',
            'UNIVERSIDAD DIEGO PORTALES': 'Universidad Diego Portales',
            'UNIVERSIDAD FINIS TERRAE': 'Universidad Finis Terrae',
            'UNIVERSIDAD GABRIELA MISTRAL': 'Universidad Gabriela Mistral',
            'UNIVERSIDAD ALBERTO HURTADO': 'Universidad Alberto Hurtado',
            'UNIVERSIDAD DE LOS ANDES': 'Universidad de los Andes',
            'UNIVERSIDAD BERNARDO O\'HIGGINS': 'Universidad Bernardo O\'Higgins',
            'UNIVERSIDAD UCINF': 'Universidad UCINF',
            'UNIVERSIDAD MIGUEL DE CERVANTES': 'Universidad Miguel de Cervantes',
            'UNIVERSIDAD ACADEMIA DE HUMANISMO CRISTIANO': 'Universidad Academia de Humanismo Cristiano',
            'UNIVERSIDAD SEK': 'Universidad SEK',
            'UNIVERSIDAD DE LAS COMUNICACIONES': 'Universidad de las Comunicaciones (UNIACC)',
            'UNIVERSIDAD ADVENTISTA DE CHILE': 'Universidad Adventista de Chile',
            'UNIVERSIDAD BOLIVARIANA': 'Universidad Bolivariana',
            'UNIVERSIDAD LA REPUBLICA': 'Universidad La República',
            'UNIVERSIDAD METROPOLITANA DE CIENCIAS DE LA EDUCACION': 'Universidad Metropolitana de Ciencias de la Educación',
            'UNIVERSIDAD TECNOLOGICA METROPOLITANA': 'Universidad Tecnológica Metropolitana (UTEM)',
            'UNIVERSIDAD ARTURO PRAT': 'Universidad Arturo Prat',
            'UNIVERSIDAD PEDRO DE VALDIVIA': 'Universidad Pedro de Valdivia',
            'UNIVERSIDAD LOS LEONES': 'Universidad Los Leones'
        }
        if n in map_chl:
            return map_chl[n]
        palabras = n.lower().split()
        excepciones = {'de', 'del', 'la', 'las', 'los', 'y', 'en', 'para', 'por', 'con'}
        return ' '.join(p if (p in excepciones and i > 0) else p.capitalize() for i, p in enumerate(palabras))

    if pais == 'URY':
        n = n.replace('Polica', 'Policía').replace('Asociacin', 'Asociación').replace('Jvenes', 'Jóvenes')
        n = n.replace('Fernndez', 'Fernández').replace('Monseor', 'Monseñor').replace('Ass', 'Asís')
        n = n.replace('Repblica', 'República')
        map_uy = {
            'UdelaR': 'Universidad de la República (UdelaR)',
            'Universidad de la República (UdelaR)': 'Universidad de la República (UdelaR)',
            'UCU': 'Universidad Católica del Uruguay (UCU)',
            'UTEC': 'Universidad Tecnológica del Uruguay (UTEC)',
            'Inst Univ CEDIIAP': 'Instituto Universitario CEDIIAP',
            'Inst Univ Elbio Fernández': 'Instituto Universitario Elbio Fernández',
            'Inst Univ Monseñor Mariano Soler': 'Instituto Universitario Monseñor Mariano Soler',
            'Inst Univ Asociación Cristiana de Jóvenes': 'Instituto Universitario Asociación Cristiana de Jóvenes (IUACJ)',
            'Instituto Universitario Francisco de Asís (UNIFA)': 'Instituto Universitario Francisco de Asís (UNIFA)',
            'Escuela Nacional de Policía': 'Escuela Nacional de Policía',
            'Instituto Militar de Estudios Superiores': 'Instituto Militar de Estudios Superiores',
            'Universidad de la Empresa': 'Universidad de la Empresa (UDE)',
            'Universidad CLAEH': 'Universidad CLAEH',
            'Universidad ORT Uruguay': 'Universidad ORT Uruguay'
        }
        return map_uy.get(n, n)

    if pais == 'ARG':
        map_arg = {
            'Gral. Sarmiento': 'General Sarmiento',
            'Patagonia S. J. Bosco': 'Patagonia San Juan Bosco'
        }
        return map_arg.get(n, n)

    return n


def procesar_instituciones_oficiales(paths, df_chl_egresados, force_rebuild=False):
    """
    Consolida las series institucionales observadas para Argentina (SPU), Chile (Mi Futuro) y Uruguay (MEC).
    Genera hecho_instituciones_egresados.csv con auditoria de gestion, sector y ano.
    Aplica normalizacion formal de nombres (Item 4.1) y filtro estricto de universidades (Item 4.2).
    """
    cache_inst = paths['data_processed'] / 'hecho_instituciones_egresados.csv'
    if not force_rebuild and cache_inst.exists():
        df_cached = pd.read_csv(cache_inst)
        if len(df_cached) > 0 and len(df_cached['pais'].unique()) >= 3:
            print(f"  ✅ Cargando instituciones desde cache: {cache_inst.name} ({len(df_cached):,} registros)")
            return df_cached

    print("\n  • Procesando datos institucionales oficiales (ARG, CHL, URY)...")
    registros = []

    # 1. Chile desde df_chl_egresados (sexo == 'T') - Solo Universidades (Decision Etapa 4 Item 4.2)
    if not df_chl_egresados.empty:
        df_chl_tot = df_chl_egresados[df_chl_egresados['sexo'] == 'T'].copy()
        grp_chl = df_chl_tot.groupby(['institucion', 'tipo_gestion', 'sector', 'anio'], as_index=False)['valor'].sum()
        for _, r in grp_chl.iterrows():
            inst_raw = str(r['institucion']).strip()
            inst_up = inst_raw.upper()
            # Excluir Centros de Formacion Tecnica (CFT) e Institutos Profesionales (IP) para paridad universitaria estricta
            if (inst_up.startswith('CFT ') or inst_up.startswith('IP ') or 
                'CENTRO DE FORMACION' in inst_up or 'CENTRO DE FORMACIÓN' in inst_up or 
                'INSTITUTO PROFESIONAL' in inst_up):
                continue
            inst_norm = normalizar_nombre_institucion(inst_raw, 'CHL')
            registros.append({
                'pais': 'CHL',
                'fuente_id': 'CL_MIFUTURO',
                'institucion': inst_norm,
                'tipo_gestion': r['tipo_gestion'],
                'tipo_institucion': 'universidad',
                'sector': r['sector'],
                'anio': int(r['anio']),
                'graduados': float(r['valor']),
                'es_observado': True
            })

    # 2. Argentina desde Anuarios SPU (2020-2022) - Cobertura de los 5 sectores
    dir_arg = paths['data_raw'] / 'argentina'
    col_map_arg = {
        'e_informatica': 'Tecnología',
        'e_ing': 'Energía',
        'e_industrias': 'Energía',
        'e_suelo': 'Energía',
        'e_medicina': 'Salud',
        'e_odontologia': 'Salud',
        'e_paramedicas_auxiliares': 'Salud',
        'e_paramedico_auxiliares': 'Salud',
        'e_salud_publica': 'Salud',
        'e_sanidad': 'Salud',
        'e_bioquimica_farmacia': 'Salud',
        'e_estadistica': 'Economía del conocimiento',
        'e_economia_administracion': 'Economía del conocimiento',
        'e_economia': 'Economía del conocimiento',
        'e_arquitectura_disenio': 'Economía del conocimiento',
        'e_demografia_geografia': 'Turismo',
        'e_dg': 'Turismo'
    }
    for yr in ['2020', '2021', '2022']:
        for tipo, cap in [('publica', 'Capitulo 2 Pregrado Grado Estatal'), ('privada', 'Capitulo 2 Pregrado Grado Privado')]:
            folder = dir_arg / f"Anuario {yr}" / cap
            if not folder.exists():
                continue
            for p in folder.glob("*.csv"):
                try:
                    df_p = pd.read_csv(p, sep='|', encoding='latin-1')
                    if 'nombre_corto' not in df_p.columns:
                        continue
                    cols_present = [c for c in col_map_arg if c in df_p.columns]
                    if not cols_present:
                        continue
                    for _, r in df_p.iterrows():
                        inst = str(r['nombre_corto']).strip()
                        if 'Total' in inst or inst == '' or inst == 'nan':
                            continue
                        inst_norm = normalizar_nombre_institucion(inst, 'ARG')
                        for col in cols_present:
                            val = pd.to_numeric(r[col], errors='coerce')
                            if pd.notna(val) and val > 0:
                                registros.append({
                                    'pais': 'ARG',
                                    'fuente_id': 'AR_SPU_ANUARIO',
                                    'institucion': inst_norm,
                                    'tipo_gestion': tipo,
                                    'tipo_institucion': 'universidad',
                                    'sector': col_map_arg[col],
                                    'anio': int(yr),
                                    'graduados': float(val),
                                    'es_observado': True
                                })
                except Exception:
                    pass

    # 3. Uruguay: Serie Historica UdelaR (2020-2024) y Anuario Estadistico MEC (2024)
    # A. UdelaR (Serie continua de grado por facultad / servicio)
    p_odf = paths['data_raw'] / 'uruguay' / '1.Serie-Egresos-totales-Grado-por-Servicio-2000-2024.ods'
    if p_odf.exists():
        try:
            df_odf = pd.read_excel(p_odf, engine='odf', header=4)
            df_tot_u = df_odf[df_odf.iloc[:, 0].astype(str).str.contains('TOTAL')]
            if not df_tot_u.empty:
                for a_col in [2020, 2021, 2022, 2023, 2024]:
                    if a_col in df_tot_u.columns:
                        v_u = pd.to_numeric(df_tot_u[a_col].iloc[0], errors='coerce')
                        if pd.notna(v_u) and v_u > 0:
                            registros.append({
                                'pais': 'URY',
                                'fuente_id': 'UY_UDELAR_SERIE',
                                'institucion': 'Universidad de la República (UdelaR)',
                                'tipo_gestion': 'publica',
                                'tipo_institucion': 'universidad',
                                'sector': 'Total Universitario',
                                'anio': int(a_col),
                                'graduados': float(v_u),
                                'es_observado': True
                            })
        except Exception as e:
            print(f"    [Aviso UY UdelaR] {e}")

    # B. Anuario Estadistico de Educacion 2024 (Cuadro II-7.1.1 con todas las universidades)
    p_uy = paths['data_raw'] / 'uruguay' / 'Anuario Estadístico de Educación 2024.xlsx'
    if p_uy.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(p_uy, data_only=True)
            sheet = wb['II-7.1.1    ']
            deptos = ['CERRO LARGO', 'COLONIA', 'DURAZNO', 'MALDONADO', 'PAYSANDÚ', 'RIVERA', 'ROCHA', 'SALTO', 'SAN JOSÉ', 'SORIANO', 'TACUAREMBÓ', 'TREINTA Y TRES', 'CANELONES', 'FLORIDA', 'FLORES', 'LAVALLEJA', 'RÍO NEGRO', 'ARTIGAS']
            for r in range(12, 70):
                name = sheet.cell(r, 1).value
                egr = sheet.cell(r, 8).value
                if name and egr is not None:
                    n_clean = str(name).strip().replace('*', '').strip()
                    if any(k in n_clean.upper() for k in ['TOTAL', 'PÚBLICO', 'PRIVADO', 'MONTEVIDEO', 'RESTO DEL PAÍS', 'DEPARTAMENTO']) or len(n_clean) == 0:
                        continue
                    if n_clean.upper() in deptos:
                        continue
                    # Desduplicar UdelaR: la serie continua UY_UDELAR_SERIE ya cubre a la UdelaR (Decision Etapa 4 Item 4.1)
                    if any(k in n_clean.upper() for k in ['UDELAR', 'REPUBLICA', 'REPÚBLICA']):
                        continue
                    val = pd.to_numeric(egr, errors='coerce')
                    if pd.notna(val) and val >= 0:
                        tipo_g = 'publica' if any(k in n_clean.upper() for k in ['UTEC', 'MILITAR', 'POLICÍA']) else 'privada'
                        inst_norm = normalizar_nombre_institucion(n_clean, 'URY')
                        for yr_u in [2022, 2024]:  # Año comun 2022 para ranking regional y ano 2024 nacional
                            registros.append({
                                'pais': 'URY',
                                'fuente_id': 'UY_MEC_ANUARIO',
                                'institucion': inst_norm,
                                'tipo_gestion': tipo_g,
                                'tipo_institucion': 'universidad',
                                'sector': 'Total Universitario',
                                'anio': yr_u,
                                'graduados': float(val),
                                'es_observado': True
                            })
            wb.close()
        except Exception as e:
            print(f"    [Aviso UY] Extraccion institucional MEC: {e}")

    df_inst = pd.DataFrame(registros)
    if not df_inst.empty:
        df_inst = df_inst.groupby(['pais', 'fuente_id', 'institucion', 'tipo_gestion', 'tipo_institucion', 'sector', 'anio', 'es_observado'], as_index=False)['graduados'].sum()
        df_inst.to_csv(cache_inst, index=False, encoding='utf-8')
        df_inst.to_csv(paths['output'] / 'hecho_instituciones_egresados.csv', index=False, encoding='utf-8')
        print(f"  ✅ hecho_instituciones_egresados.csv generado ({len(df_inst):,} registros, {df_inst['institucion'].nunique()} universidades).")
    return df_inst


def calcular_factores_ppa(paths):
    ruta_wb = resolver_ruta_archivo('wb_macro_indicadores.csv', paths['data_raw'], paths['data_processed'])
    if not ruta_wb or not ruta_wb.exists():
        print("  ⚠️ wb_macro_indicadores.csv no encontrado en data_raw. Ejecuta primero la Etapa 01.")
        return pd.DataFrame()

    df_wb = pd.read_csv(ruta_wb)
    # Decision D1 (Etapa 3 Item 3.2): Definicion unica y homogenea PA.NUS.PPP (PPA del PIB)
    df_ppa = df_wb[df_wb['indicador_codigo'] == 'PA.NUS.PPP'][['pais', 'anio', 'valor']].rename(columns={'valor': 'factor_ppa'})
    df_ipc_wb = df_wb[df_wb['indicador_codigo'] == 'FP.CPI.TOTL'][['pais', 'anio', 'valor']].rename(columns={'valor': 'ipc_wb'})

    # Ingesta/Lectura del IPC Oficial de Argentina (INDEC serie 145.3_INGNACNAL_DICI_M_15)
    df_indec_anual = pd.DataFrame()
    ruta_indec_csv = paths['data_raw'] / 'argentina' / 'indec_ipc_nacional.csv'
    ruta_indec_json = paths['data_raw'] / 'argentina' / 'indec_ipc_nacional.json'

    if ruta_indec_csv.exists():
        try:
            df_indec_raw = pd.read_csv(ruta_indec_csv)
            df_indec_anual = df_indec_raw.groupby(['pais', 'anio'], as_index=False)['ipc_indec'].mean()
        except Exception:
            pass
    elif ruta_indec_json.exists():
        try:
            with open(ruta_indec_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            registros = [{'pais': 'ARG', 'anio': int(r[0].split('-')[0]), 'ipc_indec': float(r[1])} for r in data.get('data', [])]
            df_indec_anual = pd.DataFrame(registros).groupby(['pais', 'anio'], as_index=False)['ipc_indec'].mean()
        except Exception:
            pass

    # Si aun no existe el archivo local de INDEC, consultar API oficial
    if df_indec_anual.empty:
        try:
            url_indec = "https://apis.datos.gob.ar/series/api/series/?ids=145.3_INGNACNAL_DICI_M_15&limit=1000"
            r_indec = requests.get(url_indec, headers={'User-Agent': 'ObservatorioPredictivo/1.0'}, timeout=15)
            if r_indec.status_code == 200:
                data_indec = r_indec.json().get('data', [])
                reg_indec = [{'pais': 'ARG', 'anio': int(r[0].split('-')[0]), 'ipc_indec': float(r[1])} for r in data_indec]
                df_indec_anual = pd.DataFrame(reg_indec).groupby(['pais', 'anio'], as_index=False)['ipc_indec'].mean()
        except Exception as e:
            print(f"  ⚠️ No se pudo obtener IPC INDEC en línea: {e}")

    # Consolidar serie de IPC por pais
    filas_macro = []
    anios_todos = sorted(df_ppa['anio'].unique())

    # Valores base 2016 para armonizacion
    # INDEC: dic-2016 = 100.0 (en 2016 el promedio registrado es 100.0)
    # CHL: 2016 en WB = 122.884332371416
    # URY: 2016 en WB = 164.567097713453
    val_base_2016 = {
        'ARG': 100.0,
        'CHL': 122.884332371416,
        'URY': 164.567097713453
    }

    for p in ['ARG', 'CHL', 'URY']:
        for a in anios_todos:
            # Factor PPA
            sub_ppa = df_ppa[(df_ppa['pais'] == p) & (df_ppa['anio'] == a)]
            f_ppa = float(sub_ppa['factor_ppa'].iloc[0]) if not sub_ppa.empty else np.nan

            # IPC original y armonizado base 2016
            ipc_orig = np.nan
            fuente_ipc = ''
            base_orig = ''
            ipc_2016 = np.nan

            if p == 'ARG':
                sub_indec = df_indec_anual[(df_indec_anual['pais'] == 'ARG') & (df_indec_anual['anio'] == a)]
                if not sub_indec.empty:
                    ipc_orig = round(float(sub_indec['ipc_indec'].iloc[0]), 2)
                    fuente_ipc = 'INDEC (API Datos Abiertos)'
                    base_orig = 'dic-2016=100'
                    ipc_2016 = round((ipc_orig / val_base_2016['ARG']) * 100.0, 2)
            else:
                sub_wb = df_ipc_wb[(df_ipc_wb['pais'] == p) & (df_ipc_wb['anio'] == a)]
                if not sub_wb.empty:
                    ipc_orig = round(float(sub_wb['ipc_wb'].iloc[0]), 4)
                    fuente_ipc = 'Banco Mundial WDI'
                    base_orig = '2010=100'
                    if p in val_base_2016 and pd.notna(ipc_orig):
                        ipc_2016 = round((ipc_orig / val_base_2016[p]) * 100.0, 2)

            filas_macro.append({
                'pais': p,
                'anio': a,
                'factor_ppa': f_ppa,
                'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                'anio_base_ppa': 2025,
                'ipc_base_2016': ipc_2016,
                'ipc_original': ipc_orig,
                'fuente_ipc': fuente_ipc,
                'base_original_ipc': base_orig,
                'nota_metodologica': 'PPA del PIB adoptada por cobertura observada continua 2022-2024 (Consumo Privado discontinuado por BM para ARG post-2021). IPC armonizado base comun 2016=100.'
            })

    df_macro = pd.DataFrame(filas_macro).sort_values(['pais', 'anio'])

    archivo_macro = paths['output'] / 'factores_macro_ppa.csv'
    df_macro.to_csv(archivo_macro, index=False, encoding='utf-8')
    df_macro.to_csv(paths['data_processed'] / 'factores_macro_ppa.csv', index=False, encoding='utf-8')
    print(f"  ✅ Factores PPA exportados a: {archivo_macro.name} (Definición oficial: PIB PA.NUS.PPP + IPC armonizado base 2016=100)")
    return df_macro


def procesar_ilostat_salarios(paths, df_macro):
    """
    Procesa las series de salarios medios mensuales de asalariados de la OIT/ILOSTAT
    (EAR_EMTA_SEX_ECO_NB) para Argentina, Chile y Uruguay.
    Estandariza los sectores segun CIIU Rev. 4 / ISIC Rev. 4 y convierte a USD PPA.
    """
    mapa_isic4_sector = {
        'ECO_ISIC4_J': 'Tecnología',
        'ECO_ISIC4_M': 'Economía del conocimiento',
        'ECO_ISIC4_Q': 'Salud',
        'ECO_ISIC4_D': 'Energía',
        'ECO_ISIC4_I': 'Turismo',
    }
    monedas = {'ARG': 'ARS', 'CHL': 'CLP', 'URY': 'UYU'}
    carpeta_ilo = paths['data_raw'] / 'ilostat'
    registros = []

    for p in ['ARG', 'CHL', 'URY']:
        fpath = carpeta_ilo / f"EAR_EMTA_SEX_ECO_NB_{p}.csv"
        if not fpath.exists():
            continue
        try:
            df = pd.read_csv(fpath)
            sub = df[
                (df['classif1'].isin(mapa_isic4_sector.keys())) &
                (df['sex'].isin(['SEX_T', 'SEX_M', 'SEX_F'])) &
                (df['obs_value'].notna())
            ].copy()

            for _, r in sub.iterrows():
                sec = mapa_isic4_sector[r['classif1']]
                anio = int(r['time'])
                sex_raw = r['sex']
                sex_cod = 'T' if sex_raw == 'SEX_T' else ('M' if sex_raw == 'SEX_M' else 'F')
                val_moneda = float(r['obs_value'])

                ppa_rows = df_macro[(df_macro['pais'] == p) & (df_macro['anio'] == anio)]['factor_ppa'].values if not df_macro.empty else []
                if len(ppa_rows) > 0 and pd.notna(ppa_rows[0]) and ppa_rows[0] > 0:
                    f_ppa = float(ppa_rows[0])
                    sal_usd = round(val_moneda / f_ppa, 2)
                else:
                    f_ppa = np.nan
                    sal_usd = np.nan

                tipo_sal = 'medio_asalariados_total' if sex_cod == 'T' else ('medio_asalariados_varon' if sex_cod == 'M' else 'medio_asalariados_mujer')

                registros.append({
                    'pais': p,
                    'fuente_id': 'OIT_ILOSTAT',
                    'sector': sec,
                    'carrera_id': 'SEC_GENERICO',
                    'carrera_objetivo': f"Salario Medio Sectorial OIT ({sec})",
                    'anio': anio,
                    'sexo': sex_cod,
                    'salario_moneda_local': val_moneda,
                    'moneda_local': monedas.get(p, 'LCU'),
                    'factor_ppa': f_ppa,
                    'salario_usd_ppa': sal_usd,
                    'tipo_salario': tipo_sal,
                    'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                    'es_observado': True
                })
        except Exception as e:
            print(f"  ⚠️ Error procesando ILOSTAT para {p}: {e}")

    df_ilo = pd.DataFrame(registros)
    if not df_ilo.empty:
        df_ilo.to_csv(paths['data_processed'] / 'ilostat_salarios_cache.csv', index=False, encoding='utf-8')
        print(f"  ✅ ILOSTAT salarios armonizados: {len(df_ilo)} registros procesados (ARG, CHL, URY).")
    return df_ilo


def procesar_uruguay_laboral(paths):
    """
    Procesa el relevamiento oficial del INE Uruguay de ocupados por sexo y rama de actividad
    para derivar la participacion de mujeres (share_mujeres) por sector (Decisión T5.3 Opción A).
    """
    fpath = paths['data_raw'] / 'uruguay' / '10235_distribucion_porcentual_de_las_personas_ocupadas_segun_sexo_por_rama_de_actividad_en_ocupa.csv'
    if not fpath.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(fpath, encoding='latin-1')
        df.columns = ['sexo', 'rama', 'anio', 'valor']
        df['rama_clean'] = df['rama'].str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

        mapa = {
            'informatica y comunicacion': 'Tecnología',
            'actividades profesionales. cientificas y tecnicas': 'Economía del conocimiento',
            'servicios sociales y salud': 'Salud',
            'industria manufacturera. suministro de electricidad. gas y agua': 'Energía',
            'comercio por menor y por mayor; alojamiento y servicio de comida': 'Turismo'
        }
        df['sector'] = df['rama_clean'].map(mapa)
        df_valid = df.dropna(subset=['sector', 'valor']).copy()

        piv = df_valid.pivot_table(index=['sector', 'anio'], columns='sexo', values='valor', aggfunc='first').reset_index()
        piv['share_mujeres'] = (piv['Mujeres'] / (piv['Mujeres'] + piv['Varones'])).round(3)
        piv['pais'] = 'URY'
        piv['fuente_id'] = 'UY_INE_ECH'
        return piv[['pais', 'fuente_id', 'sector', 'anio', 'share_mujeres']]
    except Exception as e:
        print(f"  ⚠️ Error procesando empleo Uruguay: {e}")
        return pd.DataFrame()


def procesar_ilostat_empleo(paths):
    """
    Procesa las series oficiales de personas ocupadas de la OIT/ILOSTAT
    (EMP_TEMP_SEX_ECO_NB) para Argentina, Chile y Uruguay.
    Permite obtener share_mujeres observado por sector en los 3 paises para la ventana comun 2024 (Decision Etapa 1 Opcion B).
    """
    mapa_isic4_sector = {
        'ECO_ISIC4_J': 'Tecnología',
        'ECO_ISIC4_M': 'Economía del conocimiento',
        'ECO_ISIC4_Q': 'Salud',
        'ECO_ISIC4_D': 'Energía',
        'ECO_ISIC4_I': 'Turismo',
    }
    carpeta_ilo = paths['data_raw'] / 'ilostat'
    registros = []

    for p in ['ARG', 'CHL', 'URY']:
        fpath = carpeta_ilo / f"EMP_TEMP_SEX_ECO_NB_{p}.csv"
        if not fpath.exists():
            continue
        try:
            df = pd.read_csv(fpath)
            sub = df[
                (df['classif1'].isin(mapa_isic4_sector.keys())) &
                (df['sex'].isin(['SEX_T', 'SEX_M', 'SEX_F'])) &
                (df['obs_value'].notna())
            ].copy()
            sub['sector'] = sub['classif1'].map(mapa_isic4_sector)
            sub['anio'] = pd.to_numeric(sub['time'], errors='coerce')
            sub = sub.dropna(subset=['anio'])
            sub['anio'] = sub['anio'].astype(int)

            piv = sub.pivot_table(index=['sector', 'anio'], columns='sex', values='obs_value', aggfunc='first').reset_index()
            if 'SEX_F' in piv.columns and 'SEX_T' in piv.columns:
                piv['share_mujeres'] = (piv['SEX_F'] / piv['SEX_T']).round(4)
                piv['puestos_empleo'] = (piv['SEX_T'] * 1000).round(0)
                piv['pais'] = p
                piv['fuente_id'] = 'OIT_ILOSTAT'
                for _, r in piv.iterrows():
                    registros.append({
                        'pais': p,
                        'fuente_id': 'OIT_ILOSTAT',
                        'sector': r['sector'],
                        'anio': int(r['anio']),
                        'puestos_empleo': float(r['puestos_empleo']),
                        'share_mujeres': float(r['share_mujeres']),
                        'meses_observados': 12,
                        'empleabilidad_1er_anio': np.nan,
                        'es_observado': True
                    })
        except Exception as e:
            print(f"  ⚠️ Error procesando empleo ILOSTAT para {p}: {e}")

    df_emp = pd.DataFrame(registros)
    if not df_emp.empty:
        print(f"  ✅ ILOSTAT empleo armonizado (Opcion B): {len(df_emp)} registros procesados (ARG, CHL, URY).")
    return df_emp


def generar_reporte_contexto_educativo_laboral(paths):
    """
    Genera el reporte consolidado de contexto educativo y desempleo terciario
    cruzando datos 100% observados de Banco Mundial (SL.UEM.ADVN.ZS, SL.UEM.TOTL.ZS)
    y CEPALSTAT (Tasa de matrícula e inserción juvenil).
    """
    wb_file = paths['data_raw'] / 'wb_macro_indicadores.csv'
    if not wb_file.exists():
        wb_file = paths['data_processed'] / 'wb_macro_indicadores.csv'

    df_final = pd.DataFrame()
    if wb_file.exists():
        df_wb = pd.read_csv(wb_file)
        df_advn = df_wb[df_wb['indicador_codigo'] == 'SL.UEM.ADVN.ZS'][['pais', 'anio', 'valor']].rename(columns={'valor': 'tasa_desempleo_educ_terciaria_pct'})
        df_totl = df_wb[df_wb['indicador_codigo'] == 'SL.UEM.TOTL.ZS'][['pais', 'anio', 'valor']].rename(columns={'valor': 'tasa_desempleo_general_pct'})

        df_m = pd.merge(df_advn, df_totl, on=['pais', 'anio'], how='outer')
        df_m = df_m.dropna(subset=['anio']).sort_values(['pais', 'anio'])
        df_m['anio'] = df_m['anio'].astype(int)
        df_m = df_m[(df_m['anio'] >= 2010) & (df_m['anio'] <= 2025)]

        # Ratio de proteccion educativa (cuanto menor a 1, mayor es la proteccion frente al desempleo)
        df_m['ratio_desempleo_terciario_vs_total'] = (df_m['tasa_desempleo_educ_terciaria_pct'] / df_m['tasa_desempleo_general_pct']).round(3)
        df_m['diferencial_puntos_pct'] = (df_m['tasa_desempleo_educ_terciaria_pct'] - df_m['tasa_desempleo_general_pct']).round(2)

        def diagnostico_proteccion(r):
            rat = r.get('ratio_desempleo_terciario_vs_total')
            if pd.isna(rat):
                return 'Sin dato comparativo'
            if rat <= 0.40:
                return 'Protección Muy Alta (desempleo terciario <= 40% de la media general)'
            elif rat <= 0.70:
                return 'Protección Alta (desempleo terciario 40%-70% de la media general)'
            elif rat <= 0.90:
                return 'Protección Moderada (desempleo terciario 70%-90% de la media general)'
            else:
                return 'Protección Neutra/Baja (desempleo terciario cercano o superior a la media)'

        df_m['diagnostico_proteccion'] = df_m.apply(diagnostico_proteccion, axis=1)

        # Integrar CEPALSTAT si existe con anos observados
        cepal_file = paths['data_raw'] / 'cepalstat_indicadores.csv'
        if not cepal_file.exists():
            cepal_file = paths['data_processed'] / 'cepalstat_indicadores.csv'

        if cepal_file.exists():
            try:
                df_c = pd.read_csv(cepal_file)
                df_c = df_c.dropna(subset=['anio', 'valor'])
                if not df_c.empty:
                    df_c['anio'] = df_c['anio'].astype(int)
                    # Indicador 99: Matricula terciaria
                    c99 = df_c[df_c['indicador_id'].astype(str) == '99'].groupby(['pais', 'anio'], as_index=False)['valor'].mean().rename(columns={'valor': 'tasa_matricula_terciaria_pct'})
                    # Indicador 5701: Jovenes que estudian
                    c5701 = df_c[df_c['indicador_id'].astype(str) == '5701'].groupby(['pais', 'anio'], as_index=False)['valor'].mean().rename(columns={'valor': 'pct_jovenes_educ_superior_pct'})

                    df_m = pd.merge(df_m, c99, on=['pais', 'anio'], how='left')
                    df_m = pd.merge(df_m, c5701, on=['pais', 'anio'], how='left')
            except Exception:
                pass

        df_m['fuente'] = 'Banco Mundial (SL.UEM.ADVN.ZS / SL.UEM.TOTL.ZS) y CEPALSTAT'
        df_m['es_observado'] = True
        df_final = df_m

        out_file = paths['output'] / 'reporte_contexto_educativo_laboral.csv'
        df_final.to_csv(out_file, index=False, encoding='utf-8')
        df_final.to_csv(paths['data_processed'] / 'reporte_contexto_educativo_laboral.csv', index=False, encoding='utf-8')
        print(f"  ✅ Reporte de contexto educativo y desempleo terciario exportado a: {out_file.name} ({len(df_final)} filas)")
    return df_final


def ejecutar_limpieza(base_dir=None, force_rebuild=False):
    """
    Punto de entrada principal para Limpieza, Normalizacion y Exportacion.
    """
    paths = get_paths(base_dir)
    print("=" * 65)
    print("INICIANDO ETAPA 02: LIMPIEZA, ARMONIZACION Y EXPORTACION")
    print(f"Ruta Base:      {paths['base']}")
    print(f"Ruta Processed: {paths['data_processed']}")
    print(f"Ruta Output:    {paths['output']}")
    print(f"Force Rebuild:  {force_rebuild}")
    print("=" * 65)

    # 1. Exportar diccionarios maestros
    print("\n[Paso 1/5] Exportando dimensiones maestras...")
    dim_carrera = pd.DataFrame([{
        'carrera_id': c[0], 'carrera_objetivo': c[1], 'sector': c[2], 'cine_f_codigo': c[3], 'nivel_esperado': c[4]
    } for c in CARRERAS_OBJETIVO])
    dim_sector = pd.DataFrame([{
        'sector': s, 'ciiu_rev4_divisiones': '|'.join(divs)
    } for s, divs in SECTORES_CIIU.items()])
    puente_carrera_sector = pd.DataFrame([{
        'carrera_id': c[0], 'carrera_objetivo': c[1], 'sector': c[2], 'cine_f_codigo': c[3],
        'nivel_esperado': c[4], 'peso': 1.0, 'tipo_vinculo': 'principal',
        'autor': 'InnovaLab-DataAnalytics', 'fecha_validacion': '2026-10-24',
        'justificacion': f"Sector {c[2]} asignado segun clasificador estandar CINE-F {c[3]} y paridad de nivel {c[4]}"
    } for c in CARRERAS_OBJETIVO])

    for df_dict, fname in [(dim_carrera, 'dim_carrera.csv'), (dim_sector, 'dim_sector.csv'), (puente_carrera_sector, 'puente_carrera_sector.csv')]:
        df_dict.to_csv(paths['output'] / fname, index=False, encoding='utf-8')
        df_dict.to_csv(paths['data_processed'] / fname, index=False, encoding='utf-8')
    print("  ✅ Dimensiones carrera, sector y puente exportadas.")

    # 2. Procesar paises
    print("\n[Paso 2/5] Procesando datos de graduados por pais...")
    df_chl_egresados = procesar_chile(paths, force_rebuild=force_rebuild)
    df_chl_sies = procesar_chile_sies(paths, force_rebuild=force_rebuild)
    df_arg_egresados = procesar_argentina(paths, force_rebuild=force_rebuild)
    df_arg_laboral = procesar_argentina_laboral(paths, force_rebuild=force_rebuild)
    df_ury_egresados = procesar_uruguay(paths, force_rebuild=force_rebuild)

    # 3. Armonizacion PPA y salarios
    print("\n[Paso 3/5] Calculando factores PPA y salarios homologados...")
    df_macro = calcular_factores_ppa(paths)
    df_ilo_sal = procesar_ilostat_salarios(paths, df_macro)

    registros_salarios = []
    if not df_arg_laboral.empty:
        df_arg_sal = df_arg_laboral.copy()
        if not df_macro.empty:
            df_arg_sal = pd.merge(df_arg_sal, df_macro[df_macro['pais'] == 'ARG'][['anio', 'factor_ppa']], on='anio', how='left')
        else:
            df_arg_sal['factor_ppa'] = np.nan

        for _, r in df_arg_sal.iterrows():
            if pd.notna(r.get('w_mean')):
                registros_salarios.append({
                    'pais': 'ARG', 'fuente_id': 'AR_CEPXXI', 'sector': r['sector'],
                    'carrera_id': 'SEC_GENERICO', 'carrera_objetivo': f"Promedio Sectorial {r['sector']}",
                    'anio': int(r['anio']), 'sexo': 'T',
                    'salario_moneda_local': float(r['w_mean']), 'moneda_local': 'ARS',
                    'factor_ppa': float(r['factor_ppa']) if pd.notna(r['factor_ppa']) else np.nan,
                    'salario_usd_ppa': round(float(r['w_mean']) / float(r['factor_ppa']), 2) if pd.notna(r['factor_ppa']) and float(r['factor_ppa']) > 0 else np.nan,
                    'tipo_salario': 'medio_sectorial', 'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                    'es_observado': pd.notna(r.get('w_mean'))
                })
            if pd.notna(r.get('w_median')):
                registros_salarios.append({
                    'pais': 'ARG', 'fuente_id': 'AR_CEPXXI', 'sector': r['sector'],
                    'carrera_id': 'SEC_GENERICO', 'carrera_objetivo': f"Mediana Sectorial {r['sector']}",
                    'anio': int(r['anio']), 'sexo': 'T',
                    'salario_moneda_local': float(r['w_median']), 'moneda_local': 'ARS',
                    'factor_ppa': float(r['factor_ppa']) if pd.notna(r['factor_ppa']) else np.nan,
                    'salario_usd_ppa': round(float(r['w_median']) / float(r['factor_ppa']), 2) if pd.notna(r['factor_ppa']) and float(r['factor_ppa']) > 0 else np.nan,
                    'tipo_salario': 'mediano_sectorial', 'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                    'es_observado': pd.notna(r.get('w_median'))
                })

    if not df_chl_sies.empty:
        ppa_chl = df_macro[(df_macro['pais'] == 'CHL') & (df_macro['anio'] == 2024)]['factor_ppa'].values if not df_macro.empty else []
        if len(ppa_chl) == 0 or np.isnan(ppa_chl[0]):
            ppa_valid = df_macro[df_macro['pais'] == 'CHL'].dropna(subset=['factor_ppa']) if not df_macro.empty else pd.DataFrame()
            f_ppa_chl = ppa_valid.iloc[-1]['factor_ppa'] if not ppa_valid.empty else np.nan
        else:
            f_ppa_chl = ppa_chl[0]

        for _, r in df_chl_sies.iterrows():
            if pd.notna(r.get('salario_clp')):
                f_ppa_val = float(f_ppa_chl) if pd.notna(f_ppa_chl) else np.nan
                sal_usd = round(float(r['salario_clp']) / f_ppa_val, 2) if pd.notna(f_ppa_val) and f_ppa_val > 0 else np.nan
                registros_salarios.append({
                    'pais': 'CHL', 'fuente_id': 'CL_SIES', 'sector': r['sector'],
                    'carrera_id': r['carrera_id'], 'carrera_objetivo': r['carrera_objetivo'], 'anio': 2024,
                    'sexo': 'T',
                    'salario_moneda_local': float(r['salario_clp']), 'moneda_local': 'CLP',
                    'factor_ppa': f_ppa_val,
                    'salario_usd_ppa': sal_usd,
                    'tipo_salario': 'ingreso_1er_anio', 'metodo_ppa': 'PPA_PIB_PA.NUS.PPP',
                    'es_observado': pd.notna(r.get('salario_clp'))
                })

    # Anexar serie homogenea OIT_ILOSTAT
    if not df_ilo_sal.empty:
        for _, r in df_ilo_sal.iterrows():
            registros_salarios.append(r.to_dict())

    hecho_salario = pd.DataFrame(registros_salarios)
    hecho_salario.to_csv(paths['output'] / 'hecho_salario.csv', index=False, encoding='utf-8')
    hecho_salario.to_csv(paths['data_processed'] / 'hecho_salario.csv', index=False, encoding='utf-8')
    print(f"  ✅ hecho_salario.csv exportado exitosamente ({len(hecho_salario):,} filas en USD PPA del PIB).")

    # 4. Construccion de hecho_ocupacion_terciarios.csv y Contexto Macro-Educativo
    print("\n[Paso 4/5] Generando tabla de ocupacion terciarios y contexto macro-educativo...")
    registros_ocupacion = []

    # A. Chile SIES: empleabilidad observada de titulados por programa (fuente única de inserción laboral formal)
    if not df_chl_sies.empty:
        for _, r in df_chl_sies.iterrows():
            registros_ocupacion.append({
                'pais': 'CHL', 'fuente_id': 'CL_SIES', 'sector': r['sector'], 'anio': 2024,
                'puestos_empleo': np.nan, 'share_mujeres': np.nan,
                'meses_observados': np.nan,
                'empleabilidad_1er_anio': float(r['empleabilidad_1er_anio']) if pd.notna(r.get('empleabilidad_1er_anio')) else np.nan,
                'empleabilidad_2do_anio': float(r['empleabilidad_2do_anio']) if pd.notna(r.get('empleabilidad_2do_anio')) else np.nan,
                'es_observado': pd.notna(r.get('empleabilidad_1er_anio')) | pd.notna(r.get('empleabilidad_2do_anio'))
            })

    # B. Serie supranacional homologada de empleo y genero OIT/ILOSTAT para ARG, CHL y URY
    # (Reemplaza y sustituye formalmente a las series artesanales locales de CEP-XXI share_mujer y ECH Uruguay para garantizar paridad y eliminar duplicidades)
    df_ilo_emp = procesar_ilostat_empleo(paths)
    if not df_ilo_emp.empty:
        for _, r in df_ilo_emp.iterrows():
            registros_ocupacion.append({
                'pais': r['pais'], 'fuente_id': r['fuente_id'], 'sector': r['sector'], 'anio': int(r['anio']),
                'puestos_empleo': float(r['puestos_empleo']),
                'share_mujeres': float(r['share_mujeres']),
                'meses_observados': 12,
                'empleabilidad_1er_anio': np.nan,
                'empleabilidad_2do_anio': np.nan,
                'es_observado': True
            })

    hecho_ocupacion = pd.DataFrame(registros_ocupacion)
    hecho_ocupacion.to_csv(paths['output'] / 'hecho_ocupacion_terciarios.csv', index=False, encoding='utf-8')
    hecho_ocupacion.to_csv(paths['data_processed'] / 'hecho_ocupacion_terciarios.csv', index=False, encoding='utf-8')
    print(f"  ✅ hecho_ocupacion_terciarios.csv exportado exitosamente ({len(hecho_ocupacion):,} filas - 100% OIT/SIES sin duplicados locales).")

    # C. Reporte de contexto educativo y desempleo terciario (Banco Mundial y CEPALSTAT)
    generar_reporte_contexto_educativo_laboral(paths)

    # 5. Consolidacion de hecho_egresados.csv y dimensiones maestras
    print("\n[Paso 5/5] Consolidando hecho_egresados y auditoria de cobertura...")
    dfs_egresados = []
    if not df_chl_egresados.empty:
        dfs_egresados.append(df_chl_egresados)
    if not df_arg_egresados.empty:
        dfs_egresados.append(df_arg_egresados)
    if not df_ury_egresados.empty:
        dfs_egresados.append(df_ury_egresados)

    hecho_egresados = pd.concat(dfs_egresados, ignore_index=True) if dfs_egresados else pd.DataFrame()
    hecho_egresados.to_csv(paths['output'] / 'hecho_egresados.csv', index=False, encoding='utf-8')
    hecho_egresados.to_csv(paths['data_processed'] / 'hecho_egresados.csv', index=False, encoding='utf-8')
    print(f"  ✅ hecho_egresados.csv consolidado exportado ({len(hecho_egresados):,} filas).")

    # Instituciones oficiales observadas (Tanda 4)
    df_hecho_inst = procesar_instituciones_oficiales(paths, df_chl_egresados, force_rebuild=force_rebuild)

    # Dimensiones
    dim_pais = pd.DataFrame([('ARG', 'Argentina'), ('CHL', 'Chile'), ('URY', 'Uruguay')], columns=['pais_iso3', 'pais_nombre'])
    dim_sexo = pd.DataFrame([('T', 'Total ambos sexos'), ('F', 'Femenino'), ('M', 'Masculino'), ('NB', 'No binario / Indefinido'), ('NS', 'No informado')], columns=['sexo_codigo', 'sexo_descripcion'])
    anios_disponibles = sorted(hecho_egresados['anio'].unique()) if not hecho_egresados.empty else [2015, 2020, 2025]
    dim_tiempo = pd.DataFrame({'anio': anios_disponibles})

    for d_df, fname in [(dim_pais, 'dim_pais.csv'), (dim_sexo, 'dim_sexo.csv'), (dim_tiempo, 'dim_tiempo.csv')]:
        d_df.to_csv(paths['output'] / fname, index=False, encoding='utf-8')
        d_df.to_csv(paths['data_processed'] / fname, index=False, encoding='utf-8')

    # Auditoria de cobertura y paridad temporal
    resumen_cobertura = []
    for p in ['ARG', 'CHL', 'URY']:
        df_p = hecho_egresados[hecho_egresados['pais'] == p]
        for s in SECTORES_CIIU.keys():
            df_ps = df_p[df_p['sector'] == s]
            n_anios = df_ps['anio'].nunique()
            anios_lista = sorted(df_ps['anio'].unique()) if n_anios > 0 else []
            resumen_cobertura.append({
                'pais': p,
                'sector': s,
                'n_anios_observados': n_anios,
                'anio_min': int(df_ps['anio'].min()) if n_anios > 0 else np.nan,
                'anio_max': int(df_ps['anio'].max()) if n_anios > 0 else np.nan,
                'serie_anios': '|'.join(map(str, anios_lista)) if anios_lista else 'sin_datos',
                'ventana_comun_paritaria': '2018-2022',
                'elegible_proyeccion': n_anios >= 5,  # Decision D7: umbral estricto >= 5
                'estado': 'proyectable' if n_anios >= 5 else ('no_proyectable_serie_corta' if n_anios > 0 else 'sin_datos_observados')
            })

    informe_cobertura = pd.DataFrame(resumen_cobertura)
    informe_cobertura.to_csv(paths['output'] / 'informe_cobertura.csv', index=False, encoding='utf-8')
    informe_cobertura.to_csv(paths['data_processed'] / 'informe_cobertura.csv', index=False, encoding='utf-8')
    print(f"  ✅ informe_cobertura.csv exportado exitosamente ({len(informe_cobertura)} sectores auditados).")

    print("\n✅ ETAPA 02 (LIMPIEZA Y EXPORTACION) COMPLETADA CON EXITO.\n")
    return {
        'hecho_egresados': hecho_egresados,
        'hecho_instituciones': df_hecho_inst,
        'hecho_salario': hecho_salario,
        'hecho_ocupacion': hecho_ocupacion,
        'informe_cobertura': informe_cobertura
    }


if __name__ == '__main__':
    force = '--force' in sys.argv or '-f' in sys.argv
    ejecutar_limpieza(force_rebuild=force)
