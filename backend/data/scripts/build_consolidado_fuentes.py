"""Cruza, limpia y consolida los datos de raw-noelia con las fuentes propias.

    python data/scripts/build_consolidado_fuentes.py [--raw-noelia CARPETA]

Lee      raw-noelia (por defecto ~/Downloads/raw-noelia; no se modifica ni se copia)
         data/raw/datasets/ (anuario_diu_argentina, indicadores_cti_argentina, mec_uruguay, mifuturo_chile)
Escribe  data/processed/consolidado_fuentes/
           inventario_fuentes.csv           qué está repetido, qué es nuevo y qué se decidió
           egresados_argentina_total.csv    anuario contra CTI, año por año
           egresados_por_universidad.csv    egresados de pregrado y grado por institución y año
           universidades_mas_egresados.csv  top 10 regional 2022 y top 10 por país en su último año
           laboral_argentina_clae2.csv      puestos, salarios y participación femenina por rama (CEP-XXI)
           empleabilidad_chile_carrera.csv  buscador SIES por carrera genérica
           empleabilidad_chile_institucion.csv  buscador SIES por carrera e institución
           controles.csv                    cada suma contra el total que publica la fuente

Comparación puntual: no toca la base de datos ni la aplicación, que carga estos egresados desde las
páginas oficiales (app/datasets/universities.py). Araucano no se consolida: son microdatos
individuales de origen sin confirmar.
"""
import argparse
import hashlib
import io
import re
import sys
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd

warnings.filterwarnings("ignore", message=".*DrawingML.*")

DATA = Path(__file__).resolve().parents[1]
RAW = DATA / "raw" / "datasets"
OUT = DATA / "processed" / "consolidado_fuentes"
DEFAULT_NOELIA = Path.home() / "Downloads" / "raw-noelia"

# CEP-XXI marks suppressed cells (statistical secrecy) with this value.
CEP_SUPPRESSED = -99
MISSING_TEXT = {"", "-", "s/d", "s/i", "n/a", "///", "None", "nan"}
RANKING_YEAR = 2022
TOP_N = 10
TOTAL_TOLERANCE = 0.02

# Sheet name -> (management, kind) and the patterns that identify each institution in the MEC
# yearbooks, where institution, faculty and program rows share one column.
MEC_INSTITUTIONS = [
    ("II-7.2.1", "publica", "universidad", r"^(TOTAL UDELAR|UdelaR)$", "Universidad de la República (UdelaR)"),
    ("II-7.2.1", "publica", "universidad", r"^(UNIVERSIDAD TECNOL[ÓO]GICA\s*-\s*UTEC|UTEC)$", "Universidad Tecnológica (UTEC)"),
    ("II-7.2.2", "privada", "universidad", r"^UCU$", "Universidad Católica del Uruguay (UCU)"),
    ("II-7.2.2", "privada", "universidad", r"^UNIVERSIDAD ORT URUGUAY$", "Universidad ORT Uruguay"),
    ("II-7.2.2", "privada", "universidad", r"^UNIVERSIDAD DE MONTEVIDEO$", "Universidad de Montevideo"),
    ("II-7.2.2", "privada", "universidad", r"^UNIVERSIDAD DE LA EMPRESA", "Universidad de la Empresa (UDE)"),
    ("II-7.2.2", "privada", "universidad", r"^UNIVERSIDAD CLAEH$", "Universidad CLAEH"),
]
MEC_INSTITUTE_SHEET = "II-7.2.3"
MEC_INSTITUTE_PATTERN = r"^(INST\b|INSTITUTO\b(?!.*/ CARRERA)|FUNDACI[ÓO]N\b|ESCUELA NACIONAL DE POLIC[ÍI]A)"
MEC_PUBLIC_INSTITUTE_PATTERN = r"MILITAR|POLIC[ÍI]A"
MEC_TOTAL_PATTERN = r"^TOTAL( PAÍS| UNIVERSIDADES P[ÚU]BLICAS)?$"
MEC_GRADUATES_COLUMN = 7
UDELAR = "Universidad de la República (UdelaR)"

# What was found for each file of raw-noelia (see docs/cruce_fuentes_noelia.md).
INVENTORY = [
    ("uruguay/00._educ_superior_datos.csv", "repetido", "indicadores_cti_argentina/*00._educ_superior_datos.csv",
     "no_consolidar", "Es Argentina, no Uruguay: el README y cleaning_02.py lo rotulan URY."),
    ("uruguay/Anuario Estadístico de Educación 2024.xlsx", "repetido", "mec_uruguay/*2024.xlsx",
     "usar_copia_propia", "Mismo archivo; se usa la copia propia."),
    ("chile/TITULADO_2007-2025_web_27_05_2026_E-1.xlsx", "repetido", "mifuturo_chile/*TITULADO*.xlsx",
     "usar_copia_propia", "Re-guardado; mismos datos celda por celda."),
    ("scraping/dataset_linkedin-jobs-scraper_2026-10-13_17-53-45-895.csv", "repetido", "../linkedin_jobs/",
     "usar_copia_propia", "Solo cambian los finales de línea."),
    ("scraping/dataset_linkedin-jobs-scraper_2026-10-13_17-54-27-392.csv", "repetido", "../linkedin_jobs/",
     "usar_copia_propia", "Solo cambian los finales de línea."),
    ("scraping/dataset_linkedin-jobs-scraper_2026-10-13_17-56-13-655.csv", "repetido", "../linkedin_jobs/",
     "usar_copia_propia", "Solo cambian los finales de línea."),
    ("argentina/anuario_csv_2020.zip", "parcial", "anuario_diu_argentina/*.zip",
     "control", "Mismo cuadro que el adelanto 2024; sirve para ver revisiones."),
    ("argentina/anuario_csv_2021.zip", "parcial", "anuario_diu_argentina/*.zip",
     "control", "Mismo cuadro que el adelanto 2024; sirve para ver revisiones."),
    ("argentina/anuario_csv_2022.zip", "parcial", "anuario_diu_argentina/*.zip",
     "consolidado", "Aporta 2012 y 2013; el adelanto 2024 empieza en 2014."),
    ("argentina/puestos_depto_priv_por_clae2.csv", "parcial", "sipa_argentina/*.xlsx",
     "consolidado", "Misma base que SIPA, con detalle por rama. Celdas suprimidas: no suman."),
    ("argentina/w_mean_privado_mensual_por_clae2.csv", "nuevo", "", "consolidado", ""),
    ("argentina/w_median_privado_mensual_por_clae2.csv", "nuevo", "", "consolidado", ""),
    ("argentina/share_mujer_privado_mensual_por_clae2.csv", "nuevo", "", "consolidado", ""),
    ("uruguay/1.Serie-Egresos-totales-Grado-por-Servicio-2000-2024.ods", "nuevo", "",
     "consolidado", "Serie principal de UdelaR; la del MEC es preliminar y se conserva al lado."),
    ("chile/Buscador_Empleabilidad_e_Ingresos_2024_2025_SIES.xlsx", "nuevo", "",
     "consolidado", "Falta confirmar de dónde se descargó."),
    ("chile/Buscador_Estadisticas_por_carrera_2024_2025_SIES.xlsx", "nuevo", "",
     "consolidado", "Falta confirmar de dónde se descargó."),
    ("argentina/base_araucano_traducida.xlsx", "nuevo", "",
     "no_consolidar", "Microdatos individuales de origen sin confirmar; no es un censo."),
    ("uruguay/10235_distribucion_porcentual_de_las_personas_ocupadas_segun_sexo_por_rama_de_actividad_en_ocupa.csv",
     "nuevo", "", "no_consolidar", "2012-2017 en porcentajes; fuentes.yaml de Noelia ya lo descarta."),
]


def to_number(value):
    """Published number or None; '-', 's/d' and the like mean there is no data."""
    if value is None or str(value).strip() in MISSING_TEXT:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return pd.to_numeric(str(value).strip().replace(".", "").replace(",", "."), errors="coerce")


def clean_name(value) -> str:
    return re.sub(r"\s+", " ", str(value).replace("*", "")).strip()


def tidy_yearbook_table(rows: list[list], management: str, source: str, file: str) -> pd.DataFrame:
    """One row per institution and year from an 'Institución | 2014 | 2015 ...' yearbook table.

    The 'Total ...' rows are kept apart: each one names the kind of the institutions below it.
    """
    records, kind = [], None
    years = rows[0]
    for row in rows[1:]:
        name = clean_name(row[0])
        if not name or name == "nan":
            continue
        if name.lower().startswith("total"):
            lowered = name.lower()
            if "institutos" in lowered:
                kind = "instituto universitario"
            elif "universidades" in lowered:
                kind = "universidad"
            continue
        for year, value in zip(years[1:], row[1:]):
            number = to_number(value)
            if year is not None and number is not None and pd.notna(number):
                records.append({
                    "pais": "ARG", "institucion": name, "gestion": management, "tipo_institucion": kind,
                    "anio": int(year), "nivel": "Pregrado y grado", "egresados": number,
                    "fuente": source, "archivo": file, "estado": "observado", "es_principal": True,
                })
    return pd.DataFrame(records)


def read_adelanto_tables(zip_path: Path) -> dict[str, list[list]]:
    """Cuadros 2.1.4 and 2.2.4 (graduates by institution) of the DIU yearbook advance."""
    tables = {}
    archive = zipfile.ZipFile(zip_path)
    for management, part, sheet in (("publica", "Z 2.1", "C 2.1.4"), ("privada", "Z 2.2", "C2.2.4")):
        name = next(n for n in archive.namelist() if n.startswith(part))
        workbook = openpyxl.load_workbook(io.BytesIO(archive.read(name)), read_only=True, data_only=True)
        all_rows = list(workbook[sheet].iter_rows(values_only=True))
        title = next(str(c) for r in all_rows for c in r if c)
        if "egresad" not in title.lower():
            raise ValueError(f"{sheet}: se esperaba el cuadro de egresados, dice: {title}")
        start = next(i for i, r in enumerate(all_rows) if any(isinstance(c, (int, float)) and 2000 < c < 2100 or str(c) == "2014" for c in r))
        columns = [i for i, c in enumerate(all_rows[start]) if str(c).split(".")[0].isdigit()]
        header = [None] + [int(str(all_rows[start][i]).split(".")[0]) for i in columns]
        first = next(i for i, c in enumerate(all_rows[start + 1]) if c is not None)
        body = [[r[first]] + [r[i] for i in columns] for r in all_rows[start + 1:] if r[first] is not None
                and not str(r[first]).startswith(("Fuente", "Nota", "(", "*"))]
        tables[management] = [header] + body
    return tables


def read_csv_table(archive: zipfile.ZipFile, name: str) -> list[list]:
    frame = pd.read_csv(io.BytesIO(archive.read(name)), sep="|", encoding="utf-8")
    year_columns = [c for c in frame.columns if re.fullmatch(r"_\d{4}", c)]
    header = [None] + [int(c[1:]) for c in year_columns]
    return [header] + frame[["nombre_corto"] + year_columns].values.tolist()


def argentina_universities(noelia: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """2014-2024 from the advance (latest revision), 2012-2013 from the 2022 yearbook."""
    adelanto = next((RAW / "anuario_diu_argentina").glob("*.zip"))
    tables = read_adelanto_tables(adelanto)
    frames, controls = [], []
    source = "Anuario Estadístico Universitario (DIU, Argentina)"
    for management, rows in tables.items():
        frame = tidy_yearbook_table(rows, management, source, adelanto.name)
        frames.append(frame)
        total_row = next(r for r in rows[1:] if clean_name(r[0]).startswith("Total Instituciones"))
        for year, published in zip(rows[0][1:], total_row[1:]):
            controls.append(control(f"ARG {management}: suma de instituciones", year,
                                    frame[frame.anio == year].egresados.sum(), to_number(published)))

    zip_2022 = noelia / "argentina" / "anuario_csv_2022.zip"
    archive = zipfile.ZipFile(zip_2022)
    for management, chapter, table in (("publica", "Estatal", "2_1_3"), ("privada", "Privado", "2_2_3")):
        rows = read_csv_table(archive, f"Anuario 2022/Capitulo 2 Pregrado Grado {chapter}/Cuadro_{table}.csv")
        frame = tidy_yearbook_table(rows, management, source, zip_2022.name)
        newest = frames[0 if management == "publica" else 1]
        # Same table in two yearbooks: how much the institution totals were revised afterwards.
        for year in sorted(set(frame.anio) & set(newest.anio)):
            controls.append(control(f"ARG {management}: anuario 2022 contra adelanto 2024", year,
                                    frame[frame.anio == year].egresados.sum(), newest[newest.anio == year].egresados.sum()))
        frames.append(frame[frame.anio < newest.anio.min()])
    return pd.concat(frames, ignore_index=True), pd.DataFrame(controls)


def chile_universities() -> pd.DataFrame:
    """Undergraduate degrees by university, added up across campuses and programs."""
    path = next((RAW / "mifuturo_chile").glob("*TITULADO*.xlsx"))
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = workbook.worksheets[0].iter_rows(values_only=True)
    header = [str(c).strip() for c in next(rows)]
    keep = [header.index(c) for c in ("AÑO", "TOTAL TITULACIONES", "CLASIFICACIÓN INSTITUCIÓN NIVEL 1",
                                      "CLASIFICACIÓN INSTITUCIÓN NIVEL 2", "NOMBRE INSTITUCIÓN", "NIVEL GLOBAL")]
    frame = pd.DataFrame([[r[i] for i in keep] for r in rows],
                         columns=["anio", "egresados", "tipo", "gestion", "institucion", "nivel"])
    frame = frame[(frame.tipo == "Universidades") & (frame.nivel == "Pregrado")]
    frame["anio"] = frame.anio.astype(str).str.extract(r"(\d{4})")[0].astype(int)
    frame["egresados"] = pd.to_numeric(frame.egresados, errors="coerce").fillna(0)
    frame["institucion"] = frame.institucion.map(clean_name)
    out = frame.groupby(["institucion", "gestion", "anio", "nivel"], as_index=False).egresados.sum()
    return out.assign(pais="CHL", tipo_institucion="universidad", fuente="Mi Futuro, titulados (SIES, MINEDUC)",
                      archivo=path.name, estado="observado", es_principal=True)


def udelar_series(noelia: Path) -> pd.DataFrame:
    path = noelia / "uruguay" / "1.Serie-Egresos-totales-Grado-por-Servicio-2000-2024.ods"
    table_ns = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
    rows = []
    root = ET.fromstring(zipfile.ZipFile(path).read("content.xml"))
    for row in root.iter(table_ns + "table-row"):
        cells = []
        for cell in row:
            repeat = int(cell.get(table_ns + "number-columns-repeated", "1"))
            cells.extend(["".join(cell.itertext()).strip()] * min(repeat, 40))
        rows.append(cells)
    header = next(r for r in rows if r and r[0].startswith("Área/servicio"))
    total = next(r for r in rows if r and r[0] == "TOTAL UNIVERSIDAD")
    records = [{
        "pais": "URY", "institucion": UDELAR, "gestion": "publica", "tipo_institucion": "universidad",
        "anio": int(year), "nivel": "Grado", "egresados": to_number(value),
        "fuente": "Serie de egresos de grado (UdelaR)", "archivo": path.name, "estado": "observado", "es_principal": True,
    } for year, value in zip(header[1:], total[1:]) if year.isdigit()]
    return pd.DataFrame(records)


def uruguay_universities(noelia: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Each year from that year's own MEC yearbook; UdelaR's own series is the main one for UdelaR."""
    records, controls = [], []
    for path in sorted((RAW / "mec_uruguay").glob("*.xlsx")):
        year = int(re.search(r"(20\d\d)(?:_0)?\.xlsx$", path.name).group(1))
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheets = {w.title.strip(): list(w.iter_rows(values_only=True)) for w in workbook.worksheets
                  if w.title.strip() in ("II-7.2.1", "II-7.2.2", MEC_INSTITUTE_SHEET)}
        found = []
        for sheet, management, kind, pattern, name in MEC_INSTITUTIONS:
            row = next((r for r in sheets[sheet] if r[0] and re.search(pattern, clean_name(r[0]))), None)
            if row is not None:
                found.append((sheet, management, kind, name, to_number(row[MEC_GRADUATES_COLUMN])))
        for row in sheets[MEC_INSTITUTE_SHEET]:
            if row[0] and re.search(MEC_INSTITUTE_PATTERN, clean_name(row[0])) and row[MEC_GRADUATES_COLUMN] is not None:
                name = clean_name(row[0])
                management = "publica" if re.search(MEC_PUBLIC_INSTITUTE_PATTERN, name) else "privada"
                found.append((MEC_INSTITUTE_SHEET, management, "instituto universitario", name,
                              to_number(row[MEC_GRADUATES_COLUMN])))
        for sheet, management, kind, name, value in found:
            if value is None:
                continue
            is_udelar = name == UDELAR
            records.append({
                "pais": "URY", "institucion": name, "gestion": management, "tipo_institucion": kind, "anio": year,
                "nivel": "Grado", "egresados": value, "fuente": "Anuario Estadístico de Educación (MEC, Uruguay)",
                "archivo": path.name, "estado": "preliminar" if is_udelar else "observado", "es_principal": not is_udelar,
            })
        for sheet, rows in sheets.items():
            total = next(r for r in rows if r[0] and re.fullmatch(MEC_TOTAL_PATTERN, clean_name(r[0])))
            added = sum(v for s, _, _, _, v in found if s == sheet and v is not None)
            controls.append(control(f"URY {sheet}: suma de instituciones", year, added, to_number(total[MEC_GRADUATES_COLUMN])))
    mec = pd.DataFrame(records)
    udelar = udelar_series(noelia)
    for _, row in mec[mec.institucion == UDELAR].iterrows():
        own = udelar[udelar.anio == row.anio].egresados.iloc[0]
        # Known gap, not an error: the yearbook prints preliminary figures; both are kept.
        controls.append(control("URY UdelaR: anuario MEC (preliminar) contra serie UdelaR", row.anio, row.egresados, own)
                        | {"resultado": "diferencia_conocida"})
    return pd.concat([mec, udelar], ignore_index=True), pd.DataFrame(controls)


def control(name: str, year, value, expected) -> dict:
    gap = (value / expected - 1) * 100 if expected else None
    return {"control": name, "anio": int(year), "valor": value, "esperado": expected,
            "dif_pct": None if gap is None else round(gap, 2),
            "resultado": "ok" if expected and abs(value / expected - 1) <= TOTAL_TOLERANCE else "revisar"}


def argentina_totals(universities: pd.DataFrame) -> pd.DataFrame:
    """Yearbook against the CTI file. The yearbook is used wherever it exists."""
    path = next((RAW / "indicadores_cti_argentina").glob("*00._educ_superior_datos.csv"))
    cti = pd.read_csv(path, sep=";", encoding="latin-1", dtype=str)
    cti = cti[(cti.TIPO_ALUMNO == "EGRESADOS") & cti.NIVEL_ACADEM.isin(["Grado", "Pregrado"])]
    cti["valor"] = pd.to_numeric(cti.VALOR.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    table = cti.pivot_table(index="ANIO", columns="NIVEL_ACADEM", values="valor", aggfunc="sum")
    table.index = table.index.astype(int)
    table = table.rename(columns={"Grado": "cti_grado", "Pregrado": "cti_pregrado"})
    table["cti_total"] = table.cti_grado + table.cti_pregrado
    arg = universities[universities.pais == "ARG"]
    yearbook = arg.pivot_table(index="anio", columns="gestion", values="egresados", aggfunc="sum")
    yearbook = yearbook.rename(columns={"publica": "anuario_estatal", "privada": "anuario_privado"})
    yearbook["anuario_total"] = yearbook.anuario_estatal + yearbook.anuario_privado
    out = yearbook.join(table, how="outer").sort_index().rename_axis("anio").reset_index()
    out["dif_cti_contra_anuario_pct"] = ((out.cti_total / out.anuario_total - 1) * 100).round(1)
    out["egresados_recomendado"] = out.anuario_total.fillna(out.cti_total)
    out["fuente_recomendada"] = out.anuario_total.notna().map({True: "anuario", False: "cti"})
    return out


def most_graduates(universities: pd.DataFrame, year: int = RANKING_YEAR, top: int = TOP_N) -> pd.DataFrame:
    """Universities with the most graduates: it measures size, not quality."""
    main = universities[universities.es_principal & (universities.tipo_institucion == "universidad")]
    columns = ["pais", "institucion", "gestion", "anio", "nivel", "egresados", "fuente"]
    regional = main[main.anio == year].nlargest(top, "egresados")[columns].assign(alcance="regional")
    regional["posicion"] = range(1, len(regional) + 1)
    national = []
    for country, group in main.groupby("pais"):
        latest = group[group.anio == group.anio.max()].nlargest(top, "egresados")[columns].assign(alcance="nacional")
        latest["posicion"] = range(1, len(latest) + 1)
        national.append(latest)
    return pd.concat([regional, *national], ignore_index=True)


def argentina_labor(noelia: Path) -> pd.DataFrame:
    folder = noelia / "argentina"
    jobs = pd.read_csv(folder / "puestos_depto_priv_por_clae2.csv")
    jobs["suprimido"] = jobs.puestos == CEP_SUPPRESSED
    jobs["puestos"] = jobs.puestos.where(~jobs.suprimido)
    out = jobs.groupby(["fecha", "clae2"], as_index=False).agg(
        puestos_informados=("puestos", "sum"), departamentos_suprimidos=("suprimido", "sum"))
    for file, column in (("w_mean_privado_mensual_por_clae2.csv", "w_mean"),
                         ("w_median_privado_mensual_por_clae2.csv", "w_median"),
                         ("share_mujer_privado_mensual_por_clae2.csv", "share_mujer")):
        frame = pd.read_csv(folder / file)
        frame[column] = frame[column].where(frame[column] != CEP_SUPPRESSED)
        out = out.merge(frame, on=["fecha", "clae2"], how="outer")
    return out.sort_values(["fecha", "clae2"])


def sies_tables(noelia: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The published columns, with their published names. 's/i' and 'n/a' become empty."""
    folder = noelia / "chile"
    def read(file: str, header_row: int) -> pd.DataFrame:
        rows = list(openpyxl.load_workbook(folder / file, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
        header = rows[header_row]
        keep = [i for i, c in enumerate(header) if c is not None]
        names = [clean_name(header[i]) for i in keep]
        if header_row > 0:
            # '1er año' alone says nothing: the group row above tells income from employability.
            groups = pd.Series(rows[header_row - 1], dtype=object).ffill()
            names = [f"{clean_name(groups[i])} | {clean_name(header[i])}" if pd.notna(groups[i]) else clean_name(header[i])
                     for i in keep]
        frame = pd.DataFrame([[r[i] for i in keep] for r in rows[header_row + 1:]], columns=names)
        frame = frame[pd.to_numeric(frame.iloc[:, 0], errors="coerce").notna()]
        return frame.replace(list(MISSING_TEXT - {""}), None).assign(procedencia="por_confirmar", archivo=file)
    by_career = read("Buscador_Estadisticas_por_carrera_2024_2025_SIES.xlsx", 1)
    by_institution = read("Buscador_Empleabilidad_e_Ingresos_2024_2025_SIES.xlsx", 0)
    return by_career, by_institution


def inventory(noelia: Path) -> pd.DataFrame:
    records = []
    for file, status, ours, decision, note in INVENTORY:
        path = noelia / file
        records.append({
            "archivo": file, "existe": path.exists(), "bytes": path.stat().st_size if path.exists() else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
            "estado": status, "equivalente_propio": ours, "decision": decision, "nota": note,
        })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-noelia", type=Path, default=DEFAULT_NOELIA)
    noelia = parser.parse_args().raw_noelia
    OUT.mkdir(parents=True, exist_ok=True)

    arg, arg_controls = argentina_universities(noelia)
    ury, ury_controls = uruguay_universities(noelia)
    universities = pd.concat([arg, chile_universities(), ury], ignore_index=True)
    columns = ["pais", "institucion", "gestion", "tipo_institucion", "anio", "nivel", "egresados",
               "fuente", "archivo", "estado", "es_principal"]
    universities = universities[columns].sort_values(["pais", "institucion", "anio", "fuente"])
    by_career, by_institution = sies_tables(noelia)
    controls = pd.concat([arg_controls, ury_controls], ignore_index=True)

    outputs = {
        "inventario_fuentes.csv": inventory(noelia),
        "egresados_argentina_total.csv": argentina_totals(universities),
        "egresados_por_universidad.csv": universities,
        "universidades_mas_egresados.csv": most_graduates(universities),
        "laboral_argentina_clae2.csv": argentina_labor(noelia),
        "empleabilidad_chile_carrera.csv": by_career,
        "empleabilidad_chile_institucion.csv": by_institution,
        "controles.csv": controls,
    }
    for name, frame in outputs.items():
        frame.to_csv(OUT / name, index=False, encoding="utf-8-sig")
        print(f"{name}: {len(frame):,} filas")
    review = controls[controls.resultado == "revisar"]
    print(f"Controles: {len(controls)}, a revisar: {len(review)}")
    if not review.empty:
        print(review.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
