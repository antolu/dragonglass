from __future__ import annotations

import dataclasses

from dragonglass.bundle.types import (
    BundleEntry,
    BundleManifest,
    RuntimeTuple,
)


def test_runtime_tuple_fields() -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    assert rt.os == "darwin"
    assert rt.arch == "arm64"
    assert rt.python == "3.13"


def test_runtime_tuple_frozen() -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    try:
        rt.os = "linux"  # type: ignore[misc]
        raise AssertionError("should be frozen")
    except (dataclasses.FrozenInstanceError, AttributeError):
        pass


def test_bundle_entry_required_keys() -> None:
    entry: BundleEntry = {
        "filename": "dragonglass-deps-1.0.0-darwin-arm64-py3.13.tar.gz",
        "sha256": "abc123",
        "size": 100_000_000,
        "deps_hash": "abc123",
        "runtime": {"os": "darwin", "arch": "arm64", "python": "3.13"},
    }
    assert entry["filename"].endswith(".tar.gz")


def test_manifest_structure() -> None:
    manifest: BundleManifest = {
        "app_version": "1.0.0",
        "created": "2026-01-01T00:00:00Z",
        "python_bundles": [],
    }
    assert manifest["app_version"] == "1.0.0"


def test_bundle_entry_has_deps_hash() -> None:
    entry: BundleEntry = {
        "filename": "dragonglass-deps-abc123def456-darwin-arm64-py3.13.tar.gz",
        "sha256": "abc",
        "size": 100,
        "deps_hash": "abc123def456",
        "runtime": {"os": "darwin", "arch": "arm64", "python": "3.13"},
    }
    assert entry["deps_hash"] == "abc123def456"
