"""Skill profiles per source version, for the Reina Roja indicator (connector: skill_versions).

For every release listed in the source's options (config/sources.yaml) and every catalog ISCO-08
unit group, store what the source lists for it in that release:

- onet: O*NET's Technology Skills file of the release (downloaded once and kept under
  datasets.raw_dir), taken to ISCO-08 with the ESCO-O*NET-SOC 2019 crosswalk: a group's profile is
  every technology listed for an O*NET occupation mapped to it.
- esco: the ESCO skills of the group's ESCO occupations in that ESCO version (public API).

Releases already stored are not fetched again and nothing is ever deleted: each version is a
snapshot to compare with the next.
"""
import asyncio
import csv
import io
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config_files import SourceConf, app_config, catalog, sources
from app.models import SkillProfile
from app.skills.esco import fetch_all, skill_code


class SkillVersionsError(Exception):
    pass


def _raw_dir(conf: SourceConf) -> Path:
    path = app_config().datasets.path(app_config().datasets.raw_dir) / conf.options["raw_subdir"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download(url: str, target: Path) -> Path:
    """Download once: a file already there is the one used (and kept)."""
    if target.exists():
        return target
    http = sources().http
    with httpx.Client(timeout=http.timeout_seconds, headers={"User-Agent": http.user_agent},
                      follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    target.write_bytes(response.content)
    return target


def onet_to_isco(conf: SourceConf, groups: set[str]) -> dict[str, set[str]]:
    """O*NET-SOC 2019 code -> ISCO-08 unit groups of the catalog, from the ESCO crosswalk."""
    cw = conf.options["crosswalk"]
    path = _download(cw["url"], _raw_dir(conf) / Path(cw["url"]).name)
    rows = openpyxl.load_workbook(path, read_only=True).worksheets[0].iter_rows(values_only=True)
    header: list | None = None
    out: dict[str, set[str]] = defaultdict(set)
    for i, row in enumerate(rows, start=1):
        if i < cw["header_row"]:
            continue
        if header is None:
            header = list(row)
            continue
        isco = str(row[header.index(cw["isco_column"])] or "")[:4]
        onet = row[header.index(cw["onet_column"])]
        if onet and isco in groups:
            out[str(onet)].add(isco)
    return out


def onet_profiles(conf: SourceConf, release: dict, mapping: dict[str, set[str]]) -> dict[str, dict]:
    """ISCO group -> {item key: name} for one O*NET release (member and item_column can be set
    per release: O*NET renamed them in 31.0)."""
    o = conf.options
    tag = release["version"].replace(".", "_")
    member = release.get("member", o["member"]).format(tag=tag)
    column = release.get("item_column", o["item_column"])
    path = _download(o["url_template"].format(tag=tag), _raw_dir(conf) / f"db_{tag}_text.zip")
    with zipfile.ZipFile(path) as z, z.open(member) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        out: dict[str, dict] = defaultdict(dict)
        for row in reader:
            item = (row.get(column) or "").strip()
            for isco in mapping.get(row[o["code_column"]], ()):
                if item:
                    out[isco][item.casefold()] = item
    return out


def esco_profiles(conf: SourceConf, version: str, groups: list[str]) -> tuple[dict[str, dict], int]:
    """ISCO group -> {skill code: name} in one ESCO version, and how many ESCO occupations failed."""
    failed: list[str] = []
    results = asyncio.run(fetch_all(conf, groups, failed, version))
    listed = sum(r[3] for r in results)
    if listed and len(failed) / listed > conf.options["max_failed_share"]:
        raise SkillVersionsError(f"ESCO {version}: {len(failed)} de {listed} ocupaciones fallaron")
    return {code: {skill_code(uri): skill.name for uri, (skill, *_rest) in group.items()}
            for code, n, group, _ in results if n}, len(failed)


def run_skill_versions(session: Session, source_code: str) -> tuple[int, int, int]:
    """Store the releases not stored yet. Returns (releases loaded, profiles stored, ESCO
    occupations skipped because the API kept failing)."""
    conf = sources().get(source_code)
    groups = [o.occupation_code for o in catalog().occupations if not o.is_excluded]
    stored_versions = set(session.scalars(select(SkillProfile.version).where(
        SkillProfile.source_code == source_code).distinct()).all())
    pending = [r for r in conf.options["releases"] if r["version"] not in stored_versions]
    mapping = onet_to_isco(conf, set(groups)) if conf.options["kind"] == "onet" and pending else {}
    loaded = profiles = skipped = 0
    for release in pending:
        version = release["version"]
        if conf.options["kind"] == "onet":
            found = onet_profiles(conf, release, mapping)
        else:
            found, failed = esco_profiles(conf, version, groups)
            skipped += failed
        now = datetime.now(UTC)
        session.add_all(SkillProfile(
            source_code=source_code, version=version,
            released=date.fromisoformat(release["released"]), occupation_code=code, items=items,
            fetched_at=now) for code, items in found.items() if items)
        session.commit()  # one release at a time: a later failure keeps what was loaded
        loaded += 1
        profiles += sum(1 for items in found.values() if items)
    return loaded, profiles, skipped
