"""
Map save/load helpers for simulation environments.
"""

from __future__ import annotations

import json
from pathlib import Path


def save_grid_to_json(grid, file_path):
    """Save static map state to JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "cols": grid.cols,
        "rows": grid.rows,
        "start": list(grid.start),
        "end": list(grid.end),
        "cells": grid.cells.tolist(),
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return str(path)


def load_grid_from_json(grid, file_path):
    """Load static map state from JSON into an existing Grid instance."""
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    cols = int(payload["cols"])
    rows = int(payload["rows"])
    if cols != grid.cols or rows != grid.rows:
        raise ValueError(
            f"Map dimensions ({cols}x{rows}) do not match current grid ({grid.cols}x{grid.rows})."
        )

    cells = payload["cells"]
    if len(cells) != grid.rows or any(len(row) != grid.cols for row in cells):
        raise ValueError("Invalid map matrix dimensions.")

    grid.reset()
    for r in range(grid.rows):
        for c in range(grid.cols):
            v = int(cells[r][c])
            grid.cells[r, c] = 1 if v == 1 else 0

    start = tuple(payload["start"])
    end = tuple(payload["end"])
    grid.set_start(int(start[0]), int(start[1]))
    grid.set_end(int(end[0]), int(end[1]))

    return str(path)
