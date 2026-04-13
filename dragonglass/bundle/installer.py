from __future__ import annotations

import collections.abc
import json
import logging
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile

from dragonglass.bundle.cache import (
    cleanup_old_versions,
    get_cached_bundle,
    set_installed_bundle_version,
    store_bundle,
)
from dragonglass.bundle.fetcher import (
    build_bundle_url,
    build_manifest_url,
    fetch_bytes,
    fetch_to_file,
)
from dragonglass.bundle.manifest import (
    find_matching_bundle,
    parse_manifest,
    verify_file_hash,
)
from dragonglass.bundle.runtime import detect_runtime
from dragonglass.bundle.types import RuntimeTuple

logger = logging.getLogger(__name__)


def _extract_bundle(
    tarball: pathlib.Path,
    dest: pathlib.Path,
    *,
    expected_runtime: RuntimeTuple | None = None,
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            parts = pathlib.PurePosixPath(member.name).parts
            if len(parts) <= 1:
                continue
            member.name = str(pathlib.PurePosixPath(*parts[1:]))
            tar.extract(member, dest, filter="data")

    if expected_runtime is not None:
        meta_path = dest / "bundle_meta.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            r = meta["runtime"]
            actual = RuntimeTuple(os=r["os"], arch=r["arch"], python=r["python"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError) as exc:
            raise ValueError(f"cannot read bundle_meta.json: {exc}") from exc
        if actual != expected_runtime:
            shutil.rmtree(dest, ignore_errors=True)
            raise ValueError(
                f"runtime mismatch: bundle has {actual}, expected {expected_runtime}"
            )
    logger.info("extracted bundle to %s", dest)


def _run_pip_install(
    venv_python: pathlib.Path,
    wheelhouse: pathlib.Path,
    package: str = "dragonglass[fetch]",
) -> None:
    from dragonglass.system_paths import resolve_tool_paths  # noqa: PLC0415

    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(resolve_tool_paths())
    cmd = [
        str(venv_python),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(wheelhouse),
        package,
    ]
    logger.info("pip install: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def install_online(
    version: str,
    venv_python: pathlib.Path,
    opencode_install_dir: pathlib.Path,
    progress: collections.abc.Callable[[str, float], None] | None = None,
    marker_path: pathlib.Path | None = None,
) -> None:
    rt = detect_runtime()
    tag = f"v{version}"

    def _emit(msg: str, pct: float = 0.0) -> None:
        logger.info("%s (%.0f%%)", msg, pct * 100)
        if progress:
            progress(msg, pct)

    _emit("Fetching manifest...", 0.0)
    manifest_bytes = fetch_bytes(build_manifest_url(tag))
    manifest = parse_manifest(manifest_bytes)

    entry = find_matching_bundle(rt, manifest)
    if entry is None:
        raise RuntimeError(
            f"No bundle found for runtime {rt}; check GitHub releases for supported platforms."
        )

    cached = get_cached_bundle(version, entry["filename"])
    if cached is None:
        _emit(f"Downloading {entry['filename']}...", 0.1)
        with tempfile.TemporaryDirectory() as td:
            tmp_path = pathlib.Path(td) / entry["filename"]

            def _dl_progress(received: int, total: int) -> None:
                pct = (received / total * 0.7) + 0.1 if total else 0.1
                _emit(f"Downloading... {received // 1024 // 1024} MB", pct)

            fetch_to_file(
                build_bundle_url(tag, entry["filename"]), tmp_path, _dl_progress
            )

            _emit("Verifying download...", 0.8)
            if not verify_file_hash(tmp_path, entry["sha256"]):
                raise RuntimeError(
                    "SHA256 mismatch — download may be corrupt. Try again."
                )

            cached = store_bundle(tmp_path, version)

    else:
        _emit("Using cached bundle...", 0.8)
        if not verify_file_hash(cached, entry["sha256"]):
            cached.unlink(missing_ok=True)
            raise RuntimeError("Cached bundle SHA256 mismatch — re-download required.")

    _install_from_archive(
        cached,
        rt,
        version,
        venv_python,
        opencode_install_dir,
        _emit,
        marker_path=marker_path,
    )


def install_offline(  # noqa: PLR0913, PLR0917
    bundle_path: pathlib.Path,
    venv_python: pathlib.Path,
    opencode_install_dir: pathlib.Path,
    version: str,
    progress: collections.abc.Callable[[str, float], None] | None = None,
    marker_path: pathlib.Path | None = None,
) -> None:
    rt = detect_runtime()

    def _emit(msg: str, pct: float = 0.0) -> None:
        logger.info("%s (%.0f%%)", msg, pct * 100)
        if progress:
            progress(msg, pct)

    _emit("Verifying bundle...", 0.1)
    try:
        with tarfile.open(bundle_path, "r:gz"):
            pass
    except tarfile.TarError as exc:
        raise RuntimeError(f"bundle is not a valid tar.gz archive: {exc}") from exc

    cached = store_bundle(bundle_path, version)
    _install_from_archive(
        cached,
        rt,
        version,
        venv_python,
        opencode_install_dir,
        _emit,
        marker_path=marker_path,
    )


def _install_from_archive(  # noqa: PLR0913, PLR0917
    tarball: pathlib.Path,
    rt: RuntimeTuple,
    version: str,
    venv_python: pathlib.Path,
    opencode_install_dir: pathlib.Path,
    emit: collections.abc.Callable[[str, float], None],
    *,
    marker_path: pathlib.Path | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        extract_dir = pathlib.Path(td) / "bundle"
        emit("Extracting bundle...", 0.85)
        _extract_bundle(tarball, extract_dir, expected_runtime=rt)

        wheelhouse = extract_dir / "wheelhouse"
        emit("Installing Python packages...", 0.9)
        _run_pip_install(venv_python, wheelhouse)

        opencode_src = extract_dir / "opencode"
        if opencode_src.exists():
            emit("Installing OpenCode...", 0.95)
            if opencode_install_dir.exists():
                shutil.rmtree(opencode_install_dir)
            shutil.copytree(opencode_src, opencode_install_dir)

    kwargs = {"marker_path": marker_path} if marker_path is not None else {}
    set_installed_bundle_version(version, **kwargs)
    cleanup_old_versions(keep=2)
    emit("Done.", 1.0)
