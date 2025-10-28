"""Efficiently index files within a repository."""
from __future__ import annotations

import os
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Iterable, Iterator, Tuple

from .metadata import FileSummary

# File categories we care about, expressed as lowercase suffixes
FILE_SUFFIX_GROUPS: Dict[str, Tuple[str, ...]] = {
    "Markdown": (".md", ".markdown"),
    "YAML": (".yml", ".yaml"),
    "PyTorch Model": (".pt", ".pth"),
    "TensorFlow Model": (".h5", ".keras", ".pb", ".tflite"),
    "FlatBuffers Schema": (".fbs",),
    "ONNX Model": (".onnx",),
    "Checkpoint": (".ckpt",),
}


class FileIndexer:
    """Walk very large directory trees while keeping memory usage low."""

    def __init__(self, follow_symlinks: bool = False, max_examples: int = 5) -> None:
        self.follow_symlinks = follow_symlinks
        self.max_examples = max_examples

    def iter_paths(self, root: Path) -> Iterator[Tuple[Path, os.stat_result]]:
        """Yield file paths and stat results, breadth first for better UX."""
        queue: Deque[Path] = deque([root])
        visited_paths: set[Path] = {root}
        visited_real: set[Path] = set()
        if self.follow_symlinks:
            try:
                visited_real.add(root.resolve())
            except OSError:
                pass
        while queue:
            current = queue.popleft()
            try:
                entries = list(current.iterdir())
            except PermissionError:
                continue
            for entry in entries:
                if entry.is_dir():
                    if entry.is_symlink() and not self.follow_symlinks:
                        continue
                    if entry in visited_paths:
                        continue
                    resolved: Path | None = None
                    if self.follow_symlinks:
                        try:
                            resolved = entry.resolve()
                        except OSError:
                            resolved = None
                        if resolved is not None and resolved in visited_real:
                            continue
                    visited_paths.add(entry)
                    if resolved is not None:
                        visited_real.add(resolved)
                    queue.append(entry)
                elif entry.is_file():
                    try:
                        stat = entry.stat()
                    except (PermissionError, OSError):
                        continue
                    yield entry, stat

    def summarize(self, root: Path) -> Dict[str, FileSummary]:
        root = root.resolve()
        buckets: Dict[str, FileSummary] = {
            category: FileSummary(category=category, count=0, total_bytes=0)
            for category in FILE_SUFFIX_GROUPS
        }
        for path, stat in self.iter_paths(root):
            suffix = path.suffix.lower()
            for category, suffixes in FILE_SUFFIX_GROUPS.items():
                if suffix in suffixes:
                    summary = buckets[category]
                    summary.count += 1
                    summary.total_bytes += stat.st_size
                    if len(summary.examples) < self.max_examples:
                        summary.examples.append(str(path.relative_to(root)))
                    break
        # Drop empty categories to reduce clutter
        return {k: v for k, v in buckets.items() if v.count > 0}


def find_candidate_packages(root: Path) -> Iterable[Path]:
    """Yield directories that look like importable packages."""
    for path, _ in FileIndexer().iter_paths(root):
        if path.name == "__init__.py":
            yield path.parent
