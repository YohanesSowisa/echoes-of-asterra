"""
Echoes of Asterra - Sound Synthesizer
Procedurally generates all sound effects and background music loops at runtime.
Requires no external audio assets.
"""
import io
import math
import struct
import wave
import pygame
from typing import Dict, Union, Callable

class SoundManager:
    """
    Manages procedural sound effects and background music.
    Generates PCM WAV files in memory and loads them as Pygame Sound objects.
    """
    def __init__(self) -> None:
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_channels: Dict[str, pygame.mixer.Channel] = {}
        self.current_music: Union[str, None] = None
        self.samplerate = 22050
        self.enabled = False
        self.music_volume = 1.0
        self.sfx_volume = 1.0

        # Initialize mixer
        try:
            pygame.mixer.init(frequency=self.samplerate, size=-16, channels=1, buffer=1024)
            self.enabled = True
        except pygame.error:
            print("Sound: Failed to initialize pygame mixer. Audio will be disabled.")
            return

        if self.enabled:
            self._generate_all_assets()

    def _generate_wav(self, filename: str, wave_func: Callable[[float], float], duration: float, volume: float = 0.5) -> pygame.mixer.Sound:
        """
        Generates a WAV file on disk (or loads it if it already exists) and loads it as a Sound object.
        """
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ASSETS_DIR = os.path.join(BASE_DIR, "assets")
        
        subfolder = "music" if "music" in filename else "sounds"
        dest_folder = os.path.join(ASSETS_DIR, subfolder)
        os.makedirs(dest_folder, exist_ok=True)
        
        file_path = os.path.join(dest_folder, filename + ".wav")
        
        if os.path.exists(file_path):
            try:
                return pygame.mixer.Sound(file_path)
            except Exception as e:
                print(f"Warning: Failed to load sound {file_path} from disk. Re-synthesizing. Details: {e}")
                
        num_samples = int(duration * self.samplerate)
        buffer = io.BytesIO()
        
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.samplerate)
            
            for i in range(num_samples):
                t = i / self.samplerate
                sample_val = wave_func(t)
                # Apply sample volume clipping and format as signed 16-bit short
                sample_val = max(-1.0, min(1.0, sample_val))
                val = int(sample_val * 32767 * volume)
                wav_file.writeframesraw(struct.pack('<h', val))
                
        # Write to disk
        try:
            with open(file_path, 'wb') as f:
                f.write(buffer.getvalue())
        except Exception as e:
            print(f"Warning: Failed to save audio file to {file_path}. Details: {e}")
            
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)


    def _generate_all_assets(self) -> None:
        """Generates all sound effects and background music loops."""
        # --- SOUND EFFECTS ---
        
        # 1. UI Click: High frequency transient
        def ui_click_wave(t: float) -> float:
            return math.sin(2.0 * math.pi * 1200 * t) * math.exp(-60.0 * t)
        self.sounds["click"] = self._generate_wav("click", ui_click_wave, 0.1, 0.4)
        
        # 2. Footstep: Low frequency noise-like sound
        def footstep_wave(t: float) -> float:
            noise = (math.sin(t * 12345.67) * 987.65) % 2.0 - 1.0
            return (math.sin(2.0 * math.pi * 80 * t) + noise * 0.3) * math.exp(-35.0 * t)
        self.sounds["footstep"] = self._generate_wav("footstep", footstep_wave, 0.08, 0.15)
        
        # 3. Sword Swing: Descending white-noise frequency sweep
        def sword_wave(t: float) -> float:
            freq = 600.0 - 400.0 * (t / 0.2)
            noise = (math.sin(t * 54321.0) * 123.45) % 2.0 - 1.0
            return (math.sin(2.0 * math.pi * freq * t) + noise * 0.5) * math.exp(-12.0 * t)
        self.sounds["sword"] = self._generate_wav("sword", sword_wave, 0.2, 0.5)
        
        # 4. Magic Cast: Ascending frequency sweep with harmonics
        def magic_wave(t: float) -> float:
            freq = 150.0 + 800.0 * (t / 0.3)
            # Add a secondary frequency for magical feel
            return (math.sin(2.0 * math.pi * freq * t) * 0.7 + 
                    math.sin(2.0 * math.pi * freq * 1.5 * t) * 0.3) * math.exp(-8.0 * t)
        self.sounds["magic"] = self._generate_wav("magic", magic_wave, 0.3, 0.4)

        # 5. Hit Damage: Low frequency explosion-like sound
        def hit_wave(t: float) -> float:
            freq = 200.0 - 150.0 * (t / 0.15)
            noise = (math.sin(t * 9999.0) * 888.0) % 2.0 - 1.0
            return (math.sin(2.0 * math.pi * freq * t) + noise * 0.6) * math.exp(-18.0 * t)
        self.sounds["hit"] = self._generate_wav("hit", hit_wave, 0.15, 0.6)

        # 6. Heal: Upward arpeggio
        def heal_wave(t: float) -> float:
            notes = [261.63, 329.63, 392.00, 523.25]  # C Major Arpeggio
            note_idx = min(int(t * 10), len(notes) - 1)
            freq = notes[note_idx]
            # Soft sine wave with minor vibrato
            vibrato = 1.0 + 0.05 * math.sin(2.0 * math.pi * 8 * t)
            return math.sin(2.0 * math.pi * freq * vibrato * t) * math.exp(-4.0 * t)
        self.sounds["heal"] = self._generate_wav("heal", heal_wave, 0.4, 0.45)

        # 7. Level Up: Triumphant Major Chords
        def levelup_wave(t: float) -> float:
            # Multi-note chord arpeggio
            notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99, 1046.50]
            note_idx = min(int(t * 8.5), len(notes) - 1)
            freq = notes[note_idx]
            # Square wave like sound for retro feel
            sin_val = math.sin(2.0 * math.pi * freq * t)
            sq_val = 1.0 if sin_val > 0 else -1.0
            return sq_val * 0.4 * math.exp(-2.5 * t)
        self.sounds["levelup"] = self._generate_wav("levelup", levelup_wave, 0.8, 0.4)

        # 8. Victory Theme: Fast happy melody
        def victory_wave(t: float) -> float:
            # Simple retro lead melody: C, E, G, C, G, C
            melody = [523.25, 659.25, 783.99, 1046.50, 783.99, 1046.50]
            idx = min(int(t * 4), len(melody) - 1)
            freq = melody[idx]
            lead = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            bass = math.sin(2.0 * math.pi * (freq / 4.0) * t) * 0.5
            return (lead * 0.4 + bass * 0.3) * math.exp(-1.0 * t)
        self.sounds["victory"] = self._generate_wav("victory", victory_wave, 1.5, 0.4)

        # 9. Game Over: Melancholy falling notes
        def gameover_wave(t: float) -> float:
            melody = [440.00, 415.30, 392.00, 349.23, 329.63, 293.66] # A, G#, G, F, E, D
            idx = min(int(t * 3.5), len(melody) - 1)
            freq = melody[idx]
            lead = math.sin(2.0 * math.pi * freq * t)
            # Add secondary minor third harmony
            harmony = math.sin(2.0 * math.pi * freq * 1.2 * t) * 0.3
            return (lead * 0.5 + harmony) * math.exp(-0.8 * t)
        self.sounds["gameover"] = self._generate_wav("gameover", gameover_wave, 1.8, 0.4)

        # --- BACKGROUND MUSIC LOOPS ---
        
        # 10. Village Music: Peaceful arpeggio loop (8 seconds)
        def village_music_wave(t: float) -> float:
            # Chord progression: C Major -> G Major -> A Minor -> F Major
            chords = [
                [261.63, 329.63, 392.00],  # C
                [196.00, 246.94, 293.66],  # G
                [220.00, 261.63, 329.63],  # Am
                [174.61, 220.00, 261.63]   # F
            ]
            chord_idx = int(t / 2.0) % 4
            current_chord = chords[chord_idx]
            
            # Arpeggiator (speeds up and loops notes within chord)
            note_idx = int(t * 4) % len(current_chord)
            freq = current_chord[note_idx]
            
            # Simple bass note
            bass_freq = current_chord[0] / 2.0
            
            lead_val = math.sin(2.0 * math.pi * freq * t)
            bass_val = math.sin(2.0 * math.pi * bass_freq * t)
            
            return (lead_val * 0.3 + bass_val * 0.4)
        self.sounds["village_music"] = self._generate_wav("village_music", village_music_wave, 8.0, 0.3)

        # 11. Dungeon Music: Spooky low drone and tense melody (8 seconds)
        def dungeon_music_wave(t: float) -> float:
            # Suspenseful progression in D Minor / G# diminished
            # Slow chords
            roots = [146.83, 138.59, 146.83, 164.81] # D, G#, D, E
            chord_idx = int(t / 2.0) % 4
            root = roots[chord_idx]
            
            # Bass drone (sine)
            bass = math.sin(2.0 * math.pi * root * t)
            # Creepy pulse (detuned second bass)
            pulse = math.sin(2.0 * math.pi * (root * 1.01) * t) * 0.5
            
            # High melody (triangle-like)
            melody_freq = root * 4.0
            if int(t * 2) % 2 == 1:
                # Tritone shift
                melody_freq *= 1.414
            
            sin_val = math.sin(2.0 * math.pi * melody_freq * t)
            melody = (abs(sin_val) * 2.0 - 1.0) * 0.15 # custom triangle wave
            
            return (bass * 0.4 + pulse * 0.2 + melody * 0.3)
        self.sounds["dungeon_music"] = self._generate_wav("dungeon_music", dungeon_music_wave, 8.0, 0.35)

        # 12. Boss Music: Intense fast tempo theme (6 seconds)
        def boss_music_wave(t: float) -> float:
            # Fast driving metal-style chiptune
            # Driving heavy bass rhythm in E minor
            roots = [164.81, 164.81, 196.00, 220.00] # E, E, G, A
            chord_idx = int(t / 1.5) % 4
            root = roots[chord_idx]
            
            # Fast chiptune bass pattern
            bass_pulse = int(t * 8) % 2
            bass = (1.0 if math.sin(2.0 * math.pi * root * t) > 0 else -1.0) * bass_pulse * 0.3
            
            # Frantic melody
            melody_notes = [root * 2.0, root * 2.4, root * 3.0, root * 4.0]
            mel_idx = int(t * 6) % len(melody_notes)
            mel_freq = melody_notes[mel_idx]
            
            melody = math.sin(2.0 * math.pi * mel_freq * t) * 0.3
            
            return (bass + melody)
        self.sounds["boss_music"] = self._generate_wav("boss_music", boss_music_wave, 6.0, 0.4)

    def play_sound(self, name: str) -> None:
        """Plays a sound effect by name, applying the SFX volume."""
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def play_music(self, name: str) -> None:
        """Loops background music by name, applying the music volume."""
        if not self.enabled:
            return
        if self.current_music == name:
            return
        
        # Stop existing music
        if self.current_music:
            music_sound = self.sounds.get(self.current_music)
            if music_sound:
                music_sound.stop()
                
        self.current_music = name
        music_sound = self.sounds.get(name)
        if music_sound:
            music_sound.set_volume(self.music_volume)
            # Loop indefinitely
            music_sound.play(loops=-1)

    def stop_music(self) -> None:
        """Stops current background music."""
        if not self.enabled or not self.current_music:
            return
        music_sound = self.sounds.get(self.current_music)
        if music_sound:
            music_sound.stop()
        self.current_music = None

    def set_music_volume(self, val: float) -> None:
        """Sets the background music volume dynamically."""
        self.music_volume = max(0.0, min(1.0, val))
        if self.current_music:
            music_sound = self.sounds.get(self.current_music)
            if music_sound:
                music_sound.set_volume(self.music_volume)

    def set_sfx_volume(self, val: float) -> None:
        """Sets the sound effects volume."""
        self.sfx_volume = max(0.0, min(1.0, val))
