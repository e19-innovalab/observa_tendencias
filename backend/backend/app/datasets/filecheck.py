"""Checks on whatever was uploaded, before reading it: is it really what its extension says?

xlsx files are zip archives: the archive must open, hold a workbook, carry no macros
(vbaProject.bin) and not grow beyond datasets.max_unzipped_bytes once unzipped (zip bombs).
csv files must be text in the profile's encoding, not a renamed Excel or a binary file.
"""
import io
import zipfile
from pathlib import Path

from app.core.config_files import app_config
from app.datasets.profiles import DatasetProfile

XLSX_REQUIRED = ("[Content_Types].xml", "xl/workbook.xml")
MACROS = "vbaProject.bin"
ZIP_MAGIC = b"PK\x03\x04"
SNIFF_BYTES = 8192


def _msg(key: str, **kw) -> str:
    return app_config().datasets.messages[key].format(**kw)


def check_file(content: bytes, file_name: str, profile: DatasetProfile) -> list[str]:
    """Problems that stop the file from being read at all (empty list: go on and read it)."""
    suffix = Path(file_name).suffix.lower()
    if suffix == ".xlsx":
        return _check_xlsx(content)
    if suffix == ".csv":
        return _check_csv(content, profile)
    return [_msg("unsupported_format", name=file_name)]


def _check_xlsx(content: bytes) -> list[str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        return [_msg("not_xlsx")]
    with archive:
        names = archive.namelist()
        if not all(n in names for n in XLSX_REQUIRED):
            return [_msg("not_xlsx")]
        if any(n.rsplit("/", 1)[-1] == MACROS for n in names):
            return [_msg("has_macros")]
        limit = app_config().datasets.max_unzipped_bytes
        if sum(i.file_size for i in archive.infolist()) > limit:
            return [_msg("unzipped_too_large", max_mb=round(limit / 1e6))]
    return []


def _check_csv(content: bytes, profile: DatasetProfile) -> list[str]:
    if content.startswith(ZIP_MAGIC):
        return [_msg("csv_is_excel")]
    if b"\x00" in content[:SNIFF_BYTES]:
        return [_msg("csv_binary")]
    encoding = profile.file.csv_encoding
    try:
        content.decode(encoding)
    except UnicodeDecodeError:
        return [_msg("csv_encoding", encoding=encoding.removesuffix("-sig").upper())]
    return []
