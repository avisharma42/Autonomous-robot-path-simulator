"""
3D camera system with orbit, zoom, pan, and follow‑robot mode.
Uses spherical coordinates for intuitive mouse‑driven control.
"""

import math
from OpenGL.GL import *
from OpenGL.GLU import *


class Camera:
    """
    Orbiting camera that looks at a target point.
    Spherical coordinates (yaw, pitch, distance) control the viewpoint.
    """

    def __init__(self, target=(15.0, 0.0, 10.0)):
        # Orbit parameters
        self.yaw = -45.0          # degrees, horizontal rotation
        self.pitch = 55.0         # degrees, vertical tilt (0=horizon, 90=top‑down)
        self.distance = 25.0      # distance from target

        # Target point the camera looks at
        self.target = list(target)  # [x, y, z] in world coords

        # Constraints
        self.min_pitch = 10.0
        self.max_pitch = 85.0
        self.min_dist = 5.0
        self.max_dist = 60.0

        # Follow mode
        self.follow_mode = False
        self.follow_target = None    # (x, z) of robot
        self.follow_smoothing = 4.0  # lerp speed

        # Pan state
        self._panning = False
        self._rotating = False
        self._last_mouse = (0, 0)

    # ────────────────── apply to OpenGL ──────────────────────

    def apply(self):
        """Set up the modelview matrix using gluLookAt."""
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        # Camera position in spherical coordinates around target
        cos_p = math.cos(pitch_rad)
        eye_x = self.target[0] + self.distance * cos_p * math.sin(yaw_rad)
        eye_y = self.target[1] + self.distance * math.sin(pitch_rad)
        eye_z = self.target[2] + self.distance * cos_p * math.cos(yaw_rad)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(
            eye_x, eye_y, eye_z,           # eye position
            self.target[0], self.target[1], self.target[2],  # look‑at
            0.0, 1.0, 0.0,                 # up vector
        )

    # ────────────────── input handling ───────────────────────

    def handle_mouse_down(self, button, pos):
        """button: 1=left, 2=middle, 3=right."""
        if button == 3:  # right = rotate
            self._rotating = True
            self._panning = False
            self._last_mouse = pos
        elif button == 2:  # middle = pan
            self._panning = True
            self._rotating = False
            self._last_mouse = pos

    def handle_mouse_up(self, button, pos):
        if button == 3:
            self._rotating = False
        elif button == 2:
            self._panning = False

    def handle_mouse_motion(self, pos, buttons_pressed):
        """
        Process mouse drag.
        buttons_pressed: (left, middle, right) booleans from pygame.
        """
        dx = pos[0] - self._last_mouse[0]
        dy = pos[1] - self._last_mouse[1]
        self._last_mouse = pos

        if self._rotating or buttons_pressed[2]:  # right drag = orbit
            self.yaw += dx * 0.3
            self.pitch += dy * 0.3
            self.pitch = max(self.min_pitch, min(self.pitch, self.max_pitch))
        elif self._panning or buttons_pressed[1]:  # middle drag = pan
            # Pan in the camera's local XZ plane
            yaw_rad = math.radians(self.yaw)
            speed = self.distance * 0.002
            self.target[0] -= (math.cos(yaw_rad) * dx + math.sin(yaw_rad) * dy) * speed
            self.target[2] += (math.sin(yaw_rad) * dx - math.cos(yaw_rad) * dy) * speed

    def handle_scroll(self, scroll_y):
        """Zoom in/out with mouse wheel."""
        self.distance -= scroll_y * 1.5
        self.distance = max(self.min_dist, min(self.distance, self.max_dist))

    # ────────────────── follow mode ──────────────────────────

    def toggle_follow(self):
        self.follow_mode = not self.follow_mode

    def update(self, dt, robot_pos=None):
        """
        Smoothly track the robot when follow mode is on.
        robot_pos: (world_x, world_z)
        """
        if self.follow_mode and robot_pos is not None:
            tx, tz = robot_pos
            lerp = 1.0 - math.exp(-self.follow_smoothing * dt)
            self.target[0] += (tx - self.target[0]) * lerp
            self.target[2] += (tz - self.target[2]) * lerp

    # ────────────────── utility ──────────────────────────────

    def reset(self, grid_cols, grid_rows):
        """Reset camera to default overview position for the given grid."""
        self.target = [grid_cols / 2.0, 0.0, grid_rows / 2.0]
        self.yaw = -45.0
        self.pitch = 55.0
        self.distance = max(grid_cols, grid_rows) * 1.1
        self.follow_mode = False
