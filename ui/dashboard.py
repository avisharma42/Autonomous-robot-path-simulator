"""
UI Dashboard overlay rendered on top of the 3D scene.
Uses Pygame surfaces converted to OpenGL textures for text/button rendering.
Implements a dark futuristic / glassmorphism theme.
"""

import pygame
from OpenGL.GL import *
from utils.config import (
    PANEL_WIDTH, PANEL_PADDING, BUTTON_HEIGHT, BUTTON_SPACING,
    SECTION_SPACING, SLIDER_HEIGHT,
    PANEL_BG, PANEL_BORDER, BUTTON_NORMAL, BUTTON_HOVER, BUTTON_ACTIVE,
    BUTTON_TEXT, LABEL_COLOR, METRIC_VALUE,
    WINDOW_WIDTH, WINDOW_HEIGHT,
)


class Button:
    """A clickable UI button."""

    def __init__(self, x, y, w, h, label, action_id):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.action_id = action_id
        self.hovered = False
        self.active = False   # visually selected / toggled

    def contains(self, mx, my):
        return self.rect.collidepoint(mx, my)


class Slider:
    """A horizontal slider control."""

    def __init__(self, x, y, w, h, label, min_val, max_val, value, action_id):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.action_id = action_id
        self.dragging = False

    def contains(self, mx, my):
        return self.rect.collidepoint(mx, my)

    def set_from_mouse(self, mx):
        t = (mx - self.rect.x) / max(self.rect.width, 1)
        t = max(0.0, min(1.0, t))
        self.value = self.min_val + t * (self.max_val - self.min_val)

    @property
    def normalized(self):
        return (self.value - self.min_val) / max(self.max_val - self.min_val, 0.001)


class Dashboard:
    """
    Left‑panel UI rendered as a Pygame surface, then drawn via OpenGL.
    """

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.panel_w = PANEL_WIDTH
        self.font_title = None
        self.font_label = None
        self.font_small = None
        self.buttons: list[Button] = []
        self.sliders: list[Slider] = []
        self.metrics = {"time": 0.0, "nodes": 0, "path_len": 0, "algorithm": "A*"}
        self.comparison = None  # dict of algorithm -> PathResult
        self._tex_id = None
        self._surface = None
        self._needs_redraw = True
        self._init_fonts()
        self._build_controls()

    def _init_fonts(self):
        if not pygame.font.get_init():
            pygame.font.init()
        self.font_title = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_label = pygame.font.SysFont("Segoe UI", 15)
        self.font_small = pygame.font.SysFont("Segoe UI", 13)
        self.font_metric = pygame.font.SysFont("Consolas", 14)

    def _build_controls(self):
        """Create buttons and sliders."""
        p = PANEL_PADDING
        x = p
        w = self.panel_w - 2 * p
        y = 60  # below title

        # Section: Algorithm
        y += 5
        self._section_label_y_algo = y
        y += 22
        for label, aid in [("A*", "algo_astar"), ("Dijkstra", "algo_dijkstra"), ("BFS", "algo_bfs")]:
            btn = Button(x, y, w, BUTTON_HEIGHT, label, aid)
            if aid == "algo_astar":
                btn.active = True
            self.buttons.append(btn)
            y += BUTTON_HEIGHT + BUTTON_SPACING

        y += SECTION_SPACING - BUTTON_SPACING

        # Section: Tools
        self._section_label_y_tools = y
        y += 22
        for label, aid in [
            ("Place Start", "tool_start"),
            ("Place End", "tool_end"),
            ("Draw Walls", "tool_obstacle"),
            ("Eraser", "tool_erase"),
        ]:
            btn = Button(x, y, w, BUTTON_HEIGHT, label, aid)
            if aid == "tool_obstacle":
                btn.active = True
            self.buttons.append(btn)
            y += BUTTON_HEIGHT + BUTTON_SPACING

        y += SECTION_SPACING - BUTTON_SPACING

        # Section: Controls
        self._section_label_y_ctrl = y
        y += 22
        for label, aid in [
            ("Find Path", "find_path"),
            ("Start Sim", "start_sim"),
            ("Pause", "pause"),
            ("Reset", "reset"),
        ]:
            self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, label, aid))
            y += BUTTON_HEIGHT + BUTTON_SPACING

        y += SECTION_SPACING - BUTTON_SPACING

        # Slider: speed
        self._slider_label_y = y
        y += 20
        self.sliders.append(
            Slider(x, y, w, SLIDER_HEIGHT, "Speed", 0.2, 5.0, 1.0, "speed")
        )
        y += SLIDER_HEIGHT + 12

        # Toggle buttons
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Dynamic Obs", "toggle_dynamic"))
        y += BUTTON_HEIGHT + BUTTON_SPACING
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Follow Cam", "toggle_follow"))
        y += BUTTON_HEIGHT + BUTTON_SPACING
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Random Map", "random_map"))
        y += BUTTON_HEIGHT + BUTTON_SPACING
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Compare All", "compare_all"))
        y += BUTTON_HEIGHT + BUTTON_SPACING
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Save Map", "save_map"))
        y += BUTTON_HEIGHT + BUTTON_SPACING
        self.buttons.append(Button(x, y, w, BUTTON_HEIGHT, "Load Map", "load_map"))
        y += BUTTON_HEIGHT + BUTTON_SPACING

        # Metrics start position
        self._metrics_y = y + 10

    # ────────────────── event handling ───────────────────────

    def handle_click(self, mx, my):
        """Returns action_id of clicked element, or None."""
        if mx > self.panel_w:
            return None
        for btn in self.buttons:
            if btn.contains(mx, my):
                self._needs_redraw = True
                return btn.action_id
        for slider in self.sliders:
            if slider.contains(mx, my):
                slider.dragging = True
                slider.set_from_mouse(mx)
                self._needs_redraw = True
                return slider.action_id
        return None

    def handle_mouse_up(self):
        for slider in self.sliders:
            slider.dragging = False

    def handle_mouse_move(self, mx, my):
        changed = False
        for btn in self.buttons:
            was = btn.hovered
            btn.hovered = btn.contains(mx, my)
            if btn.hovered != was:
                changed = True
        for slider in self.sliders:
            if slider.dragging:
                slider.set_from_mouse(mx)
                changed = True
        if changed:
            self._needs_redraw = True
        return changed

    def set_active_algorithm(self, algo_id):
        for btn in self.buttons:
            if btn.action_id.startswith("algo_"):
                btn.active = (btn.action_id == algo_id)
        self._needs_redraw = True

    def set_active_tool(self, tool_id):
        for btn in self.buttons:
            if btn.action_id.startswith("tool_"):
                btn.active = (btn.action_id == tool_id)
        self._needs_redraw = True

    def set_toggle(self, action_id, state):
        for btn in self.buttons:
            if btn.action_id == action_id:
                btn.active = state
                self._needs_redraw = True

    def update_metrics(self, **kwargs):
        self.metrics.update(kwargs)
        self._needs_redraw = True

    def set_comparison(self, comparison):
        self.comparison = comparison
        self._needs_redraw = True

    def get_speed(self):
        for s in self.sliders:
            if s.action_id == "speed":
                return s.value
        return 1.0

    def mark_dirty(self):
        self._needs_redraw = True

    # ────────────────── rendering ────────────────────────────

    def render(self):
        """Draw the UI panel as a 2D overlay on the OpenGL scene."""
        if self._needs_redraw:
            self._render_to_surface()
            self._upload_texture()
            self._needs_redraw = False

        if self._tex_id is None:
            return

        # Switch to 2D orthographic
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.screen_w, self.screen_h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self._tex_id)

        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(self.panel_w, 0)
        glTexCoord2f(1, 1); glVertex2f(self.panel_w, self.screen_h)
        glTexCoord2f(0, 1); glVertex2f(0, self.screen_h)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _render_to_surface(self):
        """Render the full UI panel to a Pygame surface."""
        surf = pygame.Surface((self.panel_w, self.screen_h), pygame.SRCALPHA)

        # Panel background with glassmorphism effect
        bg = pygame.Surface((self.panel_w, self.screen_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surf.blit(bg, (0, 0))

        # Right border line
        pygame.draw.line(surf, PANEL_BORDER, (self.panel_w - 1, 0),
                         (self.panel_w - 1, self.screen_h), 2)

        p = PANEL_PADDING

        # Title
        title_surf = self.font_title.render("Robot Path Sim", True, (230, 230, 250))
        surf.blit(title_surf, (p, 16))

        # Subtitle
        sub_surf = self.font_small.render("Autonomous Navigation", True, (130, 130, 170))
        surf.blit(sub_surf, (p, 42))

        # Section labels
        self._draw_section_label(surf, "ALGORITHM", p, self._section_label_y_algo)
        self._draw_section_label(surf, "TOOLS", p, self._section_label_y_tools)
        self._draw_section_label(surf, "CONTROLS", p, self._section_label_y_ctrl)
        self._draw_section_label(surf, "SPEED", p, self._slider_label_y)

        # Buttons
        for btn in self.buttons:
            self._draw_button(surf, btn)

        # Sliders
        for slider in self.sliders:
            self._draw_slider(surf, slider)

        # Metrics
        self._draw_metrics(surf, p, self._metrics_y)

        # Comparison results
        if self.comparison:
            self._draw_comparison(surf, p, self._metrics_y + 120)

        # Keyboard hints at bottom
        self._draw_hints(surf)

        self._surface = surf

    def _draw_section_label(self, surf, text, x, y):
        label = self.font_small.render(text, True, (100, 100, 140))
        surf.blit(label, (x, y))
        pygame.draw.line(surf, (60, 60, 100, 100), (x, y + 17),
                         (self.panel_w - PANEL_PADDING, y + 17), 1)

    def _draw_button(self, surf, btn):
        if btn.active:
            color = BUTTON_ACTIVE
        elif btn.hovered:
            color = BUTTON_HOVER
        else:
            color = BUTTON_NORMAL

        # Rounded rectangle approximation
        r = btn.rect
        bg = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg.fill(color)
        # Corner rounding via anti-aliased circles
        radius = 6
        corners = [(radius, radius), (r.width - radius, radius),
                    (radius, r.height - radius), (r.width - radius, r.height - radius)]
        for cx, cy in corners:
            pygame.draw.circle(bg, color, (cx, cy), radius)
        pygame.draw.rect(bg, color, (radius, 0, r.width - 2*radius, r.height))
        pygame.draw.rect(bg, color, (0, radius, r.width, r.height - 2*radius))

        surf.blit(bg, (r.x, r.y))

        # Border
        border_color = (100, 110, 180, 120) if btn.active else (70, 70, 110, 80)
        pygame.draw.rect(surf, border_color, r, 1, border_radius=radius)

        # Label
        text_color = (255, 255, 255) if btn.active else BUTTON_TEXT
        label = self.font_label.render(btn.label, True, text_color)
        tx = r.x + (r.width - label.get_width()) // 2
        ty = r.y + (r.height - label.get_height()) // 2
        surf.blit(label, (tx, ty))

    def _draw_slider(self, surf, slider):
        r = slider.rect
        # Track
        track_rect = pygame.Rect(r.x, r.y + r.height // 2 - 3, r.width, 6)
        pygame.draw.rect(surf, (40, 40, 70), track_rect, border_radius=3)

        # Filled portion
        fill_w = int(slider.normalized * r.width)
        fill_rect = pygame.Rect(r.x, r.y + r.height // 2 - 3, fill_w, 6)
        pygame.draw.rect(surf, (80, 100, 200), fill_rect, border_radius=3)

        # Handle
        hx = r.x + fill_w
        hy = r.y + r.height // 2
        pygame.draw.circle(surf, (120, 140, 230), (hx, hy), 8)
        pygame.draw.circle(surf, (200, 210, 255), (hx, hy), 4)

        # Value label
        val_text = f"{slider.value:.1f}x"
        val_surf = self.font_small.render(val_text, True, METRIC_VALUE)
        surf.blit(val_surf, (r.x + r.width - val_surf.get_width(), r.y - 2))

    def _draw_metrics(self, surf, x, y):
        self._draw_section_label(surf, "METRICS", x, y)
        y += 24
        items = [
            ("Algorithm", self.metrics.get("algorithm", "A*")),
            ("Time (ms)", f"{self.metrics.get('time', 0):.2f}"),
            ("Nodes explored", str(self.metrics.get("nodes", 0))),
            ("Path length", str(self.metrics.get("path_len", 0))),
        ]
        for label, value in items:
            lbl = self.font_small.render(label, True, LABEL_COLOR)
            val = self.font_metric.render(value, True, METRIC_VALUE)
            surf.blit(lbl, (x, y))
            surf.blit(val, (self.panel_w - PANEL_PADDING - val.get_width(), y))
            y += 20

    def _draw_comparison(self, surf, x, y):
        self._draw_section_label(surf, "COMPARISON", x, y)
        y += 24
        valid_results = [(name, r) for name, r in self.comparison.items() if r.success]
        max_time = max((r.time_ms for _, r in valid_results), default=1.0)
        max_nodes = max((r.nodes_explored for _, r in valid_results), default=1)

        for algo_name, result in self.comparison.items():
            color = (100, 200, 120) if result.success else (200, 100, 100)
            header = self.font_small.render(algo_name, True, color)
            surf.blit(header, (x, y))
            y += 16

            bar_w = self.panel_w - PANEL_PADDING * 2 - 84
            bar_h = 6
            bar_x = x + 78

            time_ratio = (result.time_ms / max_time) if result.success else 0.0
            nodes_ratio = (result.nodes_explored / max_nodes) if result.success else 0.0

            # Time bar
            time_label = self.font_small.render("t", True, (130, 130, 170))
            surf.blit(time_label, (x + 58, y + 1))
            pygame.draw.rect(surf, (40, 40, 70), (bar_x, y + 2, bar_w, bar_h), border_radius=3)
            pygame.draw.rect(
                surf,
                (110, 180, 255) if result.success else (100, 80, 80),
                (bar_x, y + 2, max(1, int(bar_w * time_ratio)), bar_h),
                border_radius=3,
            )
            y += 10

            # Node bar
            nodes_label = self.font_small.render("n", True, (130, 130, 170))
            surf.blit(nodes_label, (x + 58, y + 1))
            pygame.draw.rect(surf, (40, 40, 70), (bar_x, y + 2, bar_w, bar_h), border_radius=3)
            pygame.draw.rect(
                surf,
                (140, 120, 255) if result.success else (100, 80, 80),
                (bar_x, y + 2, max(1, int(bar_w * nodes_ratio)), bar_h),
                border_radius=3,
            )
            y += 12

            detail = f"  {result.time_ms:.2f}ms | {result.nodes_explored} nodes | cost {result.cost:.1f}"
            det_surf = self.font_small.render(detail, True, (150, 150, 180))
            surf.blit(det_surf, (x, y))
            y += 20

    def _draw_hints(self, surf):
        hints = [
            "RMB drag: Rotate cam",
            "Scroll: Zoom in/out",
            "F: Toggle follow cam",
            "Space: Pause/Resume",
            "R: Reset",
            "S/L: Save/Load map",
        ]
        y = self.screen_h - len(hints) * 16 - 10
        for hint in hints:
            hint_surf = self.font_small.render(hint, True, (80, 80, 120))
            surf.blit(hint_surf, (PANEL_PADDING, y))
            y += 16

    def _upload_texture(self):
        """Upload the Pygame surface as an OpenGL texture."""
        if self._surface is None:
            return
        # Keep texture rows in original order because the quad UVs
        # already match the top-left UI coordinate system used by glOrtho.
        data = pygame.image.tostring(self._surface, "RGBA", False)
        w, h = self._surface.get_size()

        if self._tex_id is None:
            self._tex_id = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
