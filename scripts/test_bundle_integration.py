#!/usr/bin/env python3
"""End-to-end integration test: build bundle → verify structure → install → smoke → pytest.

Usage:
    python scripts/test_bundle_integration.py [--version VERSION] [--keep-tmp] [--skip-pytest]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO_ROOT = pathlib.Path(__file__).parent.parent


def _stage(n: int, name: str) -> None:
    print(f"\n[{n}] {name}", flush=True)


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"  OK: {msg}", flush=True)


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    print(f"  $ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run(cmd, check=False, **kwargs)  # type: ignore[call-overload]


def _get_git_tag() -> str:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    tag = result.stdout.strip().lstrip("v")
    if not tag:
        return "0.0.0-dev"
    return tag


def _compute_deps_hash() -> str:
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "python"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return result.stdout.strip()


def _detect_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def stage_build(tmp_dir: pathlib.Path, deps_hash: str) -> pathlib.Path:
    _stage(1, "Build bundle")
    python_version = _detect_python_version()
    output_dir = tmp_dir / "bundles"
    output_dir.mkdir(parents=True)

    result = _run(
        [
            sys.executable,
            "scripts/build_bundle.py",
            "--python-version",
            python_version,
            "--deps-hash",
            deps_hash,
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        _fail(f"build_bundle.py exited {result.returncode}")

    tarballs = list(output_dir.glob("*.tar.gz"))
    if not tarballs:
        _fail("build_bundle.py produced no .tar.gz files")
    tarball = tarballs[0]
    _ok(f"built {tarball.name} ({tarball.stat().st_size // 1024} KB)")
    return tarball


def stage_verify_structure(tarball: pathlib.Path, deps_hash: str) -> None:
    _stage(2, "Verify tarball structure")
    names: list[str] = []
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            names = tf.getnames()
    except tarfile.TarError as exc:
        _fail(f"cannot open tarball: {exc}")

    def _has(prefix: str) -> bool:
        return any(n.startswith(prefix) for n in names)

    if not _has("bundle/bundle_meta.json"):
        _fail("missing bundle/bundle_meta.json")
    _ok("bundle_meta.json present")

    whl_files = [
        n for n in names if n.startswith("bundle/wheelhouse/") and n.endswith(".whl")
    ]
    if not whl_files:
        _fail("wheelhouse/ contains no .whl files")
    _ok(f"wheelhouse has {len(whl_files)} wheel(s)")

    if not _has("bundle/opencode/"):
        _fail("missing bundle/opencode/ directory")
    _ok("opencode/ directory present")

    with tarfile.open(tarball, "r:gz") as tf:
        meta_member = tf.getmember("bundle/bundle_meta.json")
        f = tf.extractfile(meta_member)
        if f is None:
            _fail("cannot read bundle_meta.json from tarball")
        assert f is not None
        meta = json.loads(f.read())

    actual_hash = meta.get("deps_hash", "")
    if actual_hash != deps_hash:
        _fail(
            f"bundle_meta.json deps_hash={actual_hash!r} does not match expected {deps_hash!r}"
        )
    _ok(f"deps_hash matches: {deps_hash}")


def stage_install(
    tarball: pathlib.Path,
    tmp_dir: pathlib.Path,
    deps_hash: str,
    version: str,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    _stage(3, "Install bundle into fresh venv")
    venv_dir = tmp_dir / "venv"
    opencode_dir = tmp_dir / "opencode"
    marker_path = tmp_dir / "installed_python_bundle_hash.txt"

    result = _run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        _fail("venv creation failed")
    _ok(f"venv created at {venv_dir}")

    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_dir / "bin" / "python3"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dragonglass.bundle",
            "install-offline",
            str(tarball),
            "--version",
            version,
            "--venv-python",
            str(venv_python),
            "--opencode-dir",
            str(opencode_dir),
            "--marker-path",
            str(marker_path),
            "--deps-hash",
            deps_hash,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        cwd=REPO_ROOT,
    )

    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  {line}", flush=True)
            lines.append(line)
    proc.wait()

    if proc.returncode != 0:
        stderr = proc.stderr.read() if proc.stderr else ""
        _fail(f"install-offline exited {proc.returncode}\nstderr: {stderr}")

    if not lines:
        _fail("install-offline produced no output")

    last = json.loads(lines[-1])
    if last.get("type") != "done":
        _fail(f"last JSON line was not 'done': {last}")
    _ok("install-offline completed successfully")

    return venv_python, opencode_dir, marker_path


def stage_structural_checks(
    venv_python: pathlib.Path,
    opencode_dir: pathlib.Path,
    marker_path: pathlib.Path,
    deps_hash: str,
) -> None:
    _stage(4, "Structural checks")

    if not marker_path.exists():
        _fail(f"marker file not written: {marker_path}")
    actual = marker_path.read_text(encoding="utf-8").strip()
    if actual != deps_hash:
        _fail(f"marker contains {actual!r}, expected {deps_hash!r}")
    _ok("marker file written with correct deps_hash")

    for pkg in ("dragonglass", "mcp_server_fetch"):
        result = _run(
            [str(venv_python), "-c", f"import {pkg}; print({pkg}.__file__)"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(f"{pkg} not importable from venv: {result.stderr.strip()}")
        _ok(f"{pkg} importable: {result.stdout.strip()}")

    if not opencode_dir.exists():
        _fail(f"opencode install dir not created: {opencode_dir}")
    _ok(f"opencode dir exists: {opencode_dir}")


def stage_functional_smoke(venv_python: pathlib.Path) -> None:
    _stage(5, "Functional smoke")
    result = _run(
        [str(venv_python), "-m", "dragonglass.bundle", "info"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail(f"dragonglass.bundle info failed: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        _fail(f"info output is not valid JSON: {exc}")

    for key in ("os", "arch", "python"):
        if key not in data:
            _fail(f"info JSON missing key {key!r}")

    expected_os = platform.system().lower()
    if data["os"] != expected_os:
        _fail(f"info os={data['os']!r}, expected {expected_os!r}")

    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if data["python"] != expected_python:
        _fail(f"info python={data['python']!r}, expected {expected_python!r}")

    _ok(f"info returned: {data}")


def stage_pytest(venv_python: pathlib.Path) -> None:
    _stage(6, "pytest -m integration")
    result = subprocess.run(
        [str(venv_python), "-m", "pytest", "tests/", "-m", "integration", "-v"],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        _fail(f"pytest -m integration exited {result.returncode}")
    _ok("all integration-marked tests passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle end-to-end integration test")
    parser.add_argument(
        "--version", default=None, help="App version (default: current git tag)"
    )
    parser.add_argument(
        "--keep-tmp", action="store_true", help="Keep temp dir after run"
    )
    parser.add_argument("--skip-pytest", action="store_true", help="Skip pytest stage")
    args = parser.parse_args()

    version = args.version or _get_git_tag()
    deps_hash = _compute_deps_hash()

    print(
        f"Bundle integration test — version={version} deps_hash={deps_hash}", flush=True
    )

    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="dragonglass-integration-"))
    print(f"Working in {tmp_dir}", flush=True)

    try:
        tarball = stage_build(tmp_dir, deps_hash)
        stage_verify_structure(tarball, deps_hash)
        venv_python, opencode_dir, marker_path = stage_install(
            tarball, tmp_dir, deps_hash, version
        )
        stage_structural_checks(venv_python, opencode_dir, marker_path, deps_hash)
        stage_functional_smoke(venv_python)
        if not args.skip_pytest:
            stage_pytest(venv_python)
        print("\nAll stages passed.", flush=True)
    finally:
        if args.keep_tmp:
            print(f"\nTemp dir kept at: {tmp_dir}", flush=True)
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
