#!/usr/bin/env python3
"""Generate manifest.json from built bundle archives.

Usage:
    python scripts/generate_manifest.py \
        --python-bundles-dir dist/bundles/python \
        --opencode-bundle dist/bundles/opencode/dragonglass-opencode-HASH-darwin-arm64.tar.gz \
        --app-version 1.2.3 \
        --output manifest.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_PYTHON_BUNDLE_RE = re.compile(
    r"dragonglass-deps-(?P<deps_hash>[a-f0-9]{12})-(?P<os>[^-]+)-(?P<arch>[^-]+)-py(?P<python>[\d.]+)\.tar\.gz"
)

_OPENCODE_BUNDLE_RE = re.compile(
    r"dragonglass-opencode-(?P<deps_hash>[a-f0-9]{12})-(?P<os>[^-]+)-(?P<arch>[^-]+)\.tar\.gz"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-bundles-dir", type=pathlib.Path, required=True)
    parser.add_argument("--opencode-bundle", type=pathlib.Path, default=None)
    parser.add_argument("--app-version", required=True)
    parser.add_argument(
        "--output", type=pathlib.Path, default=pathlib.Path("manifest.json")
    )
    args = parser.parse_args()

    python_bundles = []
    for path in sorted(args.python_bundles_dir.glob("*.tar.gz")):
        m = _PYTHON_BUNDLE_RE.match(path.name)
        if not m:
            print(f"skipping unrecognised filename: {path.name}")
            continue
        digest = sha256_file(path)
        size = path.stat().st_size
        python_bundles.append({
            "filename": path.name,
            "sha256": digest,
            "size": size,
            "deps_hash": m.group("deps_hash"),
            "runtime": {
                "os": m.group("os"),
                "arch": m.group("arch"),
                "python": m.group("python"),
            },
        })
        print(f"  python {path.name}  sha256={digest[:16]}...")

    opencode_entry = None
    if args.opencode_bundle and args.opencode_bundle.exists():
        m = _OPENCODE_BUNDLE_RE.match(args.opencode_bundle.name)
        if m:
            digest = sha256_file(args.opencode_bundle)
            size = args.opencode_bundle.stat().st_size
            opencode_entry = {
                "filename": args.opencode_bundle.name,
                "sha256": digest,
                "size": size,
                "deps_hash": m.group("deps_hash"),
            }
            print(f"  opencode {args.opencode_bundle.name}  sha256={digest[:16]}...")

    manifest = {
        "app_version": args.app_version,
        "python_bundles": python_bundles,
        "opencode_bundle": opencode_entry,
        "created": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    args.output.write_text(json.dumps(manifest, indent=2))
    print(f"manifest written to {args.output} ({len(python_bundles)} python bundles)")


if __name__ == "__main__":
    main()
