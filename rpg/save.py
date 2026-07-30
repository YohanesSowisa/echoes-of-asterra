"""
Echoes of Asterra - Save System
JSON-based serialization and deserialization of the game state.
"""
import os
import json
from typing import Any, Dict


from rpg.items import create_item

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVES_DIR = os.path.join(BASE_DIR, "saves")


def get_save_path(slot: int) -> str:
    os.makedirs(SAVES_DIR, exist_ok=True)
    return os.path.join(SAVES_DIR, f"savegame_{slot}.json")

class SaveSystem:
    """
    Handles saving and loading of game states.
    """
    @staticmethod
    def get_slot_meta(slot: int) -> Dict[str, Any]:
        """Reads basic slot metadata from savegame JSON without loading full state."""
        import json
        filename = get_save_path(slot)
        if not os.path.exists(filename):
            return {"exists": False}
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            player_data = data["player"]
            return {
                "exists": True,
                "slot_name": player_data.get("slot_name", f"Hero {slot}"),
                "level": player_data.get("level", 1),
                "gold": player_data.get("gold", 0),
                "map": player_data.get("current_map", "Village").replace("_", " ").title(),
                "date": player_data.get("save_date", "N/A")
            }
        except Exception as e:
            print(f"Warning: Failed reading slot metadata for slot {slot}: {e}")
            return {"exists": False}

    @staticmethod
    def rename_slot(slot: int, new_name: str) -> bool:
        """Modifies the slot name in an existing save file."""
        import json
        filename = get_save_path(slot)
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            data["player"]["slot_name"] = new_name
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed renaming save slot {slot}: {e}")
            return False

    @staticmethod
    def delete_slot(slot: int) -> bool:
        """Deletes the save file associated with a slot."""
        filename = get_save_path(slot)
        if os.path.exists(filename):
            try:
                os.remove(filename)
                return True
            except Exception as e:
                print(f"Warning: Failed deleting save slot {slot}: {e}")
                return False
        return False

    @staticmethod
    def save_game(player: Any, quest_manager: Any, world_manager: Any, slot: int = 1, slot_name: str = None) -> bool:

        """
        Gathers player, quest, and world state, serializes them to JSON,
        and writes them to the save file. Returns True if successful.
        """
        import datetime
        filename = get_save_path(slot)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        existing_name = f"Hero {slot}"
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    old_data = json.load(f)
                existing_name = old_data["player"].get("slot_name", existing_name)
            except Exception as e:
                print(f"Warning: Failed reading existing slot name from {filename}: {e}")
                
        final_slot_name = slot_name if slot_name is not None else existing_name
        
        try:
            # 1. Player Info
            def _serialize_item(item):
                if not item:
                    return None
                return {
                    "name": item.name,
                    "qty": item.quantity,
                    "rarity": item.rarity,
                    "stats": item.stats,
                    "sockets": getattr(item, "sockets", 0),
                    "socketed_runes": getattr(item, "socketed_runes", []),
                    "affixes": getattr(item, "affixes", []),
                }

            inventory_list = [_serialize_item(item) for item in player.inventory.slots]
            equipment_dict = {slot: _serialize_item(item) for slot, item in player.equipment.slots.items()}

            player_data = {
                "slot_name": final_slot_name,
                "save_date": now,
                "level": player.level,
                "xp": player.xp,
                "gold": player.gold,
                "hp": player.hp,
                "mana": player.mana,
                "stamina": player.stamina,
                "base_max_hp": player.base_max_hp,
                "base_max_mana": player.base_max_mana,
                "base_atk": player.base_atk,
                "base_def": player.base_def,
                "base_magic": player.base_magic,
                "base_speed": player.base_speed,
                "base_crit": player.base_crit,
                "pos_x": player.pos.x,
                "pos_y": player.pos.y,
                "current_map": world_manager.current_map_name,
                "inventory": inventory_list,
                "equipment": equipment_dict,
                "skills_unlocked": [name for name, s in player.skill_manager.skills.items() if s.unlocked]
            }

            # 2. Quest Progress
            quest_data = {}
            for q_id, quest in quest_manager.quests.items():
                obj_progress = [obj.current_count for obj in quest.objectives]
                quest_data[q_id] = {
                    "status": quest.status,
                    "progress": obj_progress
                }

            # 3. World State
            world_data = {
                "chests_opened": world_manager.chests_opened,
                "boss_defeated": world_manager.boss_defeated,
                "activated_waypoints": list(world_manager.activated_waypoints)
            }

            # Combine
            save_payload = {
                "player": player_data,
                "quests": quest_data,
                "world": world_data
            }

            if hasattr(player, "game"):
                if hasattr(player.game, "living_world"):
                    save_payload["living_world"] = player.game.living_world.to_dict()
                    if hasattr(player.game.living_world, "progression"):
                        save_payload["progression"] = player.game.living_world.progression.to_dict()
                if hasattr(player.game, "world_state"):
                    save_payload["world_simulation"] = player.game.world_state.to_dict()
                if hasattr(player.game, "factions"):
                    save_payload["factions"] = player.game.factions.to_dict()
                if hasattr(player.game, "npc_memory"):
                    save_payload["npc_memories"] = player.game.npc_memory.to_dict()
                if hasattr(player.game, "reputation_manager"):
                    save_payload["social_reputation"] = player.game.reputation_manager.to_dict()
                if hasattr(player.game, "memory_manager"):
                    save_payload["decay_memories"] = player.game.memory_manager.to_dict()
                if hasattr(player.game, "ecology"):
                    save_payload["ecology"] = player.game.ecology.to_dict()
                if hasattr(player.game, "tutorial_flags"):
                    save_payload["tutorial_flags"] = list(player.game.tutorial_flags)
                if hasattr(player.game, "difficulty_profile"):
                    save_payload["difficulty_profile"] = player.game.difficulty_profile


            with open(filename, 'w') as f:
                json.dump(save_payload, f, indent=4)
                
            print(f"Save: Successfully saved game state to {filename}.")
            return True
            
        except Exception as e:
            print(f"Save Error: Failed to write save file. Details: {e}")
            return False

    @staticmethod
    def load_game(player: Any, quest_manager: Any, world_manager: Any, slot: int = 1) -> bool:
        """
        Reads save file from disk, restores all player properties,
        rebuilds inventories, equips gear, updates quests, and spawns the map.
        Returns True if successful.
        """
        filename = get_save_path(slot)
        if not os.path.exists(filename):
            print(f"Save: No save game file found for slot {slot}.")
            return False

        try:
            with open(filename, 'r') as f:
                save_payload = json.load(f)

            player_data = save_payload["player"]
            quest_data = save_payload["quests"]
            world_data = save_payload["world"]

            # --- Restore Player Properties ---
            player.level = player_data["level"]
            player.xp = player_data["xp"]
            player.gold = player_data["gold"]
            player.base_max_hp = player_data["base_max_hp"]
            player.base_max_mana = player_data["base_max_mana"]
            player.base_atk = player_data["base_atk"]
            player.base_def = player_data["base_def"]
            player.base_magic = player_data["base_magic"]
            player.base_speed = player_data["base_speed"]
            player.base_crit = player_data["base_crit"]
            
            # Position & Map transitions
            player.pos.x = player_data["pos_x"]
            player.pos.y = player_data["pos_y"]
            player.hitbox.center = (int(player.pos.x), int(player.pos.y))
            player.rect.center = player.hitbox.center

            # --- Rebuild Inventory & Equipment Helper ---
            def _deserialize_item(info):
                if not info:
                    return None
                item_obj = create_item(info["name"], info.get("qty", 1), roll_equipment_affixes=False)
                if item_obj:
                    if "rarity" in info:
                        item_obj.rarity = info["rarity"]
                    if "stats" in info:
                        item_obj.stats = info["stats"]
                    if "sockets" in info:
                        item_obj.sockets = info["sockets"]
                    if "socketed_runes" in info:
                        item_obj.socketed_runes = info["socketed_runes"]
                    if "affixes" in info:
                        item_obj.affixes = info["affixes"]
                return item_obj

            # --- Rebuild Inventory Slots ---
            player.inventory.slots = [None] * player.inventory.size
            for idx, item_info in enumerate(player_data["inventory"]):
                if item_info:
                    # Support legacy string/simple dict or new full dict format
                    if isinstance(item_info, str):
                        item_obj = create_item(item_info, 1)
                    else:
                        item_obj = _deserialize_item(item_info)
                    if item_obj:
                        player.inventory.slots[idx] = item_obj

            # --- Rebuild Equipment Slots ---
            player.equipment.slots = {k: None for k in player.equipment.slots}
            for slot, item_info in player_data["equipment"].items():
                if item_info:
                    if isinstance(item_info, str):
                        item_obj = create_item(item_info, 1)
                    else:
                        item_obj = _deserialize_item(item_info)
                    if item_obj:
                        player.equipment.slots[slot] = item_obj

            # Recalculate stats dynamically based on equipment
            player.equipment.recalculate_player_stats(player)
            
            # Clamp HP, Mana and Stamina to loaded amounts (restore HP if saved while dead)
            loaded_hp = player_data.get("hp", player.max_hp)
            player.hp = player.max_hp if loaded_hp <= 0 else min(player.max_hp, loaded_hp)
            player.mana = min(player.max_mana, player_data.get("mana", player.max_mana))
            player.stamina = min(player.max_stamina, player_data.get("stamina", player.max_stamina))

            # Reset animation state machine back to living idle state
            player.state = "idle"
            player.action_timer = 0.0
            player.frame_index = 0.0
            player.is_invincible = False


            # --- Unlock Skills ---
            for name, skill in player.skill_manager.skills.items():
                skill.unlocked = (name in player_data["skills_unlocked"])

            # --- Restore Quest Progress ---
            for q_id, q_info in quest_data.items():
                quest = quest_manager.quests.get(q_id)
                if quest:
                    quest.status = q_info["status"]
                    for idx, progress_cnt in enumerate(q_info["progress"]):
                        if idx < len(quest.objectives):
                            quest.objectives[idx].set_progress(progress_cnt)

            # --- Restore World Progress ---
            world_manager.chests_opened = world_data.get("chests_opened", {})
            world_manager.boss_defeated = world_data.get("boss_defeated", False)
            if "activated_waypoints" in world_data:
                world_manager.activated_waypoints = set(world_data["activated_waypoints"])

            if hasattr(player, "game"):
                if "living_world" in save_payload and hasattr(player.game, "living_world"):
                    player.game.living_world.from_dict(save_payload["living_world"])
                    if "progression" in save_payload and hasattr(player.game.living_world, "progression"):
                        player.game.living_world.progression.from_dict(save_payload["progression"])
                if "world_simulation" in save_payload and hasattr(player.game, "world_state"):
                    player.game.world_state.from_dict(save_payload["world_simulation"])
                if "factions" in save_payload and hasattr(player.game, "factions"):
                    player.game.factions.from_dict(save_payload["factions"])
                if "npc_memories" in save_payload and hasattr(player.game, "npc_memory"):
                    player.game.npc_memory.from_dict(save_payload["npc_memories"])
                if "social_reputation" in save_payload and hasattr(player.game, "reputation_manager"):
                    player.game.reputation_manager.from_dict(save_payload["social_reputation"])
                if "decay_memories" in save_payload and hasattr(player.game, "memory_manager"):
                    player.game.memory_manager.from_dict(save_payload["decay_memories"])
                if "ecology" in save_payload and hasattr(player.game, "ecology"):
                    player.game.ecology.from_dict(save_payload["ecology"])
                if "tutorial_flags" in save_payload and hasattr(player.game, "tutorial_flags"):
                    player.game.tutorial_flags = set(save_payload["tutorial_flags"])
                if "difficulty_profile" in save_payload and hasattr(player.game, "difficulty_profile"):
                    player.game.difficulty_profile = save_payload["difficulty_profile"]
                if "achievements" in save_payload and hasattr(player.game, "achievement_manager"):
                    player.game.achievement_manager.from_dict(save_payload["achievements"])
                if "bestiary" in save_payload and hasattr(player.game, "bestiary_manager"):
                    player.game.bestiary_manager.from_dict(save_payload["bestiary"])


            # --- Map Transition ---
            target_map = player_data["current_map"]
            world_manager.load_map(target_map, player, portal_spawn=False)
            
            print(f"Save: Successfully loaded game state from {filename}.")
            return True

        except Exception as e:
            print(f"Load Error: Failed to restore save state. Details: {e}")
            return False
