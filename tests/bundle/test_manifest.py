from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile

import pytest

from dragonglass.bundle.manifest import (
    find_matching_bundle,
    parse_manifest,
    verify_file_hash,
)
from dragonglass.bundle.types import BundleEntry, BundleManifest, RuntimeTuple


def _make_manifest(bundles: list[BundleEntry]) -> BundleManifest:
    return {
        "app_version": "1.0.0",
        "bundles": bundles,
        "created": "2026-01-01T00:00:00Z",
    }


def test_parse_manifest_valid() -> None:
    raw = json.dumps(_make_manifest([]))
    manifest = parse_manifest(raw.encode())
    assert manifest["app_version"] == "1.0.0"
    assert manifest["bundles"] == []


def test_parse_manifest_invalid_json() -> None:
    with pytest.raises(ValueError, match="invalid manifest"):
        parse_manifest(b"not json")


def test_parse_manifest_missing_field() -> None:
    with pytest.raises(ValueError, match="invalid manifest"):
        parse_manifest(json.dumps({"app_version": "1.0.0"}).encode())


def test_find_matching_bundle_exact() -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    manifest = _make_manifest([
        {
            "filename": "dragonglass-deps-1.0.0-darwin-arm64-py3.13.tar.gz",
            "sha256": "abc",
            "size": 100,
            "runtime": {"os": "darwin", "arch": "arm64", "python": "3.13"},
        },
        {
            "filename": "dragonglass-deps-1.0.0-darwin-arm64-py3.11.tar.gz",
            "sha256": "def",
            "size": 100,
            "runtime": {"os": "darwin", "arch": "arm64", "python": "3.11"},
        },
    ])
    entry = find_matching_bundle(rt, manifest)
    assert entry is not None
    assert entry["runtime"]["python"] == "3.13"


def test_find_matching_bundle_no_match() -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    manifest = _make_manifest([
        {
            "filename": "dragonglass-deps-1.0.0-linux-x86_64-py3.13.tar.gz",
            "sha256": "abc",
            "size": 100,
            "runtime": {"os": "linux", "arch": "x86_64", "python": "3.13"},
        }
    ])
    assert find_matching_bundle(rt, manifest) is None


def test_verify_file_hash_correct() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        path = pathlib.Path(f.name)
    expected = hashlib.sha256(b"hello").hexdigest()
    assert verify_file_hash(path, expected) is True
    path.unlink()


def test_verify_file_hash_wrong() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        path = pathlib.Path(f.name)
    assert verify_file_hash(path, "deadbeef" * 8) is False
    path.unlink()
