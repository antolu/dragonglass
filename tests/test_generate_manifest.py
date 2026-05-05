from __future__ import annotations

import re

_PYTHON_BUNDLE_RE = re.compile(
    r"dragonglass-deps-(?P<deps_hash>[a-f0-9]{12})-(?P<os>[^-]+)-(?P<arch>[^-]+)-py(?P<python>[\d.]+)\.tar\.gz"
)


def test_python_bundle_re_matches() -> None:
    name = "dragonglass-deps-abc123def456-darwin-arm64-py3.13.tar.gz"
    m = _PYTHON_BUNDLE_RE.match(name)
    assert m is not None
    assert m.group("deps_hash") == "abc123def456"
    assert m.group("os") == "darwin"
    assert m.group("arch") == "arm64"
    assert m.group("python") == "3.13"


def test_python_bundle_re_rejects_old_version_format() -> None:
    assert (
        _PYTHON_BUNDLE_RE.match("dragonglass-deps-1.2.3-darwin-arm64-py3.13.tar.gz")
        is None
    )
