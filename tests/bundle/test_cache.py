from __future__ import annotations

import pathlib

import pytest

from dragonglass.bundle.cache import (
    cleanup_old_versions,
    get_cached_bundle,
    get_installed_bundle_version,
    set_installed_bundle_version,
    store_bundle,
)


@pytest.fixture
def bundle_root(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "bundles"


def test_store_and_retrieve_bundle(
    bundle_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "test-1.0.0-darwin-arm64-py3.13.tar.gz"
    src.write_bytes(b"fake archive")
    stored = store_bundle(src, version="1.0.0", bundle_root=bundle_root)
    assert stored.exists()
    assert stored.stat().st_size == len(b"fake archive")
    retrieved = get_cached_bundle(
        "1.0.0", "test-1.0.0-darwin-arm64-py3.13.tar.gz", bundle_root=bundle_root
    )
    assert retrieved == stored


def test_get_cached_bundle_missing(bundle_root: pathlib.Path) -> None:
    result = get_cached_bundle("9.9.9", "nonexistent.tar.gz", bundle_root=bundle_root)
    assert result is None


def test_set_and_get_installed_version(tmp_path: pathlib.Path) -> None:
    marker = tmp_path / "installed_bundle_version.txt"
    set_installed_bundle_version("1.2.3", marker_path=marker)
    assert get_installed_bundle_version(marker_path=marker) == "1.2.3"


def test_get_installed_version_missing(tmp_path: pathlib.Path) -> None:
    marker = tmp_path / "missing.txt"
    assert get_installed_bundle_version(marker_path=marker) is None


def test_cleanup_old_versions(
    bundle_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    for version in ("1.0.0", "1.1.0", "1.2.0", "1.3.0"):
        src = tmp_path / f"file-{version}.tar.gz"
        src.write_bytes(b"x")
        store_bundle(src, version=version, bundle_root=bundle_root)
    cleanup_old_versions(keep=2, bundle_root=bundle_root)
    remaining = sorted(p.name for p in bundle_root.iterdir())
    assert len(remaining) == 2  # noqa: PLR2004
