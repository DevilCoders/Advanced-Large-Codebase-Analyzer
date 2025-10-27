"""High level orchestration for codebase analysis."""
from __future__ import annotations

from pathlib import Path
from .dependency_inspector import DependencyInspector, PackageDetector
from .file_indexer import FileIndexer
from .insights import InsightContext, InsightEngine
from .metadata import AnalysisReport
from .plugins import AnalysisContext, PluginManager


class CodebaseAnalyzer:
    """Combine multiple scanners to produce a rich report."""

    def __init__(
        self,
        follow_symlinks: bool = False,
        max_examples: int = 5,
    ) -> None:
        self.indexer = FileIndexer(follow_symlinks=follow_symlinks, max_examples=max_examples)
        self.dependency_inspector = DependencyInspector()
        self.package_detector = PackageDetector()
        self.insight_engine = InsightEngine()
        self.plugin_manager = PluginManager()

    def analyze(self, path: str | Path) -> AnalysisReport:
        root = Path(path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")
        file_summary = self.indexer.summarize(root)
        dependencies = self.dependency_inspector.scan(root)
        packages = self.package_detector.scan(root)
        plugin_context = AnalysisContext(
            root=root,
            files=file_summary,
            dependencies=dependencies,
            packages=packages,
        )
        plugin_findings = self.plugin_manager.run(plugin_context)
        insight_context = InsightContext(
            root=root,
            files=file_summary,
            dependencies=dependencies,
            packages=packages,
        )
        warnings = self.insight_engine.generate(insight_context)
        return AnalysisReport(
            root=root,
            files=file_summary,
            dependencies=sorted(dependencies, key=lambda d: d.name.lower()),
            packages=sorted(packages, key=lambda p: p.name.lower()),
            warnings=warnings,
            plugin_findings=plugin_findings,
        )
