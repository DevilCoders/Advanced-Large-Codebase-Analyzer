"""Plugin that extracts metadata from git repositories."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Optional

from ..core.metadata import PluginFinding
from ..core.plugins import AnalysisContext, AnalyzerPlugin


class GitMetadataPlugin(AnalyzerPlugin):
    name = "Git metadata"
    description = "Capture branch, latest commit and cleanliness for Git repositories."

    def is_available(self) -> bool:
        return self._git_exists()

    def supports(self, context: AnalysisContext) -> bool:
        return (context.root / ".git").exists()

    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding]:
        branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=context.root)
        commit = self._run_git(["rev-parse", "HEAD"], cwd=context.root)
        status = self._run_git(["status", "--short"], cwd=context.root)
        summary = "Branch: {branch}\nCommit: {commit}"
        cleanliness = "clean" if not status else "dirty"
        yield PluginFinding(
            plugin="Git",
            title="Repository metadata",
            summary=summary.format(branch=branch or "unknown", commit=(commit or "unknown")[:12]),
            severity="info" if cleanliness == "clean" else "warning",
            metadata={
                "branch": branch,
                "commit": commit,
                "dirty": bool(status),
                "changed_files": status.splitlines() if status else [],
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _git_exists() -> bool:
        try:
            subprocess.run(["git", "--version"], check=False, capture_output=True)
        except FileNotFoundError:
            return False
        return True

    @staticmethod
    def _run_git(args: list[str], cwd: Path) -> Optional[str]:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                capture_output=True,
                check=False,
                text=True,
            )
        except FileNotFoundError:
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()


__all__ = ["GitMetadataPlugin"]

