# Echoes of Asterra — Update Logs & Project Timeline

Log histori perkembangan, penambahan fitur, perbaikan bug, dan optimasi sistem pada **Echoes of Asterra**.

Format: `[yyyy-mm-dd hh:mm:ss WIB] | [tipe_pekerjaan]: [pekerjaan]`

---

## Timeline Log

- **2026-07-30 14:58:00 WIB** | **quest & ux remediation**: Complete quest system audit and resource accessibility remediation. Added explicit resource acquisition hints to item descriptions (`rpg/items.py`), quest journal objectives (`rpg/quests.py`), NPC dialogue (`rpg/npc.py`), and Noticeboard choices. Expanded Merchant Silas shop inventory to sell `Oak Wood` (12g) & `Iron Ore` (25g), and rebalanced starter chest loot in Village & Forest (`rpg/map_loader.py`).
- **2026-07-30 14:41:00 WIB** | **game evolution plan**: Implementation of Game Evolution Plan phases 1–6. Added Poise Stagger system with tiered durations (1.5s/2.0s/3.0s) & 1.75x damage multiplier, Timed Shield Parry (200ms window) with screen hit-stop, QTE contracting attack telegraph ring (Red -> Yellow -> Green), WaypointObelisk (32x48 standing sprite with floating crystal bobbing animation), minimap radar markers & fast travel, dynamic Notice Board Bounty system (`BountyManager`), Settlement Construction facility upgrades (Blacksmith/Apothecary/Market Lvl 1-3), ARPG Loot Affixes & Socketed Runes, PNG tileset slicing, 4-page interactive Tutorial screen, and ESC key UI panel priority fix.
- **2026-07-30 14:00:00 WIB** | **roadmap & combat polish**: Implementation of Category A roadmap enhancements and combat feel polish.
- **2026-07-29 16:46:00 WIB** | **compendium & save fix**: Added Bestiary system, fixed state lifecycle leaks across save slots, and cleaned save UI.
- **2026-07-29 16:44:00 WIB** | **refactor & system revert**: Mengembalikan sistem save/load ke bentuk semula yang bersih (Save Game, Load Game, Rename Profile, Delete Save) dan menghapus total fungsi Export/Import serta dialog file manager eksternal dari `rpg/save.py`, `rpg/ui.py`, dan `rpg/game.py`.
- **2026-07-29 16:35:00 WIB** | **bug fix & state lifecycle**: Memperbaiki isu *state leakage* antara sesi permainan (Achievements, Bestiary, Factions, NPC Memory, & Living World). Menambahkan metode `.reset()`, `.to_dict()`, dan `.from_dict()` pada `AchievementManager` & `BestiaryManager`, mengikat progress ke masing-masing berkas save slot (`savegame_X.json`), serta me-reset seluruh manager saat `start_new_game()` dipanggil.


- **2026-07-29 16:30:00 WIB** | **full UI audit & enhancements**: Audit komprehensif seluruh UI & menu (Main, Settings, Pause, Shop, Dialogue, & Character Sheet). Penyempurnaan Tab 5 Bestiary Compendium pada Character Panel (rendering UI, mouse click bounds, & shortcut keyboard `5`), serta verifikasi simetri 100% antara rendering visual, mouse collision, dan key bindings.

- **2026-07-29 16:26:00 WIB** | **new feature & ui fix**: Integrasi opsi `Import Backup` langsung ke dalam UI slot save/load (`rpg/ui.py`), perbaikan sinkronisasi indeks tombol pause menu & deteksi presisi tabrakan mouse mouse_pos untuk slot kosong maupun slot terisi.
- **2026-07-29 16:15:00 WIB** | **code cleanup & new features**: Pembersihan total 10 pyflakes warnings (Tugas A/B/C), penghentian silent `except Exception` di 19 lokasi dengan logging eksplisit, perbaikan bug pathfinding navigation logger, serta penambahan Bestiary Enemy Compendium (`rpg/bestiary.py`) & Save Export/Import API (`rpg/save.py`) beserta test suite (`tests/test_bestiary_and_export.py`).

- **2026-07-29 11:58:00 WIB** | **bug fix & ui overhaul**: Overhaul layout menu Settings (`rpg/ui.py`) untuk menghilangkan penumpukan teks (*overlapping text*) pada tombol `Back to Menu`, re-posisi title/subtitle/box buttons, dan menambahkan styled dark info card untuk deskripsi preset kesulitan & HP regen.

- **2026-07-29 11:55:00 WIB** | **new feature**: Implementasi sistem Out-of-Combat HP Regeneration pada `rpg/player.py` dengan deteksi kedamaian 4.0s, scaling tingkat kesulitan (`hp_regen_mult` di `rpg/balance.py`), serta animasi visual 3 partikel kilau hijau-sian menyala setiap 0.4s.
- **2026-07-29 11:50:00 WIB** | **bug fix**: Memperbaiki rujukan parameter `self` pada seluruh pemanggilan `toggle_panel` di `rpg/game.py` sehingga memancing notifikasi tutorial kontekstual `first_inventory_open` dan `first_quest_accepted`.
- **2026-07-29 11:25:00 WIB** | **new feature**: Implementasi Task 3 Engagement Systems: Onboarding Tutorial Tips (`rpg/notification.py`), Quest Marker & Waypoint Overlays pada Minimap (`rpg/minimap.py`), Achievement & Milestone System (`rpg/achievements.py`, TAB 4 UI Karakter), Default Target FPS 60 (`rpg/settings.py`), Real-time Living World Feedback, Mythos Inheritance Summary Card, Gamepad Joystick Input Mapping (`rpg/input.py`), serta Unit Test Suite (`tests/test_engagement_systems.py`).
- **2026-07-29 11:20:00 WIB** | **refactor & bug fix**: Refactor Tugas 1 & 2: Restrukturisasi package `rpg/`, perbaikan path `BASE_DIR` relatif di seluruh modul & test suite, audit logging exception pada 14 file, pembersihan dead code (`player.py`, `npc.py`, `game.py`, `notification.py`, `scheduler.py`, `world.py`), dan pembersihan unused imports pyflakes.
- **2026-07-29 10:23:11 WIB** | **new feature**: Complete 31-item icon overhaul pada `rpg/items.py` dan penyesuaian contextual save rules pada `rpg/save.py`.
- **2026-07-28 10:08:22 WIB** | **new feature & bug fix**: UX inventory overhaul, Village respawn points, & penyesuaian balance pertempuran.
- **2026-07-27 16:09:01 WIB** | **new feature**: Implementasi procedural enemy mutilation, conditional HP/XP badges, wind dash trail particles, dan deteksi chest collision.
- **2026-07-27 15:15:45 WIB** | **audio fix**: Eliminasi DSP aliasing, upgrade audio sample rate ke 44.1kHz, dan penambahan pengabaian aset tergenerasi pada `.gitignore`.
- **2026-07-27 15:02:28 WIB** | **audio & architecture**: Refactor synthesizer prosedural (`rpg/sound.py`) dengan output PCM 22.050 Hz 2-channel stereo, pembersihan wah-wah noise, tema title screen D Minor (`menu_music`), instansiasi AssetService, TilemapService, ProfilingService, serta test suite service container (`tests/test_services.py`).
- **2026-07-27 14:15:19 WIB** | **architecture**: Integrasi `ServiceContainer` dan `DataService` ke core engine (`game.py`).
- **2026-07-27 13:30:11 WIB** | **architecture**: Implementasi decoupled service layer dan central `GameConfig`.
- **2026-07-27 09:31:08 WIB** | **ui overhaul**: Overhaul tipografi RPG dengan font piksel `PixelifySans`, dialog box gaya Harvest Moon DS, floating speaker badge biru, dan update rendering font pada boss HP bar & damage numbers.
- **2026-07-25 16:26:09 WIB** | **graphics & ai**: Overhaul model karakter, enemy roster, algoritma wandering AI, serta text wrapping pada UI dialogue.
- **2026-07-24 16:52:24 WIB** | **new feature**: Implementasi Phase 0-4 Production QoL Engine dengan CelebrationManager (`rpg/celebration.py`), NotificationManager (`rpg/notification.py`), Infinite Sprinting Out-of-Combat, Low-HP Vignette, Boss Danger Telegraphs, Tooltip Comparison, & Telemetry.
- **2026-07-24 16:51:00 WIB** | **new feature**: Implementasi Phase 4 Developer Diagnostics dengan EventTelemetry logger (`rpg/telemetry.py`), Live EventBus Signal Inspector (F8), dan Subsystem Microsecond Execution Profiler (`rpg/debug_overlay.py`).
- **2026-07-24 16:50:00 WIB** | **new feature**: Implementasi Phase 3 Strict Fast Travel Waypoint Rules (`rpg/world.py`, `rpg/ui.py`), Schedule Override System untuk Quest NPCs (`rpg/npc_schedule.py`), dan Visual Settlement Roof & Road Tier Upgrades (`rpg/settlement.py`).
- **2026-07-24 16:48:00 WIB** | **new feature**: Implementasi Phase 2 Music Priority Table & Cooldown Engine (`rpg/sound.py`), Dynamic Camera Screen-Shake & Directional Knockback (`rpg/combat.py`), Inventory Auto-Sort (`rpg/inventory.py`), serta Merchant Bulk "Sell All Junk/Ores" Action (`rpg/ui.py`).
- **2026-07-24 16:39:00 WIB** | **new feature**: Implementasi Phase 0 & Phase 1 Production QoL Engine dengan CelebrationManager (`rpg/celebration.py`, 4-Tier Profiles), NotificationManager (`rpg/notification.py`), Out-of-Combat Infinite Sprinting (`rpg/player.py`), Low-HP Vignette (`rpg/effects.py`), Boss Danger Telegraphs (`rpg/boss.py`), serta Tooltip Comparison & Floor Key Prompts (`rpg/ui.py`).
- **2026-07-24 16:13:16 WIB** | **new feature**: Implementasi Progressive World Unlock & Exploration Log (`rpg/progression.py`, `rpg/ui.py`) dengan Region State Machine 6-Stage, Narrative Requirement Clues, Alternative Vector Paths, Identity Metadata, Mastery Tracker, dan UI Log Eksplorasi ('R').
- **2026-07-24 16:06:00 WIB** | **new feature**: Implementasi World Scheduler (`rpg/scheduler.py`), World Snapshot API (`rpg/world_state.py`), Adaptive Game Director & Pressure Model (`rpg/director.py`), serta Developer Debug Overlay F9/F10/F11 (`rpg/debug_overlay.py`).
- **2026-07-24 15:44:00 WIB** | **bug fix**: Memperbaiki variabel `game` yang unresolved pada `draw_character_panel` di `ui.py` menjadi `player.game`.
- **2026-07-24 15:39:23 WIB** | **new feature**: Implementasi Phase 4 Procedural Bard Memory Songs (`rpg/bard.py`), Mythos Export (`rpg/mythos.py`), NPC BardFinn (`rpg/npc.py`, `rpg/world.py`), dan tampilan Gelar Player pada UI Karakter (`rpg/ui.py`).
- **2026-07-24 15:35:18 WIB** | **new feature**: Implementasi Phase 3 Contextual Dialogue, Unlocks & Enemy Recognition (`rpg/npc.py`, `rpg/ai.py`) dengan penyaringan memori domain, unlock stok langka Silas, dan reaksi takut musuh.
- **2026-07-24 15:33:35 WIB** | **new feature**: Implementasi Phase 2 Separate Reputation & Emergent Title Engine (`rpg/social.py`) dengan pemisahan Reputasi Global/NPC/Faksi, Social Recognition Tiers, TitleEngine, dan penyimpanan JSON.
- **2026-07-24 15:31:20 WIB** | **new feature**: Implementasi Phase 1 Living Memory Engine (`rpg/memory.py`) dengan SocialMemory model, Memory Decay relevance formula, integrasi EventBus, dan penyimpanan JSON.
- **2026-07-24 15:23:00 WIB** | **update**: Pembuatan dan pembentukan berkas `update_logs.md` dengan format standar timestamp WIB.
- **2026-07-24 15:20:51 WIB** | **bug fix**: Membekukan total gerakan & serangan player saat jendela UI/dialog terbuka (Harvest Moon-like freeze) pada `player.py`.
- **2026-07-24 15:20:51 WIB** | **bug fix**: Mengatur mode 1 panel aktif eksklusif di `ui.py` untuk mencegah tab UI menumpuk (misal saat menekan G, I, C, Q).
- **2026-07-24 15:20:51 WIB** | **bug fix**: Memperbaiki lebar panel Character Sheet (`'C'`) menjadi 680px dan me-render ulang dialog prasasti agar bebas dari masalah teks menumpuk (*text collapse*).
- **2026-07-24 15:20:51 WIB** | **new feature**: Menambahkan navigasi keyboard `A`/`D`, tombol panah, `Tab`, dan `1`/`2` untuk perpindahan tab Faksi & NPC Social pada Character Sheet.
- **2026-07-24 15:20:51 WIB** | **new feature**: Menambahkan opsi pengaturan Target FPS langsung di menu Settings in-game (30, 60, 120, 144, Uncapped) dengan default disetel ke `MAX (UNCAPPED)`.
- **2026-07-24 14:43:44 WIB** | **update**: Memasang objek `PastHeroStatue` di Alun-Alun Desa (`MAP_VILLAGE`) selain di Dungeon Crypt (`MAP_CRYPT`).
- **2026-07-24 14:31:45 WIB** | **new feature**: Membuat `rpg/balance.py` sebagai engine keseimbangan pertarungan terpusat (Profil Growth, Kebijakan Scaling, Kurva Polinomial, Reward Multiplier).
- **2026-07-24 14:31:45 WIB** | **new feature**: Membuat `LivingDangerEngine` untuk menghitung skor bahaya dunia berbasis pertempuran, cuaca (hujan/badai), siklus malam, krisis aktif, & kutukan greed.
- **2026-07-24 14:31:45 WIB** | **new feature**: Menambahkan `BehaviorTag` (Pack Tactics, Parry, Ranged Kite, Retreat, Berserk) pada arketipe musuh.
- **2026-07-24 14:31:45 WIB** | **new feature**: Membuat `rpg/telemetry.py` sebagai engine analitik & telemetri developer offline lokal (`developer_metrics.json`).
- **2026-07-24 14:21:33 WIB** | **new feature**: Menambahkan Mythos Inheritance Engine (`rpg/mythos.py`) dengan versi skema, API query semantik, dan pencatatan event sejarah pahlawan terdahulu.
- **2026-07-24 14:21:33 WIB** | **new feature**: Membuat objek interaktif `PastHeroStatue` di Dungeon Crypt untuk menampilkan legenda pahlawan masa lalu dari simpanan Mythos.
- **2026-07-24 14:21:33 WIB** | **update**: Meredesain Character Sheet Window (`'C'`) dengan sistem 2 Tab interaktif (`[Factions]` dan `[NPC Social]`).
- **2026-07-24 11:15:15 WIB** | **update**: Konfigurasi file `.gitignore` untuk mengabaikan direktori `assets/maps` dan `saves/`.
- **2026-07-24 11:12:55 WIB** | **bug fix**: Meredesain tombol pilihan dialog menjadi *Vertical Stacked List* untuk mencegah teks pilihan bertabrakan secara horizontal.
- **2026-07-24 11:12:55 WIB** | **update**: Menambahkan model visual kustom untuk objek `TownNoticeboard` di alun-alun desa dan `GreedAltar` di crypt exit.
- **2026-07-24 11:09:40 WIB** | **bug fix**: Memperbaiki variabel `accept` dan callback pada `RangerFaye` di `rpg/npc.py`.
- **2026-07-24 11:07:24 WIB** | **new feature**: Mengimplementasikan Decision Design Blueprint & Living World Simulation (Investasi Desa, Papan Pengumuman Ambisi NPC, Altar Greed vs Safe Extraction, Penyederhanaan 3 Material Crafting).
- **2026-07-24 10:11:15 WIB** | **new feature**: Mengimplementasikan ekspansi Living World (Orkestrator Ekonomi, Karavan Pedagang, & Pertumbuhan Pemukiman).
- **2026-07-24 09:38:25 WIB** | **update**: Inisialisasi awal repositori game Echoes of Asterra.
