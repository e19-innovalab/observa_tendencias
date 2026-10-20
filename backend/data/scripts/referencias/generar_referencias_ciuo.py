"""Genera las tablas de referencia de ocupaciones (CIUO-08 / ISCO-08) desde documentos oficiales.

    backend/backend/.venv/bin/python data/scripts/referencias/generar_referencias_ciuo.py
    backend/backend/.venv/bin/python data/scripts/referencias/generar_referencias_ciuo.py --carpeta /tmp/pdfs

Descarga los PDF de fuentes.yaml (o usa los que ya estén en --carpeta), extrae su texto y escribe:

- reference/ilo_genai_exposure.yaml: las 427 filas de la Tabla A1 de la OIT (WP 140).
- reference/isco08_occupations.yaml: las 436 ocupaciones de 4 dígitos con nombre en español
  (CIUO-08 de Uruguay) e inglés (OIT).
- reference/isco08_groups.yaml: los niveles de 1, 2 y 3 dígitos que usan esas ocupaciones.

Controla que la extracción reproduzca los totales del paper (fuentes.yaml -> controles) y no
escribe nada si alguno falla. Requiere pypdf (dependencia de desarrollo del backend).
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import yaml
from pypdf import PdfReader

AQUI = Path(__file__).resolve().parent
CONFIG = AQUI.parents[2] / "backend" / "config"
AGENTE = "ObservaTendencias/0.1 (generación de tablas de referencia)"


def descargar(url: str, destino: Path) -> Path:
    if not destino.exists():
        with urlopen(Request(url, headers={"User-Agent": AGENTE}), timeout=120) as r:
            destino.write_bytes(r.read())
    return destino


def texto_pdf(ruta: Path) -> list[str]:
    lineas = []
    for i, pagina in enumerate(PdfReader(ruta).pages):
        lineas.append(f"=== PAGE {i + 1} ===")
        lineas.extend((pagina.extract_text() or "").splitlines())
    return lineas


def tabla_a1(lineas: list[str], conf: dict) -> dict[str, dict]:
    """Filas de la Tabla A1: {código: {name_en, mean, sd, gradient}}.

    El texto del PDF parte nombres largos en varias líneas, a veces pega el nombre a la media
    ("Establishments0.12") y deja "Minimal" en la línea anterior a "Exposure": se une todo en un
    solo texto, se quitan encabezados y números de página, y se lee fila por fila."""
    inicio = next(i for i, ln in enumerate(lineas) if ln.strip().startswith(conf["inicio_tabla"]))
    fin = next(i for i in range(inicio, len(lineas)) if re.match(conf["fin_tabla"], lineas[i].strip()))
    partes = []
    for ln in lineas[inicio + 1:fin]:
        s = ln.strip()
        if (not s or s.startswith("=== PAGE") or re.match(r"^\d+\s+ILO Working Paper 140$", s)
                or s.startswith("Exposure 4-digit code") or s.startswith("X Table")):
            continue
        partes.append(s)
    texto = re.sub(r"(\D)(0\.\d)", r"\1 \2", " ".join(partes))
    texto = re.sub(r"\s+", " ", texto)
    fila = re.compile(r"(Gradient \d|Not Exposed|Minimal Exposure)?\s*\b(\d{4}) (.+?) "
                      r"(0\.\d+|0|1(?:\.0+)?) (0\.\d+|0)(?=\s|$)")
    return {m.group(2): {"name_en": m.group(3).strip(), "mean": float(m.group(4)),
                         "sd": float(m.group(5)), "gradient": m.group(1)}
            for m in fila.finditer(texto)}


def ciuo_uruguay(lineas: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """({código 4 dígitos: nombre}, {código 1-3 dígitos: nombre}) de la CIUO-08 de Uruguay.

    Los grupos están sangrados según su nivel (0, 1 o 2 espacios) y a veces el nombre sigue en
    las líneas siguientes; los números de página aparecen justo después de un salto de página."""
    ocupaciones, grupos = {}, {}
    for i, ln in enumerate(lineas):
        m4 = re.match(r"^\s*(\d{4})\s+(.+?)\s*$", ln)
        if m4 and m4.group(1) not in ocupaciones:
            ocupaciones[m4.group(1)] = re.sub(r"\s+", " ", m4.group(2)).strip()
            continue
        m = re.match(r"^( *)(\d{1,3})(?:\s+(\S.*?))?\s*$", ln)
        if not m or (i and lineas[i - 1].startswith("=== PAGE")):
            continue
        sangria, codigo, resto = len(m.group(1)), m.group(2), m.group(3)
        if sangria != len(codigo) - 1 or codigo in grupos:
            continue
        partes, j = ([resto] if resto else []), i + 1
        while not resto and j < len(lineas) and lineas[j].strip() and not re.match(r"^\s*\d", lineas[j]):
            partes.append(lineas[j].strip())
            j += 1
        nombre = re.sub(r"\s+", " ", " ".join(partes)).strip()
        if nombre and not re.match(r"^\d", nombre):
            grupos[codigo] = nombre
    return ocupaciones, grupos


def comillas(t: str) -> str:
    return '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'


ENCABEZADO_EXPOSICION = """# Exposure of occupations to generative AI (mean task score, 0-1; higher = more exposed).
# Source: Gmyrek, P., Berg, J., Kamiński, K., Konopczyński, F., Ładna, A., Nafradi, B.,
#   Rosłaniec, K., Troszyński, M. (2025). "Generative AI and Jobs: A Refined Global Index of
#   Occupational Exposure". ILO Working Paper 140 (Geneva, ILO). Annex, Table A1.
#   https://doi.org/10.54394/HETP0387 · https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf
# All 427 rows of Table A1 (Mean, SD, exposure gradient), extracted from the PDF text and
# checked against the paper: 427 occupations, 13 in Gradient 4, 112 exposed (Gradients 1-4).
# Exposure measures how much of an occupation's tasks generative AI could perform; it covers both
# automation and augmentation, so the index uses it as a proxy for automation risk (see
# analytics.yaml).
# Generated by data/scripts/referencias/generar_referencias_ciuo.py.

reference_year: 2025
# Publication month (the paper is dated "May / 2025"); used as the source update date.
published: "2025-05-01"
values:
"""

ENCABEZADO_OCUPACIONES = """# ISCO-08 / CIUO-08 unit groups (4 digits): the universe of occupations the index covers.
# name_es: CIUO-08 titles as published by Uruguay (Ministerio de Economía y Finanzas,
#   "Códigos de ocupación", CIUO-08 adaptation), https://www.gub.uy/ministerio-economia-finanzas/
#   sites/ministerio-economia-finanzas/files/2021-01/codigos_ocupacion_0.pdf
# name_en: ILO Working Paper 140 (2025), Annex Table A1 (see ilo_genai_exposure.yaml).
# Codes come from the union of both lists. name_es is null where the Uruguayan list omits the
# code; the English title is shown instead. Featured occupations (catalog.yaml) can override
# the display name.
# Generated by data/scripts/referencias/generar_referencias_ciuo.py.
# {n} codes.

occupations:
"""

ENCABEZADO_GRUPOS = """# ISCO-08 / CIUO-08 hierarchy above the unit groups: major groups (1 digit), sub-major groups
# (2 digits) and minor groups (3 digits). A 4-digit occupation code reads left to right, e.g.
# 2132 = 2 Profesionales científicos e intelectuales > 21 Profesionales de las ciencias y de la
# ingeniería > 213 Profesionales en ciencias biológicas > 2132 Agrónomos y afines.
# Source: CIUO-08 titles as published by Uruguay (Ministerio de Economía y Finanzas, "Códigos de
#   ocupación"), https://www.gub.uy/ministerio-economia-finanzas/sites/ministerio-economia-finanzas/files/2021-01/codigos_ocupacion_0.pdf
# Only the groups used by the catalog's occupations. 224 is missing from that list; it has a
# single unit group (2240) and takes its ILO title (Working Paper 140, Table A1).
# Generated by data/scripts/referencias/generar_referencias_ciuo.py.

groups:
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--carpeta", type=Path, default=AQUI / "_descargas",
                        help="dónde guardar o buscar los PDF (no se versiona)")
    parser.add_argument("--solo-controlar", action="store_true",
                        help="extrae y controla, pero no escribe los archivos")
    args = parser.parse_args()
    fuentes = yaml.safe_load((AQUI / "fuentes.yaml").read_text(encoding="utf-8"))
    docs, salidas = fuentes["documentos"], fuentes["salidas"]
    args.carpeta.mkdir(parents=True, exist_ok=True)

    oit = texto_pdf(descargar(docs["oit_wp140"]["url"], args.carpeta / "WP140_web.pdf"))
    uy = texto_pdf(descargar(docs["uruguay_ciuo08"]["url"], args.carpeta / "codigos_ocupacion.pdf"))
    a1 = tabla_a1(oit, docs["oit_wp140"])
    ocup_es, grupos = ciuo_uruguay(uy)

    control = docs["oit_wp140"]["controles"]
    gradientes = [v["gradient"] for v in a1.values()]
    resultados = {
        "ocupaciones": len(a1),
        "gradiente_4": gradientes.count("Gradient 4"),
        "expuestas": sum(1 for g in gradientes if g and g.startswith("Gradient")),
    }
    fallos = {k: (v, control[k]) for k, v in resultados.items() if v != control[k]}
    print("Tabla A1:", resultados, "| CIUO-08 Uruguay:", len(ocup_es), "ocupaciones,",
          len(grupos), "grupos")
    if fallos:
        sys.exit(f"Los controles no coinciden con el paper (obtenido, esperado): {fallos}")

    codigos = sorted(set(a1) | set(ocup_es))
    necesarios = {c[:n] for c in codigos for n in (1, 2, 3)}
    grupos = {k: v for k, v in grupos.items() if k in necesarios}
    faltan = sorted(necesarios - set(grupos), key=lambda c: (len(c), c))
    for codigo in list(faltan):
        hijos = [c for c in codigos if c.startswith(codigo)]
        if len(hijos) == 1 and hijos[0] in a1:  # grupo con una sola ocupación: toma su nombre OIT
            grupos[codigo] = a1[hijos[0]]["name_en"]
            faltan.remove(codigo)
    if faltan:
        sys.exit(f"Grupos sin nombre: {faltan}")
    if args.solo_controlar:
        print("Controles OK (no se escribió nada).")
        return

    with (CONFIG / salidas["exposicion"]).open("w", encoding="utf-8") as f:
        f.write(ENCABEZADO_EXPOSICION)
        for c in sorted(a1):
            v = a1[c]
            f.write(f'  "{c}": {{mean: {v["mean"]}, sd: {v["sd"]}, gradient: {comillas(v["gradient"])}}}'
                    f'  # {v["name_en"]}\n')
    with (CONFIG / salidas["ocupaciones"]).open("w", encoding="utf-8") as f:
        f.write(ENCABEZADO_OCUPACIONES.format(n=len(codigos)))
        for c in codigos:
            es = comillas(ocup_es[c]) if c in ocup_es else "null"
            en = comillas(a1[c]["name_en"]) if c in a1 else "null"
            f.write(f'  "{c}": {{name_es: {es}, name_en: {en}}}\n')
    with (CONFIG / salidas["grupos"]).open("w", encoding="utf-8") as f:
        f.write(ENCABEZADO_GRUPOS)
        for c in sorted(grupos, key=lambda c: (len(c), c)):
            f.write(f'  "{c}": {comillas(grupos[c])}\n')
    print("Escritos:", ", ".join(salidas.values()))


if __name__ == "__main__":
    main()
