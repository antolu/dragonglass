from __future__ import annotations

import dataclasses
import logging
import uuid

from dragonglass.hybrid_search._types import SearchHit, SemanticResult

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SearchSession:
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4())[:8])
    keyword_hits: list[SearchHit] = dataclasses.field(default_factory=list)
    vector_hits: list[SearchHit] = dataclasses.field(default_factory=list)
    semantic_hits: list[SemanticResult] = dataclasses.field(default_factory=list)
    last_read_hash_by_path: dict[str, str] = dataclasses.field(default_factory=dict)
    _allowlist_override: list[str] | None = dataclasses.field(
        default=None, repr=False, compare=False
    )

    def add_keyword_hits(self, hits: list[SearchHit]) -> None:
        before = len(self.keyword_hits)
        seen = {h.path for h in self.keyword_hits}
        for hit in hits:
            if hit.path not in seen:
                seen.add(hit.path)
                self.keyword_hits.append(hit)
        logger.debug(
            "session=%s add_keyword_hits added=%d total=%d",
            self.id,
            len(self.keyword_hits) - before,
            len(self.keyword_hits),
        )

    def add_vector_hits(self, hits: list[SearchHit]) -> None:
        before = len(self.vector_hits)
        seen = {h.path for h in self.vector_hits}
        for hit in hits:
            if hit.path not in seen:
                seen.add(hit.path)
                self.vector_hits.append(hit)
        logger.debug(
            "session=%s add_vector_hits added=%d total=%d",
            self.id,
            len(self.vector_hits) - before,
            len(self.vector_hits),
        )

    def add_semantic_hits(self, hits: list[SemanticResult]) -> None:
        self.semantic_hits.extend(hits)

    def set_allowlist(self, paths: list[str]) -> None:
        self._allowlist_override = list(paths)
        logger.debug("session=%s set_allowlist paths=%d", self.id, len(paths))

    def clear_allowlist_override(self) -> None:
        self._allowlist_override = None

    @property
    def allowlist(self) -> list[str]:
        if self._allowlist_override is not None:
            return self._allowlist_override
        return sorted({h.path for h in self.keyword_hits})

    def clear(self) -> None:
        self.keyword_hits.clear()
        self.vector_hits.clear()
        self.semantic_hits.clear()
        self.last_read_hash_by_path.clear()
        self._allowlist_override = None

    def set_last_read_hash(self, path: str, content_hash: str) -> None:
        self.last_read_hash_by_path[path] = content_hash
        logger.debug(
            "session=%s set_last_read_hash path=%s tracked=%d",
            self.id,
            path,
            len(self.last_read_hash_by_path),
        )

    def get_last_read_hash(self, path: str) -> str | None:
        return self.last_read_hash_by_path.get(path)
