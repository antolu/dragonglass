from __future__ import annotations

import dataclasses
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ScoredResult:
    path: str
    score: float


class SearchSession:
    _current: SearchSession | None = None

    def __init__(self) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.file_paths: set[str] = set()
        self.last_read_hash_by_path: dict[str, str] = {}

    def add_keyword_results(self, paths: list[str]) -> None:
        before = len(self.file_paths)
        self.file_paths.update(paths)
        logger.debug(
            "search session=%s add_keyword_results added=%d total=%d",
            self.id,
            len(self.file_paths) - before,
            len(self.file_paths),
        )

    def clear(self) -> None:
        self.file_paths.clear()
        self.last_read_hash_by_path.clear()

    def set_last_read_hash(self, path: str, content_hash: str) -> None:
        self.last_read_hash_by_path[path] = content_hash
        logger.debug(
            "search session=%s set_last_read_hash path=%s tracked=%d",
            self.id,
            path,
            len(self.last_read_hash_by_path),
        )

    def get_last_read_hash(self, path: str) -> str | None:
        return self.last_read_hash_by_path.get(path)

    @property
    def allowlist(self) -> list[str]:
        return sorted(self.file_paths)

    @classmethod
    def get_current(cls) -> SearchSession | None:
        return cls._current

    @classmethod
    def create_new(cls) -> SearchSession:
        cls._current = cls()
        logger.info("search session created id=%s", cls._current.id)
        return cls._current


def get_current_session() -> SearchSession | None:
    return SearchSession.get_current()


def new_session() -> SearchSession:
    return SearchSession.create_new()
