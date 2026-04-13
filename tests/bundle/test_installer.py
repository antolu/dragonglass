from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile

import pytest

from dragonglass.bundle.installer import (
    _extract_bundle,  # noqa: PLC2701
    _run_pip_install,  # noqa: PLC2701
)
from dragonglass.bundle.types import RuntimeTuple


def _make_fake_bundle(dest: pathlib.Path, rt: RuntimeTuple) -> tuple[pathlib.Path, str]:
    with tempfile.TemporaryDirectory() as td:
        bundle_dir = pathlib.Path(td) / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "bundle_meta.json").write_text(
            json.dumps({
                "runtime": {"os": rt.os, "arch": rt.arch, "python": rt.python},
                "app_version": "1.0.0",
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

    sha256 = hashlib.sha256(tarball.read_bytes()).hexdigest()
    return tarball, sha256


def test_extract_bundle_succeeds(tmp_path: pathlib.Path) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    tarball, _ = _make_fake_bundle(tmp_path, rt)
    extract_dir = tmp_path / "extracted"
    _extract_bundle(tarball, extract_dir)
    assert (extract_dir / "bundle_meta.json").exists()
    assert (extract_dir / "wheelhouse").is_dir()


def test_extract_bundle_runtime_mismatch(tmp_path: pathlib.Path) -> None:
    rt = RuntimeTuple(os="linux", arch="x86_64", python="3.11")
    tarball, _ = _make_fake_bundle(tmp_path, rt)
    extract_dir = tmp_path / "extracted"
    expected_rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    with pytest.raises(ValueError, match="runtime mismatch"):
        _extract_bundle(tarball, extract_dir, expected_runtime=expected_rt)


def test_run_pip_install_calls_pip(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    venv_python = pathlib.Path(sys.executable)
    _run_pip_install(
        venv_python=venv_python, wheelhouse=wheelhouse, package="dragonglass[fetch]"
    )
    assert any("pip" in str(c) for c in calls[0])
    assert "--no-index" in calls[0]
    assert "dragonglass[fetch]" in calls[0]
