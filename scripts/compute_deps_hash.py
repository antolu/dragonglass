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
    h = hashlib.sha256()
    if type_ == "python":
        h.update((root / "uv.lock").read_bytes())
        h.update((root / "DragonglassApp/opencode/package.json").read_bytes())
        try:
            import subprocess  # noqa: PLC0415

            version = subprocess.check_output(
                ["git", "describe", "--tags", "--always"],
                cwd=root,
                stderr=subprocess.DEVNULL,
            ).strip()
            h.update(version)
        except Exception:
            pass
    elif type_ == "opencode":
        h.update((root / "DragonglassApp/opencode/package.json").read_bytes())
    else:
        raise ValueError(f"unknown type: {type_!r}")
    return h.hexdigest()[:12]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["python", "opencode"])
    parser.add_argument("--root-dir", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    print(compute_hash(args.type, args.root_dir))


if __name__ == "__main__":
    main()
