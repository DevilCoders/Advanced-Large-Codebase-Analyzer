"""Plugin that detects common CI/CD providers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from ..core.metadata import PluginFinding
from ..core.plugins import AnalysisContext, AnalyzerPlugin


class ContinuousIntegrationPlugin(AnalyzerPlugin):
    name = "CI coverage"
    description = "Report which CI/CD providers are configured for the repository."

    def collect(self, context: AnalysisContext) -> Iterable[PluginFinding]:
        providers = self._detect_providers(context.root)
        if not providers:
            return [
                PluginFinding(
                    plugin=self.name,
                    title="No CI configuration detected",
                    summary="No GitHub Actions, GitLab CI, or Azure Pipelines workflows found.",
                    severity="warning",
                    metadata={},
                )
            ]
        providers.sort()
        return [
            PluginFinding(
                plugin=self.name,
                title=f"{', '.join(providers)} configured",
                summary="Repository contains CI workflows for " + ", ".join(providers),
                severity="info",
                metadata={"providers": providers},
            )
        ]

    def _detect_providers(self, root: Path) -> List[str]:
        providers: List[str] = []
        github = root / ".github" / "workflows"
        gitlab = root / ".gitlab-ci.yml"
        azure = root / "azure-pipelines.yml"
        circleci = root / ".circleci"
        if any(github.glob("*.yml")) or any(github.glob("*.yaml")):
            providers.append("GitHub Actions")
        if gitlab.exists():
            providers.append("GitLab CI")
        if azure.exists():
            providers.append("Azure Pipelines")
        if (circleci / "config.yml").exists():
            providers.append("CircleCI")
        return providers


__all__ = ["ContinuousIntegrationPlugin"]
