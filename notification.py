"""
Echoes of Asterra - Centralized Notification Manager & Anti-Fatigue Engine
Handles HUD toast queuing, priority ordering (CRITICAL -> LOW), duplicate material pickup merging,
and maximum simultaneous toast capping to prevent visual spam.
"""
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any

class NotificationPriority(Enum):
    CRITICAL = 4 # Region Unlocked, Legendary Title, Mythos Event
    HIGH = 3     # Reputation Tier Up, Silas Inventory Unlocked
    MEDIUM = 2   # Village Prosperity Up, Quest Step Completed
    LOW = 1      # XP Gain, Gold Gain, Material Pickups

@dataclass
class ToastNotification:
    message: str
    priority: NotificationPriority
    color: Tuple[int, int, int]
    category: str = "general"
    amount: int = 1
    timer: float = 3.5
    duration: float = 3.5

class NotificationManager:
    """
    Central notification coordinator enforcing Anti-Fatigue policies:
    - Maximum 3 visible toasts on screen
    - Merges duplicate item pickups within 2.0s window
    - Queues lower-priority toasts during major milestone moments
    """
    def __init__(self, max_visible: int = 3) -> None:
        self.max_visible = max_visible
        self.active_toasts: List[ToastNotification] = []
        self.toast_queue: List[ToastNotification] = []
        
        # Priority default color palette
        self.priority_colors: Dict[NotificationPriority, Tuple[int, int, int]] = {
            NotificationPriority.CRITICAL: (255, 215, 0),   # Gold
            NotificationPriority.HIGH: (0, 210, 255),       # Cyan
            NotificationPriority.MEDIUM: (60, 220, 100),    # Green
            NotificationPriority.LOW: (220, 220, 230)       # Soft White
        }

    def push_toast(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.LOW,
        color: Optional[Tuple[int, int, int]] = None,
        category: str = "general",
        amount: int = 1,
        duration: float = 3.5
    ) -> None:
        """Pushes or merges a toast notification enforcing priority and deduplication rules."""
        chosen_color = color or self.priority_colors[priority]
        
        # 1. Deduplication & Merge Check for LOW/MEDIUM category items
        for toast in self.active_toasts + self.toast_queue:
            if toast.category == category and toast.category != "general":
                toast.amount += amount
                toast.timer = duration # Refresh timer
                toast.message = f"+{toast.amount} {category.capitalize()}"
                return

        new_toast = ToastNotification(
            message=message if amount == 1 else f"+{amount} {category.capitalize()}",
            priority=priority,
            color=chosen_color,
            category=category,
            amount=amount,
            timer=duration,
            duration=duration
        )

        # 2. Insert into active toasts or queue by priority
        if len(self.active_toasts) < self.max_visible:
            self.active_toasts.append(new_toast)
            self.active_toasts.sort(key=lambda t: t.priority.value, reverse=True)
        else:
            # Preemption: if new toast has higher priority than the lowest active toast, bump lowest to queue
            self.active_toasts.sort(key=lambda t: t.priority.value, reverse=True)
            if new_toast.priority.value > self.active_toasts[-1].priority.value:
                lowest = self.active_toasts.pop()
                self.toast_queue.append(lowest)
                self.active_toasts.append(new_toast)
                self.active_toasts.sort(key=lambda t: t.priority.value, reverse=True)
            else:
                self.toast_queue.append(new_toast)
            self.toast_queue.sort(key=lambda t: t.priority.value, reverse=True)

    def update(self, dt: float) -> None:
        """Updates active toast timers and dequeues pending toasts."""
        for toast in list(self.active_toasts):
            toast.timer -= dt
            if toast.timer <= 0.0:
                self.active_toasts.remove(toast)

        # Promote queued toasts up to max_visible limit
        while len(self.active_toasts) < self.max_visible and self.toast_queue:
            next_toast = self.toast_queue.pop(0)
            self.active_toasts.append(next_toast)

    def draw(self, surface: pygame.Surface, fonts: Dict[str, pygame.font.Font], screen_w: int) -> None:
        """Renders active stacked toasts on upper-right edge of screen."""
        if not self.active_toasts:
            return

        font = fonts.get("small", pygame.font.SysFont("Arial", 14))
        start_x = screen_w - 240
        start_y = 100
        card_h = 32
        gap = 6

        for idx, toast in enumerate(self.active_toasts):
            y = start_y + idx * (card_h + gap)
            
            # Fade alpha using TweenService easeOutCubic curve if available
            if toast.timer < 0.5:
                t_ratio = max(0.0, min(1.0, toast.timer / 0.5))
                tween_service = getattr(getattr(getattr(self, "game", None), "services", None), "tween", None)
                fade_progress = tween_service.evaluate("easeOutCubic", t_ratio) if tween_service else t_ratio
                alpha = int(230 * fade_progress)
            else:
                alpha = 230
            alpha = max(0, min(230, alpha))

            
            if alpha <= 0:
                continue

            msg_surf = font.render(toast.message, True, toast.color)
            card_w = max(220, msg_surf.get_width() + 24)
            x = screen_w - card_w - 16

            bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg.fill((16, 22, 34, alpha))
            surface.blit(bg, (x, y))

            pygame.draw.rect(surface, (*toast.color, alpha), (x, y, card_w, card_h), width=1, border_radius=4)
            surface.blit(msg_surf, (x + 12, y + (card_h - msg_surf.get_height()) // 2))

    def clear(self) -> None:
        """Clears all active and queued notifications."""
        self.active_toasts.clear()
        self.toast_queue.clear()
