"""Dataset profiles (config/datasets/*.yaml): how to find, read and check an official file."""
import re
import unicodedata
from functools import lru_cache
from typing import Any, Literal

import yaml
from pydantic import BaseModel

from app.core.config import settings

PROFILES_DIR = "datasets"


def normalize_text(text: Any) -> str:
    """Case-, accent- and whitespace-insensitive form used to compare headers."""
    t = unicodedata.normalize("NFD", str(text).casefold())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


class DownloadConf(BaseModel):
    link_pattern: str
    allowed_hosts: list[str]
    max_bytes: int
    # True for files updated in place under the same URL: download every time and compare the
    # checksum (the default skips the download when the linked URL has not changed).
    always_download: bool = False
    # One file per period, each on its own page: the landing page links the pages (this pattern,
    # with a "release" group), and link_pattern finds the file on each page. Links may be
    # relative. Releases before min_release are ignored (e.g. years without a spreadsheet).
    page_pattern: str | None = None
    min_release: str | None = None


class FileConf(BaseModel):
    format: Literal["xlsx", "csv", "auto"]
    sheet: str | None = None
    header_row: int = 1
    first_data_row: int = 2
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8-sig"
    # Number format of text cells, e.g. "1.475" with thousands "." and decimal ",".
    thousands_separator: str | None = None
    decimal_separator: str = "."


class PeriodConf(BaseModel):
    column: str
    formats: list[Literal["date", "month_abbr_yy"]]
    month_abbr: dict[str, int] = {}
    provisional_marker: str | None = None


class ColumnTarget(BaseModel):
    sector: str | None = None
    occupation: str | None = None
    total: bool = False
    # Empty cells are skipped instead of reported (e.g. a 12-month change has no value for the
    # first 12 months of the series).
    skip_empty: bool = False


class LongFormatConf(BaseModel):
    columns: dict[str, str]
    required: list[str]


class AggregateConf(BaseModel):
    """Row-per-record files: rows are added up by group columns and period."""
    period_column: str
    period_pattern: str
    value_column: str
    group_columns: dict[str, str]
    filters: dict[str, list[str]] = {}


class OutlineSheet(BaseModel):
    sheet: str  # sheet name, compared without surrounding spaces
    level: str  # stored as the graduates' level


class OutlineConf(BaseModel):
    """Report-style sheets with nested headings (institution > faculty > campus > career): the
    heading rows are bold and the item rows are not. Items with the same name are added up."""
    sheets: list[OutlineSheet]
    name_column: str  # column letter
    value_column: str
    title_rows: int  # rows at the top holding the title, where period_pattern is searched
    period_pattern: str  # regex with a "year" group
    total_pattern: str  # the first row whose name matches is the sheet total
    end_pattern: str  # reading stops at the first row whose name matches (e.g. "Fuente")
    missing_values: list[str] = []  # text values meaning "no data": the row is skipped
    # The items must add up to the sheet total; a relative gap up to this is a warning (some
    # sheets leave an item empty while its heading counts it), a larger one an error.
    max_total_gap: float = 0.0


class ExpectedConf(BaseModel):
    headers: list[str] | None = None
    first_period: str | None = None
    min_periods: int | None = None
    value_min: float | None = None
    value_max: float | None = None
    max_revision: float | None = None
    revision_grace_periods: int = 0


class DatasetProfile(BaseModel):
    dataset_code: str
    source: str
    title: str
    landing_page: str | None = None
    requires_declared_source: bool = False
    target: Literal["observations", "graduates"] = "observations"
    # series: each file holds the whole series and replaces what was loaded; period: each file
    # holds its own periods and replaces only those.
    target_scope: Literal["series", "period"] = "series"
    download: DownloadConf | None = None
    file: FileConf
    country: str | None = None
    indicator: str | None = None
    frequency: Literal["A", "Q", "M"] | None = None
    period: PeriodConf | None = None
    columns: dict[str, ColumnTarget] = {}
    long_format: LongFormatConf | None = None
    aggregate: AggregateConf | None = None
    outline: OutlineConf | None = None
    expected: ExpectedConf = ExpectedConf()

    @property
    def is_long(self) -> bool:
        return self.long_format is not None


@lru_cache
def profiles() -> dict[str, DatasetProfile]:
    folder = settings.config_dir / PROFILES_DIR
    out = {}
    for path in sorted(folder.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            profile = DatasetProfile.model_validate(yaml.safe_load(f))
        out[profile.dataset_code] = profile
    return out


def profile_for_source(source_code: str) -> list[DatasetProfile]:
    return [p for p in profiles().values() if p.source == source_code and p.download]
