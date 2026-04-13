from __future__ import annotations

from dragonglass.hybrid_search import SearchSession


def test_add_keyword_results() -> None:
    session = SearchSession()
    session.add_keyword_results(["a.md", "b.md"])
    assert "a.md" in session.file_paths
    assert "b.md" in session.file_paths


def test_add_keyword_results_deduplicates() -> None:
    session = SearchSession()
    session.add_keyword_results(["a.md", "b.md"])
    session.add_keyword_results(["b.md", "c.md"])
    assert len(session.file_paths) == 3  # noqa: PLR2004


def test_allowlist_sorted() -> None:
    session = SearchSession()
    session.add_keyword_results(["z.md", "a.md", "m.md"])
    assert session.allowlist == ["a.md", "m.md", "z.md"]


def test_set_and_get_last_read_hash() -> None:
    session = SearchSession()
    session.set_last_read_hash("note.md", "abc123")
    assert session.get_last_read_hash("note.md") == "abc123"
    assert session.get_last_read_hash("other.md") is None


def test_clear() -> None:
    session = SearchSession()
    session.add_keyword_results(["a.md"])
    session.set_last_read_hash("a.md", "hash")
    session.clear()
    assert len(session.file_paths) == 0
    assert session.get_last_read_hash("a.md") is None


def test_session_has_unique_id() -> None:
    s1 = SearchSession()
    s2 = SearchSession()
    assert s1.id != s2.id
    assert len(s1.id) == 8  # noqa: PLR2004
