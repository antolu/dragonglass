from __future__ import annotations

import re

_BUNDLE_RE = re.compile(
    r"dragonglass-deps-(?P<ver>[^-]+)-(?P<os>[^-]+)-(?P<arch>[^-]+)-py(?P<python>[\d.]+)\.tar\.gz"
)


def test_bundle_re_matches_standard_version() -> None:
    name = "dragonglass-deps-1.2.3-darwin-arm64-py3.13.tar.gz"
    m = _BUNDLE_RE.match(name)
    assert m is not None
    assert m.group("ver") == "1.2.3"
    assert m.group("os") == "darwin"
    assert m.group("arch") == "arm64"
    assert m.group("python") == "3.13"


def test_bundle_re_matches_post_version() -> None:
    name = "dragonglass-deps-1.2.3.post1-linux-x86_64-py3.11.tar.gz"
    m = _BUNDLE_RE.match(name)
    assert m is not None
    assert m.group("ver") == "1.2.3.post1"
    assert m.group("os") == "linux"
    assert m.group("arch") == "x86_64"
    assert m.group("python") == "3.11"


def test_bundle_re_rejects_unrecognised_name() -> None:
    assert _BUNDLE_RE.match("someother-bundle.tar.gz") is None
    assert _BUNDLE_RE.match("dragonglass-deps.tar.gz") is None
