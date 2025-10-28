"""Application entry points for packaging and executable generation."""
from __future__ import annotations

from .gui.main_window import launch


def main() -> None:
    """Launch the graphical analyzer application."""

    launch()


__all__ = ["main", "launch"]

