from __future__ import annotations

import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class RuntimeTuple:
    os: str
    arch: str
    python: str


class RuntimeTupleDict(typing.TypedDict):
    os: str
    arch: str
    python: str


class BundleEntry(typing.TypedDict):
    filename: str
    sha256: str
    size: int
    deps_hash: str
    runtime: RuntimeTupleDict


class OpencodeBundleEntry(typing.TypedDict):
    filename: str
    sha256: str
    size: int
    deps_hash: str


class BundleManifest(typing.TypedDict):
    app_version: str
    created: str
    python_bundles: list[BundleEntry]
    opencode_bundle: OpencodeBundleEntry | None
