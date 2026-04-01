"""
Grid environment for the robot path simulation.
Manages static/dynamic obstacles, start/end points, and neighbor queries.
"""

import numpy as np
import random
import math
from utils.config import (
    GRID_COLS, GRID_ROWS, DYNAMIC_OBS_SPEED, DYNAMIC_OBS_COUNT
)


class DynamicObstacle:
    """An obstacle that moves back and forth along a line on the grid."""

    def __init__(self, start_col, start_row, direction, length):
        # direction: 0=horizontal, 1=vertical
        self.start_col = start_col
        self.start_row = start_row
        self.direction = direction       # 0=horizontal, 1=vertical
        self.length = length             # how many cells it travels
        self.progress = 0.0             # 0‑1 along its path
        self.speed = DYNAMIC_OBS_SPEED
        self.forward = True

    @property
    def col(self):
        offset = self.progress * self.length
        if self.direction == 0:
            return int(self.start_col + offset)
        return self.start_col

    @property
    def row(self):
        offset = self.progress * self.length
        if self.direction == 1:
            return int(self.start_row + offset)
        return self.start_row

    def update(self, dt):
        """Advance the obstacle along its path."""
        step = (self.speed / max(self.length, 1)) * dt
        if self.forward:
            self.progress += step
            if self.progress >= 1.0:
                self.progress = 1.0
                self.forward = False
        else:
            self.progress -= step
            if self.progress <= 0.0:
                self.progress = 0.0
                self.forward = True


class Grid:
    """
    2‑D grid world.
    Cell values: 0 = free, 1 = static obstacle, 2 = dynamic obstacle.
    """

    def __init__(self, cols=GRID_COLS, rows=GRID_ROWS):
        self.cols = cols
        self.rows = rows
        self.cells = np.zeros((rows, cols), dtype=np.int8)
        self.start = (1, 1)              # (col, row)
        self.end = (cols - 2, rows - 2)  # (col, row)
        self.dynamic_obstacles: list[DynamicObstacle] = []
        self.dynamic_enabled = False

    # ────────────────── obstacle management ──────────────────

    def set_obstacle(self, col, row):
        """Place a static obstacle if the cell is free and not start/end."""
        if not self.in_bounds(col, row):
            return
        if (col, row) == self.start or (col, row) == self.end:
            return
        self.cells[row, col] = 1

    def remove_obstacle(self, col, row):
        if self.in_bounds(col, row):
            self.cells[row, col] = 0

    def toggle_obstacle(self, col, row):
        if not self.in_bounds(col, row):
            return
        if (col, row) == self.start or (col, row) == self.end:
            return
        if self.cells[row, col] == 1:
            self.cells[row, col] = 0
        else:
            self.cells[row, col] = 1

    def is_obstacle(self, col, row):
        if not self.in_bounds(col, row):
            return True
        return self.cells[row, col] != 0

    def is_free(self, col, row):
        return self.in_bounds(col, row) and self.cells[row, col] == 0

    def in_bounds(self, col, row):
        return 0 <= col < self.cols and 0 <= row < self.rows

    # ────────────────── start / end ──────────────────────────

    def set_start(self, col, row):
        if self.in_bounds(col, row) and (col, row) != self.end:
            self.cells[row, col] = 0
            self.start = (col, row)

    def set_end(self, col, row):
        if self.in_bounds(col, row) and (col, row) != self.start:
            self.cells[row, col] = 0
            self.end = (col, row)

    # ────────────────── neighbors (4‑connected) ──────────────

    def get_neighbors(self, col, row):
        """Return walkable 4‑connected neighbors as (col, row) tuples."""
        neighbors = []
        for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nc, nr = col + dc, row + dr
            if self.in_bounds(nc, nr) and self.cells[nr, nc] == 0:
                neighbors.append((nc, nr))
        return neighbors

    def get_neighbors_8(self, col, row):
        """Return walkable 8‑connected neighbors (includes diagonals)."""
        neighbors = []
        for dc in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                if dc == 0 and dr == 0:
                    continue
                nc, nr = col + dc, row + dr
                if self.in_bounds(nc, nr) and self.cells[nr, nc] == 0:
                    # For diagonal moves, both adjacent cells must be free
                    if dc != 0 and dr != 0:
                        if self.cells[row, nc] != 0 or self.cells[nr, col] != 0:
                            continue
                    neighbors.append((nc, nr))
        return neighbors

    # ────────────────── dynamic obstacles ────────────────────

    def spawn_dynamic_obstacles(self, count=DYNAMIC_OBS_COUNT):
        """Create random dynamic obstacles that don't overlap start/end."""
        self.dynamic_obstacles.clear()
        attempts = 0
        while len(self.dynamic_obstacles) < count and attempts < 200:
            attempts += 1
            direction = random.randint(0, 1)
            length = random.randint(2, 5)
            if direction == 0:
                sc = random.randint(1, self.cols - length - 2)
                sr = random.randint(1, self.rows - 2)
            else:
                sc = random.randint(1, self.cols - 2)
                sr = random.randint(1, self.rows - length - 2)
            # check it doesn't sit on start/end
            if (sc, sr) == self.start or (sc, sr) == self.end:
                continue
            self.dynamic_obstacles.append(
                DynamicObstacle(sc, sr, direction, length)
            )

    def toggle_dynamic_obstacles(self):
        self.dynamic_enabled = not self.dynamic_enabled
        if self.dynamic_enabled:
            self.spawn_dynamic_obstacles()
        else:
            self._clear_dynamic_cells()
            self.dynamic_obstacles.clear()

    def update_dynamic_obstacles(self, dt):
        """Move dynamic obstacles and update the grid. Returns True if any moved."""
        if not self.dynamic_enabled or not self.dynamic_obstacles:
            return False
        # Clear old dynamic cells
        self._clear_dynamic_cells()
        moved = False
        for obs in self.dynamic_obstacles:
            old_col, old_row = obs.col, obs.row
            obs.update(dt)
            if obs.col != old_col or obs.row != old_row:
                moved = True
            # Stamp new position (only if free of static obstacles)
            c, r = obs.col, obs.row
            if self.in_bounds(c, r) and self.cells[r, c] != 1:
                if (c, r) != self.start and (c, r) != self.end:
                    self.cells[r, c] = 2
        return moved

    def _clear_dynamic_cells(self):
        """Remove all dynamic obstacle markers from grid."""
        self.cells[self.cells == 2] = 0

    # ────────────────── reset ────────────────────────────────

    def reset(self):
        """Clear all obstacles and reset start/end to defaults."""
        self.cells.fill(0)
        self.start = (1, 1)
        self.end = (self.cols - 2, self.rows - 2)
        self.dynamic_obstacles.clear()
        self.dynamic_enabled = False

    def clear_path_data(self):
        """Convenience: does nothing to the grid itself (path data is external)."""
        pass

    # ────────────────── utility ──────────────────────────────

    def generate_random_obstacles(self, density=0.25):
        """Fill the grid with random obstacles at given density."""
        self.cells.fill(0)
        for r in range(self.rows):
            for c in range(self.cols):
                if (c, r) == self.start or (c, r) == self.end:
                    continue
                if random.random() < density:
                    self.cells[r, c] = 1

    def cost(self, from_node, to_node):
        """Movement cost between adjacent cells (1 for cardinal, sqrt2 for diagonal)."""
        dc = abs(to_node[0] - from_node[0])
        dr = abs(to_node[1] - from_node[1])
        if dc + dr == 2:
            return math.sqrt(2)
        return 1.0
