"""Heuristic insights that augment the core analysis report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .metadata import DependencyRecord, FileSummary, PackageRecord


@dataclass(slots=True)
class InsightContext:
    """Snapshot of analyzer state used by insight rules."""

    root: Path
    files: Dict[str, FileSummary]
    dependencies: Sequence[DependencyRecord]
    packages: Sequence[PackageRecord]


class InsightRule:
    """Base class for lightweight heuristic checks."""

    name: str = ""
    description: str = ""

    def evaluate(self, context: InsightContext) -> Iterable[str]:
        return []


class PackagePresenceRule(InsightRule):
    name = "package-presence"
    description = "Ensure the scan root contains at least one detected package."

    def evaluate(self, context: InsightContext) -> Iterable[str]:
        if not context.packages:
            yield "No packages detected. Consider verifying the scan root."


class ReadmePresenceRule(InsightRule):
    name = "readme"
    description = "Recommend a top-level README for quick orientation."

    CANDIDATES = (
        "README",
        "README.md",
        "README.rst",
        "README.txt",
    )

    def evaluate(self, context: InsightContext) -> Iterable[str]:
        if any((context.root / candidate).exists() for candidate in self.CANDIDATES):
            return []
        yield "No README found at the repository root. Add one to describe the project."  # noqa: E501


class UnpinnedPythonDependenciesRule(InsightRule):
    name = "unpinned-python-deps"
    description = "Identify Python dependencies without pinned versions."

    def evaluate(self, context: InsightContext) -> Iterable[str]:
        offenders: List[str] = []
        for dependency in context.dependencies:
            if dependency.source_file.suffix not in {".txt", ".toml"}:
                continue
            version = dependency.version or ""
            if not version:
                offenders.append(dependency.label())
                continue
            normalized = version.lower().strip()
            if normalized in {"*", "latest"}:
                offenders.append(dependency.label())
                continue
            if normalized.startswith((">", "<", "^", "~")):
                offenders.append(dependency.label())
        if not offenders:
            return []
        offenders.sort(key=str.lower)
        yield (
            "Unpinned Python dependencies detected: "
            + ", ".join(offenders[:8])
            + (" and more" if len(offenders) > 8 else "")
            + ". Pin dependencies to promote deterministic builds."
        )


class DocumentationCoverageRule(InsightRule):
    name = "documentation-coverage"
    description = "Encourage a minimum amount of Markdown documentation."

    def evaluate(self, context: InsightContext) -> Iterable[str]:
        markdown = context.files.get("Markdown")
        if not markdown or markdown.count < max(1, len(context.packages)):
            yield (
                "Limited Markdown documentation discovered. Consider expanding the "
                "docs to cover the detected packages."
            )


class InsightEngine:
    """Evaluate heuristic rules to produce actionable warnings."""

    def __init__(self, rules: Sequence[InsightRule] | None = None) -> None:
        if rules is None:
            rules = (
                PackagePresenceRule(),
                ReadmePresenceRule(),
                UnpinnedPythonDependenciesRule(),
                DocumentationCoverageRule(),
            )
        self.rules: List[InsightRule] = list(rules)

    def generate(self, context: InsightContext) -> List[str]:
        warnings: List[str] = []
        for rule in self.rules:
            warnings.extend(rule.evaluate(context))
        # Remove potential duplicates while preserving order
        seen: set[str] = set()
        unique: List[str] = []
        for warning in warnings:
            if warning not in seen:
                seen.add(warning)
                unique.append(warning)
        return unique


__all__ = [
    "DocumentationCoverageRule",
    "InsightContext",
    "InsightEngine",
    "InsightRule",
    "PackagePresenceRule",
    "ReadmePresenceRule",
    "UnpinnedPythonDependenciesRule",
]
