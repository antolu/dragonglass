from __future__ import annotations

from dragonglass.hybrid_search import SearchHit, SearchSession


def test_add_keyword_hits() -> None:
    session = SearchSession()
    session.add_keyword_hits([SearchHit(path="a.md"), SearchHit(path="b.md")])
    assert len(session.keyword_hits) == 2  # noqa: PLR2004
    paths = {h.path for h in session.keyword_hits}
    assert "a.md" in paths
    assert "b.md" in paths


def test_add_keyword_hits_deduplicates() -> None:
    session = SearchSession()
    session.add_keyword_hits([SearchHit(path="a.md"), SearchHit(path="b.md")])
    session.add_keyword_hits([SearchHit(path="b.md"), SearchHit(path="c.md")])
    assert len(session.keyword_hits) == 3  # noqa: PLR2004


def test_add_vector_hits() -> None:
    session = SearchSession()
    session.add_vector_hits([SearchHit(path="x.md", score=0.8)])
    assert len(session.vector_hits) == 1
    assert session.vector_hits[0].path == "x.md"


def test_add_vector_hits_deduplicates() -> None:
    session = SearchSession()
    session.add_vector_hits([SearchHit(path="x.md", score=0.8)])
    session.add_vector_hits([SearchHit(path="x.md", score=0.9)])
    assert len(session.vector_hits) == 1


def test_allowlist_from_keyword_hits_sorted() -> None:
    session = SearchSession()
    session.add_keyword_hits([
        SearchHit(path="z.md"),
        SearchHit(path="a.md"),
        SearchHit(path="m.md"),
    ])
    assert session.allowlist == ["a.md", "m.md", "z.md"]


def test_allowlist_override() -> None:
    session = SearchSession()
    session.add_keyword_hits([SearchHit(path="a.md")])
    session.set_allowlist(["forced.md"])
    assert session.allowlist == ["forced.md"]


def test_allowlist_override_cleared() -> None:
    session = SearchSession()
    session.add_keyword_hits([SearchHit(path="a.md")])
    session.set_allowlist(["forced.md"])
    session.clear_allowlist_override()
    assert session.allowlist == ["a.md"]


def test_set_and_get_last_read_hash() -> None:
    session = SearchSession()
    session.set_last_read_hash("note.md", "abc123")
    assert session.get_last_read_hash("note.md") == "abc123"
    assert session.get_last_read_hash("other.md") is None


def test_clear() -> None:
    session = SearchSession()
    session.add_keyword_hits([SearchHit(path="a.md")])
    session.add_vector_hits([SearchHit(path="b.md", score=0.7)])
    session.set_last_read_hash("a.md", "hash")
    session.set_allowlist(["forced.md"])
    session.clear()
    assert len(session.keyword_hits) == 0
    assert len(session.vector_hits) == 0
    assert session.get_last_read_hash("a.md") is None
    assert session.allowlist == []


def test_session_has_unique_id() -> None:
    s1 = SearchSession()
    s2 = SearchSession()
    assert s1.id != s2.id
    assert len(s1.id) == 8  # noqa: PLR2004
