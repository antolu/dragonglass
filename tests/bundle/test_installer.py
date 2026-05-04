from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile

import pytest

import dragonglass.bundle.installer as installer_mod
from dragonglass.bundle.cache import set_installed_bundle_version
from dragonglass.bundle.installer import (
    _extract_bundle,  # noqa: PLC2701
    _run_pip_install,  # noqa: PLC2701
    install_offline,
    install_online,
)
from dragonglass.bundle.types import RuntimeTuple


def _make_fake_bundle(dest: pathlib.Path, rt: RuntimeTuple) -> tuple[pathlib.Path, str]:
    with tempfile.TemporaryDirectory() as td:
        bundle_dir = pathlib.Path(td) / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "bundle_meta.json").write_text(
            json.dumps({
                "runtime": {"os": rt.os, "arch": rt.arch, "python": rt.python},
                "deps_hash": "abc123def456",
                "built_at": "2026-04-16T12:00:00Z",
            }),
            encoding="utf-8",
        )
        wheelhouse = bundle_dir / "wheelhouse"
        wheelhouse.mkdir()
        (wheelhouse / "placeholder.whl").write_bytes(b"fake wheel")

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


def test_extract_bundle_deps_hash_mismatch(tmp_path: pathlib.Path) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    tarball, _ = _make_fake_bundle(tmp_path, rt)
    extract_dir = tmp_path / "extracted"
    with pytest.raises(ValueError, match="deps_hash mismatch"):
        _extract_bundle(
            tarball,
            extract_dir,
            expected_runtime=rt,
            expected_deps_hash="wronghash0000",
        )


def test_extract_bundle_deps_hash_matches(tmp_path: pathlib.Path) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    tarball, _ = _make_fake_bundle(tmp_path, rt)
    extract_dir = tmp_path / "extracted"
    _extract_bundle(
        tarball, extract_dir, expected_runtime=rt, expected_deps_hash="abc123def456"
    )
    assert (extract_dir / "bundle_meta.json").exists()


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


def test_install_offline_writes_version_marker(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    tarball, _ = _make_fake_bundle(tmp_path, rt)
    marker = tmp_path / "marker.txt"

    captured: list[dict] = []

    def fake_install_from_archive(  # noqa: PLR0913
        tarball_: pathlib.Path,
        rt_: object,
        deps_hash: str,
        venv_python: pathlib.Path,
        emit: object,
        *,
        system_python: str | None = None,
        marker_path: pathlib.Path | None = None,
    ) -> None:
        captured.append({
            "deps_hash": deps_hash,
            "marker_path": marker_path,
        })

        if marker_path:
            set_installed_bundle_version(deps_hash, marker_path=marker_path)

    monkeypatch.setattr(
        installer_mod, "_install_from_archive", fake_install_from_archive
    )
    monkeypatch.setattr(installer_mod, "store_bundle", lambda src, version, **kw: src)

    install_offline(
        bundle_path=tarball,
        deps_hash="abc123def456",
        venv_python=pathlib.Path(sys.executable),
        version="1.0.0",
        marker_path=marker,
    )

    assert len(captured) == 1
    assert captured[0]["deps_hash"] == "abc123def456"
    assert captured[0]["marker_path"] == marker
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == "abc123def456"


def test_install_offline_invalid_tarball_raises(
    tmp_path: pathlib.Path,
) -> None:
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"not a tarball")
    with pytest.raises(RuntimeError, match=r"not a valid tar\.gz"):
        install_offline(
            bundle_path=bad,
            deps_hash="abc123def456",
            venv_python=pathlib.Path(sys.executable),
            version="1.0.0",
        )


def test_install_online_fetches_and_installs(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    tarball, sha256 = _make_fake_bundle(tmp_path, rt)
    deps_hash = "abc123def456"
    filename = f"dragonglass-deps-{deps_hash}-darwin-arm64-py3.13.tar.gz"
    marker = tmp_path / "marker.txt"

    fake_entry = {
        "filename": filename,
        "sha256": sha256,
        "size": tarball.stat().st_size,
        "runtime": {"os": rt.os, "arch": rt.arch, "python": rt.python},
        "deps_hash": deps_hash,
    }

    captured: list[dict] = []

    def fake_install_from_archive(  # noqa: PLR0913
        tarball_: pathlib.Path,
        rt_: object,
        deps_hash_: str,
        venv_python: pathlib.Path,
        emit: object,
        *,
        system_python: str | None = None,
        marker_path: pathlib.Path | None = None,
    ) -> None:
        captured.append({"deps_hash": deps_hash_, "marker_path": marker_path})
        if marker_path:
            set_installed_bundle_version(deps_hash_, marker_path=marker_path)

    monkeypatch.setattr(installer_mod, "fetch_bytes", lambda url: b"{}")
    monkeypatch.setattr(
        installer_mod,
        "parse_manifest",
        lambda data: {"python_bundles": [], "app_version": "", "created": ""},
    )
    monkeypatch.setattr(
        installer_mod, "find_matching_bundle", lambda rt_, dh, manifest: fake_entry
    )
    monkeypatch.setattr(installer_mod, "verify_file_hash", lambda path, expected: True)
    monkeypatch.setattr(
        installer_mod,
        "fetch_to_file",
        lambda url, dest, progress=None: dest.write_bytes(tarball.read_bytes()) or dest,
    )
    monkeypatch.setattr(installer_mod, "store_bundle", lambda src, version, **kw: src)
    monkeypatch.setattr(
        installer_mod, "_install_from_archive", fake_install_from_archive
    )
    monkeypatch.setattr(installer_mod, "detect_runtime", lambda: rt)

    install_online(
        version="1.0.0",
        deps_hash=deps_hash,
        venv_python=pathlib.Path(sys.executable),
        marker_path=marker,
    )

    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == deps_hash


def test_install_online_raises_on_no_matching_bundle(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.13")
    deps_hash = "abc123def456"

    monkeypatch.setattr(installer_mod, "fetch_bytes", lambda url: b"{}")
    monkeypatch.setattr(
        installer_mod,
        "parse_manifest",
        lambda data: {"python_bundles": [], "app_version": "", "created": ""},
    )
    monkeypatch.setattr(
        installer_mod, "find_matching_bundle", lambda rt_, dh, manifest: None
    )
    monkeypatch.setattr(installer_mod, "detect_runtime", lambda: rt)

    with pytest.raises(RuntimeError, match="No bundle found"):
        install_online(
            version="1.0.0",
            deps_hash=deps_hash,
            venv_python=pathlib.Path(sys.executable),
        )
