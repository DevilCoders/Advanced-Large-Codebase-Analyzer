# Plugin System

The plugin system allows you to extend the analyzer with custom insights without changing the core code. Plugins execute after the primary scan completes and receive the full analysis context so they can contribute additional findings.

## Lifecycle

1. `PluginManager` searches the `advanced_codebase_analyzer.plugins` package for subclasses of `AnalyzerPlugin` using `pkgutil.iter_modules`.
2. Each plugin class is instantiated and probed via `is_available()`. You can override this method to ensure optional dependencies or platform requirements are met before executing the plugin.
3. If `supports(context)` returns `True`, the analyzer calls `collect(context)`.
4. `collect` may yield a single `PluginFinding` or an iterable of findings. The manager normalises the result, aggregates it with other plugins, and sorts the combined list before returning it to the analyzer.

All findings appear in the GUI's **Plugins** tab and are included in exported JSON reports.

## Writing a plugin

```python
from advanced_codebase_analyzer.core.metadata import PluginFinding
from advanced_codebase_analyzer.core.plugins import AnalysisContext, AnalyzerPlugin


class MyPlugin(AnalyzerPlugin):
    name = "Custom insight"
    description = "Explain what the plugin surfaces."

    def collect(self, context: AnalysisContext):
        # inspect context.root, context.files, context.dependencies, or context.packages
        if some_condition:
            yield PluginFinding(
                plugin=self.name,
                title="Short summary",
                summary="Detailed explanation for the user",
                severity="info",
                metadata={"path": "relative/path"},
            )
```

### Accessing scan data

- `context.root` – Absolute `Path` to the repository root selected by the user.
- `context.files` – Mapping of category name to `FileSummary` containing counts, total bytes, and example paths.
- `context.dependencies` – Sequence of `DependencyRecord` values covering Python and Node.js ecosystems.
- `context.packages` – Sequence of `PackageRecord` entries for Python packages and Node projects.

### Recommended patterns

- Use `PluginFinding.metadata` to attach structured data that downstream tooling can parse.
- Populate `PluginFinding.severity` with values such as `info`, `warning`, or `error` so the GUI can prioritise the results.
- For expensive checks, override `supports` to run only when the repository layout suggests the plugin is relevant.

## Built-in plugins

The tool ships with several plugins ready to use:

| Plugin | Description |
| --- | --- |
| `GitMetadataPlugin` | Captures branch name, latest commit, and working tree status by inspecting the `.git` directory. |
| `LargeFilePlugin` | Lists the largest files discovered during the scan so you can flag oversized artifacts. |
| `LicenseInventoryPlugin` | Enumerates `LICENSE`, `NOTICE`, and `COPYING` files for compliance reviews. |
| `DependencyHealthPlugin` | Highlights unpinned dependencies, duplicates, and VCS-sourced requirements. |
| `CIConfigPlugin` | Detects GitHub Actions, GitLab CI, Azure Pipelines, and CircleCI configurations to summarise CI coverage. |

You can add new modules under `advanced_codebase_analyzer/plugins/` and they will be discovered automatically on the next run.
