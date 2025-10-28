# Advanced Large Codebase Analyzer

This project provides a desktop application that can quickly survey extremely large
codebases (hundreds of gigabytes) and surface the critical artifacts you care
about, including:

- Markdown and documentation files
- YAML configuration files
- PyTorch model artifacts (`.pt`, `.pth`)
- TensorFlow model artifacts (`.h5`, `.keras`, `.pb`, `.tflite`)
- ONNX models (`.onnx`)
- FlatBuffers schemas (`.fbs`)
- Training checkpoints (`.ckpt`)
- Application packages and modules
- Dependency manifests across Python and Node.js ecosystems

The application is built entirely with Python's standard library (Tkinter for the
GUI) so it can be executed without installing third-party packages.

## Features

- **High-throughput scanning** – a streaming file indexer walks the target
  repository breadth-first to keep the UI responsive, even for directories with
  millions of files.
- **Dependency awareness** – automatically parses `requirements*.txt`,
  `pyproject.toml`, and `package.json` files to build a dependency map.
- **Package discovery** – finds Python packages (directories containing
  `__init__.py`) and Node packages (directories with `package.json`).
- **Management workflow** – triage detected items directly in the UI by adding
  them to a management queue for follow-up or remediation.
- **Plugin powered insights** – extensible plugin system exposes additional
  insights such as large file detection and Git metadata without modifying the
  analyzer core.
- **Heuristic guidance** – an insight engine evaluates documentation coverage,
  README presence, and dependency pinning to highlight next steps directly in
  the analysis report.
- **Report lifecycle** – import previously exported JSON reports, export fresh
  scans, and replay the results without re-running the analyzer.
- **Neon operations console** – hacker-inspired UI with a searchable command
  center, live activity console, and context menus for opening items directly
  in your editor or file manager.
- **Deep search** – instant filtering across every tab (files, dependencies,
  packages, plugins) with keyboard-driven neon search.

## Getting started

1. Ensure you have Python 3.11 or later installed.
2. Launch the UI with:

   ```bash
   python -m advanced_codebase_analyzer
   ```
3. Select the target directory and click **Scan**. Double-click any row in the
   results to add it to the management queue, including plugin findings surfaced
   in the dedicated **Plugins** tab.
4. Use **File → Export Report** to save the findings as JSON, or **File → Import
   Report** to load a previous session.

## Building a standalone executable

The repository includes a PyInstaller helper so you can produce a Windows/Linux
`.exe` bundle without touching the source tree:

```bash
python scripts/build_executable.py --onefile --name advanced-analyzer
```

The script requires PyInstaller (`pip install pyinstaller`) and writes
artifacts to `dist/`.

## Documentation

Detailed guides are available in the `docs/` directory:

- [Project overview](docs/overview.md) – High-level summary of the tool's goals and capabilities.
- [Architecture](docs/architecture.md) – Component map, execution sequence, and extensibility points.
- [Plugin system](docs/plugins.md) – How discovery works and how to author custom plugins.
- [User interface guide](docs/ui-guide.md) – Walkthrough of the Tkinter application layout and interactions.
- [Insights and heuristics](docs/insights-and-heuristics.md) – Details on the heuristic warning engine and built-in rules.

## Architecture overview

```
advanced_codebase_analyzer/
├── __init__.py          # Package re-export of main UI helpers
├── __main__.py          # Module entry point for `python -m`
├── app.py               # Executable-friendly entry point wiring
├── core/                # Back-end scanning components
│   ├── analyzer.py      # Orchestrates file, dependency, package, and plugin scans
│   ├── dependency_inspector.py  # Parses dependency manifests and packages
│   ├── file_indexer.py  # Efficient file system traversal and summaries
│   ├── metadata.py      # Data models shared between components
│   └── plugins.py       # Plugin interfaces and discovery helpers
├── plugins/             # Built-in plugin implementations
│   ├── ci_config.py     # Detect GitHub Actions, GitLab CI, Azure, CircleCI
│   ├── dependency_health.py  # Flag duplicate, unpinned, and VCS dependencies
│   ├── git_metadata.py  # Git status, branch, commit information
│   ├── large_files.py   # Top-N large file detection
│   └── license_inventory.py  # Enumerate LICENSE and NOTICE artifacts
└── gui/                 # Tkinter user interface
    └── main_window.py   # Neon desktop experience with management workflow
```

The design separates scanning logic from the GUI so the backend can be reused in
CLI tools or headless environments in the future.

## Plugin system

Plugins provide a lightweight extension mechanism for surfacing new insights
without touching the analyzer core. Each plugin subclasses
`AnalyzerPlugin` from `advanced_codebase_analyzer.core.plugins` and implements
the `collect` method, returning one or more `PluginFinding` instances. Place the
implementation inside the `advanced_codebase_analyzer/plugins/` package and the
analyzer will automatically discover it at runtime.

Example skeleton:

```python
from advanced_codebase_analyzer.core.metadata import PluginFinding
from advanced_codebase_analyzer.core.plugins import AnalysisContext, AnalyzerPlugin


class MyCustomPlugin(AnalyzerPlugin):
    name = "Custom insight"
    description = "Explain what the plugin surfaces."

    def collect(self, context: AnalysisContext):
        yield PluginFinding(
            plugin=self.name,
            title="Result title",
            summary="Brief human readable summary",
            metadata={"extra": "data"},
        )
```

Plugins can optionally override `is_available` or `supports` to toggle
execution based on environment requirements or repository characteristics.

The desktop application ships with a curated plugin set out of the box:

- **Git metadata** – capture branch, latest commit, and workspace cleanliness.
- **Large file detector** – surface the heaviest artifacts discovered during a scan.
- **License inventory** – enumerate `LICENSE`, `NOTICE`, and `COPYING` files.
- **Dependency health** – highlight unpinned, duplicate, and VCS-backed dependencies.
- **CI coverage** – report which CI providers (GitHub Actions, GitLab, Azure, CircleCI) are configured.
