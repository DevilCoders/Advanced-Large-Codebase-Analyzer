"""Tkinter based GUI for the advanced codebase analyzer."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
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
    scrolledtext,
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
        self.configure(padx=8, pady=8, bg="#080808")
        Label(
            self,
            text="Management Queue",
            font=("Consolas", 11, "bold"),
            fg="#39ff14",
            bg="#080808",
        ).pack(anchor="w")
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

        button_frame = Frame(self, bg="#080808")
        button_frame.pack(fill="x", pady=(4, 0))
        Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_selected,
            bg="#39ff14",
            activebackground="#52ff80",
        ).pack(side=LEFT)
        Button(
            button_frame,
            text="Clear",
            command=self.clear,
            bg="#39ff14",
            activebackground="#52ff80",
        ).pack(side=RIGHT)

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
        self._current_query: str = ""
        self._data_cache: Dict[str, list[tuple[tuple[object, ...], tuple[str, ...]]]] = {
            "files": [],
            "dependencies": [],
            "packages": [],
            "plugins": [],
        }
        self.file_tree = self._create_file_tab()
        self.dependency_tree = self._create_dependency_tab()
        self.package_tree = self._create_package_tab()
        self.plugin_tree = self._create_plugin_tab()
        self.trees = {
            "files": self.file_tree,
            "dependencies": self.dependency_tree,
            "packages": self.package_tree,
            "plugins": self.plugin_tree,
        }

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
        tree.tag_configure("severity::critical", foreground="#ff6b6b")
        tree.tag_configure("severity::warning", foreground="#f7e967")
        tree.tag_configure("severity::info", foreground="#63f5b0")
        self.add(frame, text="Plugins")
        return tree

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------
    def populate_files(self, summaries: Iterable[FileSummary]) -> None:
        rows: list[tuple[tuple[object, ...], tuple[str, ...]]] = []
        for summary in summaries:
            example = summary.examples[0] if summary.examples else summary.category
            rows.append(
                (
                    (summary.category, summary.count, summary.human_size),
                    (example,),
                )
            )
        self._data_cache["files"] = rows
        self._apply_filter_to_tree("files")

    def populate_dependencies(self, deps: Iterable[DependencyRecord]) -> None:
        rows: list[tuple[tuple[object, ...], tuple[str, ...]]] = []
        for record in deps:
            rows.append(
                (
                    (record.name, record.version or "-", record.source_file.name),
                    (str(record.source_file),),
                )
            )
        self._data_cache["dependencies"] = rows
        self._apply_filter_to_tree("dependencies")

    def populate_packages(self, packages: Iterable[PackageRecord]) -> None:
        rows: list[tuple[tuple[object, ...], tuple[str, ...]]] = []
        for record in packages:
            root_display = str(record.root)
            if self.base_root:
                try:
                    root_display = str(record.root.relative_to(self.base_root))
                except ValueError:
                    root_display = str(record.root)
            rows.append(
                (
                    (record.name, record.kind, root_display),
                    (str(record.root),),
                )
            )
        self._data_cache["packages"] = rows
        self._apply_filter_to_tree("packages")

    def populate_plugins(self, findings: Iterable[PluginFinding]) -> None:
        rows: list[tuple[tuple[object, ...], tuple[str, ...]]] = []
        for finding in findings:
            rows.append(
                (
                    (finding.plugin, finding.severity.title(), finding.title),
                    (
                        finding.summary,
                        f"severity::{finding.severity.lower()}",
                        json.dumps(finding.metadata, default=str),
                    ),
                )
            )
        self._data_cache["plugins"] = rows
        self._apply_filter_to_tree("plugins")

    def _clear(self, tree: ttk.Treeview) -> None:
        for item_id in tree.get_children():
            tree.delete(item_id)

    def apply_query(self, query: str) -> None:
        self._current_query = query.lower()
        for key in self.trees:
            self._apply_filter_to_tree(key)

    def _apply_filter_to_tree(self, key: str) -> None:
        tree = self.trees[key]
        self._clear(tree)
        for values, tags in self._data_cache[key]:
            if self._current_query:
                haystacks = [str(value) for value in values] + list(tags)
                if not any(self._current_query in hay.lower() for hay in haystacks):
                    continue
            tree.insert("", END, values=values, tags=tags)

    def iter_trees(self):
        for key, tree in self.trees.items():
            yield key, tree

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

        self._apply_hacker_theme()

        self._create_menu()
        self._build_layout()
        self.after(200, self._poll_queue)

    # ------------------------------------------------------------------
    # UI creation
    # ------------------------------------------------------------------
    def _create_menu(self) -> None:
        menu_bar = Menu(self)
        file_menu = Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Import Report", command=self._import_report)
        file_menu.add_command(label="Export Report", command=self._export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def _build_layout(self) -> None:
        container = Frame(self)
        container.pack(fill=BOTH, expand=True)

        control_frame = Frame(container, padx=10, pady=10, bg=self._bg_color)
        control_frame.pack(side=TOP, fill="x")

        Label(control_frame, text="Target Directory:", fg=self._fg_color, bg=self._bg_color).grid(
            row=0, column=0, sticky="w"
        )
        self.path_var = StringVar()
        Entry(control_frame, textvariable=self.path_var, width=80, bg="#0d0d0d", fg=self._accent_color).grid(
            row=0, column=1, sticky="we", padx=(6, 6)
        )
        Button(
            control_frame,
            text="Browse",
            command=self._choose_directory,
            bg=self._accent_color,
            activebackground="#52ff80",
        ).grid(row=0, column=2, padx=(0, 6))
        Button(
            control_frame,
            text="Scan",
            command=self._start_scan,
            bg=self._accent_color,
            activebackground="#52ff80",
        ).grid(row=0, column=3)

        control_frame.columnconfigure(1, weight=1)

        self.follow_symlinks = BooleanVar(value=False)
        self.max_examples = IntVar(value=5)

        ttk.Checkbutton(
            control_frame,
            text="Follow symlinks",
            variable=self.follow_symlinks,
            style="Hacker.TCheckbutton",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(control_frame, text="Examples per bucket:", style="Hacker.TLabel").grid(
            row=1, column=1, sticky="e", pady=(6, 0)
        )
        ttk.Spinbox(
            control_frame,
            from_=1,
            to=20,
            textvariable=self.max_examples,
            width=5,
            style="Hacker.TSpinbox",
        ).grid(row=1, column=2, sticky="w", pady=(6, 0))

        self.status_var = StringVar(value="Idle")
        Label(
            control_frame,
            textvariable=self.status_var,
            fg=self._accent_color,
            bg=self._bg_color,
        ).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        body_frame = Frame(container)
        body_frame.pack(fill=BOTH, expand=True)

        self.manager_panel = ManagementPanel(body_frame)
        self.manager_panel.pack(side=RIGHT, fill="y")

        notebook_frame = Frame(body_frame, bg=self._bg_color)
        notebook_frame.pack(side=LEFT, fill=BOTH, expand=True)
        search_frame = Frame(notebook_frame, bg=self._bg_color)
        search_frame.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(search_frame, text="Deep Search:", style="Hacker.TLabel").pack(side=LEFT)
        self.search_var = StringVar()
        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=40,
            style="Hacker.TEntry",
        )
        search_entry.pack(side=LEFT, padx=(8, 0))
        search_entry.bind("<KeyRelease>", lambda _event: self._on_search())
        ttk.Button(search_frame, text="Clear", style="Hacker.TButton", command=self._clear_search).pack(
            side=LEFT, padx=(8, 0)
        )

        self.notebook = ResultsNotebook(notebook_frame, manager=self.manager_panel)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10, 6))

        summary_container = Frame(notebook_frame, bg=self._bg_color)
        summary_container.pack(fill="x", padx=10, pady=(0, 6))
        self._summary_vars = {
            "files": StringVar(value="Files: -"),
            "size": StringVar(value="Size: -"),
            "dependencies": StringVar(value="Dependencies: -"),
            "packages": StringVar(value="Packages: -"),
        }
        for index, key in enumerate(self._summary_vars):
            card = ttk.Label(
                summary_container,
                textvariable=self._summary_vars[key],
                style="HackerCard.TLabel",
                anchor="w",
            )
            card.grid(row=0, column=index, sticky="we", padx=(0 if index == 0 else 8, 0))
        summary_container.columnconfigure((0, 1, 2, 3), weight=1)

        console_label = ttk.Label(
            notebook_frame, text="Activity Console", style="Hacker.Section.TLabel"
        )
        console_label.pack(anchor="w", padx=10)
        self.log_console = scrolledtext.ScrolledText(
            notebook_frame,
            height=8,
            bg="#050505",
            fg=self._accent_color,
            insertbackground=self._accent_color,
            relief="flat",
        )
        self.log_console.pack(fill=BOTH, expand=False, padx=10, pady=(0, 10))
        self.log_console.configure(state="disabled")

        self._register_tree_context_menus()
        self._update_summary_cards(None)
        self.notebook.apply_query("")

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
        self._log(f"Launching analysis for {path}")
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
                self._log(f"Scan failed: {payload}")
                messagebox.showerror("Scan failed", str(payload))
            elif event == "success":
                self.report = payload  # type: ignore[assignment]
                self._render_report(payload)
                self.status_var.set(f"Scan complete for {payload.root}")
                self._log(f"Scan complete for {payload.root}")
        self.after(250, self._poll_queue)

    def _render_report(self, report: AnalysisReport) -> None:
        self.notebook.base_root = report.root
        self.notebook.populate_files(report.iter_files())
        self.notebook.populate_dependencies(report.iter_dependencies())
        self.notebook.populate_packages(report.iter_packages())
        self.notebook.populate_plugins(report.iter_plugin_findings())
        self._on_search()
        self.manager_panel.clear()
        if report.warnings:
            messagebox.showwarning("Analyzer warnings", "\n".join(report.warnings))
            for warning in report.warnings:
                self._log(f"Warning: {warning}")
        self._update_summary_cards(report)

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
        self._log(f"Report exported to {path}")

    def _import_report(self) -> None:
        path = filedialog.askopenfilename(
            title="Import report",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            report = self._report_from_json(Path(path))
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Import failed", f"Could not load report: {exc}")
            self._log(f"Import failed for {path}: {exc}")
            return
        self.report = report
        self._render_report(report)
        self.status_var.set(f"Loaded report from {path}")
        self._log(f"Loaded report from {path}")

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

    # ------------------------------------------------------------------
    # Advanced utilities
    # ------------------------------------------------------------------
    def _apply_hacker_theme(self) -> None:
        self._bg_color = "#050505"
        self._fg_color = "#e8f1f2"
        self._accent_color = "#39ff14"
        self.configure(bg=self._bg_color)
        self.option_add("*Font", "Consolas 11")
        self.option_add("*Label.Foreground", self._fg_color)
        self.option_add("*Label.Background", self._bg_color)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:  # pragma: no cover - depends on tk theme availability
            pass
        style.configure("Hacker.TLabel", foreground=self._accent_color, background=self._bg_color)
        style.configure("Hacker.Section.TLabel", foreground=self._fg_color, background=self._bg_color)
        style.configure(
            "Hacker.TButton",
            background=self._bg_color,
            foreground=self._accent_color,
            borderwidth=0,
            focusthickness=3,
            focuscolor=self._accent_color,
        )
        style.map(
            "Hacker.TButton",
            background=[("active", "#0f3d0f")],
            foreground=[("active", self._accent_color)],
        )
        style.configure(
            "Treeview",
            background="#0c0c0c",
            fieldbackground="#0c0c0c",
            foreground=self._fg_color,
            rowheight=24,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", "#124f29")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure("TNotebook", background=self._bg_color, tabmargins=4)
        style.configure(
            "TNotebook.Tab",
            background="#111111",
            foreground=self._fg_color,
            padding=(12, 6),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#1f5c2e")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "HackerCard.TLabel",
            background="#0a0a0a",
            foreground=self._accent_color,
            padding=(10, 6),
            relief="flat",
        )
        style.configure(
            "Hacker.TEntry",
            fieldbackground="#0d0d0d",
            foreground=self._accent_color,
            insertcolor=self._accent_color,
        )
        style.configure("Hacker.TCheckbutton", background=self._bg_color, foreground=self._fg_color)
        style.configure(
            "Hacker.TSpinbox",
            arrowsize=12,
            foreground=self._accent_color,
            fieldbackground="#0d0d0d",
            background="#0d0d0d",
            borderwidth=0,
        )

    def _on_search(self) -> None:
        query = self.search_var.get().strip()
        self.notebook.apply_query(query)
        if query:
            self.status_var.set(f"Filtering results for '{query}'")
        elif self.report:
            self.status_var.set(f"Scan complete for {self.report.root}")
        else:
            self.status_var.set("Idle")

    def _clear_search(self) -> None:
        if self.search_var.get():
            self.search_var.set("")
            self._on_search()

    def _register_tree_context_menus(self) -> None:
        self._context_menus: Dict[str, Menu] = {}
        for key, tree in self.notebook.iter_trees():
            menu = Menu(tree, tearoff=False, bg="#141414", fg=self._accent_color)
            menu.add_command(
                label="Copy Row", command=lambda tree=tree: self._copy_selected_row(tree)
            )
            if key == "plugins":
                menu.add_command(
                    label="Show Details",
                    command=lambda tree=tree: self._show_plugin_details(tree),
                )
            else:
                menu.add_command(
                    label="Open Location",
                    command=lambda tree=tree: self._open_selected_location(tree),
                )
            tree.bind(
                "<Button-3>",
                lambda event, menu=menu, tree=tree: self._display_context_menu(
                    menu, tree, event
                ),
            )
            self._context_menus[key] = menu

    def _display_context_menu(self, menu: Menu, tree: ttk.Treeview, event) -> None:
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _copy_selected_row(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        text = "\t".join(str(value) for value in values)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._log(f"Copied row: {text}")

    def _open_selected_location(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        tags = tree.item(item_id, "tags")
        if not tags:
            return
        path = Path(tags[0])
        if not path.is_absolute() and self.report:
            path = self.report.root / path
        self._open_path(path)

    def _show_plugin_details(self, tree: ttk.Treeview) -> None:
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        tags = tree.item(item_id, "tags")
        summary = tags[0] if tags else "No summary available."
        metadata = ""
        if tags and len(tags) > 2:
            metadata = tags[2]
        detail = f"Plugin: {values[0]}\nSeverity: {values[1]}\nTitle: {values[2]}\n\nSummary:\n{summary}"
        if metadata:
            detail += f"\n\nMetadata:\n{metadata}"
        messagebox.showinfo("Plugin details", detail)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showwarning("Missing path", f"The path '{path}' does not exist.")
            return
        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(path)])
            elif os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self._log(f"Opened path {path}")
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))
            self._log(f"Failed to open {path}: {exc}")

    def _update_summary_cards(self, report: Optional[AnalysisReport]) -> None:
        if not report:
            for key, var in self._summary_vars.items():
                label = key.replace("_", " ").title()
                var.set(f"{label}: -")
            return
        total_files = sum(summary.count for summary in report.iter_files())
        total_size = sum(summary.total_bytes for summary in report.iter_files())
        self._summary_vars["files"].set(f"Files: {total_files:,}")
        self._summary_vars["size"].set(f"Size: {self._human_size(total_size)}")
        self._summary_vars["dependencies"].set(
            f"Dependencies: {len(list(report.iter_dependencies())):,}"
        )
        self._summary_vars["packages"].set(f"Packages: {len(list(report.iter_packages())):,}")

    @staticmethod
    def _human_size(total_bytes: int) -> str:
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        value = float(total_bytes)
        for suffix in suffixes:
            if value < 1024 or suffix == suffixes[-1]:
                return f"{value:.2f} {suffix}"
            value /= 1024
        return f"{value:.2f} TB"

    def _log(self, message: str) -> None:
        self.log_console.configure(state="normal")
        self.log_console.insert(END, f"▶ {message}\n")
        self.log_console.see(END)
        self.log_console.configure(state="disabled")

    def _report_from_json(self, path: Path) -> AnalysisReport:
        data = json.loads(path.read_text())
        root = Path(data["root"]).expanduser()
        files = {
            entry["category"]: FileSummary(
                category=entry["category"],
                count=int(entry["count"]),
                total_bytes=int(entry["total_bytes"]),
                examples=list(entry.get("examples", [])),
            )
            for entry in data.get("files", [])
        }
        dependencies = [
            DependencyRecord(
                name=entry["name"],
                version=entry.get("version"),
                source_file=Path(entry["source_file"]),
                metadata=dict(entry.get("metadata", {})),
            )
            for entry in data.get("dependencies", [])
        ]
        packages = [
            PackageRecord(
                name=entry["name"],
                root=Path(entry["root"]),
                kind=entry.get("kind", "unknown"),
                metadata=dict(entry.get("metadata", {})),
            )
            for entry in data.get("packages", [])
        ]
        plugins = [
            PluginFinding(
                plugin=entry["plugin"],
                title=entry.get("title", ""),
                summary=entry.get("summary", ""),
                severity=entry.get("severity", "info"),
                metadata=dict(entry.get("metadata", {})),
            )
            for entry in data.get("plugins", [])
        ]
        warnings = list(data.get("warnings", []))
        return AnalysisReport(
            root=root,
            files=files,
            dependencies=dependencies,
            packages=packages,
            warnings=warnings,
            plugin_findings=plugins,
        )


def launch() -> None:  # pragma: no cover - convenience helper
    app = AnalyzerApp()
    app.mainloop()


__all__ = ["launch", "AnalyzerApp"]
