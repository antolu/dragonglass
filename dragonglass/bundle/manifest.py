from __future__ import annotations

import hashlib
import json
import logging
import pathlib

from dragonglass.bundle.types import BundleEntry, BundleManifest, RuntimeTuple

logger = logging.getLogger(__name__)


def parse_manifest(data: bytes) -> BundleManifest:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("invalid manifest: expected object")  # noqa: TRY004
    for key in ("app_version", "bundles", "created"):
        if key not in obj:
            raise ValueError(f"invalid manifest: missing field {key!r}")
    if not isinstance(obj["bundles"], list):
        raise ValueError("invalid manifest: 'bundles' must be a list")  # noqa: TRY004
    return obj  # type: ignore[return-value]


def find_matching_bundle(
    rt: RuntimeTuple, manifest: BundleManifest
) -> BundleEntry | None:
    for entry in manifest["bundles"]:
        r = entry["runtime"]
        if r["os"] == rt.os and r["arch"] == rt.arch and r["python"] == rt.python:
            logger.debug("found matching bundle %s", entry["filename"])
            return entry
    logger.debug("no bundle matched runtime %s", rt)
    return None


def verify_file_hash(path: pathlib.Path, expected_sha256: str) -> bool:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()
    match = actual == expected_sha256
    if match:
        logger.info("hash OK %s", path.name)
    else:
        logger.warning(
            "hash MISMATCH %s expected=%s actual=%s", path.name, expected_sha256, actual
        )
    return match
