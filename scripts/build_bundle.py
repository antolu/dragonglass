#!/usr/bin/env python3
"""Build a Python dependency bundle for a given Python version.

Usage:
    python scripts/build_bundle.py \
        --python-version 3.13 \
        --deps-hash abc123def456 \
        --output-dir dist/bundles/python
"""

from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
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


def extract_wheel_license(whl_path: pathlib.Path, licenses_dir: pathlib.Path) -> None:
    """Extract license text from a wheel into licenses_dir/python/{name}-{version}.LICENSE."""
    with zipfile.ZipFile(whl_path) as zf:
        names = zf.namelist()
        dist_info = next(
            (n.split("/")[0] for n in names if n.endswith(".dist-info/METADATA")),
            None,
        )
        if dist_info is None:
            return

        metadata_path = f"{dist_info}/METADATA"
        raw = zf.read(metadata_path).decode("utf-8", errors="replace")
        msg = email.parser.Parser().parsestr(raw)
        pkg_name = msg.get("Name", "unknown")
        pkg_version = msg.get("Version", "unknown")
        license_header = msg.get("License", "")

        record_path = f"{dist_info}/RECORD"
        license_file_content: str | None = None
        if record_path in names:
            record = zf.read(record_path).decode("utf-8", errors="replace")
            for line in record.splitlines():
                fname = line.split(",")[0]
                base = fname.rsplit("/", 1)[-1].upper()
                if (
                    base
                    in {
                        "LICENSE",
                        "LICENSE.TXT",
                        "LICENSE.MD",
                        "COPYING",
                        "COPYING.TXT",
                    }
                    and fname in names
                ):
                    license_file_content = zf.read(fname).decode(
                        "utf-8", errors="replace"
                    )
                    break

        content = license_file_content or license_header or "No license text found."
        out_path = licenses_dir / "python" / f"{pkg_name}-{pkg_version}.LICENSE"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")


def main() -> None:  # noqa: PLR0914
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--deps-hash", required=True)
    parser.add_argument(
        "--output-dir", type=pathlib.Path, default=pathlib.Path("dist/bundles/python")
    )
    parser.add_argument("--wheel-cache-dir", type=pathlib.Path, default=None)
    args = parser.parse_args()

    python_version: str = args.python_version
    deps_hash: str = args.deps_hash
    output_dir: pathlib.Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    arch = detect_arch()
    os_name = platform.system().lower()
    bundle_name = (
        f"dragonglass-deps-{deps_hash}-{os_name}-{arch}-py{python_version}.tar.gz"
    )

    tarball_path = output_dir / bundle_name
    if tarball_path.exists():
        print(f"Bundle already exists, skipping build: {tarball_path}")
        print(f"SHA256: {sha256_file(tarball_path)}")
        print(f"Output: {tarball_path}")
        return

    wheel_cache = args.wheel_cache_dir
    if wheel_cache:
        wheel_cache.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        bundle_dir = pathlib.Path(td) / "bundle"
        wheelhouse = bundle_dir / "wheelhouse"
        wheelhouse.mkdir(parents=True)
        licenses_dir = bundle_dir / "licenses"

        repo_root = pathlib.Path(__file__).parent.parent

        pip_download_args = [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary",
            ":all:",
            "--platform",
            f"macosx_11_0_{arch}",
            "--python-version",
            python_version,
            "--dest",
            str(wheelhouse),
            "--find-links",
            str(wheelhouse),
        ]
        if wheel_cache:
            pip_download_args += ["--find-links", str(wheel_cache)]

        print("Building dragonglass wheel...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--wheel-dir",
                str(wheelhouse),
            ],
            check=True,
            cwd=repo_root,
        )

        print(f"Downloading wheels for Python {python_version} via pip...")
        subprocess.run([*pip_download_args, ".[fetch]"], check=True, cwd=repo_root)

        if wheel_cache:
            for whl in wheelhouse.glob("*.whl"):
                dest = wheel_cache / whl.name
                if not dest.exists():
                    shutil.copy2(whl, dest)

        print("Extracting licenses from wheels...")
        for whl in wheelhouse.glob("*.whl"):
            extract_wheel_license(whl, licenses_dir)

        meta = {
            "runtime": {"os": os_name, "arch": arch, "python": python_version},
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
