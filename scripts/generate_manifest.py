#!/usr/bin/env python3
"""Generate manifest.json from all bundle archives in a directory.

Usage:
    python scripts/generate_manifest.py \
        --bundles-dir dist/bundles \
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


_BUNDLE_RE = re.compile(
    r"dragonglass-deps-(?P<ver>[^-]+)-(?P<os>[^-]+)-(?P<arch>[^-]+)-py(?P<python>[\d.]+)\.tar\.gz"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundles-dir", type=pathlib.Path, required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument(
        "--output", type=pathlib.Path, default=pathlib.Path("manifest.json")
    )
    args = parser.parse_args()

    bundles = []
    for path in sorted(args.bundles_dir.glob("*.tar.gz")):
        m = _BUNDLE_RE.match(path.name)
        if not m:
            print(f"skipping unrecognised filename: {path.name}")
            continue
        digest = sha256_file(path)
        size = path.stat().st_size
        bundles.append({
            "filename": path.name,
            "sha256": digest,
            "size": size,
            "runtime": {
                "os": m.group("os"),
                "arch": m.group("arch"),
                "python": m.group("python"),
            },
        })
        print(f"  {path.name}  sha256={digest[:16]}...")

    manifest = {
        "app_version": args.app_version,
        "bundles": bundles,
        "created": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    args.output.write_text(json.dumps(manifest, indent=2))
    print(f"manifest written to {args.output} ({len(bundles)} bundles)")


if __name__ == "__main__":
    main()
