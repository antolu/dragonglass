from __future__ import annotations

import dataclasses
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SearchSession:
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4())[:8])
    file_paths: set[str] = dataclasses.field(default_factory=set)
    last_read_hash_by_path: dict[str, str] = dataclasses.field(default_factory=dict)

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
