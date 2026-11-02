"""Builds data/labels_es.jsonl: every Spanish name we know for each CIUO-08 unit group.

Sources:
- config/reference/isco08_occupations.yaml: official CIUO-08 title (name_es) and "incluye" list.
- ESCO API (URL from config/sources.yaml): each group's ESCO occupations, with their preferred and
  alternative Spanish names. Raw responses are cached in data/esco_raw so reruns don't refetch.
- local_names.yaml: words used in Argentina, Chile and Uruguay that ESCO lacks (one row per code,
  including the "also" codes).

One JSON line per (code, label): {"code", "label", "kind", "source", "esco_uri"}.
kind: ciuo_title | ciuo_incluye | esco_preferred | esco_alternative | local.

Usage: .venv/bin/python build_data.py
"""
import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).parent
CONF = yaml.safe_load((HERE / "config.yaml").read_text())
ISCO_URI = "http://data.europa.eu/esco/isco/C{code}"


def _path(key: str) -> Path:
    return (HERE / CONF["paths"][key]).resolve()


def esco_base_url() -> str:
    sources = yaml.safe_load(_path("sources_config").read_text())
    entries = sources["sources"] if isinstance(sources, dict) else sources
    return next(s["base_url"] for s in entries if s["source_code"] == "esco")


async def fetch(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str, params: dict) -> dict:
    key = hashlib.sha1(json.dumps([url, params], sort_keys=True).encode()).hexdigest()
    cache = _path("esco_cache") / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    async with sem:
        for attempt in range(4):
            try:
                r = await client.get(url, params=params)
                r.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 3:
                    raise
                await asyncio.sleep(2 ** attempt)
    cache.write_text(r.text)
    return r.json()


async def esco_labels(codes: list[str]) -> list[dict]:
    base, lang = esco_base_url(), CONF["esco"]["language"]
    sem = asyncio.Semaphore(CONF["esco"]["concurrency"])
    _path("esco_cache").mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failed: list[str] = []
    async with httpx.AsyncClient(timeout=CONF["esco"]["timeout_seconds"]) as client:

        async def occupation(code: str, uri: str, seen: set[str]) -> None:
            if uri in seen:
                return
            seen.add(uri)
            try:
                d = await fetch(client, sem, f"{base}/resource/occupation", {"uri": uri, "language": lang})
            except httpx.HTTPError:
                failed.append(f"{code}:{uri.rsplit('/', 1)[-1]}")
                return
            pref = (d.get("preferredLabel") or {}).get(lang)
            if pref:
                rows.append({"code": code, "label": pref, "kind": "esco_preferred", "source": "esco", "esco_uri": uri})
            for alt in (d.get("alternativeLabel") or {}).get(lang, []):
                rows.append({"code": code, "label": alt, "kind": "esco_alternative", "source": "esco", "esco_uri": uri})
            # ESCO occupations can have narrower ESCO occupations (same ISCO group)
            await asyncio.gather(*(occupation(code, n["uri"], seen)
                                   for n in d.get("_links", {}).get("narrowerOccupation", [])))

        async def group(code: str) -> None:
            try:
                g = await fetch(client, sem, f"{base}/resource/concept",
                                {"uri": ISCO_URI.format(code=code), "language": lang})
            except httpx.HTTPError:
                failed.append(code)
                return
            seen: set[str] = set()
            await asyncio.gather(*(occupation(code, o["uri"], seen)
                                   for o in g.get("_links", {}).get("narrowerOccupation", [])))

        await asyncio.gather(*(group(c) for c in codes))
    if failed:
        print(f"ESCO: {len(failed)} pedidos fallaron: {', '.join(sorted(failed)[:20])}")
    return rows


def ciuo_labels() -> tuple[list[str], list[dict]]:
    ref = yaml.safe_load(_path("isco_reference").read_text())["occupations"]
    rows = []
    for code, o in ref.items():
        if o.get("name_es"):
            rows.append({"code": code, "label": o["name_es"], "kind": "ciuo_title", "source": "ciuo08", "esco_uri": None})
        for item in o.get("incluye") or []:
            rows.append({"code": code, "label": item, "kind": "ciuo_incluye", "source": "ciuo08", "esco_uri": None})
    return list(ref), rows


def local_labels() -> list[dict]:
    entries = yaml.safe_load(_path("local_names").read_text())["entries"]
    return [{"code": code, "label": e["term"], "kind": "local", "source": "local_names", "esco_uri": None}
            for e in entries for code in [e["code"], *e.get("also", [])]]


def main() -> None:
    codes, rows = ciuo_labels()
    rows += local_labels()
    rows += asyncio.run(esco_labels(codes))
    # same label for the same code only once (keep the first kind found)
    unique, seen = [], set()
    for r in rows:
        key = (r["code"], r["label"].strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(r)
    out = _path("labels")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in unique))
    by_kind: dict[str, int] = {}
    for r in unique:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    covered = len({r["code"] for r in unique})
    print(f"{len(unique)} nombres para {covered}/{len(codes)} códigos CIUO → {out.relative_to(HERE)}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(by_kind.items())))


if __name__ == "__main__":
    main()
