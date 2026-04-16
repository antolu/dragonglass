from __future__ import annotations

import re

_OPENCODE_BUNDLE_RE = re.compile(
    r"dragonglass-opencode-(?P<deps_hash>[a-f0-9]{12})-(?P<os>[^-]+)-(?P<arch>[^-]+)\.tar\.gz"
)


def test_opencode_filename_format() -> None:
    name = "dragonglass-opencode-def789abc012-darwin-arm64.tar.gz"
    m = _OPENCODE_BUNDLE_RE.match(name)
    assert m is not None
    assert m.group("deps_hash") == "def789abc012"
    assert m.group("os") == "darwin"
    assert m.group("arch") == "arm64"


def test_opencode_filename_rejects_wrong_format() -> None:
    assert _OPENCODE_BUNDLE_RE.match("dragonglass-opencode.tar.gz") is None
    assert (
        _OPENCODE_BUNDLE_RE.match("dragonglass-deps-abc123def456-darwin-arm64.tar.gz")
        is None
    )


def test_opencode_filename_rejects_short_hash() -> None:
    assert (
        _OPENCODE_BUNDLE_RE.match("dragonglass-opencode-abc123-darwin-arm64.tar.gz")
        is None
    )


def test_opencode_filename_rejects_uppercase_hash() -> None:
    assert (
        _OPENCODE_BUNDLE_RE.match(
            "dragonglass-opencode-ABC123DEF456-darwin-arm64.tar.gz"
        )
        is None
    )
