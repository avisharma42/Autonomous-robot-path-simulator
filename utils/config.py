"""
Configuration constants for the Autonomous Robot Path Simulation.
All tunable parameters are centralized here for easy modification.
"""

# ──────────────────────────── Window ────────────────────────────
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
FPS = 60
TITLE = "Autonomous Robot Path Simulator"

# ──────────────────────────── Grid ──────────────────────────────
GRID_COLS = 30          # number of columns
GRID_ROWS = 20          # number of rows
CELL_SIZE = 1.0         # world‑space size of one cell

# ──────────────────────────── Colors (RGBA 0‑255) ───────────────
BG_COLOR          = (15, 15, 26, 255)
GRID_LINE_COLOR   = (40, 40, 70, 120)
GRID_FILL_COLOR   = (22, 22, 38, 255)

OBSTACLE_TOP      = (58, 58, 78, 255)
OBSTACLE_SIDE     = (38, 38, 55, 255)
OBSTACLE_SHADOW   = (10, 10, 20, 100)

START_COLOR       = (68, 255, 136)       # green
END_COLOR         = (255, 68, 102)       # red
PATH_COLOR        = (68, 136, 255)       # neon blue
PATH_GLOW_COLOR   = (68, 136, 255, 60)
VISITED_COLOR     = (51, 68, 136, 90)    # light blue translucent

ROBOT_COLOR       = (255, 200, 60)
ROBOT_TRAIL_COLOR = (255, 200, 60, 40)

# UI panel colors
PANEL_BG          = (20, 20, 42, 220)
PANEL_BORDER      = (60, 60, 110, 180)
BUTTON_NORMAL     = (45, 45, 85, 230)
BUTTON_HOVER      = (65, 75, 140, 240)
BUTTON_ACTIVE     = (80, 100, 200, 250)
BUTTON_TEXT       = (220, 220, 240)
LABEL_COLOR       = (170, 170, 200)
METRIC_VALUE      = (120, 200, 255)

# ──────────────────────────── Robot Motion ──────────────────────
ROBOT_MAX_SPEED      = 4.0   # cells per second
ROBOT_ACCELERATION   = 8.0   # cells per second^2
ROBOT_TURN_SPEED     = 6.0   # radians per second
ROBOT_ARRIVE_RADIUS  = 0.15  # distance to consider waypoint reached
ROBOT_SLOW_RADIUS    = 0.8   # distance to start slowing down

# ──────────────────────────── Dynamic Obstacles ─────────────────
DYNAMIC_OBS_SPEED    = 1.5   # cells per second
DYNAMIC_OBS_COUNT    = 3     # default count when toggled on

# ──────────────────────────── Visualization ─────────────────────
VISITED_ANIM_SPEED   = 200   # nodes revealed per second during viz
PATH_PULSE_SPEED     = 2.0   # pulse animation speed
GLOW_LAYERS          = 6     # number of glow layers for effects

# ──────────────────────────── UI Layout ─────────────────────────
PANEL_WIDTH          = 280   # left panel width in pixels
PANEL_PADDING        = 16
BUTTON_HEIGHT        = 36
BUTTON_SPACING       = 8
SLIDER_HEIGHT        = 20
SECTION_SPACING      = 20

# ──────────────────────────── Storage / Integration ─────────────
DEFAULT_MAP_PATH     = "maps/default_map.json"
ENABLE_ROS_BRIDGE    = False
