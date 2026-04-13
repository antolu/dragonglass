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
    runtime: RuntimeTupleDict


class BundleManifest(typing.TypedDict):
    app_version: str
    bundles: list[BundleEntry]
    created: str
