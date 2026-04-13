from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class KeywordHit:
    path: str


@dataclasses.dataclass(frozen=True, slots=True)
class VectorHit:
    path: str
    score: float


@dataclasses.dataclass(frozen=True, slots=True)
class SemanticResult:
    path: str
    score: float
    reasoning: str = ""
