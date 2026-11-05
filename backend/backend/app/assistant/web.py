"""Searching outside the observatory, only for questions about the experimental indicators
(app.yaml -> assistant.web_search).

The tool is not offered on any other topic, so the model cannot call it. What it returns is written
by third parties: it is data for the answer, never instructions, and each source goes back as a link.
"""
import json
from urllib.parse import urlparse

import httpx

from app.assistant.tools import ToolRun
from app.connectors.http import ssl_context
from app.core.config_files import WebSearchConf

SEARCH_NAMESPACE = 0  # articles


def on_topic(conf: WebSearchConf, words: list[str], page: str | None) -> bool:
    """The text (question and previous one, already folded into words) or the page is about an indicator."""
    from app.assistant.scripted import words as fold

    padded = f" {' '.join(words)} "
    return any(f" {' '.join(fold(w))} " in padded for w in conf.topic_words) or bool(
        page and any(page == p or page.startswith(f"{p}/") for p in conf.topic_pages))


async def search(conf: WebSearchConf, query: str) -> list[dict]:
    """[{title, url, extract}], best match first."""
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": query,
              "gsrnamespace": SEARCH_NAMESPACE, "gsrlimit": conf.max_results, "prop": "extracts|info",
              "exintro": 1, "explaintext": 1, "exlimit": conf.max_results, "inprop": "url", "redirects": 1}
    async with httpx.AsyncClient(timeout=conf.timeout_seconds, verify=ssl_context(),
                                 headers={"User-Agent": conf.user_agent}) as client:
        r = await client.get(conf.api_url, params=params)
        r.raise_for_status()
    pages = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    return [{"title": p["title"], "url": p["fullurl"], "extract": (p.get("extract") or "")[:conf.max_chars]}
            for p in pages if urlparse(p.get("fullurl", "")).hostname == conf.allowed_host]


async def run(conf: WebSearchConf, args: dict) -> ToolRun:
    query = str((args or {}).get("q") or "").strip()
    name = conf.tool.name
    if not query:
        return ToolRun(name, args or {}, False, "Faltan parámetros: q")
    try:
        items = await search(conf, query)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return ToolRun(name, {"q": query}, False, f"No se pudo buscar fuera del observatorio: {type(e).__name__}")
    data = {"fuente": conf.source_name, "resultados": items}
    links = [{"label": f"{conf.source_name}: {i['title']}", "href": i["url"]} for i in items]
    return ToolRun(name, {"q": query}, True, json.dumps(data, ensure_ascii=False), data, None, external_links=links)
