"""Búsqueda por texto tolerante: cada palabra debe coincidir con el comienzo de una palabra del
nombre, en cualquier orden y sin importar tildes ("asesorar ganado" encuentra "Asesorar sobre
la productividad del ganado"). También sin importar plural ni género: se busca la raíz de cada
palabra ("enfermera" encuentra "enfermería", "desarrolladores" encuentra "Desarrollador/a").
Usa expresiones regulares que entienden Postgres y SQLite. La misma regla tiene el frontend en
src/lib/utils/search.ts."""

import re

from sqlalchemy import and_
from sqlalchemy.sql.elements import ColumnElement

MAX_TOKENS = 6
# vocal o eñe -> clase con sus variantes acentuadas
_ACCENTS = {"a": "[aáàä]", "e": "[eéèë]", "i": "[iíìï]", "o": "[oóòö]", "u": "[uúùü]", "n": "[nñ]", "c": "[cç]"}
_FOLD = str.maketrans("áàäéèëíìïóòöúùüñç", "aaaeeeiiiooouuunc")
# comienzo de palabra: inicio del texto o un separador (\b no significa lo mismo en Postgres y en Python)
_WORD_START = r"(^|[ (/,.;:'\"-])"
# terminaciones de plural y género que se sacan para buscar la raíz (la más larga primero), siempre
# que queden al menos MIN_STEM letras
_ENDINGS = ("es", "as", "os", "a", "o", "s")
MIN_STEM = 4


def tokens(q: str) -> list[str]:
    """Palabras de la búsqueda, en minúsculas, sin tildes ni signos."""
    words = re.sub(r"[^\w]+", " ", q.lower().translate(_FOLD)).split()
    return [w for w in words if w][:MAX_TOKENS]


def stem(word: str) -> str:
    """Raíz para buscar: "enfermeras" → "enfermer", "desarrolladores" → "desarrollador"."""
    for end in _ENDINGS:
        if word.endswith(end) and len(word) - len(end) >= MIN_STEM:
            return word[: -len(end)]
    return word


def token_pattern(token: str) -> str:
    return _WORD_START + "".join(_ACCENTS.get(ch, ch) for ch in token)


def text_match(column, q: str) -> ColumnElement[bool] | None:
    """Condición SQL: todas las palabras de q aparecen al comienzo de alguna palabra de column."""
    words = tokens(q)
    if not words:
        return None
    return and_(*(column.regexp_match(token_pattern(stem(w)), flags="i") for w in words))


def matches(text: str, q: str) -> bool:
    """La misma regla que text_match, en Python (para listas que no están en la base)."""
    words = tokens(q)
    return bool(words) and all(re.search(token_pattern(stem(w)), text, re.I) for w in words)


def alias_matches(q: str) -> list[tuple[str, str]]:
    """(nombre local, código CIUO) de los nombres locales que coinciden con la búsqueda, incluidos
    los códigos de "also". Nombres de app.yaml -> search.aliases_file."""
    from app.core.config_files import occupation_aliases

    out: list[tuple[str, str]] = []
    for a in occupation_aliases():
        if matches(a.term, q):
            out += [(a.term, code) for code in [a.code, *a.also] if (a.term, code) not in out]
    return out
