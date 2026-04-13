from __future__ import annotations

import argparse
import json
import pathlib
import sys


def _emit(obj: dict) -> None:  # type: ignore[type-arg]
    print(json.dumps(obj), flush=True)


def _emit_progress(message: str, fraction: float) -> None:
    _emit({"type": "progress", "message": message, "fraction": fraction})


def _cmd_info(_args: argparse.Namespace) -> int:
    from dragonglass.bundle.runtime import detect_runtime  # noqa: PLC0415

    rt = detect_runtime()
    _emit({"os": rt.os, "arch": rt.arch, "python": rt.python})
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    import tarfile  # noqa: PLC0415

    from dragonglass.bundle.manifest import verify_file_hash  # noqa: PLC0415

    path = pathlib.Path(args.bundle_path)
    if not path.exists():
        _emit({"type": "error", "message": f"file not found: {path}"})
        return 1
    try:
        with tarfile.open(path, "r:gz"):
            pass
    except Exception as exc:
        _emit({"type": "error", "message": f"not a valid tar.gz: {exc}"})
        return 1
    if args.sha256 and not verify_file_hash(path, args.sha256):
        _emit({"type": "error", "message": "SHA256 mismatch"})
        return 1
    _emit({"type": "done", "message": "bundle OK"})
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    from dragonglass.bundle.installer import install_online  # noqa: PLC0415
    from dragonglass.bundle.runtime import (  # noqa: PLC0415
        detect_runtime,
        validate_runtime,
    )

    rt = detect_runtime()
    errors = validate_runtime(rt)
    if errors:
        for e in errors:
            _emit({"type": "error", "message": e})
        return 1
    try:
        install_online(
            version=args.version,
            venv_python=pathlib.Path(args.venv_python),
            opencode_install_dir=pathlib.Path(args.opencode_dir),
            progress=_emit_progress,
            marker_path=pathlib.Path(args.marker_path) if args.marker_path else None,
        )
    except Exception as exc:
        _emit({"type": "error", "message": str(exc)})
        return 1
    else:
        _emit({"type": "done"})
        return 0


def _cmd_install_offline(args: argparse.Namespace) -> int:
    from dragonglass.bundle.installer import install_offline  # noqa: PLC0415
    from dragonglass.bundle.runtime import (  # noqa: PLC0415
        detect_runtime,
        validate_runtime,
    )

    rt = detect_runtime()
    errors = validate_runtime(rt)
    if errors:
        for e in errors:
            _emit({"type": "error", "message": e})
        return 1
    try:
        install_offline(
            bundle_path=pathlib.Path(args.bundle_path),
            venv_python=pathlib.Path(args.venv_python),
            opencode_install_dir=pathlib.Path(args.opencode_dir),
            version=args.version,
            progress=_emit_progress,
            marker_path=pathlib.Path(args.marker_path) if args.marker_path else None,
        )
    except Exception as exc:
        _emit({"type": "error", "message": str(exc)})
        return 1
    else:
        _emit({"type": "done"})
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m dragonglass.bundle")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Print runtime tuple as JSON")

    p_verify = sub.add_parser("verify", help="Verify a bundle archive")
    p_verify.add_argument("bundle_path")
    p_verify.add_argument("--sha256", default=None)

    p_install = sub.add_parser("install", help="Download and install bundle")
    p_install.add_argument("--version", required=True)
    p_install.add_argument("--venv-python", required=True, dest="venv_python")
    p_install.add_argument("--opencode-dir", required=True, dest="opencode_dir")
    p_install.add_argument("--marker-path", default=None, dest="marker_path")

    p_offline = sub.add_parser("install-offline", help="Install bundle from local file")
    p_offline.add_argument("bundle_path")
    p_offline.add_argument("--version", required=True)
    p_offline.add_argument("--venv-python", required=True, dest="venv_python")
    p_offline.add_argument("--opencode-dir", required=True, dest="opencode_dir")
    p_offline.add_argument("--marker-path", default=None, dest="marker_path")

    args = parser.parse_args()
    dispatch = {
        "info": _cmd_info,
        "verify": _cmd_verify,
        "install": _cmd_install,
        "install-offline": _cmd_install_offline,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
