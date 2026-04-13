from __future__ import annotations

import dataclasses
import json

import pytest

from dragonglass.hybrid_search import SearchHit, SemanticResult


def test_search_hit_serializable_no_score() -> None:
    hit = SearchHit(path="notes/foo.md")
    d = dataclasses.asdict(hit)
    assert json.dumps(d) == '{"path": "notes/foo.md", "score": null}'


def test_search_hit_serializable_with_score() -> None:
    hit = SearchHit(path="notes/bar.md", score=0.85)
    d = dataclasses.asdict(hit)
    parsed = json.loads(json.dumps(d))
    assert parsed["path"] == "notes/bar.md"
    assert parsed["score"] == pytest.approx(0.85)


def test_semantic_result_serializable() -> None:
    result = SemanticResult(path="notes/baz.md", score=0.9, reasoning="matches topic")
    d = dataclasses.asdict(result)
    parsed = json.loads(json.dumps(d))
    assert parsed["path"] == "notes/baz.md"
    assert parsed["score"] == pytest.approx(0.9)
    assert parsed["reasoning"] == "matches topic"


def test_semantic_result_default_reasoning() -> None:
    result = SemanticResult(path="notes/x.md", score=0.5)
    assert not result.reasoning


def test_types_frozen() -> None:
    hit = SearchHit(path="notes/foo.md")
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.path = "other.md"  # type: ignore[misc]

    hit_scored = SearchHit(path="notes/foo.md", score=0.5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit_scored.score = 0.9  # type: ignore[misc]
