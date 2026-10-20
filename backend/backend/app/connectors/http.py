"""Shared HTTP client with retries and exponential backoff (settings in config/sources.yaml)."""
import asyncio
import ssl
import time
from functools import lru_cache

import certifi
import httpx

from app.core.config import settings
from app.core.config_files import sources


@lru_cache
def ssl_context() -> ssl.SSLContext:
    """Standard CA bundle plus the extra intermediates in config (sources.yaml -> http)."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    for path in sources().http.extra_ca_files:
        ctx.load_verify_locations(cafile=str(settings.config_dir / path))
    return ctx


async def get_with_retry(
    client: httpx.AsyncClient, url: str, params: dict | None = None, headers: dict | None = None
) -> httpx.Response:
    conf = sources().http
    last_error: Exception | None = None
    for attempt in range(conf.retries):
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if attempt < conf.retries - 1:
                await asyncio.sleep(conf.backoff_seconds * 2**attempt)
    raise last_error  # type: ignore[misc]


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=sources().http.timeout_seconds, follow_redirects=True,
                             verify=ssl_context())


def download_sync(url: str, max_bytes: int, headers: dict | None = None) -> bytes:
    """Download a file with retries, refusing anything larger than max_bytes."""
    conf = sources().http
    last_error: Exception | None = None
    for attempt in range(conf.retries):
        try:
            with httpx.Client(timeout=conf.timeout_seconds, follow_redirects=True,
                              verify=ssl_context()) as client:
                with client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError(f"file larger than {max_bytes} bytes")
                        chunks.append(chunk)
                    return b"".join(chunks)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if attempt < conf.retries - 1:
                time.sleep(conf.backoff_seconds * 2**attempt)
    raise last_error  # type: ignore[misc]
