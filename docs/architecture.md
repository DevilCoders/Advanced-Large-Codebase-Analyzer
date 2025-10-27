# Architecture

The analyzer separates responsibilities into modular components so that large repositories can be scanned efficiently without blocking the graphical interface. This document explains the major subsystems and how they collaborate during a run.

## Component map

| Module | Purpose |
| --- | --- |
| `advanced_codebase_analyzer.core.analyzer` | Coordinates all scanning subsystems and produces an `AnalysisReport`. |
| `advanced_codebase_analyzer.core.file_indexer` | Streams through the filesystem, grouping files into semantic categories and tracking representative examples. |
| `advanced_codebase_analyzer.core.dependency_inspector` | Extracts dependencies from Python and Node.js manifests and detects package roots. |
| `advanced_codebase_analyzer.core.insights` | Contains heuristic rules that emit warnings about documentation, README files, dependency hygiene, and package presence. |
| `advanced_codebase_analyzer.core.plugins` | Defines the plugin API, discovery routines, and execution manager. |
| `advanced_codebase_analyzer.core.metadata` | Houses shared dataclasses, including `AnalysisReport`, `FileSummary`, `DependencyRecord`, and `PluginFinding`. |
| `advanced_codebase_analyzer.gui.main_window` | Implements the Tkinter desktop experience, including result tabs, the management queue, and JSON export. |

### Execution sequence

1. `CodebaseAnalyzer.analyze` validates the target path and resolves it to an absolute `Path`.
2. `FileIndexer.summarize` walks the directory structure breadth-first to keep memory usage manageable while gathering per-category statistics such as counts, total size, and sample paths.
3. `DependencyInspector.scan` and `PackageDetector.scan` parse supported manifest formats to build dependency and package inventories. The detector recognises Python packages via `__init__.py` files and Node packages through `package.json` files.
4. The analyzer creates an `AnalysisContext` and delegates to `PluginManager.run`, which loads all plugin classes from `advanced_codebase_analyzer.plugins` and aggregates their findings.
5. An `InsightContext` is passed to the `InsightEngine`, which runs the configured rules and deduplicates the resulting warning strings.
6. An `AnalysisReport` combines the file summaries, dependencies, packages, warnings, and plugin findings. The GUI consumes this report to update each tab.

## Threading model

The GUI launches `AnalyzerWorker`, a daemon `threading.Thread`, to execute `CodebaseAnalyzer.analyze` away from the Tkinter main loop. Results propagate back through a `queue.Queue`, allowing the UI to stay responsive and poll for completion or errors.

## Data flow and serialization

All cross-component data is represented by dataclasses in `core.metadata`. These classes provide convenience methods such as `PluginFinding.to_row` for GUI rendering and are serialisable via `dataclasses.asdict`, which the export workflow uses to persist reports as JSON.

## Extensibility points

- **Plugins:** Implementations discovered under `advanced_codebase_analyzer.plugins` receive full context about the scan and may emit structured findings.
- **Insight rules:** You can subclass `InsightRule` and supply a custom rule sequence when instantiating `InsightEngine` to tailor heuristic warnings.
- **Alternate front-ends:** Because the analyzer core returns a plain `AnalysisReport`, you can build CLI or web interfaces without modifying the scanning logic.
