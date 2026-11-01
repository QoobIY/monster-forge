"""Original continuous orchestral score, rendered from explicit note events.

FluidR3 supplies instrument recordings, not musical phrases. Install nothing:
pass its SF2 and a local FluidSynth library to the audio authoring command.
"""

from __future__ import annotations

import ctypes as ct
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SR = 44100
BEAT = 0.5
PROGRAMS = {
    0: 73,
    1: 46,
    2: 48,
    3: 42,
    4: 60,
    5: 57,
    6: 45,
    7: 47,
    8: 44,
    10: 8,
    11: 70,
    12: 48,
    13: 49,
    14: 42,
}


@dataclass(frozen=True)
class Note:
    at: float
    duration: float
    channel: int
    pitch: int
    velocity: int


def arrange(duration=168):
    """A single 84-bar movement; sustained releases cross all scene cuts."""
    if duration != 168:
        raise ValueError("This orchestration is authored for the 168-second cut")
    rng = np.random.default_rng(17023)
    notes = []

    def put(at, length, ch, pitch, velocity):
        timing = float(rng.uniform(-0.012, 0.012)) if ch != 9 else 0
        notes.append(
            Note(
                max(0.0, at + timing),
                length,
                ch,
                int(pitch),
                int(np.clip(velocity + rng.integers(-4, 5), 1, 120)),
            )
        )

    # D major opens the town; its rising D–F–A signature returns in D minor.
    chords = [(50, 54, 57), (47, 50, 54), (43, 47, 50), (45, 49, 52)]
    minor = [(38, 41, 45), (34, 38, 41), (43, 46, 50), (45, 49, 52)]
    theme = [
        (0, 0, 1.5),
        (1.5, 3, 0.5),
        (2, 7, 2),
        (4, 10, 1),
        (5, 7, 1),
        (6, 5, 1),
        (7, 3, 1),
        (8, 2, 1.5),
        (9.5, 3, 0.5),
        (10, 5, 2),
        (12, 7, 1.5),
        (13.5, 5, 0.5),
        (14, 2, 1),
        (15, 0, 1),
    ]
    for bar in range(84):
        at = bar * 2.0
        town = bar < 8
        danger = 8 <= bar < 14
        heroes = 14 <= bar < 30
        mystery = 30 <= bar < 35
        battle = 35 <= bar < 39
        god = 39 <= bar < 48
        fall = 48 <= bar < 60
        crypt = 60 <= bar < 72
        finale = bar >= 72
        loud = battle or fall or finale
        root, third, fifth = chords[(bar // 2) % 4] if town else minor[(bar // 2) % 4]
        strength = (
            48 if town else 55 if heroes else 39 if mystery else 47 if god else 43 if crypt else 66
        )
        # An overlap of 0.4–0.9 s joins chords; no per-scene reset or mute.
        for j, pitch in enumerate((root + 12, third + 12, fifth + 12)):
            put(at + j * 0.028, 2.55, 2, pitch, strength + (3 if j == 1 else 0))
        put(at, 2.65, 3, root, strength + 8)
        if danger:
            for pitch in (root + 24, fifth + 24):
                put(at, 2.4, 8, pitch, 40 + (bar - 8) * 4)
            put(at, 1.6, 7, root, 50 + (bar - 8) * 5)
        # Harp has its own changing harmony and inversions, not a looped motif.
        if town or heroes or mystery or crypt:
            order = (
                root + 24,
                fifth + 24,
                third + 36,
                fifth + 24,
                root + 36,
                third + 36,
                fifth + 36,
                third + 36,
            )
            for k, pitch in enumerate(order):
                put(at + k * 0.25, 1.25, 1, pitch, 44 if crypt else 52)
        if town:
            for k in range(4):
                put(at + k * 0.5, 0.3, 6, (root, fifth, third, fifth)[k] + 12, 51)
        if mystery or god or crypt:
            put(at + 0.25, 3.2, 10, third + 36, 35 if god else 45)
            put(at + 1.25, 2.5, 10, fifth + 36, 39)
        if loud:
            # Moving sixteenth-note strings, accented in groups of four.
            scale = (root + 24, fifth + 12, third + 24, fifth + 24)
            for k in range(16):
                put(
                    at + k * 0.125,
                    0.19,
                    12,
                    scale[(k + bar) % 4],
                    (74 if k % 4 == 0 else 57) + (7 if finale else 0),
                )
            for k in range(4):
                put(at + k * 0.5, 0.43, 3, root + (12 if k % 2 else 0), 78)
                put(at + k * 0.5, 0.7, 7, root, 96 if k == 0 else 67)
            for k, pitch in enumerate((36, 42, 38, 42, 36, 42, 38, 46)):
                put(at + k * 0.25, 0.15, 9, pitch, 92 if k % 2 == 0 else 55)
            if bar % 4 == 0:
                put(at, 2.5, 9, 49, 88)
        elif heroes and bar >= 25:
            for k in range(4):
                put(at + k * 0.5, 0.8, 7, root, 40 + (bar - 25) * 7)
        if god:
            put(at, 1.5, 11, root + 12, 61)
            if bar % 2 == 0:
                put(at + 0.5, 2.5, 5, fifth + 12, 53)
        if crypt and bar % 2 == 0:
            put(at + 1, 2.8, 11, third + 12, 57)
        if finale:
            for pitch in (root + 12, fifth + 12):
                put(at, 1.75, 5, pitch, 65 + min(14, bar - 72))

    # Four related theme statements with distinct articulation/orchestration.
    for start, ch, base, velocity in [
        (0, 0, 74, 76),
        (8, 0, 74, 80),
        (28, 4, 62, 78),
        (36, 13, 74, 73),
        (54, 4, 62, 91),
        (70, 4, 62, 100),
        (96, 13, 74, 90),
        (104, 4, 62, 88),
        (112, 13, 74, 94),
        (144, 4, 62, 91),
        (152, 4, 74, 103),
    ]:
        for beat, interval, length in theme:
            pitch = base + interval
            if start < 16 and interval in (3, 10):
                pitch += 1
            put(start + beat * BEAT, length * BEAT * 0.94, ch, pitch, velocity)
    # A quieter continuation of the heroes' phrase carries the book joke.
    for k, pitch in enumerate((69, 67, 65, 64, 62, 65, 64, 61)):
        put(44 + k, 0.88, 0, pitch, 61 - k)
    # God gets an inverted, slower fragment, answered by bassoon/celesta.
    for k, pitch in enumerate((69, 65, 62, 60, 61, 64, 69, 67)):
        put(80 + k * 1.8, 1.65, 4 if k < 4 else 11, pitch, 66)
    for k, pitch in enumerate((62, 65, 69, 67, 64, 65, 62, 61)):
        put(122 + k * 2.5, 2.2, 14, pitch - 12, 62)
    # Single broad D-minor ending; melody resolves, percussion stops naturally.
    notes = [n for n in notes if n.at < 160]
    for ch, pitches, vel in [
        (2, (50, 57, 62, 65, 69), 83),
        (4, (62, 65, 69), 92),
        (5, (38, 45, 50), 76),
        (3, (38, 50), 88),
    ]:
        for pitch in pitches:
            put(160, 5.6, ch, pitch, vel)
    put(160, 2, 7, 38, 110)
    put(160, 3, 9, 49, 96)
    return sorted(notes, key=lambda n: n.at)


def render(notes, soundfont: Path, library: Path, duration=168):
    """Offline floating-point synthesis. No audio device or realtime I/O."""
    lib = ct.CDLL(str(library))

    def api(name, result, args):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
        return fn

    ptr, integer, real, string = ct.c_void_p, ct.c_int, ct.c_double, ct.c_char_p
    settings = api("new_fluid_settings", ptr, [])()
    setnum = api("fluid_settings_setnum", integer, [ptr, string, real])
    setint = api("fluid_settings_setint", integer, [ptr, string, integer])
    setnum(settings, b"synth.sample-rate", SR)
    setnum(settings, b"synth.gain", 0.65)
    setnum(settings, b"synth.reverb.room-size", 0.79)
    setnum(settings, b"synth.reverb.damp", 0.38)
    setnum(settings, b"synth.reverb.width", 75.0)
    setnum(settings, b"synth.reverb.level", 0.32)
    setint(settings, b"synth.polyphony", 512)
    synth = api("new_fluid_synth", ptr, [ptr])(settings)
    try:
        loaded = api("fluid_synth_sfload", integer, [ptr, string, integer])(
            synth, str(soundfont).encode(), 1
        )
        if loaded < 0:
            raise RuntimeError("Cannot load orchestral instruments")
        program = api("fluid_synth_program_change", integer, [ptr, integer, integer])
        cc = api("fluid_synth_cc", integer, [ptr, integer, integer, integer])
        for channel, preset in PROGRAMS.items():
            program(synth, channel, preset)
            cc(
                synth,
                channel,
                10,
                {
                    0: 44,
                    1: 86,
                    2: 48,
                    3: 76,
                    4: 40,
                    5: 83,
                    6: 55,
                    7: 70,
                    8: 64,
                    10: 88,
                    11: 49,
                    12: 58,
                    13: 43,
                    14: 74,
                }[channel],
            )
        on = api("fluid_synth_noteon", integer, [ptr, integer, integer, integer])
        off = api("fluid_synth_noteoff", integer, [ptr, integer, integer])
        write = api(
            "fluid_synth_write_float",
            integer,
            [ptr, integer, ptr, integer, integer, ptr, integer, integer],
        )
        events = []
        for n in notes:
            events.extend(
                [(round(n.at * SR), True, n), (round((n.at + n.duration) * SR), False, n)]
            )
        events.sort(key=lambda e: (e[0], e[1]))
        length = int(duration * SR)
        audio = np.zeros((length, 2), np.float32)
        cursor = 0

        def samples(end):
            nonlocal cursor
            end = min(end, length)
            if end > cursor:
                address = audio.ctypes.data + cursor * 8
                if write(synth, end - cursor, address, 0, 2, address, 1, 2) != 0:
                    raise RuntimeError("Instrument rendering failed")
                cursor = end

        held = {}
        for frame, active, n in events:
            if frame >= length:
                break
            samples(frame)
            # Tied orchestral tones must survive an overlapping chord's
            # note-off, rather than vanishing halfway through the next bar.
            if n.channel in (2, 3, 8):
                key = (n.channel, n.pitch)
                count = held.get(key, 0)
                held[key] = count + (1 if active else -1)
                if active and count == 0:
                    on(synth, n.channel, n.pitch, n.velocity)
                elif not active and count == 1:
                    off(synth, n.channel, n.pitch)
                continue
            if active:
                on(synth, n.channel, n.pitch, n.velocity)
            else:
                off(synth, n.channel, n.pitch)
        samples(length)
        # Continuous bus compression, no section normalization or gain resets.
        block = 441
        peaks = np.max(np.abs(audio[: length // block * block].reshape(-1, block, 2)), axis=(1, 2))
        smoothed = np.zeros_like(peaks)
        level = 0.0
        for i, peak in enumerate(peaks):
            factor = 0.6 if peak > level else 0.025
            level += (peak - level) * factor
            smoothed[i] = level
        gain = np.minimum(1.0, (0.22 / np.maximum(smoothed, 1e-6)) ** 0.55)
        audio *= np.interp(np.arange(length), np.arange(len(gain)) * block, gain)[:, None]
        audio *= 1.8
        audio = np.tanh(audio).astype(np.float32)
        fade = np.minimum(np.arange(length) / (SR * 0.25), 1.0)
        fade *= np.minimum((length - 1 - np.arange(length)) / (SR * 2.0), 1.0)
        audio *= fade[:, None]
        return audio
    finally:
        api("delete_fluid_synth", None, [ptr])(synth)
        api("delete_fluid_settings", None, [ptr])(settings)


def provenance(notes, font):
    import hashlib

    return {
        "title": "Игра только начинается — непрерывная оркестровая сюита",
        "bpm": 120,
        "meter": "4/4",
        "bars": 84,
        "duration": 168,
        "composition": "Original note-level composition; no music loops or borrowed melodies.",
        "instruments": "FluidR3 GM 3.1, Frank Wen and contributors, MIT license",
        "soundfont_sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
        "programs": PROGRAMS,
        "notes": [asdict(n) for n in notes],
    }
