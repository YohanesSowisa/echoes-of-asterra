# Echoes of Asterra — Living World Expansion

> 📘 **Dokumen Serah Terima AI / Developer**: Lihat [handover.md](handover.md) untuk panduan arsitektur & kelanjutan proyek di sesi chat baru.  
> 📜 **Histori Log Pembaruan**: Lihat [update_logs.md](update_logs.md) untuk riwayat lengkap penambahan fitur & perbaikan bug.

**Echoes of Asterra** is a complete, production-quality, top-down Action RPG built from scratch in Python 3.12+ using **Pygame Community Edition (`pygame-ce`)**.

The game features an explorable world across multiple procedural maps, real-time combo combat with weapon identities, deeply integrated living world systems (Dynamic World, Factions & Reputation, Monster Ecology, Persistent NPC Memory, and Procedural Endless Dungeons), deep RPG mechanics (leveling, inventory, equipment, crafting, and quests), branching dialogue, ambient systems (day-night cycle, dynamic weather), and a procedural audio synthesizer.

---

## 🎮 Controls Reference

| Action | Control (Keyboard/Mouse) |
| :--- | :--- |
| **Move** | `W`, `A`, `S`, `D` |
| **Sprinting** | Hold `Left Shift` |
| **Dodge Roll** | `Spacebar` |
| **Melee Attack / Combo** | `J` or Left Click |
| **Shield Block** | Hold `K` or Hold Right Click (requires equipped shield) |
| **Quick Skills** | `1` (Fireball), `2` (Ice Spike), `3` (Healing), `4` (Dash) |
| **Interact** | `E` (Talk to NPCs, Open chests) |
| **Use Consumables / Equip** | Right-click item inside inventory Backpack |
| **Unequip Gear** | Right-click equipped slot in Attributes Menu |
| **Sell Silas Items** | Right-click backpack items while Silas shop is open |
| **Backpack Menu** | Toggle `I` |
| **Character Attributes & Factions** | Toggle `C` |
| **Quest Journal** | Toggle `Q` |
| **Crafting Forge** | Toggle `G` |
| **Radar Minimap** | Toggle `M` |
| **Save / Load Game** | Pause the game (`ESC`), select Save/Load buttons |
| **Pause Game / Exit Shop** | Press `ESC` |

---

## 🌟 Living World Features (6 Integrated Systems)

1. **Dynamic World (`world_state.py`)**: Persistent day/season simulation engine tracking prosperity (0-100), danger level (0-100), and 8 dynamic world events (Village Festival, Merchant Caravan, Bandit Outbreak, Harvest Season, etc.).
2. **Faction & Reputation (`factions.py`)**: Standing tracking across 6 factions (Knights, Mages, Hunters, Merchants, Bandits, Void Cult). Player choices alter reputation (-100 Hostile to +100 Exalted), dynamically scaling shop prices and unlocking dialogues.
3. **Persistent NPC Memory (`npc_memory.py`)**: NPCs remember hero interactions, completed quests, gifts, and witnessed crimes. Friendship tiers evolve (Enemy, Stranger, Acquaintance, Friend, Close Friend), altering greeting prefixes and merchant discounts.
4. **Monster Ecology (`ecology.py`)**: Simulated species dynamics with predator-prey hunting, territory tracking, natural reproduction, nocturnal/diurnal activity windows, and over-hunting migration.
5. **Weapon Identity & Combo Combat (`weapon_types.py`)**: 5 weapon classes (Sword, Axe, Hammer, Spear, Dagger) with distinct attack speeds, ranges, armor-piercing capabilities, stuns, combo chains, finisher multipliers, and elemental reactions (Ignite, Freeze, Overload, Miasma).
6. **Procedural Endless Dungeon (`dungeon_gen.py`)**: BSP (Binary Space Partitioning) algorithm generating infinite replayable dungeon levels with scaling depth difficulty, traps, theme biomes (Crypt, Cave, Temple, Ice, Volcano), and boss chambers every 5 floors.

---

## 🚀 Installation & Play

1. **Ensure Python 3.12+ is installed.**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch the game:**
   ```bash
   python main.py
   ```

---

## 🏗️ Folder Structure

```
rpg/
├── main.py            # Game launcher and display entry setup
├── game.py            # Core engine coordinator and main state machine
├── events.py          # Central EventBus for decoupled system messaging
├── world_state.py     # Dynamic world simulation engine (days, seasons, events)
├── factions.py        # 6-faction reputation and price modifier system
├── npc_memory.py      # Persistent NPC memory and relationship tracker
├── ecology.py          # Monster ecology, predator-prey & population simulation
├── weapon_types.py    # 5 weapon classes, combo movesets, elemental reactions
├── dungeon_gen.py     # BSP procedural endless dungeon floor generator
├── settings.py        # Frame rate, screen dimensions, bindings, configurations
├── constants.py       # Global color definitions, states, enums, item types
├── camera.py          # Centered tracking viewport with camera shakes
├── input.py           # Unified keyboard key polling and mouse clicks
├── save.py            # JSON-based saving/loading state serialization
├── collision.py       # Spatial culling AABB grid collision resolution
├── items.py           # Item database model, weapon classes, and properties
├── inventory.py       # Grid inventory backpack with sorting and dragging
├── equipment.py       # Sockets matching modifiers to player stats
├── crafting.py        # Crafting recipe validator consuming items
├── skills.py          # Active/passive spell trees and cast costs
├── combat.py          # Hit registration, damage calculations, Projectiles
├── ai.py              # Finite State Machine patrolling/chasing/attacking
├── quests.py          # Log tracking with talk/kill/collect objective tasks
├── dialogue.py        # Branching dialogues with typing text animation
├── npc.py             # Elder, Merchant Silas, Faye, Mira, Dennis interactions
├── player.py          # Hero movements, actions, combo state machine, leveling
├── enemy.py           # Slime, Wolf, Skeleton, Mage, Goblin, Knight archetypes
├── boss.py            # Final Shadow Overlord with Phase 1 & 2 patterns
├── animation.py       # Procedural pixel-art frames generation (renders in memory)
├── sprite.py          # BaseSprite and depth Y-sorted drawing group
├── ui.py              # HUD gauges, overlay menus, stats layouts, combo counter
├── minimap.py         # Real-time scaling radar coordinates tracker
├── particles.py       # Blood splatters, dust footsteps, magic sparks
├── sound.py           # In-memory procedural WAV synthesizer (chiptunes)
├── weather.py         # Rain cascades, snow drift, fog veil, swaying leaves
├── lighting.py        # Day-Night cycles and radial darkness masks carve-outs
├── effects.py         # Screen flashes, hit-stops, outline highlights
├── README.md          # Technical handbook (this file)
└── requirements.txt   # Pygame Community Edition installation package
```

---

## 🛠️ Architecture & Cross-System Integration

- **Event Bus Decoupling**: Systems communicate asynchronously via `EventBus` topics (`"enemy_killed"`, `"quest_completed"`, `"npc_talked"`, `"day_changed"`, `"item_bought"`), eliminating tight circular dependencies.
- **Procedural Graphics & Audio**: On startup, `animation.py` renders pixel-art styles directly to Surfaces, and `sound.py` synthesizes PCM chiptune WAV structures in memory.
- **Y-Sorted Layered Drawing**: The `YSortedGroup` sorts drawing coordinates of chests, players, and trees dynamically by their bottom coordinates before drawing.
- **Spatial Collision Culling**: `CollisionSystem` divides grid tiles spatially, testing wall block intersections ONLY for adjacent neighboring tiles.
- **Rendering Culling**: Background drawing loops only blit tiles falling inside the viewport's camera bounding coordinates, maintaining a stable 60 FPS.
