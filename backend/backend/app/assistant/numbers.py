"""Numbers check: every number in the answer must appear in the data the tools returned.

Numbers in the answer are read in Spanish or English notation ("1.068,27", "1068.27", "64,5 %");
"1.068" is ambiguous, so both readings are tried. A number matches a value from the data when it
is within the relative tolerance, or when the value is a share (0.64) and the number its
percentage (64). Small whole numbers and years are skipped (app.yaml -> numbers_check).
"""
import re

from app.core.config_files import NumbersCheckConf

NUMBER = re.compile(r"(?<![\w.,])\d[\d.,]*\d|(?<![\w.,])\d")


def readings(token: str) -> set[float]:
    """Possible values of a number as written."""
    t = token.strip(".,")
    out = set()
    if "," in t and "." in t:  # the last separator is the decimal one
        dec, thou = (",", ".") if t.rfind(",") > t.rfind(".") else (".", ",")
        candidates = [t.replace(thou, "").replace(dec, ".")]
    elif "," in t:
        candidates = [t.replace(",", "."), t.replace(",", "")]
    elif t.count(".") == 1:
        candidates = [t, t.replace(".", "")]
    else:
        candidates = [t.replace(".", "")]
    for c in candidates:
        try:
            out.add(float(c))
        except ValueError:
            pass
    return out


def answer_numbers(text: str) -> list[str]:
    return NUMBER.findall(text)


def data_values(data, out: set[float] | None = None) -> set[float]:
    """Every number in the tool results, also numbers written inside strings (labels, periods)."""
    out = set() if out is None else out
    if isinstance(data, bool) or data is None:
        return out
    if isinstance(data, (int, float)):
        out.add(float(data))
    elif isinstance(data, str):
        for tok in answer_numbers(data):
            out |= readings(tok)
    elif isinstance(data, dict):
        for v in data.values():
            data_values(v, out)
    elif isinstance(data, list):
        for v in data:
            data_values(v, out)
    return out


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= max(tol * abs(b), 0.051)


def unverified(answer: str, values: set[float], conf: NumbersCheckConf, also_allowed: str = "") -> list[str]:
    """Numbers in the answer that match nothing in the data (nor in also_allowed, e.g. the question)."""
    allowed = data_values(also_allowed)
    lo, hi = conf.year_range
    bad = []
    for tok in answer_numbers(answer):
        reads = readings(tok)
        if not reads:
            continue
        if any(r == int(r) and (r <= conf.ignore_up_to or lo <= r <= hi) for r in reads):
            continue
        ok = any(_close(r, v, conf.tolerance) or _close(r, v * 100, conf.tolerance)
                 for r in reads for v in values | allowed)
        if not ok:
            bad.append(tok)
    return bad
