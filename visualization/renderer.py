"""
OpenGL 3D renderer for the robot path simulation.

Draws the grid floor, obstacles, path, visited nodes, robot,
start/end markers, and glow effects using the fixed‑function pipeline.
"""

import math
from OpenGL.GL import *
from OpenGL.GLU import *
from utils.config import (
    GRID_COLS, GRID_ROWS, CELL_SIZE,
    OBSTACLE_TOP, OBSTACLE_SIDE,
    START_COLOR, END_COLOR, PATH_COLOR, VISITED_COLOR,
    ROBOT_COLOR, ROBOT_TRAIL_COLOR,
    GLOW_LAYERS, PATH_PULSE_SPEED,
)


def _gl_color(rgb_or_rgba, alpha=1.0):
    """Convert a (R, G, B[, A]) tuple (0‑255) to OpenGL float colour."""
    r, g, b = rgb_or_rgba[0] / 255, rgb_or_rgba[1] / 255, rgb_or_rgba[2] / 255
    a = rgb_or_rgba[3] / 255 if len(rgb_or_rgba) == 4 else alpha
    return (r, g, b, a)


def _set_material(rgb, alpha=1.0, emission=0.0):
    """Quick helper to set GL material colours."""
    c = _gl_color(rgb, alpha)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, c)
    if emission > 0:
        e = (c[0] * emission, c[1] * emission, c[2] * emission, 1.0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, e)
    else:
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0, 0, 0, 1))


class Renderer:
    """Manages all OpenGL drawing for the simulation scene."""

    def __init__(self, viewport_width, viewport_height):
        self.vp_width = viewport_width
        self.vp_height = viewport_height
        self.time = 0.0  # running clock for animations

    # ────────────────── initialisation ───────────────────────

    def init_gl(self):
        """One‑time OpenGL state setup."""
        glClearColor(0.06, 0.06, 0.10, 1.0)  # dark background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)

        # Light 0: directional "sun" from upper‑right
        glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 1.0, 0.3, 0.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.25, 0.25, 0.30, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  (0.75, 0.73, 0.70, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (0.4, 0.4, 0.4, 1.0))

        # Light 1: soft fill from opposite side
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_POSITION, (-0.3, 0.6, -0.5, 0.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT,  (0.05, 0.05, 0.08, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  (0.20, 0.22, 0.30, 1.0))

        # Blending for translucent effects
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Perspective projection
        self._setup_projection()

    def _setup_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.vp_width / max(self.vp_height, 1)
        gluPerspective(45.0, aspect, 0.5, 200.0)
        glMatrixMode(GL_MODELVIEW)

    def resize(self, w, h):
        self.vp_width = w
        self.vp_height = h
        glViewport(0, 0, w, h)
        self._setup_projection()

    # ────────────────── per‑frame entry ──────────────────────

    def begin_frame(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def tick(self, dt):
        self.time += dt

    # ════════════════════════════════════════════════════════
    #  DRAW CALLS
    # ════════════════════════════════════════════════════════

    def draw_grid_floor(self, cols, rows):
        """Draw the ground plane and grid lines."""
        # Solid dark floor
        glDisable(GL_LIGHTING)
        glColor4f(0.09, 0.09, 0.15, 1.0)
        glBegin(GL_QUADS)
        glVertex3f(-0.5, -0.01, -0.5)
        glVertex3f(cols + 0.5, -0.01, -0.5)
        glVertex3f(cols + 0.5, -0.01, rows + 0.5)
        glVertex3f(-0.5, -0.01, rows + 0.5)
        glEnd()

        # Grid lines with subtle glow
        glEnable(GL_BLEND)
        glLineWidth(1.0)
        glColor4f(0.18, 0.18, 0.30, 0.5)
        glBegin(GL_LINES)
        for c in range(cols + 1):
            glVertex3f(c, 0.001, 0)
            glVertex3f(c, 0.001, rows)
        for r in range(rows + 1):
            glVertex3f(0, 0.001, r)
            glVertex3f(cols, 0.001, r)
        glEnd()

        # Brighter border
        glLineWidth(2.0)
        glColor4f(0.25, 0.25, 0.45, 0.7)
        glBegin(GL_LINE_LOOP)
        glVertex3f(0, 0.002, 0)
        glVertex3f(cols, 0.002, 0)
        glVertex3f(cols, 0.002, rows)
        glVertex3f(0, 0.002, rows)
        glEnd()

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    # ──────────────────── obstacles ──────────────────────────

    def draw_obstacles(self, grid):
        """Draw obstacles as 3D blocks with lighting."""
        for r in range(grid.rows):
            for c in range(grid.cols):
                if grid.cells[r, c] == 1:
                    self._draw_block(c, r, OBSTACLE_TOP, OBSTACLE_SIDE, height=0.7)
                elif grid.cells[r, c] == 2:
                    # Dynamic obstacle – slightly different colour
                    self._draw_block(c, r, (90, 50, 50, 255), (70, 35, 35, 255), height=0.5)

    def _draw_block(self, col, row, top_color, side_color, height=0.7):
        """Draw a single 3D block at grid position (col, row)."""
        x0, z0 = col, row
        x1, z1 = col + CELL_SIZE, row + CELL_SIZE
        y0, y1 = 0.0, height

        glEnable(GL_LIGHTING)
        # Top face
        _set_material(top_color)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(x0, y1, z0)
        glVertex3f(x1, y1, z0)
        glVertex3f(x1, y1, z1)
        glVertex3f(x0, y1, z1)
        glEnd()

        # Front face
        _set_material(side_color)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, -1)
        glVertex3f(x0, y0, z0)
        glVertex3f(x1, y0, z0)
        glVertex3f(x1, y1, z0)
        glVertex3f(x0, y1, z0)
        glEnd()

        # Back face
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(x0, y0, z1)
        glVertex3f(x0, y1, z1)
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y0, z1)
        glEnd()

        # Left face
        glBegin(GL_QUADS)
        glNormal3f(-1, 0, 0)
        glVertex3f(x0, y0, z0)
        glVertex3f(x0, y1, z0)
        glVertex3f(x0, y1, z1)
        glVertex3f(x0, y0, z1)
        glEnd()

        # Right face
        glBegin(GL_QUADS)
        glNormal3f(1, 0, 0)
        glVertex3f(x1, y0, z0)
        glVertex3f(x1, y0, z1)
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z0)
        glEnd()

    # ──────────────────── visited nodes ──────────────────────

    def draw_visited(self, visited_cells, progress):
        """
        Draw explored nodes as translucent quads on the floor.
        `progress` is how many nodes to reveal (animated).
        """
        if not visited_cells:
            return
        count = min(int(progress), len(visited_cells))
        if count == 0:
            return

        glEnable(GL_BLEND)
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        y = 0.005

        for i in range(count):
            c, r = visited_cells[i]
            # Fade based on reveal order
            fade = max(0.2, 1.0 - (count - i) / max(count, 1) * 0.5)
            glColor4f(0.20, 0.35, 0.60, 0.30 * fade)
            glBegin(GL_QUADS)
            glVertex3f(c + 0.05, y, r + 0.05)
            glVertex3f(c + 0.95, y, r + 0.05)
            glVertex3f(c + 0.95, y, r + 0.95)
            glVertex3f(c + 0.05, y, r + 0.95)
            glEnd()

        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
        glDisable(GL_BLEND)

    # ──────────────────── path ───────────────────────────────

    def draw_path(self, path_cells):
        """Draw the final path as glowing raised tiles."""
        if not path_cells:
            return

        pulse = 0.5 + 0.5 * math.sin(self.time * PATH_PULSE_SPEED)

        glEnable(GL_BLEND)

        for idx, (c, r) in enumerate(path_cells):
            # Wave effect along path
            wave = 0.5 + 0.5 * math.sin(self.time * 3.0 - idx * 0.3)
            h = 0.04 + 0.03 * wave

            # Core path tile
            glDisable(GL_LIGHTING)
            base_r = PATH_COLOR[0] / 255
            base_g = PATH_COLOR[1] / 255
            base_b = PATH_COLOR[2] / 255
            glColor4f(base_r, base_g, base_b, 0.85)
            glBegin(GL_QUADS)
            glVertex3f(c + 0.1, h, r + 0.1)
            glVertex3f(c + 0.9, h, r + 0.1)
            glVertex3f(c + 0.9, h, r + 0.9)
            glVertex3f(c + 0.1, h, r + 0.9)
            glEnd()

            # Glow layers underneath
            for layer in range(GLOW_LAYERS):
                expand = (layer + 1) * 0.04
                alpha = 0.12 * pulse * (1.0 - layer / GLOW_LAYERS)
                glColor4f(base_r, base_g, base_b, alpha)
                glBegin(GL_QUADS)
                glVertex3f(c + 0.1 - expand, 0.003, r + 0.1 - expand)
                glVertex3f(c + 0.9 + expand, 0.003, r + 0.1 - expand)
                glVertex3f(c + 0.9 + expand, 0.003, r + 0.9 + expand)
                glVertex3f(c + 0.1 - expand, 0.003, r + 0.9 + expand)
                glEnd()

        glEnable(GL_LIGHTING)
        glDisable(GL_BLEND)

    # ──────────────────── start / end markers ────────────────

    def draw_start_end(self, start, end):
        """Draw glowing pillars at start and end positions."""
        if start:
            self._draw_marker(start[0], start[1], START_COLOR, "start")
        if end:
            self._draw_marker(end[0], end[1], END_COLOR, "end")

    def _draw_marker(self, col, row, color, marker_type):
        """Draw a glowing vertical pillar marker."""
        cx = col + 0.5
        cz = row + 0.5
        pulse = 0.6 + 0.4 * math.sin(self.time * 2.5 + (0 if marker_type == "start" else math.pi))

        # Base glow on ground
        glEnable(GL_BLEND)
        glDisable(GL_LIGHTING)
        cr, cg, cb = color[0] / 255, color[1] / 255, color[2] / 255
        for layer in range(8):
            radius = 0.35 + layer * 0.06
            alpha = 0.15 * pulse * (1.0 - layer / 8.0)
            glColor4f(cr, cg, cb, alpha)
            self._draw_circle(cx, 0.004, cz, radius, 16)

        # Vertical beam
        glColor4f(cr, cg, cb, 0.6 * pulse)
        beam_radius = 0.12
        height = 1.2 * pulse + 0.5
        segments = 12
        glBegin(GL_QUAD_STRIP)
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            nx = math.cos(angle)
            nz = math.sin(angle)
            glVertex3f(cx + beam_radius * nx, 0, cz + beam_radius * nz)
            glVertex3f(cx + beam_radius * 0.4 * nx, height, cz + beam_radius * 0.4 * nz)
        glEnd()

        # Top cap
        _set_material(color, emission=0.5)
        glEnable(GL_LIGHTING)
        self._draw_sphere(cx, height, cz, 0.15, color)
        glDisable(GL_BLEND)

    def _draw_circle(self, x, y, z, radius, segments):
        """Draw a flat circle on the XZ plane."""
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(x, y, z)
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            glVertex3f(x + radius * math.cos(angle), y, z + radius * math.sin(angle))
        glEnd()

    def _draw_sphere(self, x, y, z, radius, color):
        """Draw a simple low‑poly sphere using triangle strips."""
        cr, cg, cb = color[0] / 255, color[1] / 255, color[2] / 255
        glColor4f(cr, cg, cb, 1.0)
        stacks, slices_ = 8, 10
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + i / stacks)
            lat1 = math.pi * (-0.5 + (i + 1) / stacks)
            y0, yr0 = math.sin(lat0), math.cos(lat0)
            y1, yr1 = math.sin(lat1), math.cos(lat1)
            glBegin(GL_QUAD_STRIP)
            for j in range(slices_ + 1):
                lng = 2 * math.pi * j / slices_
                xn, zn = math.cos(lng), math.sin(lng)
                glNormal3f(xn * yr0, y0, zn * yr0)
                glVertex3f(x + radius * xn * yr0, y + radius * y0, z + radius * zn * yr0)
                glNormal3f(xn * yr1, y1, zn * yr1)
                glVertex3f(x + radius * xn * yr1, y + radius * y1, z + radius * zn * yr1)
            glEnd()

    # ──────────────────── robot ──────────────────────────────

    def draw_robot(self, robot):
        """Draw the robot as a 3D arrow / rover shape."""
        if robot.finished and not robot.waypoints:
            return

        x, z = robot.x, robot.y  # robot.y is world Z
        heading = robot.heading
        speed = robot.speed

        glPushMatrix()
        glTranslatef(x, 0.15, z)
        glRotatef(-math.degrees(heading), 0, 1, 0)

        # Body: low box
        _set_material(ROBOT_COLOR, emission=0.15)
        self._draw_robot_body()

        # Direction indicator: small cone at front
        glPushMatrix()
        glTranslatef(0.25, 0.05, 0)
        _set_material((255, 240, 200), emission=0.3)
        self._draw_cone(0.08, 0.15)
        glPopMatrix()

        glPopMatrix()

        # Trail
        self._draw_trail(robot.trail)

    def _draw_robot_body(self):
        """Draw a small 3D box for the robot chassis."""
        sx, sy, sz = 0.35, 0.12, 0.25  # half‑extents
        # simple box
        glBegin(GL_QUADS)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-sx, sy, -sz); glVertex3f(sx, sy, -sz)
        glVertex3f(sx, sy, sz);  glVertex3f(-sx, sy, sz)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-sx, -sy, -sz); glVertex3f(-sx, -sy, sz)
        glVertex3f(sx, -sy, sz);  glVertex3f(sx, -sy, -sz)
        # Front
        glNormal3f(1, 0, 0)
        glVertex3f(sx, -sy, -sz); glVertex3f(sx, -sy, sz)
        glVertex3f(sx, sy, sz);  glVertex3f(sx, sy, -sz)
        # Back
        glNormal3f(-1, 0, 0)
        glVertex3f(-sx, -sy, -sz); glVertex3f(-sx, sy, -sz)
        glVertex3f(-sx, sy, sz);  glVertex3f(-sx, -sy, sz)
        # Left
        glNormal3f(0, 0, -1)
        glVertex3f(-sx, -sy, -sz); glVertex3f(sx, -sy, -sz)
        glVertex3f(sx, sy, -sz);  glVertex3f(-sx, sy, -sz)
        # Right
        glNormal3f(0, 0, 1)
        glVertex3f(-sx, -sy, sz); glVertex3f(-sx, sy, sz)
        glVertex3f(sx, sy, sz);  glVertex3f(sx, -sy, sz)
        glEnd()

    def _draw_cone(self, radius, height):
        """Small cone for direction indicator."""
        segments = 8
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(1, 0, 0)
        glVertex3f(height, 0, 0)  # tip
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            ny = math.cos(angle)
            nz = math.sin(angle)
            glVertex3f(0, radius * ny, radius * nz)
        glEnd()

    def _draw_trail(self, trail):
        """Draw fading trail behind robot."""
        if len(trail) < 2:
            return
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glLineWidth(2.0)
        cr, cg, cb = ROBOT_TRAIL_COLOR[0]/255, ROBOT_TRAIL_COLOR[1]/255, ROBOT_TRAIL_COLOR[2]/255

        glBegin(GL_LINE_STRIP)
        n = len(trail)
        for i, (tx, tz) in enumerate(trail):
            alpha = (i / n) * 0.6
            glColor4f(cr, cg, cb, alpha)
            glVertex3f(tx, 0.05, tz)
        glEnd()

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        glLineWidth(1.0)

    # ──────────────────── world picking ──────────────────────

    def screen_to_grid(self, mouse_x, mouse_y, viewport_x_offset=0):
        """
        Convert screen (mouse) coordinates to grid (col, row).
        Uses OpenGL un‑projection with ray‑plane intersection.
        """
        try:
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            viewport = glGetIntegerv(GL_VIEWPORT)

            # Adjust for viewport offset (UI panel)
            adj_x = mouse_x - viewport_x_offset
            win_y = viewport[3] - mouse_y

            near = gluUnProject(adj_x, win_y, 0.0, modelview, projection, viewport)
            far = gluUnProject(adj_x, win_y, 1.0, modelview, projection, viewport)

            # Ray‑plane intersection with Y = 0
            denom = far[1] - near[1]
            if abs(denom) < 1e-6:
                return None
            t = -near[1] / denom
            if t < 0:
                return None
            hit_x = near[0] + t * (far[0] - near[0])
            hit_z = near[2] + t * (far[2] - near[2])

            col = int(math.floor(hit_x))
            row = int(math.floor(hit_z))
            return (col, row)
        except Exception:
            return None
