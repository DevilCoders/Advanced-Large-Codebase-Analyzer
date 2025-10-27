"""Plugin system powering the advanced analyzer."""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Type

from .metadata import AnalysisReport, DependencyRecord, FileSummary, PackageRecord, PluginFinding


@dataclass(slots=True)
class AnalysisContext:
    """Snapshot of analyzer state shared with plugins."""

    root: Path
    files: dict[str, FileSummary]
    dependencies: Sequence[DependencyRecord]
    packages: Sequence[PackageRecord]

    def to_report(self) -> AnalysisReport:
        """Create a partial report with the currently known data."""

        return AnalysisReport(
            root=self.root,
            files=dict(self.files),
            dependencies=list(self.dependencies),
            packages=list(self.packages),
            plugin_findings=[],
        )


class AnalyzerPlugin:
    """Base class for all analyzer plugins."""

    #: Human friendly name displayed in the UI.
    name: str = "Unnamed Plugin"

    #: Short sentence describing what the plugin surfaces.
    description: str = ""

    def is_available(self) -> bool:
        """Return whether the plugin can run in the current environment."""

        return True

    def supports(self, context: AnalysisContext) -> bool:
        """Return whether the plugin should run for this repository."""

        return True

    # The return type can be an iterable or a single finding for ergonomics.
    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding] | PluginFinding:
        raise NotImplementedError


class PluginManager:
    """Locate and execute plugins bundled with the tool."""

    def __init__(self) -> None:
        self._plugin_types: List[Type[AnalyzerPlugin]] = list(self._discover_builtin_plugins())

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def _discover_builtin_plugins(self) -> Iterator[Type[AnalyzerPlugin]]:
        from .. import plugins

        package_path = plugins.__path__  # type: ignore[attr-defined]
        prefix = plugins.__name__ + "."
        for module_info in pkgutil.iter_modules(package_path, prefix):
            module = importlib.import_module(module_info.name)
            candidates = self._collect_plugin_types(module)
            for candidate in candidates:
                yield candidate

    @staticmethod
    def _collect_plugin_types(module: object) -> Iterator[Type[AnalyzerPlugin]]:
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, AnalyzerPlugin) and value is not AnalyzerPlugin:
                yield value

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run(self, context: AnalysisContext) -> List[PluginFinding]:
        findings: List[PluginFinding] = []
        for plugin_type in self._plugin_types:
            plugin = plugin_type()
            if not plugin.is_available():
                continue
            if not plugin.supports(context):
                continue
            results = plugin.collect(context)
            if isinstance(results, PluginFinding):
                results = [results]
            findings.extend(results)
        findings.sort(key=lambda f: (f.plugin.lower(), f.title.lower()))
        return findings


__all__ = [
    "AnalysisContext",
    "AnalyzerPlugin",
    "PluginManager",
]

