"""
Echoes of Asterra - Offline Developer Telemetry & Analytics Engine
Lightweight local analytics engine for developers to observe combat metrics,
battle durations, win rates, death counts, danger scores, and level pacing.
Stores records in rpg/saves/developer_metrics.json with zero external dependencies.
"""
import os
import json
import time
from typing import Dict, List, Any, Optional

TELEMETRY_FILE_PATH = os.path.join(os.path.dirname(__file__), "saves", "developer_metrics.json")

class DeveloperTelemetry:
    """
    Offline local developer telemetry engine.
    Logs combat metrics, battle durations, player survival, and living danger scores.
    """
    def __init__(self) -> None:
        self.battles_started = 0
        self.battles_won = 0
        self.player_deaths = 0
        self.potions_used = 0
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.kill_counts: Dict[str, int] = {}
        self.battle_durations: List[float] = []
        self.danger_scores_logged: List[int] = []
        self.load_metrics()

    def load_metrics(self) -> None:
        """Loads saved local developer metrics if available."""
        if not os.path.exists(TELEMETRY_FILE_PATH):
            return
        try:
            with open(TELEMETRY_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.battles_started = data.get("battles_started", 0)
                self.battles_won = data.get("battles_won", 0)
                self.player_deaths = data.get("player_deaths", 0)
                self.potions_used = data.get("potions_used", 0)
                self.total_damage_dealt = data.get("total_damage_dealt", 0)
                self.total_damage_taken = data.get("total_damage_taken", 0)
                self.kill_counts = data.get("kill_counts", {})
                self.battle_durations = data.get("battle_durations", [])[-50:]  # Keep last 50
                self.danger_scores_logged = data.get("danger_scores_logged", [])[-50:]
        except Exception as e:
            print(f"Echoes of Asterra: Telemetry load warning ({e}).")

    def save_metrics(self) -> None:
        """Saves telemetry summary to local JSON file."""
        os.makedirs(os.path.dirname(TELEMETRY_FILE_PATH), exist_ok=True)
        payload = {
            "battles_started": self.battles_started,
            "battles_won": self.battles_won,
            "win_rate": round(self.battles_won / max(1, self.battles_started), 3),
            "player_deaths": self.player_deaths,
            "potions_used": self.potions_used,
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_taken": self.total_damage_taken,
            "kill_counts": self.kill_counts,
            "avg_battle_duration_sec": round(sum(self.battle_durations) / max(1, len(self.battle_durations)), 2),
            "avg_danger_score": round(sum(self.danger_scores_logged) / max(1, len(self.danger_scores_logged)), 1)
        }
        try:
            with open(TELEMETRY_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Echoes of Asterra: Telemetry save error ({e}).")

    def log_battle_end(self, duration: float, won: bool, danger_score: int) -> None:
        """Logs a completed combat encounter duration and outcome."""
        self.battles_started += 1
        if won:
            self.battles_won += 1
        self.battle_durations.append(duration)
        self.danger_scores_logged.append(danger_score)
        self.save_metrics()

    def log_kill(self, enemy_type: str) -> None:
        """Logs a slain enemy type."""
        self.kill_counts[enemy_type] = self.kill_counts.get(enemy_type, 0) + 1

    def log_player_death(self) -> None:
        """Logs a player death event."""
        self.player_deaths += 1
        self.save_metrics()

    def log_potion_use(self) -> None:
        """Logs a consumable potion usage."""
        self.potions_used += 1

    def log_damage(self, dealt: int = 0, taken: int = 0) -> None:
        """Logs damage dealt/taken metrics."""
        self.total_damage_dealt += dealt
        self.total_damage_taken += taken
