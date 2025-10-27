"""Plugin that inventories license and notice files."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from ..core.file_indexer import FileIndexer
from ..core.metadata import PluginFinding
from ..core.plugins import AnalysisContext, AnalyzerPlugin


class LicenseInventoryPlugin(AnalyzerPlugin):
    name = "License inventory"
    description = "List LICENSE, NOTICE, and COPYING files discovered in the tree."

    CANDIDATE_PREFIXES = ("LICENSE", "COPYING", "NOTICE")

    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding]:
        matches = self._find_license_files(context.root)
        if not matches:
            return [
                PluginFinding(
                    plugin=self.name,
                    title="No license artifacts",
                    summary="No LICENSE or NOTICE files were discovered.",
                    severity="warning",
                    metadata={},
                )
            ]
        matches.sort()
        return [
            PluginFinding(
                plugin=self.name,
                title=f"{len(matches)} license artifact(s)",
                summary=", ".join(matches[:10]) + (" and more" if len(matches) > 10 else ""),
                severity="info",
                metadata={"files": matches},
            )
        ]

    def _find_license_files(self, root: Path) -> List[str]:
        indexer = FileIndexer(follow_symlinks=False, max_examples=0)
        results: List[str] = []
        root = root.resolve()
        for path, _ in indexer.iter_paths(root):
            upper_name = path.name.upper()
            if any(upper_name.startswith(prefix) for prefix in self.CANDIDATE_PREFIXES):
                try:
                    relative = str(path.relative_to(root))
                except ValueError:
                    relative = str(path)
                results.append(relative)
        return results


__all__ = ["LicenseInventoryPlugin"]
