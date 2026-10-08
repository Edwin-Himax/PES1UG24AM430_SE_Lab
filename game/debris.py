import pygame


class Debris:
    """A sliced-off piece of a block that tumbles away and fades out.

    Physics are frame-based (one step per `update()` call), matching the rest of
    the game, which runs a fixed 60 FPS loop.

    `x`/`y` are the top-left corner of the *unrotated* piece. Rotation is applied
    around the piece's center at render time, so the piece spins in place while
    its center follows the falling path.
    """

    BORDER_COLOR = (245, 245, 250)  # same outline Block.render() uses

    def __init__(self, x, y, width, height, color,
                 vx=0.0, vy=0.0, angular_velocity=0.0,
                 gravity=0.45, fade_rate=3.5):
        # --- Geometry & look ---
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.height = float(height)
        self.color = color

        # --- Motion ---
        self.vx = vx                            # horizontal drift (px/frame)
        self.vy = vy                            # vertical speed (px/frame), grows with gravity
        self.gravity = gravity                  # added to vy every frame
        self.angle = 0.0                        # current rotation in degrees (+ = counter-clockwise)
        self.angular_velocity = angular_velocity  # degrees/frame

        # --- Fading ---
        self.alpha = 255.0                      # opacity: 255 = solid, 0 = invisible
        self.fade_rate = fade_rate              # alpha lost per frame

        # Draw the piece once; render() only rotates and blits it.
        self._sprite = self._build_sprite()

    def _build_sprite(self):
        """Pre-render the piece with the same style as Block.render()."""
        w = max(1, int(self.width))
        h = max(1, int(self.height))
        sprite = pygame.Surface((w, h), pygame.SRCALPHA)
        rect = sprite.get_rect()
        pygame.draw.rect(sprite, self.color, rect, border_radius=4)
        pygame.draw.rect(sprite, self.BORDER_COLOR, rect, width=2, border_radius=4)
        return sprite

    def update(self):
        """Advance the simulation by one frame."""
        self.vy += self.gravity          # accelerate downward
        self.x += self.vx
        self.y += self.vy
        self.angle += self.angular_velocity
        self.alpha = max(0.0, self.alpha - self.fade_rate)

    def is_alive(self, screen_height):
        """False once fully faded or fallen below the bottom of the screen."""
        return self.alpha > 0 and self.y < screen_height

    def render(self, surface):
        """Draw the piece rotated about its center, with the current opacity."""
        rotated = pygame.transform.rotate(self._sprite, self.angle)
        rotated.set_alpha(int(self.alpha))

        center = (self.x + self.width / 2, self.y + self.height / 2)
        surface.blit(rotated, rotated.get_rect(center=center))