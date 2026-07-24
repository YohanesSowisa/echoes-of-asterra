"""
Echoes of Asterra - Centralized Celebration Manager
Orchestrates 4-tier achievement celebrations (SMALL, MEDIUM, LARGE, LEGENDARY)
with screen banners, particle bursts, camera effects, sound stings, and micro freeze-frames.
"""
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List

class CelebrationTier(Enum):
    SMALL = "small"         # Item/Landmark discovery (chime sound, subtle micro toast)
    MEDIUM = "medium"       # Quest completed / Relationship tier (medium banner, particle burst, reward card)
    LARGE = "large"         # Region unlocked / Boss defeated (large banner, music sting, 0.2s freeze frame)
    LEGENDARY = "legendary" # Mythos milestone / Legendary title (gold banner, heroic fanfare, camera zoom, 0.4s freeze)

@dataclass
class CelebrationProfile:
    tier: CelebrationTier
    title: str
    subtitle: str = ""
    freeze_duration: float = 0.0
    particle_count: int = 0
    sound_sting: Optional[str] = None
    color: Tuple[int, int, int] = (255, 215, 0)
    banner_height: int = 50
    shake_intensity: float = 0.0

class CelebrationManager:
    """
    Central authority orchestrating visual, audio, and gameplay fanfare
    for major milestones across all game subsystems.
    """
    def __init__(self) -> None:
        self.active_celebration: Optional[CelebrationProfile] = None
        self.celebration_timer: float = 0.0
        self.celebration_duration: float = 3.5
        self.cooldown_timer: float = 0.0
        self.cooldown_duration: float = 1.5
        self.freeze_timer: float = 0.0
        
        # Predefined profile presets
        self.tier_defaults: Dict[CelebrationTier, Dict[str, Any]] = {
            CelebrationTier.SMALL: {
                "freeze_duration": 0.0,
                "particle_count": 8,
                "sound_sting": "click",
                "color": (160, 220, 255),
                "banner_height": 38,
                "shake_intensity": 0.0
            },
            CelebrationTier.MEDIUM: {
                "freeze_duration": 0.0,
                "particle_count": 25,
                "sound_sting": "magic",
                "color": (60, 220, 100),
                "banner_height": 56,
                "shake_intensity": 2.0
            },
            CelebrationTier.LARGE: {
                "freeze_duration": 0.2,
                "particle_count": 50,
                "sound_sting": "fanfare",
                "color": (255, 215, 0),
                "banner_height": 72,
                "shake_intensity": 4.5
            },
            CelebrationTier.LEGENDARY: {
                "freeze_duration": 0.4,
                "particle_count": 80,
                "sound_sting": "legendary_fanfare",
                "color": (255, 140, 0),
                "banner_height": 90,
                "shake_intensity": 7.0
            }
        }

    def trigger_celebration(
        self,
        tier: CelebrationTier,
        title: str,
        subtitle: str = "",
        color: Optional[Tuple[int, int, int]] = None,
        duration: float = 3.5,
        event_bus: Optional[Any] = None
    ) -> bool:
        """
        Triggers a new celebration event if cooldown permits.
        """
        if self.cooldown_timer > 0.0 and tier != CelebrationTier.LEGENDARY:
            return False

        defaults = self.tier_defaults[tier]
        chosen_color = color or defaults["color"]
        
        self.active_celebration = CelebrationProfile(
            tier=tier,
            title=title,
            subtitle=subtitle,
            freeze_duration=defaults["freeze_duration"],
            particle_count=defaults["particle_count"],
            sound_sting=defaults["sound_sting"],
            color=chosen_color,
            banner_height=defaults["banner_height"],
            shake_intensity=defaults["shake_intensity"]
        )
        
        self.celebration_timer = duration
        self.celebration_duration = duration
        self.cooldown_timer = duration + self.cooldown_duration
        self.freeze_timer = defaults["freeze_duration"]

        if event_bus:
            event_bus.emit(
                "celebration_triggered",
                tier=tier.value,
                title=title,
                subtitle=subtitle,
                freeze=defaults["freeze_duration"]
            )
        return True

    def update(self, dt: float) -> None:
        """Updates active celebration timers and cooldowns."""
        if self.freeze_timer > 0.0:
            self.freeze_timer = max(0.0, self.freeze_timer - dt)

        if self.celebration_timer > 0.0:
            self.celebration_timer = max(0.0, self.celebration_timer - dt)
            if self.celebration_timer <= 0.0:
                self.active_celebration = None

        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

    def is_freezing_gameplay(self) -> bool:
        """Returns True if a high-tier celebration freeze frame is active."""
        return self.freeze_timer > 0.0

    def draw(self, surface: pygame.Surface, fonts: Dict[str, pygame.font.Font], screen_w: int, screen_h: int) -> None:
        """Renders active celebration banner overlay at upper screen center."""
        if not self.active_celebration or self.celebration_timer <= 0.0:
            return

        celeb = self.active_celebration
        
        # Calculate alpha fade
        alpha = 240
        if self.celebration_timer > self.celebration_duration - 0.3:
            alpha = int(240 * ((self.celebration_duration - self.celebration_timer) / 0.3))
        elif self.celebration_timer < 0.5:
            alpha = int(240 * (self.celebration_timer / 0.5))
        alpha = max(0, min(240, alpha))
        
        if alpha <= 0:
            return

        # Font & text setup
        t_font = fonts.get("large", fonts.get("title", pygame.font.SysFont("Arial", 24, bold=True)))
        sub_font = fonts.get("small", pygame.font.SysFont("Arial", 14))

        t_surf = t_font.render(celeb.title, True, celeb.color)
        sub_surf = sub_font.render(celeb.subtitle, True, (230, 240, 255)) if celeb.subtitle else None

        req_w = max(t_surf.get_width(), sub_surf.get_width() if sub_surf else 0) + 50
        w = max(420, min(screen_w - 60, req_w))
        h = celeb.banner_height
        x = (screen_w - w) // 2
        y = 85

        # Banner Backdrop Surface
        banner_bg = pygame.Surface((w, h), pygame.SRCALPHA)
        banner_bg.fill((14, 20, 32, alpha))
        surface.blit(banner_bg, (x, y))

        # Golden / Tier Border
        pygame.draw.rect(surface, (*celeb.color, alpha), (x, y, w, h), width=2, border_radius=6)
        
        # Render Title & Subtitle centered
        surface.blit(t_surf, (x + (w - t_surf.get_width()) // 2, y + 8))
        if sub_surf:
            surface.blit(sub_surf, (x + (w - sub_surf.get_width()) // 2, y + 8 + t_surf.get_height() + 2))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes celebration state."""
        return {
            "cooldown_timer": self.cooldown_timer
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes celebration state."""
        if data:
            self.cooldown_timer = data.get("cooldown_timer", 0.0)
