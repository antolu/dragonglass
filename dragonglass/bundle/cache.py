from __future__ import annotations

import logging
import pathlib
import shutil

from dragonglass import paths

logger = logging.getLogger(__name__)

_DEFAULT_BUNDLE_ROOT = paths.CACHE_DIR / "bundles"
_DEFAULT_MARKER = paths.CACHE_DIR / "installed_bundle_version.txt"


def get_cached_bundle(
    version: str,
    filename: str,
    *,
    bundle_root: pathlib.Path = _DEFAULT_BUNDLE_ROOT,
) -> pathlib.Path | None:
    path = bundle_root / version / filename
    if path.exists():
        logger.debug("cache hit %s", path)
        return path
    logger.debug("cache miss %s", path)
    return None


def store_bundle(
    src: pathlib.Path,
    version: str,
    *,
    bundle_root: pathlib.Path = _DEFAULT_BUNDLE_ROOT,
) -> pathlib.Path:
    dest_dir = bundle_root / version
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    logger.info("cached bundle %s → %s", src.name, dest)
    return dest


def get_installed_bundle_version(
    *,
    marker_path: pathlib.Path = _DEFAULT_MARKER,
) -> str | None:
    try:
        return marker_path.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def set_installed_bundle_version(
    version: str,
    *,
    marker_path: pathlib.Path = _DEFAULT_MARKER,
) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(version, encoding="utf-8")
    logger.info("set installed bundle version → %s", version)


def cleanup_old_versions(
    keep: int = 2,
    *,
    bundle_root: pathlib.Path = _DEFAULT_BUNDLE_ROOT,
) -> None:
    if not bundle_root.exists():
        return
    versions = sorted(
        (p for p in bundle_root.iterdir() if p.is_dir()),
        key=lambda p: p.name,
    )
    to_remove = versions[: max(0, len(versions) - keep)]
    for old in to_remove:
        shutil.rmtree(old)
        logger.info("removed old bundle version %s", old.name)
