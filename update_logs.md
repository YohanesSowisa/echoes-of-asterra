# Echoes of Asterra — Update Logs & Project Timeline

Log histori perkembangan, penambahan fitur, perbaikan bug, dan optimasi sistem pada **Echoes of Asterra**.

Format: `[yyyy-mm-dd hh:mm:ss WIB] | [tipe_pekerjaan]: [pekerjaan]`

---

## Timeline Log

- **2026-07-24 15:38:00 WIB** | **new feature**: Implementasi Phase 4 Procedural Bard Memory Songs (`rpg/bard.py`), Mythos Export (`rpg/mythos.py`), NPC BardFinn (`rpg/npc.py`, `rpg/world.py`), dan tampilan Gelar Player pada UI Karakter (`rpg/ui.py`).
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
