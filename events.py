"""
Echoes of Asterra - Event Bus System
Provides a lightweight publish/subscribe event dispatcher for decoupled communication
between gameplay systems (WorldState, Factions, NPC Memory, Ecology, Combat, Quests, UI).
"""
from typing import Dict, List, Callable, Any

class EventBus:
    """
    Global event dispatcher.
    Systems subscribe callbacks to specific event topics, and emit events without direct coupling.
    """
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[..., None]) -> None:
        """Subscribes a listener callback to an event topic."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[..., None]) -> None:
        """Unsubscribes a listener callback from an event topic."""
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)

    def emit(self, event_type: str, **kwargs: Any) -> None:
        """Dispatches an event to all subscribed callbacks with keyword arguments."""
        if event_type in self._listeners:
            for callback in list(self._listeners[event_type]):
                try:
                    callback(**kwargs)
                except Exception as e:
                    print(f"EventBus Error on handling '{event_type}': {e}")

    def clear(self) -> None:
        """Clears all event listeners."""
        self._listeners.clear()
