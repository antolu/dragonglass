from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class ScoredResult:
    path: str
    score: float


class SearchSession:
    _current: SearchSession | None = None

    def __init__(self) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.file_paths: set[str] = set()

    def add_keyword_results(self, paths: list[str]) -> None:
        self.file_paths.update(paths)

    def clear(self) -> None:
        self.file_paths.clear()

    @property
    def allowlist(self) -> list[str]:
        return sorted(self.file_paths)

    @classmethod
    def get_current(cls) -> SearchSession | None:
        return cls._current

    @classmethod
    def create_new(cls) -> SearchSession:
        cls._current = cls()
        return cls._current


def get_current_session() -> SearchSession | None:
    return SearchSession.get_current()


def new_session() -> SearchSession:
    return SearchSession.create_new()
