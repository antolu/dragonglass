from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class SearchHit:
    path: str
    score: float | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class SemanticResult:
    path: str
    score: float
    reasoning: str = ""
