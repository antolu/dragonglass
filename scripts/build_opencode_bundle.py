#!/usr/bin/env python3
"""Build the opencode npm bundle with all tarballs for offline install.

Usage:
    python scripts/build_opencode_bundle.py \
        --deps-hash def789abc012 \
        --output-dir dist/bundles/opencode
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in {"arm64", "aarch64"} else machine


def extract_npm_license(
    tarball: pathlib.Path, name: str, version: str, licenses_dir: pathlib.Path
) -> None:
    """Extract license file from an npm tarball into licenses_dir/{name}-{version}.LICENSE."""
    licenses_dir.mkdir(parents=True, exist_ok=True)
    out_path = licenses_dir / f"{name}-{version}.LICENSE"
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getmembers():
                base = pathlib.PurePosixPath(member.name).name.upper()
                if base in {"LICENSE", "LICENSE.TXT", "LICENSE.MD", "COPYING"}:
                    f = tar.extractfile(member)
                    if f:
                        out_path.write_bytes(f.read())
                        return
    except tarfile.TarError:
        pass
    out_path.write_text("No license file found in package.\n", encoding="utf-8")


def main() -> None:  # noqa: PLR0914, PLR0915
    parser = argparse.ArgumentParser()
    parser.add_argument("--deps-hash", required=True)
    parser.add_argument(
        "--output-dir", type=pathlib.Path, default=pathlib.Path("dist/bundles/opencode")
    )
    parser.add_argument("--npm-cache-dir", type=pathlib.Path, default=None)
    args = parser.parse_args()

    deps_hash: str = args.deps_hash
    output_dir: pathlib.Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    arch = detect_arch()
    os_name = platform.system().lower()
    bundle_name = f"dragonglass-opencode-{deps_hash}-{os_name}-{arch}.tar.gz"

    tarball_path = output_dir / bundle_name
    if tarball_path.exists():
        print(f"Bundle already exists, skipping: {tarball_path}")
        print(f"SHA256: {sha256_file(tarball_path)}")
        print(f"Output: {tarball_path}")
        return

    npm_cache = args.npm_cache_dir
    if npm_cache:
        npm_cache.mkdir(parents=True, exist_ok=True)

    package_json = pathlib.Path("DragonglassApp/opencode/package.json")

    with tempfile.TemporaryDirectory() as td:
        work_dir = pathlib.Path(td)
        bundle_dir = work_dir / "bundle"
        npm_cache_dir = bundle_dir / "npm-cache"
        licenses_dir = bundle_dir / "licenses" / "npm"
        npm_cache_dir.mkdir(parents=True)
        licenses_dir.mkdir(parents=True)

        shutil.copy2(package_json, bundle_dir / "package.json")

        print("Running npm install to resolve full dependency graph...")
        subprocess.run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts"],
            cwd=str(bundle_dir),
            check=True,
        )

        lock_path = bundle_dir / "package-lock.json"
        with lock_path.open() as f:
            lock = json.load(f)

        print("Packing all npm dependencies...")
        for pkg_name, pkg_info in lock.get("packages", {}).items():
            if not pkg_name:
                continue
            name = (
                pkg_name[len("node_modules/") :]
                if pkg_name.startswith("node_modules/")
                else pkg_name
            )
            if not name:
                continue
            version = pkg_info.get("version", "")
            if not version:
                continue
            safe_name = name.replace("/", "-").lstrip("-")
            cache_tarball = npm_cache_dir / f"{safe_name}-{version}.tgz"
            if cache_tarball.exists():
                extract_npm_license(cache_tarball, safe_name, version, licenses_dir)
                continue
            try:
                subprocess.run(
                    [
                        "npm",
                        "pack",
                        f"{name}@{version}",
                        "--pack-destination",
                        str(npm_cache_dir),
                    ],
                    check=True,
                    capture_output=True,
                )
                if cache_tarball.exists():
                    extract_npm_license(cache_tarball, safe_name, version, licenses_dir)
            except subprocess.CalledProcessError as e:
                print(f"  warning: failed to pack {name}@{version}: {e}")

        meta = {
            "deps_hash": deps_hash,
            "built_at": datetime.now(UTC).isoformat(),
        }
        (bundle_dir / "bundle_meta.json").write_text(json.dumps(meta, indent=2))

        print(f"Creating {tarball_path}...")
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(bundle_dir, arcname="bundle")

    digest = sha256_file(tarball_path)
    print(f"SHA256: {digest}")
    print(f"Output: {tarball_path}")


if __name__ == "__main__":
    main()
