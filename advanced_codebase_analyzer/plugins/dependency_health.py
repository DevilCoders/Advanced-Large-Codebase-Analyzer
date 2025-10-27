"""Plugin that evaluates dependency hygiene."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from ..core.metadata import PluginFinding
from ..core.plugins import AnalysisContext, AnalyzerPlugin


class DependencyHealthPlugin(AnalyzerPlugin):
    name = "Dependency health"
    description = "Highlight unpinned, duplicate, and VCS-based dependencies."

    UNPINNED_PREFIXES = ("^", "~", ">", "<", "*")
    VCS_PREFIXES = ("git+", "hg+", "svn+", "bzr+", "http://", "https://")
    LOCAL_PREFIXES = ("file:", "./", "../")

    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding]:
        findings: List[PluginFinding] = []
        unpinned: List[str] = []
        duplicates: dict[str, List[str]] = defaultdict(list)
        vcs_backed: List[str] = []

        for dependency in context.dependencies:
            version = (dependency.version or "").strip()
            name_key = dependency.name.lower()
            label = dependency.label()
            duplicates[name_key].append(label)

            normalized = version.lower()
            if not version or normalized.startswith(self.UNPINNED_PREFIXES) or normalized in {"latest", "*"}:
                unpinned.append(label)
            if normalized.startswith(self.VCS_PREFIXES):
                vcs_backed.append(label)
            if normalized.startswith(self.LOCAL_PREFIXES):
                vcs_backed.append(label)

        duplicate_items = [labels for labels in duplicates.values() if len(labels) > 1]
        if duplicate_items:
            flattened = sorted({label for labels in duplicate_items for label in labels}, key=str.lower)
            findings.append(
                PluginFinding(
                    plugin=self.name,
                    title="Duplicate dependencies",
                    summary=", ".join(flattened[:10]) + (" and more" if len(flattened) > 10 else ""),
                    severity="warning",
                    metadata={"duplicates": duplicate_items},
                )
            )

        if unpinned:
            unpinned_sorted = sorted(set(unpinned), key=str.lower)
            findings.append(
                PluginFinding(
                    plugin=self.name,
                    title="Unpinned dependencies",
                    summary=", ".join(unpinned_sorted[:10]) + (" and more" if len(unpinned_sorted) > 10 else ""),
                    severity="warning",
                    metadata={"dependencies": unpinned_sorted},
                )
            )

        if vcs_backed:
            vcs_sorted = sorted(set(vcs_backed), key=str.lower)
            findings.append(
                PluginFinding(
                    plugin=self.name,
                    title="VCS or local path dependencies",
                    summary=", ".join(vcs_sorted[:10]) + (" and more" if len(vcs_sorted) > 10 else ""),
                    severity="info",
                    metadata={"dependencies": vcs_sorted},
                )
            )

        if not findings:
            findings.append(
                PluginFinding(
                    plugin=self.name,
                    title="Dependency hygiene",
                    summary="All discovered dependencies appear pinned and unique.",
                    severity="info",
                    metadata={},
                )
            )
        return findings


__all__ = ["DependencyHealthPlugin"]
