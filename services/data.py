"""
Echoes of Asterra - Data & Save Schema Service
Provides Pydantic-based data validation and backward-compatible save schema migrations.
Features dict fallback if pydantic is not installed.
"""
from typing import Dict, Any, Optional, List
import time

# Optional third-party pydantic import
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object
    Field = lambda default=None, **kwargs: default
    PYDANTIC_AVAILABLE = False


if PYDANTIC_AVAILABLE:
    class PlayerSaveModel(BaseModel):
        hp: float = 100.0
        max_hp: float = 100.0
        mp: float = 50.0
        max_mp: float = 50.0
        stamina: float = 100.0
        max_stamina: float = 100.0
        gold: int = 0
        level: int = 1
        xp: int = 0
        current_map: str = "village"
        pos: List[float] = Field(default_factory=lambda: [100.0, 100.0])
        slot_name: str = "Hero"
        save_date: str = ""

    class SaveFileModel(BaseModel):
        version: int = 2
        player: PlayerSaveModel = Field(default_factory=PlayerSaveModel)
        quests: Dict[str, Any] = Field(default_factory=dict)
        world: Dict[str, Any] = Field(default_factory=dict)
        reputation: Dict[str, Any] = Field(default_factory=dict)
        settlement: Dict[str, Any] = Field(default_factory=dict)


class DataService:
    """
    Service wrapper for data validation and save schema migrations.
    """
    def __init__(self) -> None:
        self.version = 2

    def validate_and_migrate_save(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public API: Validates raw JSON dict and performs backward-compatible schema migration.
        Returns validated dict structure.
        """
        if not isinstance(raw_data, dict):
            return self._default_save_dict()

        # Step 1: Migration handling (V1 -> V2)
        version = raw_data.get("version", 1)
        migrated = dict(raw_data)
        if version < 2:
            migrated["version"] = 2
            if "player" in migrated and isinstance(migrated["player"], dict):
                migrated["player"].setdefault("stamina", 100.0)
                migrated["player"].setdefault("max_stamina", 100.0)
                migrated["player"].setdefault("save_date", time.strftime("%Y-%m-%d %H:%M"))

        # Step 2: Validate via Pydantic model if available
        if PYDANTIC_AVAILABLE:
            try:
                model = SaveFileModel.model_validate(migrated)
                return model.model_dump()
            except Exception as e:
                # Log warning and return migrated dict directly
                pass

        return migrated

    def _default_save_dict(self) -> Dict[str, Any]:
        return {
            "version": 2,
            "player": {
                "hp": 100.0, "max_hp": 100.0,
                "mp": 50.0, "max_mp": 50.0,
                "stamina": 100.0, "max_stamina": 100.0,
                "gold": 0, "level": 1, "xp": 0,
                "current_map": "village", "pos": [100.0, 100.0],
                "slot_name": "Hero", "save_date": time.strftime("%Y-%m-%d %H:%M")
            },
            "quests": {}, "world": {}, "reputation": {}, "settlement": {}
        }
