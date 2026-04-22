from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

HASH_LENGTH = 12
HEX_CHARS = "0123456789abcdef"


def test_python_hash_is_12_hex_chars() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "python"],
        capture_output=True,
        text=True,
        check=True,
    )
    h = result.stdout.strip()
    assert len(h) == HASH_LENGTH
    assert all(c in HEX_CHARS for c in h)


def test_opencode_hash_is_12_hex_chars() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "opencode"],
        capture_output=True,
        text=True,
        check=True,
    )
    h = result.stdout.strip()
    assert len(h) == HASH_LENGTH
    assert all(c in HEX_CHARS for c in h)


def test_python_hash_matches_manual_sha256() -> None:
    h = hashlib.sha256()
    h.update(pathlib.Path("uv.lock").read_bytes())
    h.update(pathlib.Path("DragonglassApp/opencode/package.json").read_bytes())
    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            stderr=subprocess.DEVNULL,
        ).strip()
        h.update(version)
    except Exception:
        pass
    expected = h.hexdigest()[:12]
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "python"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected


def test_opencode_hash_matches_manual_sha256() -> None:
    content = pathlib.Path("DragonglassApp/opencode/package.json").read_bytes()
    expected = hashlib.sha256(content).hexdigest()[:12]
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "opencode"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected
