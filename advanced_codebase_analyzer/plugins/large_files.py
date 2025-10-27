"""Plugin that surfaces the largest files within a repository."""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from ..core.file_indexer import FileIndexer
from ..core.metadata import PluginFinding
from ..core.plugins import AnalysisContext, AnalyzerPlugin


@dataclass(slots=True)
class LargeFileRecord:
    path: Path
    size: int

    def to_finding(self, root: Path) -> PluginFinding:
        try:
            relative_path = self.path.relative_to(root)
        except ValueError:
            relative_path = self.path
        return PluginFinding(
            plugin="Large files",
            title=str(relative_path),
            summary=f"{self.size / (1024 * 1024):.2f} MB",
            severity="warning" if self.size >= 100 * 1024 * 1024 else "info",
            metadata={"bytes": self.size},
        )


class LargeFilePlugin(AnalyzerPlugin):
    name = "Large file detector"
    description = "Identify the top ten largest files within the repository."

    def __init__(self, threshold: int = 10 * 1024 * 1024, limit: int = 10) -> None:
        self.threshold = threshold
        self.limit = limit

    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding]:
        records = list(self._find_large_files(context.root))
        return [record.to_finding(context.root) for record in records]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_large_files(self, root: Path) -> Iterator[LargeFileRecord]:
        indexer = FileIndexer(follow_symlinks=False)
        heap: List[Tuple[int, Path]] = []
        for path, stat in indexer.iter_paths(root):
            size = stat.st_size
            if size < self.threshold:
                continue
            heapq.heappush(heap, (size, path))
            if len(heap) > self.limit:
                heapq.heappop(heap)
        for size, path in sorted(heap, reverse=True):
            yield LargeFileRecord(path=path, size=size)


__all__ = ["LargeFilePlugin"]

