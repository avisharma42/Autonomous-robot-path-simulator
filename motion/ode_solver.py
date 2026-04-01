"""
ODE‑based robot motion model using RK4 (Runge‑Kutta 4th order) integration.

State vector: [x, y, theta, v]
  x, y   – position in world coordinates (continuous, not grid‑locked)
  theta  – heading angle in radians (0 = +X direction)
  v      – forward speed (cells per second)

The robot follows a list of waypoints produced by the path planner,
steering and accelerating smoothly using proportional control.
"""

import math
from utils.config import (
    ROBOT_MAX_SPEED, ROBOT_ACCELERATION,
    ROBOT_TURN_SPEED, ROBOT_ARRIVE_RADIUS, ROBOT_SLOW_RADIUS,
)


def _angle_diff(target, current):
    """Signed shortest angular difference in (‑pi, pi]."""
    d = (target - current) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d


class RobotMotion:
    """
    Smooth robot motion along a waypoint path using ODE + RK4 integration.
    """

    def __init__(self):
        # State: [x, y, theta, v]
        self.state = [0.0, 0.0, 0.0, 0.0]
        self.waypoints: list[tuple[float, float]] = []
        self.waypoint_idx = 0
        self.finished = False
        self.trail: list[tuple[float, float]] = []   # position history
        self.max_trail = 300

        # Tunable gains
        self.k_turn = ROBOT_TURN_SPEED
        self.k_accel = ROBOT_ACCELERATION
        self.max_speed = ROBOT_MAX_SPEED
        self.arrive_radius = ROBOT_ARRIVE_RADIUS
        self.slow_radius = ROBOT_SLOW_RADIUS
        self.speed_multiplier = 1.0   # controlled by UI slider

    # ────────────────── public interface ──────────────────────

    def set_waypoints(self, path_cells):
        """
        Convert grid‑cell path [(col, row), ...] to world waypoints
        (center of each cell) and reset the motion state.
        """
        if not path_cells:
            return
        self.waypoints = [(c + 0.5, r + 0.5) for c, r in path_cells]
        sx, sy = self.waypoints[0]
        # Initial heading towards second waypoint (if available)
        if len(self.waypoints) > 1:
            nx, ny = self.waypoints[1]
            theta0 = math.atan2(ny - sy, nx - sx)
        else:
            theta0 = 0.0
        self.state = [sx, sy, theta0, 0.0]
        self.waypoint_idx = 1  # start moving toward index 1
        self.finished = False
        self.trail.clear()

    def replan_waypoints(self, path_cells):
        """
        Update waypoint list while preserving current continuous state.
        Used for real-time replanning when dynamic obstacles move.
        """
        if not path_cells:
            return

        # If no active trajectory exists, fall back to full reset behavior.
        if not self.waypoints or self.finished:
            self.set_waypoints(path_cells)
            return

        self.waypoints = [(c + 0.5, r + 0.5) for c, r in path_cells]
        self.finished = False

        # Keep state continuity: do not reset x, y, heading, or speed.
        if len(self.waypoints) == 1:
            self.waypoint_idx = 0
            return

        # Skip first target if we are already effectively at it.
        tx, ty = self.waypoints[0]
        dx = tx - self.state[0]
        dy = ty - self.state[1]
        if math.sqrt(dx * dx + dy * dy) < self.arrive_radius * 1.6:
            self.waypoint_idx = 1
        else:
            self.waypoint_idx = 0

    def update(self, dt):
        """Advance the simulation by dt seconds using RK4 integration."""
        if self.finished or not self.waypoints or self.waypoint_idx >= len(self.waypoints):
            self.finished = True
            return

        effective_dt = dt * self.speed_multiplier

        # Perform RK4 step (may subdivide for stability)
        substeps = max(1, int(effective_dt / 0.005))
        h = effective_dt / substeps
        for _ in range(substeps):
            self.state = self._rk4_step(self.state, h)

        # Record trail
        self.trail.append((self.state[0], self.state[1]))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        # Check if we reached the current waypoint
        tx, ty = self.waypoints[self.waypoint_idx]
        dx = tx - self.state[0]
        dy = ty - self.state[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < self.arrive_radius:
            self.waypoint_idx += 1
            if self.waypoint_idx >= len(self.waypoints):
                self.finished = True
                self.state[3] = 0.0  # stop

    # ────────────────── RK4 integrator ───────────────────────

    def _rk4_step(self, state, h):
        """
        Fourth‑order Runge‑Kutta integration step.
        Computes k1..k4 slopes and combines them for accurate integration.
        """
        k1 = self._derivatives(state)
        s2 = [s + 0.5 * h * k for s, k in zip(state, k1)]
        k2 = self._derivatives(s2)
        s3 = [s + 0.5 * h * k for s, k in zip(state, k2)]
        k3 = self._derivatives(s3)
        s4 = [s + h * k for s, k in zip(state, k3)]
        k4 = self._derivatives(s4)

        new_state = [
            s + (h / 6.0) * (a + 2*b + 2*c + d)
            for s, a, b, c, d in zip(state, k1, k2, k3, k4)
        ]
        # Clamp speed to [0, max]
        new_state[3] = max(0.0, min(new_state[3], self.max_speed))
        # Normalise heading to [0, 2pi)
        new_state[2] = new_state[2] % (2 * math.pi)
        return new_state

    def _derivatives(self, state):
        """
        Compute the time‑derivatives of the state vector.
        dx/dt = v * cos(theta)
        dy/dt = v * sin(theta)
        dtheta/dt = omega   (proportional control toward target heading)
        dv/dt = acceleration (proportional control toward desired speed)
        """
        x, y, theta, v = state

        if self.waypoint_idx >= len(self.waypoints):
            return [0.0, 0.0, 0.0, -self.k_accel * v]

        # Target waypoint
        tx, ty = self.waypoints[self.waypoint_idx]
        dx_t = tx - x
        dy_t = ty - y
        dist = math.sqrt(dx_t * dx_t + dy_t * dy_t)

        # Desired heading
        desired_theta = math.atan2(dy_t, dx_t)
        angle_err = _angle_diff(desired_theta, theta)

        # Angular velocity (proportional to angle error, clamped)
        omega = self.k_turn * angle_err
        omega = max(-self.k_turn * 2, min(omega, self.k_turn * 2))

        # Desired speed: slow down near waypoints and when facing wrong way
        heading_factor = max(0.0, math.cos(angle_err))  # 1 when aligned, 0 when perpendicular
        if dist < self.slow_radius:
            speed_target = self.max_speed * (dist / self.slow_radius) * heading_factor
        else:
            speed_target = self.max_speed * heading_factor

        speed_target = max(speed_target, 0.3)  # minimum creep speed

        # Acceleration
        accel = self.k_accel * (speed_target - v)

        # Kinematic equations
        dx_dt = v * math.cos(theta)
        dy_dt = v * math.sin(theta)

        return [dx_dt, dy_dt, omega, accel]

    # ────────────────── properties ───────────────────────────

    @property
    def x(self):
        return self.state[0]

    @property
    def y(self):
        return self.state[1]

    @property
    def heading(self):
        return self.state[2]

    @property
    def speed(self):
        return self.state[3]

    @property
    def position(self):
        return (self.state[0], self.state[1])
