# Insights and Heuristics

Beyond raw inventory data, the analyzer surfaces heuristic warnings to guide remediation work. These insights help teams prioritise documentation, dependency hygiene, and repository hygiene tasks that often fall behind in large codebases.

## Insight engine

`advanced_codebase_analyzer.core.insights` defines the `InsightEngine`, which evaluates a sequence of `InsightRule` subclasses. During analysis, the engine receives an `InsightContext` containing the repository root, aggregated file summaries, dependency records, and detected packages.

Each rule implements `evaluate(context)` and yields zero or more human-readable warning strings. The engine concatenates the results, removes duplicates while preserving order, and returns the list to the analyzer. The GUI displays these warnings in a banner above the results notebook.

## Built-in rules

| Rule | Trigger | Recommendation |
| --- | --- | --- |
| `PackagePresenceRule` | No packages detected in the scan root. | Verify the directory selection or ensure packages include `__init__.py` or `package.json`. |
| `ReadmePresenceRule` | No README file found among common variants. | Add a top-level README to orient contributors. |
| `UnpinnedPythonDependenciesRule` | Dependencies without explicit versions or using wildcards (`*`, `latest`, `>`, `<`, `^`, `~`). | Pin versions to encourage reproducible environments. |
| `DocumentationCoverageRule` | Markdown count is less than the number of detected packages. | Expand documentation to cover each module or service. |

## Customising insights

You can inject your own rules by instantiating `InsightEngine` with a custom sequence:

```python
from advanced_codebase_analyzer.core.insights import InsightEngine, InsightRule


class SecurityNoticeRule(InsightRule):
    name = "security-notice"
    description = "Alert if SECURITY.md is missing."

    def evaluate(self, context):
        if not (context.root / "SECURITY.md").exists():
            yield "Add a SECURITY.md file describing the vulnerability disclosure process."


def build_engine():
    return InsightEngine(rules=(SecurityNoticeRule(),))
```

You can then wire the custom engine into a bespoke front-end or modify `CodebaseAnalyzer` instantiation to use it.

## Relationship to plugins

Insights differ from plugins in two key ways:

- **Execution timing:** Insight rules run synchronously within the core analyzer, whereas plugins are discovered dynamically and may return structured findings.
- **Output format:** Insight rules yield plain warning strings intended for quick guidance, while plugins return `PluginFinding` objects with severity, summaries, and metadata.

Use insight rules for lightweight heuristics and rely on plugins for more involved analyses that benefit from structured output.
