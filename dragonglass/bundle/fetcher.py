from __future__ import annotations

import collections.abc
import logging
import pathlib
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = frozenset({"github.com", "objects.githubusercontent.com"})
_REPO = "antolu/dragonglass"
_RELEASE_BASE = f"https://github.com/{_REPO}/releases/download"
_CHUNK_SIZE = 65536


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"only https URLs allowed, got scheme {parsed.scheme!r}")
    if parsed.hostname not in _ALLOWED_HOSTS:
        raise ValueError(
            f"host {parsed.hostname!r} not in allowed hosts {_ALLOWED_HOSTS}"
        )


def build_manifest_url(tag: str) -> str:
    return f"{_RELEASE_BASE}/{tag}/manifest.json"


def build_bundle_url(tag: str, filename: str) -> str:
    return f"{_RELEASE_BASE}/{tag}/{filename}"


def fetch_bytes(url: str) -> bytes:
    _validate_url(url)
    logger.info("fetching %s", url)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def fetch_to_file(
    url: str,
    dest: pathlib.Path,
    progress: collections.abc.Callable[[int, int], None] | None = None,
) -> pathlib.Path:
    _validate_url(url)
    logger.info("downloading %s → %s", url, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        received = 0
        with dest.open("wb") as f:
            while True:
                chunk = resp.read(_CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
                if progress:
                    progress(received, total)
    logger.info("download complete %s (%d bytes)", dest.name, received)
    return dest
