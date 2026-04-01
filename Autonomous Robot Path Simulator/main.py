"""
main.py  --  Entry point for the Autonomous Robot Path Simulation.

Integrates:
  - Grid environment          (utils/grid.py)
  - Path planning algorithms  (pathfinding/algorithms.py)
  - ODE / RK4 robot motion    (motion/ode_solver.py)
  - 3D OpenGL renderer        (visualization/renderer.py)
  - Camera system             (visualization/camera.py)
  - UI dashboard              (ui/dashboard.py)

Run:  python main.py
"""

import sys
from pathlib import Path
import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL, QUIT, KEYDOWN, KEYUP,
    MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION,
    K_ESCAPE, K_SPACE, K_r, K_f, K_1, K_2, K_3,
    K_c, K_d, K_s, K_l,
)
from OpenGL.GL import glViewport

from utils.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, TITLE,
    GRID_COLS, GRID_ROWS, PANEL_WIDTH,
    VISITED_ANIM_SPEED, DEFAULT_MAP_PATH, ENABLE_ROS_BRIDGE,
)
from utils.grid import Grid
from utils.map_io import save_grid_to_json, load_grid_from_json
from pathfinding.algorithms import astar, dijkstra, bfs, compare_all
from motion.ode_solver import RobotMotion
from visualization.renderer import Renderer
from visualization.camera import Camera
from ui.dashboard import Dashboard
from ros_integration.ros_bridge import ROSBridge


# ═══════════════════════════════════════════════════════════════
#  Application states
# ═══════════════════════════════════════════════════════════════

class State:
    EDITING        = "editing"
    VISUALIZING    = "visualizing"     # showing algorithm exploration
    SIMULATING     = "simulating"      # robot moving
    PAUSED         = "paused"
    FINISHED       = "finished"


# ═══════════════════════════════════════════════════════════════
#  Main Simulation class
# ═══════════════════════════════════════════════════════════════

class Simulation:
    def __init__(self):
        # Pygame / OpenGL window
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            DOUBLEBUF | OPENGL
        )
        self.clock = pygame.time.Clock()

        # Core objects
        self.grid = Grid(GRID_COLS, GRID_ROWS)
        self.robot = RobotMotion()
        self.camera = Camera(
            target=(GRID_COLS / 2.0, 0.0, GRID_ROWS / 2.0)
        )
        self.camera.distance = max(GRID_COLS, GRID_ROWS) * 1.1

        # Renderer (uses entire window; UI is overlaid)
        self.renderer = Renderer(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.renderer.init_gl()

        # Dashboard UI
        self.dashboard = Dashboard(WINDOW_WIDTH, WINDOW_HEIGHT)

        # State machine
        self.state = State.EDITING
        self._prev_state = State.EDITING   # for pause/resume

        # Current tool for grid editing
        self.tool = "tool_obstacle"

        # Algorithm selection
        self.algo_id = "algo_astar"
        self._algo_funcs = {
            "algo_astar": lambda g, start=None, end=None: astar(g, start=start, end=end, use_8connect=True),
            "algo_dijkstra": lambda g, start=None, end=None: dijkstra(g, start=start, end=end, use_8connect=False),
            "algo_bfs": lambda g, start=None, end=None: bfs(g, start=start, end=end, use_8connect=False),
        }

        # Path result & visualisation progress
        self.path_result = None
        self.viz_progress = 0.0      # how many visited nodes revealed

        # Mouse state for grid interaction (only LMB on grid)
        self._mouse_drawing = False
        self._last_grid_cell = None

        # Save/load path and optional ROS bridge
        self.map_file = Path(DEFAULT_MAP_PATH)
        self.ros_bridge = ROSBridge(enabled=ENABLE_ROS_BRIDGE)

    # ────────────────── main loop ────────────────────────────

    def run(self):
        """Main application loop."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap delta for stability

            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                else:
                    self._handle_event(event)

            self._update(dt)
            self._render()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ────────────────── event handling ───────────────────────

    def _handle_event(self, event):
        if event.type == KEYDOWN:
            self._handle_key(event.key)
            return

        if event.type == MOUSEBUTTONDOWN:
            mx, my = event.pos
            # UI panel click
            if mx < PANEL_WIDTH:
                action = self.dashboard.handle_click(mx, my)
                if action:
                    self._handle_ui_action(action)
                return
            # Scroll wheel (zoom)
            if event.button == 4:
                self.camera.handle_scroll(1)
                return
            if event.button == 5:
                self.camera.handle_scroll(-1)
                return
            # Right mouse button: camera orbit
            if event.button == 3:
                self.camera.handle_mouse_down(3, event.pos)
                return
            # Middle mouse button: camera pan
            if event.button == 2:
                self.camera.handle_mouse_down(2, event.pos)
                return
            # Left mouse button on grid: place / erase
            if event.button == 1 and self.state == State.EDITING:
                self._mouse_drawing = True
                self._grid_interact(mx, my)
                return

        if event.type == MOUSEBUTTONUP:
            self.dashboard.handle_mouse_up()
            if event.button in (2, 3):
                self.camera.handle_mouse_up(event.button, event.pos)
            if event.button == 1:
                self._mouse_drawing = False
                self._last_grid_cell = None

        if event.type == MOUSEMOTION:
            mx, my = event.pos
            self.dashboard.handle_mouse_move(mx, my)
            buttons = pygame.mouse.get_pressed()
            # Camera orbit / pan
            if buttons[2] or buttons[1]:
                self.camera.handle_mouse_motion(event.pos, buttons)
            # Continuous grid drawing
            if self._mouse_drawing and self.state == State.EDITING and mx > PANEL_WIDTH:
                self._grid_interact(mx, my)

    def _handle_key(self, key):
        if key == K_ESCAPE:
            pygame.event.post(pygame.event.Event(QUIT))
        elif key == K_SPACE:
            self._toggle_pause()
        elif key == K_r:
            self._reset()
        elif key == K_f:
            self.camera.toggle_follow()
            self.dashboard.set_toggle("toggle_follow", self.camera.follow_mode)
        elif key == K_1:
            self._select_algorithm("algo_astar")
        elif key == K_2:
            self._select_algorithm("algo_dijkstra")
        elif key == K_3:
            self._select_algorithm("algo_bfs")
        elif key == K_c:
            self._compare_all()
        elif key == K_d:
            self.grid.toggle_dynamic_obstacles()
            self.dashboard.set_toggle("toggle_dynamic", self.grid.dynamic_enabled)
        elif key == K_s:
            self._save_map()
        elif key == K_l:
            self._load_map()

    # ────────────────── UI actions ───────────────────────────

    def _handle_ui_action(self, action):
        # Algorithm selection
        if action.startswith("algo_"):
            self._select_algorithm(action)
            return

        # Tool selection
        if action.startswith("tool_"):
            self.tool = action
            self.dashboard.set_active_tool(action)
            return

        # Controls
        if action == "find_path":
            self._find_path()
        elif action == "start_sim":
            self._start_simulation()
        elif action == "pause":
            self._toggle_pause()
        elif action == "reset":
            self._reset()
        elif action == "toggle_dynamic":
            self.grid.toggle_dynamic_obstacles()
            self.dashboard.set_toggle("toggle_dynamic", self.grid.dynamic_enabled)
        elif action == "toggle_follow":
            self.camera.toggle_follow()
            self.dashboard.set_toggle("toggle_follow", self.camera.follow_mode)
        elif action == "random_map":
            self._random_map()
        elif action == "compare_all":
            self._compare_all()
        elif action == "save_map":
            self._save_map()
        elif action == "load_map":
            self._load_map()
        elif action == "speed":
            # Speed slider changed; value read in update
            pass

    def _select_algorithm(self, algo_id):
        self.algo_id = algo_id
        self.dashboard.set_active_algorithm(algo_id)
        name_map = {"algo_astar": "A*", "algo_dijkstra": "Dijkstra", "algo_bfs": "BFS"}
        self.dashboard.update_metrics(algorithm=name_map.get(algo_id, "A*"))

        # Recompute immediately so switching algorithms visibly updates path.
        if self.state in (State.EDITING, State.VISUALIZING, State.FINISHED):
            self._find_path()

    # ────────────────── commands ─────────────────────────────

    def _find_path(self):
        algo_func = self._algo_funcs[self.algo_id]
        result = algo_func(self.grid)
        self.path_result = result
        self.viz_progress = 0.0
        self.state = State.VISUALIZING
        self.dashboard.update_metrics(
            time=result.time_ms,
            nodes=result.nodes_explored,
            path_len=len(result.path),
            algorithm=result.algorithm,
        )

    def _start_simulation(self):
        if self.path_result is None or not self.path_result.success:
            self._find_path()
            if not self.path_result.success:
                return
        # Make sure visualisation is complete
        if self.path_result:
            self.viz_progress = len(self.path_result.visited)
        self.robot.set_waypoints(self.path_result.path)
        self.state = State.SIMULATING

    def _toggle_pause(self):
        if self.state == State.PAUSED:
            self.state = self._prev_state
        elif self.state in (State.VISUALIZING, State.SIMULATING):
            self._prev_state = self.state
            self.state = State.PAUSED

    def _reset(self):
        self.state = State.EDITING
        self.path_result = None
        self.viz_progress = 0.0
        self.robot = RobotMotion()
        self.grid.reset()
        self.camera.reset(GRID_COLS, GRID_ROWS)
        self.dashboard.update_metrics(time=0, nodes=0, path_len=0)
        self.dashboard.set_comparison(None)
        self.dashboard.mark_dirty()

    def _random_map(self):
        self.state = State.EDITING
        self.path_result = None
        self.viz_progress = 0.0
        self.robot = RobotMotion()
        self.grid.generate_random_obstacles(density=0.25)
        self.dashboard.mark_dirty()

    def _compare_all(self):
        results = compare_all(self.grid)
        self.dashboard.set_comparison(results)
        # Also set the current path to the selected algorithm
        algo_name_map = {"algo_astar": "A*", "algo_dijkstra": "Dijkstra", "algo_bfs": "BFS"}
        selected = algo_name_map.get(self.algo_id, "A*")
        if selected in results and results[selected].success:
            self.path_result = results[selected]
            self.viz_progress = len(self.path_result.visited)
            self.dashboard.update_metrics(
                time=self.path_result.time_ms,
                nodes=self.path_result.nodes_explored,
                path_len=len(self.path_result.path),
            )

    def _save_map(self):
        save_grid_to_json(self.grid, self.map_file)

    def _load_map(self):
        try:
            load_grid_from_json(self.grid, self.map_file)
            self.state = State.EDITING
            self.path_result = None
            self.viz_progress = 0.0
            self.robot = RobotMotion()
            self.dashboard.update_metrics(time=0, nodes=0, path_len=0)
            self.dashboard.set_comparison(None)
            self.dashboard.mark_dirty()
        except FileNotFoundError:
            # No existing file yet; keep simulation untouched.
            pass
        except Exception:
            # Invalid files are ignored to keep interaction simple in-app.
            pass

    # ────────────────── grid interaction ─────────────────────

    def _grid_interact(self, mx, my):
        """Place or remove items on the grid based on current tool."""
        cell = self.renderer.screen_to_grid(mx, my)
        if cell is None:
            return
        col, row = cell
        if not self.grid.in_bounds(col, row):
            return
        # Avoid re‑processing same cell during drag
        if (col, row) == self._last_grid_cell:
            return
        self._last_grid_cell = (col, row)

        if self.tool == "tool_start":
            self.grid.set_start(col, row)
        elif self.tool == "tool_end":
            self.grid.set_end(col, row)
        elif self.tool == "tool_obstacle":
            self.grid.set_obstacle(col, row)
        elif self.tool == "tool_erase":
            self.grid.remove_obstacle(col, row)

        # Invalidate previous path
        self.path_result = None
        self.viz_progress = 0.0

    # ────────────────── update ───────────────────────────────

    def _update(self, dt):
        # Speed multiplier from slider
        speed_mult = self.dashboard.get_speed()
        self.robot.speed_multiplier = speed_mult

        # Dynamic obstacles
        if self.grid.dynamic_enabled:
            moved = self.grid.update_dynamic_obstacles(dt)
            if moved and self.state == State.SIMULATING:
                # Re‑plan path in real time
                algo_func = self._algo_funcs[self.algo_id]
                # Use robot's current position (nearest grid cell) as start
                rx, ry = int(self.robot.x), int(self.robot.y)
                if self.grid.in_bounds(rx, ry) and self.grid.is_free(rx, ry):
                    result = algo_func(self.grid, start=(rx, ry))
                    if result.success:
                        self.path_result = result
                        self.robot.replan_waypoints(result.path)

        # State‑specific updates
        if self.state == State.VISUALIZING:
            self.viz_progress += VISITED_ANIM_SPEED * dt * speed_mult
            if self.path_result and self.viz_progress >= len(self.path_result.visited):
                self.viz_progress = len(self.path_result.visited)
                # Auto‑start simulation after visualisation completes
                # (User can also click Start Sim manually)

        elif self.state == State.SIMULATING:
            self.robot.update(dt)
            if self.robot.finished:
                self.state = State.FINISHED

        # Camera follow
        if self.state in (State.SIMULATING, State.FINISHED):
            self.camera.update(dt, robot_pos=(self.robot.x, self.robot.y))
        else:
            self.camera.update(dt)

        # Tick renderer clock
        self.renderer.tick(dt)

        if self.ros_bridge.enabled:
            self.ros_bridge.publish_state(
                self.state,
                (self.robot.x, self.robot.y),
                self.dashboard.metrics,
            )

    # ────────────────── render ───────────────────────────────

    def _render(self):
        # Set viewport to full window for 3D scene
        glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.renderer.begin_frame()

        # Apply camera
        self.camera.apply()

        # 3D scene
        self.renderer.draw_grid_floor(GRID_COLS, GRID_ROWS)
        self.renderer.draw_obstacles(self.grid)
        self.renderer.draw_start_end(self.grid.start, self.grid.end)

        if self.path_result:
            self.renderer.draw_visited(self.path_result.visited, self.viz_progress)
            if self.viz_progress >= len(self.path_result.visited):
                self.renderer.draw_path(self.path_result.path)

        if self.state in (State.SIMULATING, State.FINISHED):
            self.renderer.draw_robot(self.robot)

        # UI overlay (2D on top of 3D)
        self.dashboard.render()


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sim = Simulation()
    try:
        sim.run()
    finally:
        sim.ros_bridge.shutdown()
