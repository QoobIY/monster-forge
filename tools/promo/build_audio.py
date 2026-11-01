"""Original instrumental score and authored foley for the subtitled promo.

Run with numpy installed. No speech synthesis or downloaded voice is used.
Original orchestration uses FluidR3 instrument recordings (MIT), never sampled music.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import wave
from dataclasses import replace
from pathlib import Path

import numpy as np
from cinematic_score import arrange, provenance, render

SR = 44100
RNG = np.random.default_rng(20261021)


def envelope(t, attack, release):
    return np.minimum(t / attack, 1) * np.minimum((t[-1] - t) / release, 1)


def note(midi, duration, kind):
    t = np.arange(int(duration * SR)) / SR
    f = 440 * 2 ** ((midi - 69) / 12)
    phase = 2 * np.pi * f * t
    if kind != "bell":
        raise ValueError("Foley tone must be a bell")
    return (
        sum(
            np.sin(phase * r) * np.exp(-t * (0.8 + i * 0.5)) / (i + 1)
            for i, r in enumerate([1, 2.01, 2.76, 4.07])
        )
        * envelope(t, 0.004, 0.3)
        * 0.22
    )


def drum(duration=1.5, heavy=False):
    t = np.arange(int(duration * SR)) / SR
    sweep = 2 * np.pi * (42 * t + (50 if heavy else 75) * (0.025 * (1 - np.exp(-t / 0.025))))
    body = np.sin(sweep) * np.exp(-t * 5)
    noise = RNG.normal(0, 1, len(t))
    filtered = np.convolve(noise, np.ones(13) / 13, mode="same")
    return (body * 0.55 + filtered * np.exp(-t * 18) * 0.5) * envelope(t, 0.003, 0.2)


def stamp(sec):
    ms = round(sec * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--soundfont", type=Path, required=True)
    parser.add_argument("--synth-library", type=Path, required=True)
    parser.add_argument("--instrument-license", type=Path, required=True)
    args = parser.parse_args()
    story = json.loads(args.story.read_text())
    knots = np.asarray(
        story.get("edit", [[0, 0], [story["duration"], story["duration"]]]), dtype=float
    )
    if (
        knots.ndim != 2
        or knots.shape[1] != 2
        or len(knots) < 2
        or not np.isfinite(knots).all()
        or np.any(knots[0] != 0)
        or np.any(np.diff(knots, axis=0) <= 0)
        or knots[-1, 0] != story["duration"]
    ):
        raise ValueError("Invalid authored/output film clocks")

    def cut(t):
        return float(np.interp(t, knots[:, 0], knots[:, 1]))

    output_duration = cut(story["duration"])
    n = int((output_duration + 3) * SR)
    music = np.zeros((n, 2), np.float32)
    foley = np.zeros_like(music)

    def add(bus, t, signal, gain=1.0, pan=0.0):
        # Foley follows the same edit as the picture. Pitch changes are limited
        # to authored synthetic impacts/whooshes; musical notes retain pitch.
        end = cut(t + len(signal) / SR)
        at = cut(t)
        count = max(1, round((end - at) * SR))
        signal = np.interp(np.linspace(0, len(signal) - 1, count), np.arange(len(signal)), signal)
        i = round(at * SR)
        if i < 0 or i + len(signal) > n:
            raise ValueError("Audio event outside movie")
        bus[i : i + len(signal), 0] += signal * (gain * np.sqrt((1 - pan) / 2))
        bus[i : i + len(signal), 1] += signal * (gain * np.sqrt((1 + pan) / 2))

    notes = arrange(story["duration"])
    notes = [replace(n, at=cut(n.at), duration=cut(n.at + n.duration) - cut(n.at)) for n in notes]
    score = render(notes, args.soundfont, args.synth_library, output_duration)
    music[: len(score)] = score

    # Foley: birds and market bell; low-frequency arrival, impact, portals, fall.
    for i, t in enumerate(np.arange(0.4, 16, 1.1)):
        x = np.arange(int(0.23 * SR)) / SR
        chirp = np.sin(2 * np.pi * (2100 * x + 2400 * x * x)) * np.sin(np.pi * x / 0.23) ** 2
        add(foley, float(t), chirp, 0.025, np.sin(i) * 0.8)
    add(foley, 1, note(86, 4, "bell"), 0.14, -0.6)
    for at, duration, gain in [
        (17, 5, 0.4),
        (21.7, 6, 1.3),
        (56, 3, 0.6),
        (60, 2, 0.4),
        (76.5, 2, 0.75),
        (96, 4, 0.9),
        (100, 18, 0.22),
        (119, 2, 0.9),
        (149, 7, 0.35),
    ]:
        t = np.arange(int(duration * SR)) / SR
        noise = RNG.normal(0, 1, len(t))
        rumble = np.convolve(noise, np.ones(160) / 160, mode="same")
        env = envelope(t, 0.1, 0.7)
        if at == 21.7:
            env = np.exp(-t * 0.7)
            add(foley, at, drum(3, True), 1.8)
        add(foley, at, (rumble * 0.9 + np.sin(2 * np.pi * (38 * t + 2 * t * t)) * 0.12) * env, gain)
    for at in [71.4, 72.4, 73.2, 74.1, 75.2, 76.5, 93, 95, 97]:
        t = np.arange(int(1.3 * SR)) / SR
        sweep = np.sin(2 * np.pi * (110 * t + 900 * t * t)) * np.exp(-t * 4)
        add(foley, at, sweep, 0.25, np.sin(at) * 0.6)
    for at in [22, 22.25, 22.6, 23.1, 23.6, 24.2]:
        add(foley, at, drum(0.8), 0.6, np.sin(at * 4) * 0.8)

    # The dispossession is an audible sequence: pull, absorption, lift, throw.
    for at, gain in [
        (72.6, 0.65),
        (73.7, 1.0),
        (76.5, 0.8),
        (92.3, 0.45),
        (94.3, 0.6),
        (95.3, 0.45),
        (97, 1.25),
        (99.7, 0.7),
    ]:
        add(foley, at, drum(1.3, True), gain)

    # Reading time is independent of TTS duration; no spoken track is generated.
    for i, line in enumerate(story["dialogue"]):
        next_at = story["dialogue"][i + 1]["at"] if i + 1 < len(story["dialogue"]) else 157
        end = line["at"] + max(2.3, len(line["text"]) / 17 + 1)
        if line["who"] == "Маг" and line["at"] == 46:
            end = min(end, 50.4)
        line["end"] = round(min(next_at - 0.3, end), 3)
        line.pop("voice", None)

    # One continuous score bus; scene cuts never reset its gain or reverb.
    length = int(output_duration * SR)
    tail = np.minimum((length - np.arange(length)) / int(1.5 * SR), 1)
    final = np.tanh(music[:length] * 1.05 + foley[:length] * 0.38)
    final *= tail[:, None]
    music = music[:length]
    assert np.isfinite(final).all() and np.max(np.abs(final)) <= 1
    root = args.root
    target = root / "media/audio/cinematic/random-god-reckoning"
    target.mkdir(parents=True, exist_ok=True)
    files = {}
    for role, data in [
        ("instrumental", final),
        ("music", music),
        ("foley", np.tanh(foley[:length] * 0.7) * tail[:, None]),
    ]:
        assert np.isfinite(data).all() and np.max(np.abs(data)) <= 1, role
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp:
            with wave.open(temp.name, "wb") as out:
                out.setnchannels(2)
                out.setsampwidth(2)
                out.setframerate(SR)
                out.writeframes((data * 30000).astype("<i2").tobytes())
            blob = Path(temp.name).read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        path = target / f"{role}.{digest[:24]}.wav"
        path.write_bytes(blob)
        files[role] = {
            "path": path.relative_to(root / "media").as_posix(),
            "sha256": digest,
            "size_bytes": len(blob),
            "media_type": "audio/wav",
        }
    files["audio"] = files["instrumental"]
    srt = (
        "\n\n".join(
            f"{i + 1}\n{stamp(cut(line['at']))} --> {stamp(cut(line['end']))}\n{line['who']}: {line['text']}"
            for i, line in enumerate(story["dialogue"])
        )
        + "\n"
    )
    score_provenance = provenance(notes, args.soundfont)
    score_provenance.update(
        duration=output_duration,
        edit=knots.tolist(),
        bpm="120 authored, tempo follows the cinematic edit",
    )
    for role, blob, suffix, mime in [
        ("subtitles", srt.encode(), ".srt", "application/x-subrip"),
        (
            "story",
            json.dumps(story, ensure_ascii=False, indent=2).encode(),
            ".json",
            "application/json",
        ),
        (
            "score",
            json.dumps(score_provenance, ensure_ascii=False, indent=2).encode(),
            ".json",
            "application/json",
        ),
        ("instrument_license", args.instrument_license.read_bytes(), ".txt", "text/plain"),
    ]:
        digest = hashlib.sha256(blob).hexdigest()
        path = target / (role + "." + digest[:24] + suffix)
        path.write_bytes(blob)
        files[role] = {
            "path": path.relative_to(root / "media").as_posix(),
            "sha256": digest,
            "size_bytes": len(blob),
            "media_type": mime,
        }
    catalog_path = root / "media/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    identity = "audio.cinematic.random_god_reckoning"
    old = next((a for a in catalog["assets"] if a["id"] == identity), None)
    entry = {
        "id": identity,
        "kind": "audio",
        "title": "Игра только начинается — оркестровая сюита без голосов",
        "group": "Cinematics",
        "tags": [
            "original-score",
            "orchestral",
            "continuous",
            "instrumental",
            "subtitled",
            "promo",
        ],
        "revision": (old["revision"] + 1 if old else 1),
        "files": files,
    }
    catalog["assets"] = [a for a in catalog["assets"] if a["id"] != identity] + [entry]
    pending = catalog_path.with_suffix(".next")
    pending.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    pending.replace(catalog_path)
    print("Published", identity, flush=True)


if __name__ == "__main__":
    main()
