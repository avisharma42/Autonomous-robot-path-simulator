"""
Pathfinding algorithms: A*, Dijkstra, and BFS.
Each algorithm returns a PathResult for consistent comparison and visualization.
"""

import heapq
import math
import time
from dataclasses import dataclass, field


@dataclass
class PathResult:
    """Unified result from any pathfinding algorithm."""
    path: list          # list of (col, row) from start to end
    visited: list       # nodes visited in exploration order
    cost: float         # total path cost
    time_ms: float      # wall‑clock time in milliseconds
    nodes_explored: int # total nodes expanded
    algorithm: str      # algorithm name
    success: bool       # whether a path was found


def _reconstruct(came_from, current):
    """Walk the came_from map backwards to build the path list."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def heuristic(a, b):
    """Manhattan distance heuristic for A*."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristic_euclidean(a, b):
    """Euclidean distance heuristic (tighter for 8‑connected grids)."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# ═══════════════════════════════════════════════════════════════
#  A* Algorithm
# ═══════════════════════════════════════════════════════════════

def astar(grid, start=None, end=None, use_8connect=False):
    """
    A* pathfinding on the grid.
    Uses Manhattan heuristic for 4‑connected and Euclidean for 8‑connected.
    """
    start = start or grid.start
    end = end or grid.end
    h_func = heuristic_euclidean if use_8connect else heuristic
    get_nbrs = grid.get_neighbors_8 if use_8connect else grid.get_neighbors

    t0 = time.perf_counter()

    open_set = []  # min‑heap of (f_score, counter, node)
    counter = 0    # tie‑breaker to keep heap stable
    heapq.heappush(open_set, (0, counter, start))

    came_from = {}
    g_score = {start: 0.0}
    f_score = {start: h_func(start, end)}
    visited_order = []
    closed = set()

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)
        visited_order.append(current)

        if current == end:
            elapsed = (time.perf_counter() - t0) * 1000
            path = _reconstruct(came_from, current)
            return PathResult(
                path=path,
                visited=visited_order,
                cost=g_score[end],
                time_ms=elapsed,
                nodes_explored=len(closed),
                algorithm="A*",
                success=True,
            )

        for neighbor in get_nbrs(*current):
            tentative_g = g_score[current] + grid.cost(current, neighbor)
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + h_func(neighbor, end)
                f_score[neighbor] = f
                counter += 1
                heapq.heappush(open_set, (f, counter, neighbor))

    elapsed = (time.perf_counter() - t0) * 1000
    return PathResult(
        path=[], visited=visited_order, cost=0, time_ms=elapsed,
        nodes_explored=len(closed), algorithm="A*", success=False,
    )


# ═══════════════════════════════════════════════════════════════
#  Dijkstra's Algorithm
# ═══════════════════════════════════════════════════════════════

def dijkstra(grid, start=None, end=None, use_8connect=False):
    """
    Dijkstra's algorithm – identical to A* but with heuristic = 0.
    Guarantees shortest path by exploring all directions uniformly.
    """
    start = start or grid.start
    end = end or grid.end
    get_nbrs = grid.get_neighbors_8 if use_8connect else grid.get_neighbors

    t0 = time.perf_counter()

    open_set = []
    counter = 0
    heapq.heappush(open_set, (0.0, counter, start))

    came_from = {}
    g_score = {start: 0.0}
    visited_order = []
    closed = set()

    while open_set:
        dist, _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)
        visited_order.append(current)

        if current == end:
            elapsed = (time.perf_counter() - t0) * 1000
            path = _reconstruct(came_from, current)
            return PathResult(
                path=path, visited=visited_order, cost=g_score[end],
                time_ms=elapsed, nodes_explored=len(closed),
                algorithm="Dijkstra", success=True,
            )

        for neighbor in get_nbrs(*current):
            tentative_g = g_score[current] + grid.cost(current, neighbor)
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                counter += 1
                heapq.heappush(open_set, (tentative_g, counter, neighbor))

    elapsed = (time.perf_counter() - t0) * 1000
    return PathResult(
        path=[], visited=visited_order, cost=0, time_ms=elapsed,
        nodes_explored=len(closed), algorithm="Dijkstra", success=False,
    )


# ═══════════════════════════════════════════════════════════════
#  Breadth‑First Search (BFS)
# ═══════════════════════════════════════════════════════════════

def bfs(grid, start=None, end=None, use_8connect=False):
    """
    BFS – explores layer‑by‑layer.  Optimal for uniform‑cost grids.
    """
    from collections import deque

    start = start or grid.start
    end = end or grid.end
    get_nbrs = grid.get_neighbors_8 if use_8connect else grid.get_neighbors

    t0 = time.perf_counter()

    queue = deque([start])
    came_from = {}
    visited = {start}
    visited_order = [start]

    while queue:
        current = queue.popleft()

        if current == end:
            elapsed = (time.perf_counter() - t0) * 1000
            path = _reconstruct(came_from, current)
            return PathResult(
                path=path, visited=visited_order,
                cost=float(len(path) - 1),
                time_ms=elapsed, nodes_explored=len(visited),
                algorithm="BFS", success=True,
            )

        for neighbor in get_nbrs(*current):
            if neighbor not in visited:
                visited.add(neighbor)
                visited_order.append(neighbor)
                came_from[neighbor] = current
                queue.append(neighbor)

    elapsed = (time.perf_counter() - t0) * 1000
    return PathResult(
        path=[], visited=visited_order, cost=0, time_ms=elapsed,
        nodes_explored=len(visited), algorithm="BFS", success=False,
    )


# ═══════════════════════════════════════════════════════════════
#  Comparison helper
# ═══════════════════════════════════════════════════════════════

def compare_all(grid, use_8connect=False):
    """
    Run all three algorithms and return a dict of results.

    By default, A* uses 8-connectivity for smoother robot-like routes,
    while Dijkstra and BFS remain 4-connected for baseline comparison.
    Pass use_8connect=True to run all in 8-connected mode.
    """
    a_star_diag = True if not use_8connect else True
    baseline_diag = use_8connect
    return {
        "A*": astar(grid, use_8connect=a_star_diag),
        "Dijkstra": dijkstra(grid, use_8connect=baseline_diag),
        "BFS": bfs(grid, use_8connect=baseline_diag),
    }
