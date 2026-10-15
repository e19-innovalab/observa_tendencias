"""Alinea las exportaciones de ofertas de LinkedIn (Apify) con las etiquetas de informe_cobertura.csv.

    python data/scripts/build_ofertas_linkedin.py

Lee      data/raw/linkedin_jobs/*.csv  (un archivo por búsqueda de provincia)
Escribe  data/processed/data_analytics/ofertas_linkedin.csv

Las etiquetas de sector son exactamente las de informe_cobertura: Tecnología, Economía del
conocimiento, Salud, Energía y Turismo. Todo lo demás es "Otros". El sector se asigna primero
según la industria de LinkedIn de la empresa (como hace CIIU/ISIC) y, si no alcanza, según
palabras clave del título. `regla_clasificacion` registra cuál de las dos se aplicó, para poder
auditar el resultado.

Tecnología y Economía del conocimiento se superponen en CIIU/ISIC (J62-63). Acá cada oferta
recibe UNA sola etiqueta: industrias de TI -> Tecnología; servicios profesionales y de
conocimiento que no son de TI -> Economía del conocimiento.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1]
RAW = DATA / "raw" / "linkedin_jobs"
OUT = DATA / "processed" / "data_analytics" / "ofertas_linkedin.csv"

# Each file is one search; the province is the search, not parsed from free text.
FILE_PROVINCE = {
    "17-53-45": "Córdoba",
    "17-54-27": "Santa Fe",
    "17-56-13": "Buenos Aires",
}

# Order matters: first match wins (Salud/Energía/Turismo are narrower than the IT/knowledge sets).
INDUSTRY_RULES = [
    ("Salud", r"hospitals|health care|medical|pharmaceutical|biotech|nursing|wellness|health and human"),
    ("Energía", r"oil and gas|\boil\b|utilities|renewable|electric power|energy"),
    ("Turismo", r"hospitality|travel arrangements|airlines|aviation|restaurants|hotel|tourism"),
    ("Tecnología", r"it services|software development|technology, information|computer|"
                   r"data infrastructure|information services"),
    # ISIC M69-M75: legal, accounting, consulting, engineering/architecture, R&D, advertising, design
    ("Economía del conocimiento", r"business consulting|advertising|marketing services|"
                                  r"accounting|legal|law practice|research|architecture|"
                                  r"design services|professional services|public relations|"
                                  r"engineering services|market research"),
]
TITLE_RULES = [
    ("Salud", r"m[eé]dic|enfermer|farmac|kinesi|odont|cl[ií]nic|paciente|sanatorio|quir[uú]rgic"),
    ("Energía", r"energ[ií]a|petr[oó]le|solar|e[oó]lic|gas natural|hidr[aá]ulic"),
    ("Turismo", r"hotel|turism|gastronom|cocinero|mucam|viajes|chef"),
    ("Tecnología", r"developer|desarrollador|programador|devops|software|data engineer|"
                   r"data scientist|qa |sistemas|ciberseguridad|machine learning|\bit\b|cloud|"
                   r"fullstack|full stack|backend|frontend"),
    ("Economía del conocimiento", r"contador|contable|auditor|marketing|consultor|analista de datos|"
                                  r"business intelligence|\bbi\b|abogad|jur[ií]dic|investigaci|"
                                  r"dise[nñ]ad"),
]
OTROS = "Otros"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).lower()
    return text if text != "nan" else ""


def classify_sector(industries: str, title: str) -> tuple[str, str]:
    ind, ttl = _norm(industries), _norm(title)
    for sector, pattern in INDUSTRY_RULES:
        if re.search(pattern, ind):
            return sector, "industria"
    for sector, pattern in TITLE_RULES:
        if re.search(pattern, ttl):
            return sector, "titulo"
    return OTROS, "ninguna"


def province_from_file(path: Path) -> str:
    for stamp, province in FILE_PROVINCE.items():
        if stamp in path.name:
            return province
    raise ValueError(f"Unknown search file (add it to FILE_PROVINCE): {path.name}")


def build() -> pd.DataFrame:
    frames = []
    for path in sorted(RAW.glob("*.csv")):
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df["provincia"] = province_from_file(path)
        stamp = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})", path.name)
        df["scraped_at"] = f"{stamp[1]}T{stamp[2]}:{stamp[3]}:{stamp[4]}Z"
        frames.append(df)
    df = pd.concat(frames, ignore_index=True).drop_duplicates("id")

    sector = [classify_sector(i, t) for i, t in zip(df["industries"], df["title"], strict=True)]
    out = pd.DataFrame({
        "pais": "ARG",
        "provincia": df["provincia"],
        "sector": [s for s, _ in sector],
        "regla_clasificacion": [r for _, r in sector],
        "id": df["id"],
        "titulo": df["title"],
        "empresa": df["companyName"],
        "ubicacion": df["location"],
        "fecha_publicacion": df["postedAt"],
        "nivel_experiencia": df["seniorityLevel"],
        "tipo_empleo": df["employmentType"],
        "industria": df["industries"],
        "postulantes": df["applicantsCount"],
        "url": "https://www.linkedin.com/jobs/view/" + df["id"],
        "scraped_at": df["scraped_at"],
    })
    return out


def main() -> None:
    out = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"{len(out)} ofertas -> {OUT}")
    print(out.groupby(["provincia", "sector"]).size().unstack(fill_value=0).to_string())
    print(out["regla_clasificacion"].value_counts().to_string())


if __name__ == "__main__":
    main()
