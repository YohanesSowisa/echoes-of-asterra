"""
Echoes of Asterra - Tween Service
Encapsulates animation easing curves and motion interpolation for UI, camera, and FX.
Features fallback to linear interpolation.
"""
from typing import Optional
from rpg.config import TweenConfig, game_config

# Optional third-party PyTweening import
try:
    import pytweening
    PYTWEENING_AVAILABLE = True
except ImportError:
    pytweening = None
    PYTWEENING_AVAILABLE = False


class TweenService:
    """
    Service wrapper for animation easing.
    Owns curve evaluation for popups, camera moves, and combat damage text.
    """
    def __init__(self, config: Optional[TweenConfig] = None) -> None:
        self.config = config or game_config.tween

    def evaluate(self, curve_name: str, t: float) -> float:
        """
        Public API: Evaluates progress parameter t in [0.0, 1.0] using specified easing curve.
        Returns float in [0.0, 1.0].
        """
        t_clamped = max(0.0, min(1.0, t))
        
        if self.config.enable_easing and PYTWEENING_AVAILABLE:
            try:
                curve_fn = getattr(pytweening, curve_name, None)
                if callable(curve_fn):
                    return float(curve_fn(t_clamped))
            except Exception:
                pass

        # Fallback: Linear interpolation
        return t_clamped

    def interpolate(self, start: float, end: float, curve_name: str, t: float) -> float:
        """
        Public API: Interpolates value between start and end using named easing curve.
        """
        progress = self.evaluate(curve_name, t)
        return start + (end - start) * progress
