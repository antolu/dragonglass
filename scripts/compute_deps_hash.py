#!/usr/bin/env python3
"""Print a 12-char SHA-256 fingerprint of dependency inputs.

Usage:
    python scripts/compute_deps_hash.py --type python
    python scripts/compute_deps_hash.py --type opencode
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib


def compute_hash(type_: str, root: pathlib.Path) -> str:
    if type_ == "python":
        path = root / "uv.lock"
    elif type_ == "opencode":
        path = root / "DragonglassApp/opencode/package.json"
    else:
        raise ValueError(f"unknown type: {type_!r}")
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:12]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["python", "opencode"])
    parser.add_argument("--root-dir", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    print(compute_hash(args.type, args.root_dir))


if __name__ == "__main__":
    main()
