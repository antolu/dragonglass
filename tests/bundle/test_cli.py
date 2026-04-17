from __future__ import annotations

import json
import os
import pathlib
import platform
import subprocess
import sys
import tarfile
import tempfile

from dragonglass.bundle.runtime import validate_runtime
from dragonglass.bundle.types import RuntimeTuple


def _run_bundle(*args: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, "-m", "dragonglass.bundle", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_info_command() -> None:
    result = _run_bundle("info")
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert "os" in data
    assert "python" in data
    assert "arch" in data


def test_verify_nonexistent_file() -> None:
    result = _run_bundle("verify", "/nonexistent/path.tar.gz")
    assert result.returncode != 0
    lines = [line for line in result.stdout.strip().splitlines() if line]
    last = json.loads(lines[-1])
    assert last["type"] == "error"


def test_install_rejects_unsupported_runtime() -> None:
    errors = validate_runtime(RuntimeTuple(os="freebsd", arch="arm64", python="3.13"))
    assert errors


def test_install_accepts_marker_path_arg() -> None:
    result = _run_bundle("install", "--help")
    assert "--marker-path" in result.stdout


def test_install_offline_accepts_marker_path_arg() -> None:
    result = _run_bundle("install-offline", "--help")
    assert "--marker-path" in result.stdout


def _make_fake_bundle_for_cli(dest: pathlib.Path) -> tuple[pathlib.Path, str]:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else machine
    os_name = platform.system().lower()
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"

    with tempfile.TemporaryDirectory() as td:
        bundle_dir = pathlib.Path(td) / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "bundle_meta.json").write_text(
            json.dumps({
                "runtime": {"os": os_name, "arch": arch, "python": python_ver},
                "deps_hash": "testdepshash001",
                "built_at": "2026-04-17T00:00:00Z",
            }),
            encoding="utf-8",
        )
        wheelhouse = bundle_dir / "wheelhouse"
        wheelhouse.mkdir()
        (wheelhouse / "placeholder.whl").write_bytes(b"fake wheel")
        opencode_dir = bundle_dir / "opencode"
        opencode_dir.mkdir()
        (opencode_dir / "placeholder.tgz").write_bytes(b"fake node")

        tarball = dest / "bundle.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(bundle_dir, arcname="bundle")

    return tarball, "testdepshash001"


def test_install_offline_cli_succeeds(tmp_path: pathlib.Path) -> None:
    tarball, deps_hash = _make_fake_bundle_for_cli(tmp_path)
    marker = tmp_path / "marker.txt"
    opencode_dir = tmp_path / "oc"

    fake_pip_script = tmp_path / "fake_python"
    fake_pip_script.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
        encoding="utf-8",
    )
    fake_pip_script.chmod(0o755)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path.cwd())

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dragonglass.bundle",
            "install-offline",
            str(tarball),
            "--version",
            "1.0.0",
            "--venv-python",
            str(fake_pip_script),
            "--opencode-dir",
            str(opencode_dir),
            "--marker-path",
            str(marker),
            "--deps-hash",
            deps_hash,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    lines = [line for line in result.stdout.strip().splitlines() if line]
    assert lines, "no stdout lines"
    for line in lines:
        json.loads(line)
    last = json.loads(lines[-1])
    assert last["type"] == "done"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == deps_hash
