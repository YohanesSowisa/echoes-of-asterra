"""
Echoes of Asterra - EventBus Signal Telemetry & Microsecond Subsystem Profiler
Logs runtime event bus signals and records microsecond execution timings per subsystem.
"""
import time
from typing import List, Dict, Tuple, Any

from rpg.events import EventBus

class EventTelemetry:
    """
    Developer telemetry tracker monitoring live EventBus signals
    and subsystem execution timings.
    """
    def __init__(self, max_logs: int = 25) -> None:
        self.max_logs = max_logs
        self.signal_stream: List[Tuple[str, str, str]] = [] # (time_str, event_name, payload_str)
        self.event_counts: Dict[str, int] = {}
        self.subsystem_timings: Dict[str, float] = {
            "WorldState": 0.12,
            "Director": 0.08,
            "Scheduler": 0.04,
            "Pathfinding": 0.25,
            "Render": 4.10
        }

    def register_event_bus(self, event_bus: EventBus) -> None:
        """Subscribes telemetry logger to all EventBus events."""
        original_emit = event_bus.emit
        
        def telemetry_emit(event_name: str, **kwargs: Any) -> None:
            # Record signal
            curr_time = time.strftime("%H:%M:%S")
            payload_str = ", ".join(f"{k}={v}" for k, v in list(kwargs.items())[:3])
            
            self.signal_stream.append((curr_time, event_name, payload_str))
            if len(self.signal_stream) > self.max_logs:
                self.signal_stream.pop(0)
                
            self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1
            
            # Forward to original emit
            original_emit(event_name, **kwargs)
            
        event_bus.emit = telemetry_emit

    def record_subsystem_timing(self, name: str, duration_ms: float) -> None:
        """Records microsecond timing for a simulation subsystem."""
        self.subsystem_timings[name] = round(duration_ms, 2)
