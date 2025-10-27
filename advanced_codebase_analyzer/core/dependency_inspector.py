"""Inspect a repository for dependency manifest files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from .metadata import DependencyRecord, PackageRecord

_REQUIREMENTS_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.\-]+)(?P<version>==[A-Za-z0-9_.\-]+)?")


class DependencyInspector:
    """Collect dependencies across common ecosystems."""

    def __init__(self) -> None:
        self.handlers = [
            self._from_requirements,
            self._from_pyproject,
            self._from_package_json,
        ]

    def scan(self, root: Path) -> List[DependencyRecord]:
        dependencies: List[DependencyRecord] = []
        for handler in self.handlers:
            dependencies.extend(handler(root))
        return dependencies

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _from_requirements(self, root: Path) -> List[DependencyRecord]:
        results: List[DependencyRecord] = []
        for requirements in root.rglob("requirements*.txt"):
            for line in requirements.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = _REQUIREMENTS_RE.match(line)
                if not match:
                    continue
                name = match.group("name")
                version = (match.group("version") or "").lstrip("=") or None
                results.append(
                    DependencyRecord(
                        name=name,
                        version=version,
                        source_file=requirements,
                        metadata={"line": line},
                    )
                )
        return results

    def _from_pyproject(self, root: Path) -> List[DependencyRecord]:
        path = root / "pyproject.toml"
        if not path.exists():
            return []
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(path.read_text())
        dependencies: List[DependencyRecord] = []
        project = data.get("project") or {}
        deps = project.get("dependencies", [])
        for dep in deps:
            if isinstance(dep, str):
                pkg, _, version = dep.partition(" ")
                dependencies.append(
                    DependencyRecord(
                        name=pkg,
                        version=version.strip() or None,
                        source_file=path,
                    )
                )
        optional = project.get("optional-dependencies", {})
        for group_name, group_deps in optional.items():
            for dep in group_deps:
                pkg, _, version = dep.partition(" ")
                dependencies.append(
                    DependencyRecord(
                        name=pkg,
                        version=version.strip() or None,
                        source_file=path,
                        metadata={"group": group_name},
                    )
                )
        return dependencies

    def _from_package_json(self, root: Path) -> List[DependencyRecord]:
        path = root / "package.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            return []
        dependencies: List[DependencyRecord] = []
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in data.get(section, {}).items():
                dependencies.append(
                    DependencyRecord(
                        name=name,
                        version=version,
                        source_file=path,
                        metadata={"section": section},
                    )
                )
        return dependencies


class PackageDetector:
    """Heuristically detect language specific packages."""

    def __init__(self) -> None:
        self.detectors = [
            self._python_packages,
            self._node_packages,
        ]

    def scan(self, root: Path) -> List[PackageRecord]:
        packages: List[PackageRecord] = []
        for detector in self.detectors:
            packages.extend(detector(root))
        return packages

    def _python_packages(self, root: Path) -> List[PackageRecord]:
        packages: List[PackageRecord] = []
        for pkg_root in root.rglob("__init__.py"):
            name = pkg_root.parent.name
            packages.append(
                PackageRecord(name=name, root=pkg_root.parent, kind="python")
            )
        return packages

    def _node_packages(self, root: Path) -> List[PackageRecord]:
        packages: List[PackageRecord] = []
        for package_json in root.rglob("package.json"):
            try:
                data = json.loads(package_json.read_text())
            except json.JSONDecodeError:
                continue
            name = data.get("name") or package_json.parent.name
            packages.append(
                PackageRecord(
                    name=name,
                    root=package_json.parent,
                    kind="node",
                    metadata={"version": data.get("version", "unknown")},
                )
            )
        return packages
