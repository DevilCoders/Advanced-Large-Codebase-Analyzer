"""Tkinter based GUI for the advanced codebase analyzer."""
from __future__ import annotations

import json
import queue
import threading
from dataclasses import asdict
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    TOP,
    BooleanVar,
    Button,
    Entry,
    Frame,
    IntVar,
    Label,
    Menu,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    ttk,
)
from typing import Dict, Iterable, Optional

from ..core.analyzer import CodebaseAnalyzer
from ..core.metadata import (
    AnalysisReport,
    DependencyRecord,
    FileSummary,
    PackageRecord,
    PluginFinding,
)


class AnalyzerWorker(threading.Thread):
    """Background thread wrapper so the UI stays responsive."""

    def __init__(self, analyzer: CodebaseAnalyzer, path: Path, output: queue.Queue):
        super().__init__(daemon=True)
        self.analyzer = analyzer
        self.path = path
        self.output = output

    def run(self) -> None:  # pragma: no cover - GUI threads are hard to test
        try:
            report = self.analyzer.analyze(self.path)
        except Exception as exc:  # pylint: disable=broad-except
            self.output.put(("error", exc))
        else:
            self.output.put(("success", report))


class ManagementPanel(Frame):
    """Allow users to triage items detected by the analyzer."""

    def __init__(self, master: Frame) -> None:
        super().__init__(master)
        self.configure(padx=8, pady=8)
        Label(self, text="Management Queue", font=("TkDefaultFont", 11, "bold")).pack(
            anchor="w"
        )
        self.listbox = ttk.Treeview(
            self,
            columns=("type", "label", "path"),
            show="headings",
            height=6,
        )
        for name, width in ("type", 120), ("label", 180), ("path", 260):
            self.listbox.heading(name, text=name.title())
            self.listbox.column(name, width=width, stretch=True)
        self.listbox.pack(fill=BOTH, expand=True, pady=(6, 4))

        button_frame = Frame(self)
        button_frame.pack(fill="x", pady=(4, 0))
        Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(
            side=LEFT
        )
        Button(button_frame, text="Clear", command=self.clear).pack(side=RIGHT)

    def add_item(self, item_type: str, label: str, path: Path) -> None:
        self.listbox.insert("", END, values=(item_type, label, str(path)))

    def remove_selected(self) -> None:
        for item_id in self.listbox.selection():
            self.listbox.delete(item_id)

    def clear(self) -> None:
        for item_id in self.listbox.get_children():
            self.listbox.delete(item_id)


class ResultsNotebook(ttk.Notebook):
    """Tabbed view hosting file summaries, dependencies, and packages."""

    def __init__(self, master: Frame, manager: ManagementPanel) -> None:
        super().__init__(master)
        self.manager = manager
        self.base_root: Path | None = None
        self.file_tree = self._create_file_tab()
        self.dependency_tree = self._create_dependency_tab()
        self.package_tree = self._create_package_tab()
        self.plugin_tree = self._create_plugin_tab()

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------
    def _create_file_tab(self) -> ttk.Treeview:
        frame = Frame(self)
        tree = ttk.Treeview(frame, columns=("category", "count", "size"), show="headings")
        tree.heading("category", text="Category")
        tree.heading("count", text="Count")
        tree.heading("size", text="Total Size")
        tree.column("category", width=180)
        tree.column("count", width=80, anchor="center")
        tree.column("size", width=120, anchor="center")
        tree.pack(fill=BOTH, expand=True, padx=6, pady=6)
        tree.bind("<Double-1>", lambda _: self._add_selected_file(tree))
        self.add(frame, text="Files")
        return tree

    def _create_dependency_tab(self) -> ttk.Treeview:
        frame = Frame(self)
        tree = ttk.Treeview(
            frame,
            columns=("name", "version", "source"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("name", text="Name")
        tree.heading("version", text="Version")
        tree.heading("source", text="Manifest")
        tree.column("name", width=180)
        tree.column("version", width=100)
        tree.column("source", width=220)
        tree.pack(fill=BOTH, expand=True, padx=6, pady=6)
        tree.bind("<Double-1>", lambda _: self._add_selected_dependency(tree))
        self.add(frame, text="Dependencies")
        return tree

    def _create_package_tab(self) -> ttk.Treeview:
        frame = Frame(self)
        tree = ttk.Treeview(
            frame,
            columns=("name", "type", "path"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("name", text="Name")
        tree.heading("type", text="Type")
        tree.heading("path", text="Location")
        tree.column("name", width=160)
        tree.column("type", width=80, anchor="center")
        tree.column("path", width=260)
        tree.pack(fill=BOTH, expand=True, padx=6, pady=6)
        tree.bind("<Double-1>", lambda _: self._add_selected_package(tree))
        self.add(frame, text="Packages")
        return tree

    def _create_plugin_tab(self) -> ttk.Treeview:
        frame = Frame(self)
        tree = ttk.Treeview(
            frame,
            columns=("plugin", "severity", "title"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("plugin", text="Plugin")
        tree.heading("severity", text="Severity")
        tree.heading("title", text="Summary")
        tree.column("plugin", width=160)
        tree.column("severity", width=80, anchor="center")
        tree.column("title", width=280)
        tree.pack(fill=BOTH, expand=True, padx=6, pady=6)
        tree.bind("<Double-1>", lambda _: self._add_selected_plugin(tree))
        self.add(frame, text="Plugins")
        return tree

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------
    def populate_files(self, summaries: Iterable[FileSummary]) -> None:
        self._clear(self.file_tree)
        for summary in summaries:
            example = summary.examples[0] if summary.examples else summary.category
            self.file_tree.insert(
                "",
                END,
                values=(summary.category, summary.count, summary.human_size),
                tags=(example,),
            )

    def populate_dependencies(self, deps: Iterable[DependencyRecord]) -> None:
        self._clear(self.dependency_tree)
        for record in deps:
            self.dependency_tree.insert(
                "",
                END,
                values=(record.name, record.version or "-", record.source_file.name),
                tags=(str(record.source_file),),
            )

    def populate_packages(self, packages: Iterable[PackageRecord]) -> None:
        self._clear(self.package_tree)
        for record in packages:
            root_display = str(record.root)
            if self.base_root:
                try:
                    root_display = str(record.root.relative_to(self.base_root))
                except ValueError:
                    root_display = str(record.root)
            self.package_tree.insert(
                "",
                END,
                values=(record.name, record.kind, root_display),
                tags=(str(record.root),),
            )

    def populate_plugins(self, findings: Iterable[PluginFinding]) -> None:
        self._clear(self.plugin_tree)
        for finding in findings:
            self.plugin_tree.insert(
                "",
                END,
                values=(finding.plugin, finding.severity.title(), finding.title),
                tags=(finding.summary, finding.severity, str(finding.metadata)),
            )

    def _clear(self, tree: ttk.Treeview) -> None:
        for item_id in tree.get_children():
            tree.delete(item_id)

    # ------------------------------------------------------------------
    # Management integration
    # ------------------------------------------------------------------
    def _add_selected_file(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        tags = tree.item(item_id, "tags")
        example = tags[0] if tags else values[0]
        label = f"{values[0]} ({values[1]} files)"
        example_path = Path(example)
        if not example_path.is_absolute() and self.base_root:
            example_path = self.base_root / example_path
        self.manager.add_item("File Category", label, example_path)

    def _add_selected_dependency(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        source = Path(tree.item(item_id, "tags")[0])
        self.manager.add_item("Dependency", f"{values[0]} {values[1]}", source)

    def _add_selected_package(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        source = Path(tree.item(item_id, "tags")[0])
        self.manager.add_item("Package", values[0], source)

    def _add_selected_plugin(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        self.manager.add_item("Plugin", values[2], Path(self.base_root or "."))


class AnalyzerApp(Tk):
    """Main entry point for the Tkinter application."""

    def __init__(self) -> None:  # pragma: no cover - GUI bootstrapping
        super().__init__()
        self.title("Advanced Codebase Analyzer")
        self.geometry("980x720")
        self._queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._worker: Optional[AnalyzerWorker] = None
        self.report: Optional[AnalysisReport] = None

        self._create_menu()
        self._build_layout()
        self.after(200, self._poll_queue)

    # ------------------------------------------------------------------
    # UI creation
    # ------------------------------------------------------------------
    def _create_menu(self) -> None:
        menu_bar = Menu(self)
        file_menu = Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Export Report", command=self._export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def _build_layout(self) -> None:
        container = Frame(self)
        container.pack(fill=BOTH, expand=True)

        control_frame = Frame(container, padx=10, pady=10)
        control_frame.pack(side=TOP, fill="x")

        Label(control_frame, text="Target Directory:").grid(row=0, column=0, sticky="w")
        self.path_var = StringVar()
        Entry(control_frame, textvariable=self.path_var, width=80).grid(
            row=0, column=1, sticky="we", padx=(6, 6)
        )
        Button(control_frame, text="Browse", command=self._choose_directory).grid(
            row=0, column=2, padx=(0, 6)
        )
        Button(control_frame, text="Scan", command=self._start_scan).grid(row=0, column=3)

        control_frame.columnconfigure(1, weight=1)

        self.follow_symlinks = BooleanVar(value=False)
        self.max_examples = IntVar(value=5)

        ttk.Checkbutton(
            control_frame,
            text="Follow symlinks",
            variable=self.follow_symlinks,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(control_frame, text="Examples per bucket:").grid(
            row=1, column=1, sticky="e", pady=(6, 0)
        )
        ttk.Spinbox(
            control_frame,
            from_=1,
            to=20,
            textvariable=self.max_examples,
            width=5,
        ).grid(row=1, column=2, sticky="w", pady=(6, 0))

        self.status_var = StringVar(value="Idle")
        Label(control_frame, textvariable=self.status_var).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        body_frame = Frame(container)
        body_frame.pack(fill=BOTH, expand=True)

        self.manager_panel = ManagementPanel(body_frame)
        self.manager_panel.pack(side=RIGHT, fill="y")

        notebook_frame = Frame(body_frame)
        notebook_frame.pack(side=LEFT, fill=BOTH, expand=True)
        self.notebook = ResultsNotebook(notebook_frame, manager=self.manager_panel)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _choose_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select Codebase Root")
        if directory:
            self.path_var.set(directory)

    def _start_scan(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Scan in progress", "Please wait for the current scan to finish.")
            return
        path = Path(self.path_var.get() or ".").expanduser()
        if not path.exists():
            messagebox.showerror("Invalid Path", f"The directory '{path}' does not exist.")
            return
        self.status_var.set(f"Scanning {path}…")
        analyzer = CodebaseAnalyzer(
            follow_symlinks=self.follow_symlinks.get(),
            max_examples=self.max_examples.get(),
        )
        self._worker = AnalyzerWorker(analyzer, path, self._queue)
        self._worker.start()

    def _poll_queue(self) -> None:
        while True:
            try:
                event, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            if event == "error":
                self.status_var.set("Scan failed")
                messagebox.showerror("Scan failed", str(payload))
            elif event == "success":
                self.report = payload  # type: ignore[assignment]
                self._render_report(payload)
                self.status_var.set(f"Scan complete for {payload.root}")
        self.after(250, self._poll_queue)

    def _render_report(self, report: AnalysisReport) -> None:
        self.notebook.base_root = report.root
        self.notebook.populate_files(report.iter_files())
        self.notebook.populate_dependencies(report.iter_dependencies())
        self.notebook.populate_packages(report.iter_packages())
        self.notebook.populate_plugins(report.iter_plugin_findings())
        self.manager_panel.clear()
        if report.warnings:
            messagebox.showwarning("Analyzer warnings", "\n".join(report.warnings))

    def _export_report(self) -> None:
        if not self.report:
            messagebox.showinfo("Nothing to export", "Run a scan before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export report",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        export_data = {
            "root": str(self.report.root),
            "files": [asdict(summary) for summary in self.report.iter_files()],
            "dependencies": [self._dependency_to_dict(dep) for dep in self.report.iter_dependencies()],
            "packages": [self._package_to_dict(pkg) for pkg in self.report.iter_packages()],
            "plugins": [self._plugin_to_dict(finding) for finding in self.report.iter_plugin_findings()],
            "warnings": list(self.report.warnings),
        }
        Path(path).write_text(json.dumps(export_data, indent=2))
        messagebox.showinfo("Export complete", f"Report written to {path}")

    @staticmethod
    def _dependency_to_dict(dep: DependencyRecord) -> Dict[str, object]:
        data = asdict(dep)
        data["source_file"] = str(dep.source_file)
        return data

    @staticmethod
    def _package_to_dict(pkg: PackageRecord) -> Dict[str, object]:
        data = asdict(pkg)
        data["root"] = str(pkg.root)
        return data

    @staticmethod
    def _plugin_to_dict(finding: PluginFinding) -> Dict[str, object]:
        data = asdict(finding)
        return data


def launch() -> None:  # pragma: no cover - convenience helper
    app = AnalyzerApp()
    app.mainloop()


__all__ = ["launch", "AnalyzerApp"]
