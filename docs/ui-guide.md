# User Interface Guide

The desktop application is built with Tkinter and designed to remain responsive while scanning extremely large repositories. This guide walks through each element of the interface and explains how to interact with analysis results.

## Launching the application

Run the following command from the repository root:

```bash
python -m advanced_codebase_analyzer
```

The main window opens with controls for selecting a target directory, toggling scan options, and viewing results.

## Layout overview

1. **Scan controls** – Located at the top of the window. Use the folder icon to choose a directory, then click **Scan** to start a background analysis. The status label reflects progress (idle, scanning, completed, or error).
2. **Options panel** – Provides toggles such as "Follow symlinks" and the maximum number of example paths to store per category. Adjust these before launching a scan.
3. **Results notebook** – A tabbed view that displays four result sets:
   - **Files** – Category counts, total sizes, and representative examples for Markdown, YAML, model checkpoints, and more.
   - **Dependencies** – Parsed Python and Node.js dependencies with versions and source manifests.
   - **Packages** – Detected Python package directories and Node projects with their paths.
   - **Plugins** – Findings surfaced by built-in or custom plugins, including severity, titles, and summaries.
4. **Management queue** – A side panel where you can triage items for follow-up. Double-click entries in any results tab to add them to the queue.
5. **Insight banner** – When heuristic warnings are generated, they appear above the notebook to highlight missing documentation, README files, or unpinned dependencies.

## Interaction patterns

- **Double-click to triage** – Any double-clickable row in the Files, Dependencies, Packages, or Plugins tabs is added to the management queue for later action.
- **Contextual metadata** – Selected rows show additional details in the status bar, such as example file paths or plugin summaries.
- **Queue management** – Use the **Remove Selected** button to delete highlighted queue entries or **Clear** to reset the entire queue.
- **Export report** – The **File → Export Report** menu saves the current `AnalysisReport` as JSON using `dataclasses.asdict`. This includes plugin findings and heuristic warnings.
- **Error handling** – If the scan encounters an exception, a message dialog appears and the status label indicates failure. Logs and stack traces are printed to the console for debugging.

## Accessibility tips

- Keyboard navigation works across all tabs. Use the arrow keys to move between rows and press **Enter** to trigger the same action as a double-click.
- The window remembers the last scanned path for the current session, making repeated analyses faster.
- For extremely large repositories, consider increasing the "Max examples" option to capture more representative paths, or disabling "Follow symlinks" to reduce scan time.
