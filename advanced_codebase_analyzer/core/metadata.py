"""Data models shared across the codebase analyzer."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(slots=True)
class FileSummary:
    """Summary information for a collection of related files.

    Attributes:
        category: Human readable name for this file bucket.
        count: Number of files captured in the bucket.
        total_bytes: Total size for the files in bytes.
        examples: Sample file paths (relative to scan root) for preview.
    """

    category: str
    count: int
    total_bytes: int
    examples: List[str] = field(default_factory=list)

    @property
    def human_size(self) -> str:
        """Return a human friendly size string."""
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        value = float(self.total_bytes)
        for suffix in suffixes:
            if value < 1024 or suffix == suffixes[-1]:
                return f"{value:.2f} {suffix}"
            value /= 1024
        return f"{value:.2f} TB"


@dataclass(slots=True)
class DependencyRecord:
    """Represents a dependency discovered in the code base."""

    name: str
    version: Optional[str]
    source_file: Path
    metadata: Dict[str, str] = field(default_factory=dict)

    def label(self) -> str:
        version_suffix = f"=={self.version}" if self.version else ""
        return f"{self.name}{version_suffix}"


@dataclass(slots=True)
class PackageRecord:
    """Represents a language specific package discovered in the project."""

    name: str
    root: Path
    kind: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AnalysisReport:
    """High level outcome of a full repository scan."""

    root: Path
    files: Dict[str, FileSummary]
    dependencies: List[DependencyRecord]
    packages: List[PackageRecord]
    warnings: List[str] = field(default_factory=list)
    plugin_findings: List["PluginFinding"] = field(default_factory=list)

    def iter_files(self) -> Iterable[FileSummary]:
        return self.files.values()

    def iter_dependencies(self) -> Iterable[DependencyRecord]:
        return self.dependencies

    def iter_packages(self) -> Iterable[PackageRecord]:
        return self.packages

    def iter_plugin_findings(self) -> Iterable["PluginFinding"]:
        return self.plugin_findings


@dataclass(slots=True)
class PluginFinding:
    """Represents the output of a plugin execution."""

    plugin: str
    title: str
    summary: str
    severity: str = "info"
    metadata: Dict[str, object] = field(default_factory=dict)
