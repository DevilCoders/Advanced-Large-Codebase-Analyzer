"""Utility script to generate a standalone executable via PyInstaller."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = PROJECT_ROOT / "advanced_codebase_analyzer" / "app.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        default="advanced_codebase-analyzer",
        help="Name of the generated executable",
    )
    parser.add_argument(
        "--onefile",
        dest="onefile",
        action="store_true",
        default=True,
        help="Bundle into a single-file executable (mirrors the Windows guidance)",
    )
    parser.add_argument(
        "--no-onefile",
        dest="onefile",
        action="store_false",
        help="Disable single-file bundling if you prefer the directory layout",
    )
    parser.add_argument(
        "--windowed",
        dest="windowed",
        action="store_true",
        default=True,
        help="Generate a windowed build (suppresses the console on Windows)",
    )
    parser.add_argument(
        "--console",
        dest="windowed",
        action="store_false",
        help="Keep the console window attached to the executable",
    )
    parser.add_argument(
        "--icon",
        help="Path to an .ico file to brand the executable (e.g. C:/path/to/icon.ico)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous build artifacts before packaging",
    )
    return parser.parse_args()


def ensure_pyinstaller() -> str:
    executable = shutil.which("pyinstaller")
    if not executable:
        raise SystemExit(
            "PyInstaller is not available. Install it with 'pip install pyinstaller' first."
        )
    return executable


def run() -> None:
    args = parse_args()
    pyinstaller = ensure_pyinstaller()
    build_dir = PROJECT_ROOT / "build"
    dist_dir = PROJECT_ROOT / "dist"
    if args.clean:
        shutil.rmtree(build_dir, ignore_errors=True)
        shutil.rmtree(dist_dir, ignore_errors=True)

    command = [pyinstaller, "--noconfirm"]
    if args.onefile:
        command.append("--onefile")
    if args.clean:
        command.append("--clean")
    command.extend(["--name", args.name])
    if args.windowed:
        command.append("--windowed")
    if args.icon:
        command.extend(["--icon", str(Path(args.icon).expanduser())])
    data_path = PROJECT_ROOT / "advanced_codebase_analyzer"
    command.extend(["--add-data", f"{data_path}{os.pathsep}advanced_codebase_analyzer"])
    command.append(str(ENTRY_POINT))
    subprocess.check_call(command, cwd=PROJECT_ROOT)


if __name__ == "__main__":  # pragma: no cover - automation helper
    run()

