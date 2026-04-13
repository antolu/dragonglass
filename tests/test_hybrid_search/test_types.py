from __future__ import annotations

import dataclasses
import json

import pytest

from dragonglass.hybrid_search import KeywordHit, SemanticResult, VectorHit


def test_keyword_hit_serializable() -> None:
    hit = KeywordHit(path="notes/foo.md")
    d = dataclasses.asdict(hit)
    assert json.dumps(d) == '{"path": "notes/foo.md"}'


def test_vector_hit_serializable() -> None:
    hit = VectorHit(path="notes/bar.md", score=0.85)
    d = dataclasses.asdict(hit)
    json_str = json.dumps(d)
    parsed = json.loads(json_str)
    assert parsed["path"] == "notes/bar.md"
    assert parsed["score"] == pytest.approx(0.85)


def test_semantic_result_serializable() -> None:
    result = SemanticResult(path="notes/baz.md", score=0.9, reasoning="matches topic")
    d = dataclasses.asdict(result)
    json_str = json.dumps(d)
    parsed = json.loads(json_str)
    assert parsed["path"] == "notes/baz.md"
    assert parsed["score"] == pytest.approx(0.9)
    assert parsed["reasoning"] == "matches topic"


def test_semantic_result_default_reasoning() -> None:
    result = SemanticResult(path="notes/x.md", score=0.5)
    assert not result.reasoning


def test_types_frozen() -> None:
    hit = KeywordHit(path="notes/foo.md")
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.path = "other.md"  # type: ignore[misc]

    vhit = VectorHit(path="notes/foo.md", score=0.5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        vhit.score = 0.9  # type: ignore[misc]
