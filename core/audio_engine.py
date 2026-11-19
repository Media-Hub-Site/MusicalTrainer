"""
core/audio_engine.py
────────────────────
Motor de audio de alta fidelidad para MusicalTrainer.
Proporciona dos capas de reproducción de sonido:
  1. WinMM Native General MIDI Synthesizer (Zero-latency, SoundFont de alta fidelidad de Windows,
     polifonía completa, y soporte real de Note-On y Note-Off para sustain/release natural).
  2. Sintetizador PCM estéreo de respaldo en caso de plataformas sin driver MIDI.
"""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
import struct
import tempfile
import threading
import time
import wave
from typing import Sequence


def midi_to_freq(midi_note: int) -> float:
    """Convierte un número de nota MIDI (ej. 69 = A4) a frecuencia en Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69.0) / 12.0))


class ConservatoryAudioEngine:
    """Motor polifónico con soporte para Note-On / Note-Off y timbres orquestales."""

    SAMPLE_RATE = 22050

    # Programas MIDI de General MIDI para máxima fidelidad
    MIDI_PROGRAMS = {
        "piano": 0,    # Acoustic Grand Piano (Yamaha / Steinway D)
        "rhodes": 4,   # Electric Piano 1 (Rhodes Vintage)
        "guitar": 24,  # Acoustic Guitar (Nylon / Classical Concert)
        "strings": 48, # String Ensemble 1 (Cuerdas de conservatorio)
    }

    def __init__(self) -> None:
        self.enabled: bool = True
        self._timbre: str = "piano"
        self.volume: float = 0.85
        self._cache_dir = os.path.join(tempfile.gettempdir(), "mediahub_musicaltrainer_audio")
        os.makedirs(self._cache_dir, exist_ok=True)
        self._lock = threading.Lock()

        # WinMM MIDI Handle
        self._midi_handle: ctypes.c_void_p | None = None
        self._winmm = None
        self._active_midi_notes: set[int] = set()
        self._note_timers: dict[int, threading.Timer] = {}

        self._init_midi_device()

    @property
    def timbre(self) -> str:
        return self._timbre

    @timbre.setter
    def timbre(self, value: str) -> None:
        self._timbre = value
        self._apply_midi_program()

    def _init_midi_device(self) -> None:
        """Inicializa el sintetizador MIDI de hardware/sistema operativo."""
        if os.name == "nt":
            try:
                self._winmm = ctypes.windll.winmm
                handle = ctypes.c_void_p()
                res = self._winmm.midiOutOpen(ctypes.byref(handle), -1, 0, 0, 0)
                if res == 0:
                    self._midi_handle = handle
                    self._apply_midi_program()
            except Exception:
                self._midi_handle = None

    def _apply_midi_program(self) -> None:
        """Configura el instrumento seleccionado en el canal 0 del sintetizador MIDI."""
        if self._midi_handle and self._winmm:
            prog = self.MIDI_PROGRAMS.get(self._timbre, 0)
            msg = 0x0000C0 | (prog << 8)  # Program Change en canal 0
            try:
                self._winmm.midiOutShortMsg(self._midi_handle, msg)
            except Exception:
                pass

    def note_on(self, midi_note: int, velocity: int = 100) -> None:
        """
        Dispara una nota sostenida (Note On).
        Permite mantener pulsada una tecla en el teclado o piano sin re-disparos artificiales.
        """
        if not self.enabled:
            return

        with self._lock:
            # Si la nota ya está activa, no volvemos a enviarla (evita efecto ametralladora)
            if midi_note in self._active_midi_notes:
                return
            self._active_midi_notes.add(midi_note)

            # Cancelar temporizador previo de apagado si existía
            prev_timer = self._note_timers.pop(midi_note, None)
            if prev_timer:
                prev_timer.cancel()

        if self._midi_handle and self._winmm:
            vel = max(1, min(127, int(velocity * self.volume)))
            msg = 0x90 | (midi_note << 8) | (vel << 16)
            try:
                self._winmm.midiOutShortMsg(self._midi_handle, msg)
                return
            except Exception:
                pass

        # Respaldo PCM si no hay driver MIDI
        wav_path = self._render_events_to_wav([(midi_note, 0.0, 1.4)])
        self._play_wav_async(wav_path)

    def note_off(self, midi_note: int) -> None:
        """
        Libera la nota sostenida (Note Off).
        El instrumento comenzará su fase de release/apagado natural.
        """
        with self._lock:
            if midi_note not in self._active_midi_notes:
                return
            self._active_midi_notes.discard(midi_note)

        if self._midi_handle and self._winmm:
            msg = 0x80 | (midi_note << 8) | (0 << 16)
            try:
                self._winmm.midiOutShortMsg(self._midi_handle, msg)
            except Exception:
                pass

    def play_note(self, midi_note: int, duration: float = 0.95, velocity: int = 100) -> None:
        """Toca una nota y programa automáticamente su apagado tras `duration` segundos."""
        if not self.enabled:
            return

        # Note On inmediato
        self.note_on(midi_note, velocity)

        # Programar Note Off suave tras la duración deseada
        def _delayed_off() -> None:
            self.note_off(midi_note)

        t = threading.Timer(duration, _delayed_off)
        t.daemon = True
        with self._lock:
            old_timer = self._note_timers.get(midi_note)
            if old_timer:
                old_timer.cancel()
            self._note_timers[midi_note] = t
        t.start()

    def play_chord(
        self,
        midi_notes: Sequence[int],
        duration: float = 1.35,
        arpeggiate: bool = True,
        arp_step: float = 0.055,
    ) -> None:
        """Reproduce un acorde orquestal polifónico (simultáneo o arpegiado)."""
        if not self.enabled or not midi_notes:
            return

        def _chord_worker() -> None:
            for idx, m in enumerate(midi_notes):
                self.play_note(m, duration=duration, velocity=98)
                if arpeggiate and idx < len(midi_notes) - 1:
                    time.sleep(arp_step)

        threading.Thread(target=_chord_worker, daemon=True).start()

    def play_sequence(
        self,
        midi_notes: Sequence[int],
        step_delay: float = 0.30,
        note_duration: float = 0.45,
    ) -> None:
        """Reproduce una escala o secuencia melódica."""
        if not self.enabled or not midi_notes:
            return

        def _seq_worker() -> None:
            for m in midi_notes:
                self.play_note(m, duration=note_duration, velocity=95)
                time.sleep(step_delay)

        threading.Thread(target=_seq_worker, daemon=True).start()

    def play_interval(
        self,
        midi_low: int,
        midi_high: int,
        mode: str = "melodic_asc",
    ) -> None:
        """Reproduce un intervalo melódico o armónico."""
        if not self.enabled:
            return

        if mode == "harmonic":
            self.play_chord([midi_low, midi_high], duration=1.2, arpeggiate=False)
        elif mode == "melodic_desc":
            def _desc():
                self.play_note(midi_high, duration=0.45)
                time.sleep(0.40)
                self.play_note(midi_low, duration=0.50)
                time.sleep(0.48)
                self.play_chord([midi_low, midi_high], duration=0.90, arpeggiate=False)
            threading.Thread(target=_desc, daemon=True).start()
        else:
            def _asc():
                self.play_note(midi_low, duration=0.45)
                time.sleep(0.40)
                self.play_note(midi_high, duration=0.50)
                time.sleep(0.48)
                self.play_chord([midi_low, midi_high], duration=0.90, arpeggiate=False)
            threading.Thread(target=_asc, daemon=True).start()

    def play_error_cue(self) -> None:
        """Toque sutil de error."""
        if not self.enabled:
            return
        def _err():
            self.play_note(48, duration=0.15, velocity=85)
            time.sleep(0.12)
            self.play_note(47, duration=0.20, velocity=80)
        threading.Thread(target=_err, daemon=True).start()

    def play_metronome_click(self, accent: bool = False) -> None:
        """Pulso acústico tipo metrónomo de madera."""
        if not self.enabled:
            return
        # MIDI Woodblock (GM Program 115) o Side Stick (Note 31 / 37 en canal 9 percusión)
        if self._midi_handle and self._winmm:
            try:
                note = 76 if accent else 77  # Wood Blocks Hi / Low (General MIDI Drum channel 9)
                msg = 0x99 | (note << 8) | (115 << 16)
                self._winmm.midiOutShortMsg(self._midi_handle, msg)
                return
            except Exception:
                pass

        wav_name = "metro_hi.wav" if accent else "metro_lo.wav"
        wav_path = os.path.join(self._cache_dir, wav_name)
        if not os.path.isfile(wav_path):
            sr = self.SAMPLE_RATE
            dur = 0.045
            n = int(sr * dur)
            f0 = 1180.0 if accent else 820.0
            frames = bytearray(n * 4)
            for i in range(n):
                t = i / sr
                env = math.exp(-75.0 * t)
                val = env * (
                    math.sin(2.0 * math.pi * f0 * t)
                    + 0.45 * math.sin(2.0 * math.pi * (f0 * 1.58) * t)
                )
                s = int(max(-32767, min(32767, val * 22000 * self.volume)))
                struct.pack_into("<hh", frames, i * 4, s, s)
            with self._lock:
                if not os.path.isfile(wav_path):
                    with wave.open(wav_path, "wb") as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(sr)
                        wf.writeframes(frames)
        self._play_wav_async(wav_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Respaldo PCM sintetizado
    # ─────────────────────────────────────────────────────────────────────────

    def _voice_sample(self, freq: float, t: float, dur: float, timbre: str) -> tuple[float, float]:
        if t < 0.0 or t > dur:
            return 0.0, 0.0
        two_pi_f = 2.0 * math.pi * freq
        attack = min(1.0, t / 0.005)
        tail = max(0.0, min(1.0, (dur - t) / 0.05))
        b = 0.00018
        s_l = 0.0
        s_r = 0.0
        weights = (1.00, 0.52, 0.28, 0.15, 0.09, 0.05)
        decays = (1.85, 2.65, 3.60, 4.90, 6.50, 8.40)
        for n, (w, d) in enumerate(zip(weights, decays), start=1):
            fn = freq * n * math.sqrt(1.0 + b * (n * n))
            if fn >= self.SAMPLE_RATE * 0.46:
                break
            env_n = math.exp(-d * t)
            phase_l = 2.0 * math.pi * fn * t
            phase_r = 2.0 * math.pi * (fn * 1.0004) * t + (0.15 * n)
            s_l += w * env_n * math.sin(phase_l)
            s_r += w * env_n * math.sin(phase_r)
        scale = attack * tail * 0.72
        return s_l * scale, s_r * scale

    def _render_events_to_wav(self, events: Sequence[tuple[int, float, float]]) -> str:
        sig = f"{self._timbre}|{self.volume:.2f}|" + ";".join(
            f"{m}:{s:.3f}:{d:.3f}" for m, s, d in events
        )
        digest = hashlib.md5(sig.encode("utf-8")).hexdigest()[:16]
        wav_path = os.path.join(self._cache_dir, f"mt_{digest}.wav")
        if os.path.isfile(wav_path):
            return wav_path

        sr = self.SAMPLE_RATE
        total_dur = max((s + d for _, s, d in events), default=0.4) + 0.04
        num_samples = max(1, int(total_dur * sr))
        buf_l = [0.0] * num_samples
        buf_r = [0.0] * num_samples

        for midi_note, start_s, dur_s in events:
            freq = midi_to_freq(midi_note)
            idx_start = max(0, int(start_s * sr))
            idx_end = min(num_samples, int((start_s + dur_s) * sr))
            for i in range(idx_start, idx_end):
                local_t = (i - idx_start) / sr
                vl, vr = self._voice_sample(freq, local_t, dur_s, self._timbre)
                buf_l[i] += vl
                buf_r[i] += vr

        peak = max(
            max((abs(x) for x in buf_l), default=0.0),
            max((abs(x) for x in buf_r), default=0.0),
            1.0,
        )
        gain = (30000.0 * self.volume) / peak
        frames = bytearray(num_samples * 4)
        pack_into = struct.pack_into
        for i in range(num_samples):
            sl = int(max(-32767.0, min(32767.0, buf_l[i] * gain)))
            sr_val = int(max(-32767.0, min(32767.0, buf_r[i] * gain)))
            pack_into("<hh", frames, i * 4, sl, sr_val)

        with self._lock:
            if not os.path.isfile(wav_path):
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(frames)
        return wav_path

    def _play_wav_async(self, wav_path: str) -> None:
        if not self.enabled or not wav_path or not os.path.isfile(wav_path):
            return
        def _worker() -> None:
            try:
                import winsound
                winsound.PlaySound(
                    wav_path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def close(self) -> None:
        """Cierra el sintetizador MIDI al salir."""
        with self._lock:
            for t in self._note_timers.values():
                t.cancel()
            self._note_timers.clear()
            self._active_midi_notes.clear()

        if self._midi_handle and self._winmm:
            try:
                self._winmm.midiOutReset(self._midi_handle)
                self._winmm.midiOutClose(self._midi_handle)
            except Exception:
                pass
            self._midi_handle = None
