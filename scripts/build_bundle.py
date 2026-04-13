#!/usr/bin/env python3
"""Build a dependency bundle for a given Python version.

Usage:
    python scripts/build_bundle.py \
        --python-version 3.13 \
        --app-version 1.2.3 \
        --output-dir dist/bundles
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


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in {"arm64", "aarch64"} else machine


def main() -> None:  # noqa: PLR0914
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument(
        "--output-dir", type=pathlib.Path, default=pathlib.Path("dist/bundles")
    )
    args = parser.parse_args()

    python_version: str = args.python_version
    app_version: str = args.app_version
    output_dir: pathlib.Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    arch = detect_arch()
    os_name = platform.system().lower()
    bundle_name = (
        f"dragonglass-deps-{app_version}-{os_name}-{arch}-py{python_version}.tar.gz"
    )

    python_bin = f"python{python_version}"

    with tempfile.TemporaryDirectory() as td:
        bundle_dir = pathlib.Path(td) / "bundle"
        wheelhouse = bundle_dir / "wheelhouse"
        wheelhouse.mkdir(parents=True)

        print(f"Downloading wheels for Python {python_version}...")
        subprocess.run(
            [
                python_bin,
                "-m",
                "pip",
                "download",
                ".",
                "--dest",
                str(wheelhouse),
                "--python-version",
                python_version,
                "--only-binary",
                ":all:",
                "--platform",
                f"macosx_11_0_{arch}",
            ],
            check=True,
        )
        subprocess.run(
            [
                python_bin,
                "-m",
                "pip",
                "download",
                ".[fetch]",
                "--dest",
                str(wheelhouse),
                "--python-version",
                python_version,
                "--only-binary",
                ":all:",
                "--platform",
                f"macosx_11_0_{arch}",
            ],
            check=True,
        )

        opencode_dir = bundle_dir / "opencode"
        opencode_dir.mkdir()
        opencode_package_json = pathlib.Path("DragonglassApp/opencode/package.json")
        shutil.copy2(opencode_package_json, opencode_dir / "package.json")

        print("Packing opencode...")
        pkg_data = json.loads(opencode_package_json.read_text(encoding="utf-8"))
        opencode_version = pkg_data["dependencies"]["opencode-ai"]
        subprocess.run(
            [
                "npm",
                "pack",
                f"opencode-ai@{opencode_version}",
                "--pack-destination",
                str(opencode_dir),
            ],
            check=True,
        )

        meta = {
            "runtime": {"os": os_name, "arch": arch, "python": python_version},
            "app_version": app_version,
        }
        (bundle_dir / "bundle_meta.json").write_text(json.dumps(meta, indent=2))

        tarball_path = output_dir / bundle_name
        print(f"Creating {tarball_path}...")
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(bundle_dir, arcname="bundle")

    digest = sha256_file(tarball_path)
    print(f"SHA256: {digest}")
    print(f"Output: {tarball_path}")


if __name__ == "__main__":
    main()
