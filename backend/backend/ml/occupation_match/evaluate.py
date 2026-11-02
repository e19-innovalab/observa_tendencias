"""Compares ways of turning a search phrase into a CIUO-08 code, on testset.yaml.

Methods:
- lexical_ciuo: the app's current rule (every word starts a word, any order, no accents) over the
  CIUO titles only. This is what the search finds today.
- lexical_all: the same rule over every name in data/labels_es.jsonl (CIUO + ESCO). No model.
- each model in config.yaml (and models/occupation-match-es if train.py was run): meaning
  search; a code's score is its best-matching name.

Prints top-k accuracy and time per query, and saves results/<date>_<time>.json with every answer
(old results are kept).

Names equal to a test phrase are hidden from the index (evaluate.hide_test_phrases), so the score
measures words the method has not seen; --with-test-phrases shows what the app would answer.

Usage: .venv/bin/python evaluate.py [--only NAME ...] [--with-test-phrases]
"""
import argparse
import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).parent
CONF = yaml.safe_load((HERE / "config.yaml").read_text())
ACCENTS = {"a": "[aáàä]", "e": "[eéèë]", "i": "[iíìï]", "o": "[oóòö]", "u": "[uúùü]", "n": "[nñ]", "c": "[cç]"}


def _path(key: str) -> Path:
    return (HERE / CONF["paths"][key]).resolve()


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).lower()


def tokens(q: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", fold(q)) if t][:6]


def lexical(labels: list[dict], k: int):
    """The app's search rule (app/core/search.py), ranked like the frontend (lib/utils/search.ts)."""
    def search(q: str) -> list[str]:
        words = tokens(q)
        pats = [re.compile(r"(?<!\w)" + "".join(ACCENTS.get(ch, re.escape(ch)) for ch in w), re.I) for w in words]
        phrase = " ".join(words)
        best: dict[str, int] = {}
        for r in labels:
            if not all(p.search(r["label"]) for p in pats):
                continue
            t = fold(r["label"])
            score = 4 if t == phrase else 3 if t.startswith(phrase) else 2 if phrase in t else 1
            best[r["code"]] = max(best.get(r["code"], 0), score)
        return [c for c, _ in sorted(best.items(), key=lambda x: -x[1])][:k]
    return search


def semantic(name: str, labels: list[dict], k: int, qp: str, pp: str):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(name)
    t0 = time.perf_counter()
    emb = model.encode([pp + r["label"] for r in labels], batch_size=128, normalize_embeddings=True,
                       convert_to_tensor=True, show_progress_bar=False)
    print(f"  {len(labels)} nombres codificados en {time.perf_counter() - t0:.0f} s")
    codes = [r["code"] for r in labels]

    def search(q: str) -> list[str]:
        qv = model.encode(qp + q, normalize_embeddings=True, convert_to_tensor=True)
        sims = (emb @ qv).tolist()
        best: dict[str, float] = {}
        for code, s in zip(codes, sims):
            if s > best.get(code, -1.0):
                best[code] = s
        return [c for c, _ in sorted(best.items(), key=lambda x: -x[1])][:k]
    return search


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="evaluar solo estos métodos (nombre o parte del nombre)")
    ap.add_argument("--with-test-phrases", action="store_true", help="no ocultar del índice las frases de prueba")
    args = ap.parse_args()

    labels = [json.loads(line) for line in _path("labels").read_text().splitlines()]
    tests = yaml.safe_load(_path("testset").read_text())["queries"]
    hide = CONF["evaluate"]["hide_test_phrases"] and not args.with_test_phrases
    if hide:
        phrases = {fold(t["q"]).strip() for t in tests}
        before = len(labels)
        labels = [r for r in labels if fold(r["label"]).strip() not in phrases]
        print(f"{before - len(labels)} nombres iguales a frases de prueba ocultos del índice")
    ks = CONF["evaluate"]["top_k"]
    kmax = max(ks)

    methods = [("lexical_ciuo", lambda: lexical([r for r in labels if r["kind"] == "ciuo_title"], kmax)),
               ("lexical_all", lambda: lexical(labels, kmax))]
    for m in CONF["models"]:
        methods.append((m["name"], lambda m=m: semantic(m["name"], labels, kmax, m["query_prefix"], m["passage_prefix"])))
    trained = _path("trained_model")
    if trained.exists():
        t = CONF["train"]
        methods.append((f"trained:{trained.name}",
                        lambda: semantic(str(trained), labels, kmax, t["query_prefix"], t["passage_prefix"])))
    if args.only:
        methods = [(n, f) for n, f in methods if any(o in n for o in args.only)]

    report = {"run_at": datetime.now().isoformat(timespec="seconds"), "labels": len(labels),
              "queries": len(tests), "test_phrases_hidden": hide,
              "testset_reviewed": yaml.safe_load(_path("testset").read_text()).get("reviewed"),
              "methods": {}}
    print(f"{len(tests)} búsquedas, {len(labels)} nombres\n")
    for name, build in methods:
        print(name)
        search = build()
        hits = {k: 0 for k in ks}
        answers, times = [], []
        for t in tests:
            t0 = time.perf_counter()
            got = search(t["q"])
            times.append(time.perf_counter() - t0)
            rank = next((i + 1 for i, c in enumerate(got) if c in t["codes"]), None)
            for k in ks:
                hits[k] += rank is not None and rank <= k
            answers.append({"q": t["q"], "expected": t["codes"], "got": got, "rank": rank})
        acc = {f"top{k}": round(hits[k] / len(tests), 3) for k in ks}
        ms = 1000 * sum(times) / len(times)
        print("  " + "  ".join(f"top{k}: {hits[k]}/{len(tests)} ({hits[k] / len(tests):.0%})" for k in ks)
              + f"  · {ms:.1f} ms/búsqueda\n")
        report["methods"][name] = {"accuracy": acc, "ms_per_query": round(ms, 2), "answers": answers}

    out = _path("results") / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"Detalle → {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
