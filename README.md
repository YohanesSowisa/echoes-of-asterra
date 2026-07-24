# Echoes of Asterra

**Echoes of Asterra** is a complete, production-quality, top-down Action RPG built from scratch in Python 3.12+ using **Pygame Community Edition (`pygame-ce`)**.

The game features an explorable world across multiple procedural maps, real-time combat with melee and projectiles, deep RPG systems (leveling, inventory, equipment, crafting, and quests), branching dialogue, ambient systems (day-night cycle, dynamic weather), and a procedural audio synthesizer.

---

## 🎮 Controls Reference

| Action | Control (Keyboard/Mouse) |
| :--- | :--- |
| **Move** | `W`, `A`, `S`, `D` |
| **Sprinting** | Hold `Left Shift` |
| **Dodge Roll** | `Spacebar` |
| **Melee Attack** | `J` or Left Click |
| **Shield Block** | Hold `K` or Hold Right Click (requires equipped shield) |
| **Quick Skills** | `1` (Fireball), `2` (Ice Spike), `3` (Healing), `4` (Dash) |
| **Interact** | `E` (Talk to NPCs, Open chests) |
| **Use Consumables / Equip** | Right-click item inside inventory Backpack |
| **Unequip Gear** | Right-click equipped slot in Attributes Menu |
| **Sell Silas Items** | Right-click backpack items while Silas shop is open |
| **Backpack Menu** | Toggle `I` |
| **Character Attributes** | Toggle `C` |
| **Quest Journal** | Toggle `Q` |
| **Crafting Forge** | Toggle `G` |
| **Radar Minimap** | Toggle `M` |
| **Save / Load Game** | Pause the game (`ESC`), select Save/Load buttons |
| **Pause Game / Exit Shop** | Press `ESC` |

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
├── settings.py        # Frame rate, screen dimensions, bindings, configurations
├── constants.py       # Global color definitions, states, item types
├── camera.py          # Centered tracking viewport with camera shakes
├── input.py           # Unified keyboard key polling and mouse clicks
├── save.py            # JSON-based saving/loading state serialization
├── collision.py       # Spatial culling AABB grid collision resolution
├── items.py           # Item database model and properties
├── inventory.py       # Grid inventory backpack with sorting and dragging
├── equipment.py       # Sockets matching modifiers to player stats
├── crafting.py        # Crafting recipe validator consuming items
├── skills.py          # Active/passive spell trees and cast costs
├── combat.py          # Hit registration, damage calculations, and Projectiles
├── ai.py              # Finite State Machine patrolling/chasing/attacking
├── quests.py          # Log tracking with talk/kill/collect objective tasks
├── dialogue.py        # Branching dialogues with typing text animation
├── npc.py             # Elder, Merchant Silas, and Dennis interactions
├── player.py          # Hero movements, actions, level-up calculations
├── enemy.py           # Slime, Wolf, Skeleton, Mage, Goblin, Knight archetypes
├── boss.py            # Final Shadow Overlord with Phase 1 & 2 patterns
├── animation.py       # Procedural pixel-art frames generation (renders in memory)
├── sprite.py          # BaseSprite and depth Y-sorted drawing group
├── ui.py              # HUD gauges, overlay menus, stats layouts
├── minimap.py         # Real-time scaling radar coordinates tracker
├── particles.py       # Blood splatters, dust footsteps, magic sparks
├── sound.py           # In-memory procedural WAV synthesizer (chiptunes)
├── weather.py         # Rain cascades, snow drift, fog veil, and swaying leaves
├── lighting.py        # Day-Night cycles and radial darkness masks carve-outs
├── effects.py         # Screen flashes, hit-stops, outline highlights
├── README.md          # Technical handbook (this file)
└── requirements.txt   # Pygame Community Edition installation package
```

---

## 🛠️ Architecture & Systems

- **OOP Design**: Structurally clean classes, each handling a single responsibility to avoid God Objects (e.g., separating `CollisionSystem` from player movement, and `CombatSystem` from sprite rendering).
- **Procedural Graphics & Audio**: On startup, `animation.py` renders pixel-art styles directly to Surfaces, and `sound.py` synthesizes PCM chiptune WAV structures in memory. This eliminates missing assets errors, guarantees portability, and allows dynamic sprite recoloring.
- **Y-Sorted Layered Drawing**: The `YSortedGroup` sorts drawing coordinates of chests, players, and trees dynamically by their bottom coordinates before drawing.
- **Spatial Collision Culling**: `CollisionSystem` divides grid tiles spatially, looking up and testing wall block intersections ONLY for adjacent neighboring tiles.
- **Rendering Culling**: Background drawing loops only blit tiles falling inside the viewport's camera bounding coordinates, maintaining a stable 60 FPS.

---

## 🔮 Future Enhancements

1. **Pathfinding AI**: Implementing A* algorithms for enemies to walk around walls.
2. **Audio Synthesizer Expansion**: Adding support for modular multi-voice channels and custom sound fonts.
3. **Advanced Biomes**: Integrating noise generators (Perlin/Simplex) for infinite map expansions.
