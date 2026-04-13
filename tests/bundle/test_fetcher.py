from __future__ import annotations

import pytest

from dragonglass.bundle.fetcher import (
    _validate_url,  # noqa: PLC2701
    build_bundle_url,
    build_manifest_url,
)


def test_validate_url_allowed_github() -> None:
    _validate_url(
        "https://github.com/antolu/dragonglass/releases/download/v1.0.0/manifest.json"
    )


def test_validate_url_allowed_githubusercontent() -> None:
    _validate_url("https://objects.githubusercontent.com/releases/manifest.json")


def test_validate_url_rejects_other_host() -> None:
    with pytest.raises(ValueError, match="not in allowed hosts"):
        _validate_url("https://evil.com/manifest.json")


def test_validate_url_rejects_http() -> None:
    with pytest.raises(ValueError, match="https"):
        _validate_url("http://github.com/file")


def test_build_manifest_url() -> None:
    url = build_manifest_url("v1.0.0")
    assert "github.com" in url
    assert "v1.0.0" in url
    assert url.endswith("manifest.json")


def test_build_bundle_url() -> None:
    url = build_bundle_url(
        "v1.0.0", "dragonglass-deps-1.0.0-darwin-arm64-py3.13.tar.gz"
    )
    assert "github.com" in url
    assert "dragonglass-deps-1.0.0-darwin-arm64-py3.13.tar.gz" in url
