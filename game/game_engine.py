import math
import random
import pygame
from game.block import Block
from game.debris import Debris


def hex_to_rgb(hex_str):
    """'#4A90E2' -> (74, 144, 226)."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    """Linear interpolation: t=0 -> a, t=1 -> b."""
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Channel-wise lerp between two RGB tuples, returned as ints."""
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


class FloatingText:
    """A short-lived text popup that rises and fades out (frame-based)."""

    def __init__(self, text, font, color, center_x, y, lifetime=60, rise_speed=1.2):
        self.surface = font.render(text, True, color)  # pre-rendered once
        self.x = center_x - self.surface.get_width() / 2
        self.y = float(y)
        self.age = 0
        self.lifetime = lifetime
        self.rise_speed = rise_speed

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self):
        self.age += 1
        self.y -= self.rise_speed

    def render(self, screen):
        # Fade out linearly over the lifetime
        alpha = max(0, int(255 * (1 - self.age / self.lifetime)))
        self.surface.set_alpha(alpha)
        screen.blit(self.surface, (self.x, self.y))


class GameEngine:
    # --- Perfect Placement tuning ---
    PERFECT_TOLERANCE = 4    # max px offset that still counts as "perfect"
    PERFECT_BONUS = 50       # bonus points per perfect drop
    COMBO_THRESHOLD = 3      # perfect drops in a row needed for a width reward
    WIDTH_RESTORE = 12       # px of width restored per combo reward

    # --- Sky progression ---
    # (altitude, top/zenith color, bottom/horizon color). The sky lerps between
    # consecutive keyframes, so every stage blends smoothly into the next.
    SKY_KEYFRAMES = [
        (0,  hex_to_rgb("#4A90E2"), hex_to_rgb("#8CC3F5")),  # afternoon day blue...
        (10, hex_to_rgb("#4A90E2"), hex_to_rgb("#8CC3F5")),  # ...held until altitude 10
        (25, hex_to_rgb("#762B80"), hex_to_rgb("#E65C00")),  # golden sunset (orange horizon)
        (45, hex_to_rgb("#0F2027"), hex_to_rgb("#2C3E50")),  # twilight dusk
        (50, hex_to_rgb("#02030A"), hex_to_rgb("#0A0D1F")),  # deep space
    ]
    SKY_EASE = 0.05            # fraction of the gap closed per frame (1.0 = follow score instantly)
    STAR_FADE = (45, 50)       # altitude range over which the stars fade in
    STAR_COUNT = 70

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.block_height = 28
        self.base_width = 180

        self.font_title = pygame.font.SysFont(None, 38)
        self.font_hud = pygame.font.SysFont(None, 28)
        self.font_big = pygame.font.SysFont(None, 46)

        self._init_sky()
        self.reset()

    def get_color(self, index):
        palette = [
            (230, 75, 75),   # Crimson
            (240, 140, 45),  # Orange
            (245, 210, 50),  # Gold
            (60, 195, 110),  # Green
            (50, 150, 240),  # Blue
            (165, 80, 225),  # Purple
        ]
        return palette[index % len(palette)]

    def reset(self):
        self.score = 0          # tower height (number of blocks stacked)
        self.bonus = 0          # bonus points from perfect drops
        self.combo = 0          # current streak of consecutive perfect drops
        self.floating_texts = []
        self.debris = []        # falling off-cut pieces
        self.sky_altitude = 0.0  # smoothed copy of score that drives the sky
        self.game_over = False

        base_x = (self.width - self.base_width) // 2
        base_y = self.height - 60
        base_block = Block(base_x, base_y, self.base_width, self.block_height, self.get_color(0), speed=0)
        self.stack = [base_block]

        self.spawn_active_block()

    def spawn_active_block(self):
        top_block = self.stack[-1]
        next_y = top_block.y - self.block_height - 4
        speed = min(10.0, 4.5 + (len(self.stack) * 0.35))
        color = self.get_color(len(self.stack))

        start_x = 25 if random.choice([True, False]) else self.width - 25 - top_block.width
        self.active_block = Block(start_x, next_y, top_block.width, self.block_height, color, speed=speed)

    # ------------------------------------------------------------------
    # Drop logic
    # ------------------------------------------------------------------
    def _compute_landing(self, act, top):
        """Work out where the dropped block lands.

        Returns (x, width, is_perfect), or None on a complete miss.
        """
        # Perfect placement: active and top blocks share the same width, so the
        # offset between their left edges is the whole misalignment.
        if abs(act.x - top.x) <= self.PERFECT_TOLERANCE:
            return top.x, top.width, True  # snap flush: zero width loss

        # Otherwise: 1D interval intersection on the x-axis
        left = max(act.x, top.x)
        right = min(act.x + act.width, top.x + top.width)
        overlap = right - left

        if overlap <= 0:
            return None  # nothing to rest on -> miss
        return left, overlap, False

    def _restore_width(self, x, width):
        """Combo reward: widen the block (centered), capped at the base width.

        Returns (x, width, restored).
        """
        new_width = min(float(self.base_width), width + self.WIDTH_RESTORE)
        if new_width <= width:
            return x, width, False  # already at max width

        new_x = x - (new_width - width) / 2
        new_x = max(20, min(new_x, self.width - 20 - new_width))  # stay on screen
        return new_x, new_width, True

    def _scroll_camera_if_needed(self, new_block):
        """Shift the whole scene down once the tower gets high."""
        if new_block.y < 180:
            shift = self.block_height + 4
            for b in self.stack:
                b.y += shift
            for t in self.floating_texts:  # keep popups attached to the scene
                t.y += shift
            for d in self.debris:          # ...and falling debris
                d.y += shift

    def _spawn_perfect_feedback(self, block, restored):
        """Create the rising "+50 PERFECT!" popup (and combo reward popup)."""
        cx = block.x + block.width / 2
        self.floating_texts.append(
            FloatingText(f"+{self.PERFECT_BONUS} PERFECT!", self.font_hud,
                         (255, 230, 90), cx, block.y - 26)
        )
        if restored:
            self.floating_texts.append(
                FloatingText("WIDTH RESTORED!", self.font_hud,
                             (90, 230, 140), cx, block.y - 50, lifetime=75)
            )

    def _make_debris(self, x, y, width, color, direction):
        """Build one off-cut. direction: -1 = fell off the left side, +1 = right."""
        return Debris(
            x, y, width, self.block_height, color,
            vx=direction * random.uniform(0.6, 1.6),                 # drift outward
            angular_velocity=-direction * random.uniform(1.0, 2.5),  # tip over the edge
        )

    def _spawn_debris(self, act, kept_x, kept_width):
        """Turn whatever part of the active block was trimmed off into debris."""
        kept_right = kept_x + kept_width
        act_right = act.x + act.width

        if kept_x - act.x > 0.5:                 # overhang on the left
            self.debris.append(
                self._make_debris(act.x, act.y, kept_x - act.x, act.color, -1))
        if act_right - kept_right > 0.5:         # overhang on the right
            self.debris.append(
                self._make_debris(kept_right, act.y, act_right - kept_right, act.color, +1))

    def _spawn_miss_debris(self, act, top_block):
        """A complete miss: the entire block tumbles away to the side it missed on."""
        direction = -1 if (act.x + act.width / 2) < (top_block.x + top_block.width / 2) else 1
        self.debris.append(self._make_debris(act.x, act.y, act.width, act.color, direction))

    def drop_block(self):
        """Land the active block: perfect snap, normal trim, or game over."""
        if self.game_over:
            return

        top_block = self.stack[-1]
        act = self.active_block

        landing = self._compute_landing(act, top_block)
        if landing is None:
            self.combo = 0
            self._spawn_miss_debris(act, top_block)  # whole block falls away
            self.game_over = True
            return

        x, width, is_perfect = landing
        restored = False

        if is_perfect:
            self.combo += 1
            self.bonus += self.PERFECT_BONUS
            # Every COMBO_THRESHOLD perfects in a row -> width reward
            if self.combo % self.COMBO_THRESHOLD == 0:
                x, width, restored = self._restore_width(x, width)
        else:
            self.combo = 0  # a non-perfect landing breaks the streak
            self._spawn_debris(act, x, width)  # slice off the overhang

        new_block = Block(x, act.y, width, self.block_height, act.color, speed=0)
        self.stack.append(new_block)
        self.score += 1

        self._scroll_camera_if_needed(new_block)  # before feedback so it isn't shifted
        if is_perfect:
            self._spawn_perfect_feedback(new_block, restored)

        self.spawn_active_block()

    def handle_event(self, event):
        if self.game_over:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_r) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.reset()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.drop_block()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drop_block()

    def _update_floating_texts(self):
        """Advance popup animations and drop the ones that have faded out."""
        for t in self.floating_texts:
            t.update()
        self.floating_texts = [t for t in self.floating_texts if t.alive]

    # ------------------------------------------------------------------
    # Sky / background
    # ------------------------------------------------------------------
    def _init_sky(self):
        """Allocate the cached gradient surfaces and the fixed star field."""
        self.frame = 0
        self.sky_altitude = 0.0
        self._sky_strip = pygame.Surface((1, self.height))             # 1px-wide gradient column
        self._sky_surface = pygame.Surface((self.width, self.height))  # cached full-size sky
        self._sky_key = None                                           # colors the cache was built for

        rng = random.Random(7)  # private RNG: same stars every run, game's RNG untouched
        self.stars = [
            (rng.randrange(self.width), rng.randrange(self.height),   # x, y
             rng.choice((1, 1, 1, 2)),                                # size (mostly 1px)
             rng.uniform(0.5, 1.0),                                   # peak brightness
             rng.uniform(0.03, 0.12),                                 # twinkle speed (rad/frame)
             rng.uniform(0, math.tau))                                # twinkle phase
            for _ in range(self.STAR_COUNT)
        ]

    def _sky_colors(self, altitude):
        """Lerp the (top, bottom) sky colors for an altitude using SKY_KEYFRAMES."""
        frames = self.SKY_KEYFRAMES
        if altitude <= frames[0][0]:
            return frames[0][1], frames[0][2]
        for (a0, top0, bot0), (a1, top1, bot1) in zip(frames, frames[1:]):
            if altitude <= a1:
                t = (altitude - a0) / (a1 - a0)
                return lerp_color(top0, top1, t), lerp_color(bot0, bot1, t)
        return frames[-1][1], frames[-1][2]  # above the last keyframe: stay in deep space

    def _star_visibility(self):
        """0 below the fade range, ramping to 1 at its end."""
        start, end = self.STAR_FADE
        return min(1.0, max(0.0, (self.sky_altitude - start) / (end - start)))

    def _update_sky_altitude(self):
        """Ease sky_altitude toward score so colors glide instead of stepping."""
        diff = self.score - self.sky_altitude
        if abs(diff) < 0.01:
            self.sky_altitude = float(self.score)
        else:
            self.sky_altitude += diff * self.SKY_EASE

    def _refresh_sky_surface(self):
        """Rebuild the cached gradient only when its colors actually change.

        Most frames (held stages, or easing steps too small to change an RGB
        value) return immediately. A rebuild writes one 1px column (height
        set_at calls) and stretches it across the width with a single scale.
        """
        top, bottom = self._sky_colors(self.sky_altitude)
        if (top, bottom) == self._sky_key:
            return
        self._sky_key = (top, bottom)

        last = self.height - 1
        for y in range(self.height):
            self._sky_strip.set_at((0, y), lerp_color(top, bottom, y / last))
        pygame.transform.scale(self._sky_strip, (self.width, self.height), self._sky_surface)

    def _render_stars(self, screen):
        """Draw twinkling stars, faded in by altitude. Cheap: ~70 tiny fills."""
        visibility = self._star_visibility()
        if visibility <= 0:
            return
        for x, y, size, peak, speed, phase in self.stars:
            twinkle = 0.5 + 0.5 * math.sin(self.frame * speed + phase)  # 0..1
            v = int(255 * visibility * peak * (0.35 + 0.65 * twinkle))
            screen.fill((v, v, min(255, v + 15)), (x, y, size, size))   # faintly blue-white

    def _render_background(self, screen):
        """Draw the altitude-based sky: cached gradient, then stars on top."""
        self._refresh_sky_surface()
        screen.blit(self._sky_surface, (0, 0))
        self._render_stars(screen)

    def _update_debris(self):
        """Step debris physics and discard pieces that faded out or left the screen."""
        for d in self.debris:
            d.update()
        self.debris = [d for d in self.debris if d.is_alive(self.height)]

    def update(self):
        self.frame += 1
        self._update_sky_altitude()
        self._update_debris()          # keep animating even after game over
        self._update_floating_texts()
        if not self.game_over:
            self.active_block.update(self.width)

    def _render_hud(self, screen):
        """Height, bonus and combo streak."""
        score_surf = self.font_hud.render(
            f"Height: {self.score}   Bonus: {self.bonus}", True, (255, 220, 80))
        screen.blit(score_surf, (self.width // 2 - score_surf.get_width() // 2, 54))

        if self.combo > 0:
            combo_surf = self.font_hud.render(
                f"Perfect streak x{self.combo}", True, (90, 230, 140))
            screen.blit(combo_surf, (self.width // 2 - combo_surf.get_width() // 2, 80))

    def render(self, screen):
        self._render_background(screen)

        title_surf = self.font_title.render("Skyscraper Stack", True, (245, 245, 245))
        screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 16))

        self._render_hud(screen)

        for b in self.stack:
            b.render(screen)

        if not self.game_over:
            self.active_block.render(screen)

        for d in self.debris:
            d.render(screen)

        for t in self.floating_texts:
            t.render(screen)

        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 195))
            screen.blit(overlay, (0, 0))

            over_surf = self.font_big.render("TOWER COLLAPSED!", True, (240, 75, 75))
            screen.blit(over_surf, (self.width // 2 - over_surf.get_width() // 2, self.height // 2 - 40))

            final_surf = self.font_hud.render(
                f"Final Height: {self.score}   Bonus: {self.bonus}", True, (255, 255, 255))
            screen.blit(final_surf, (self.width // 2 - final_surf.get_width() // 2, self.height // 2 + 10))

            restart_surf = self.font_hud.render("Press [Space] or [R] to Play Again", True, (200, 200, 200))
            screen.blit(restart_surf, (self.width // 2 - restart_surf.get_width() // 2, self.height // 2 + 50))