"""Звуки, синтезовані в коді: жодних сторонніх аудіофайлів і ліцензій."""

import math
import random
from array import array

import pygame

RATE = 22050


def _tone(f0, f1, duration, volume=0.3, wave="square", noise=0.0, decay=1.5):
    n = int(RATE * duration)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += (f0 + (f1 - f0) * t) / RATE
        if wave == "square":
            s = 1.0 if (phase % 1.0) < 0.5 else -1.0
        elif wave == "triangle":
            s = 4 * abs((phase % 1.0) - 0.5) - 1
        else:
            s = math.sin(2 * math.pi * phase)
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        env = min(1.0, i / (RATE * 0.004)) * (1 - t) ** decay
        v = int(s * env * volume * 32767)
        buf.append(v)
        buf.append(v)
    return buf


def _chord(notes, duration, volume=0.22):
    parts = [_tone(f, f, duration, volume / len(notes), "triangle", decay=1.0) for f in notes]
    out = array("h", [0] * len(parts[0]))
    for p in parts:
        for i, v in enumerate(p):
            out[i] += v
    return out


class Audio:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.ok = False
        self.sounds = {}
        try:
            pygame.mixer.pre_init(RATE, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self.ok = True
        except pygame.error:
            return

        def snd(buf):
            return pygame.mixer.Sound(buffer=buf.tobytes())

        self.sounds = {
            "paddle": snd(_tone(440, 520, 0.07, 0.25, "triangle")),
            "wall": snd(_tone(300, 300, 0.04, 0.12, "triangle")),
            "steel": snd(_tone(1800, 1500, 0.12, 0.15, "sine")),
            "explode": snd(_tone(200, 40, 0.45, 0.4, noise=0.75)),
            "laser": snd(_tone(1500, 600, 0.08, 0.12)),
            "good": snd(_chord((523, 659, 784), 0.3)),
            "bad": snd(_tone(300, 120, 0.35, 0.3, "square")),
            "lose": snd(_tone(400, 60, 0.8, 0.35, "triangle", noise=0.2)),
            "clear": snd(_chord((523, 659, 784, 1046), 0.9)),
            "launch": snd(_tone(300, 700, 0.1, 0.2, "triangle")),
        }
        # Звук удару по блоку — висота залежить від ряду (як у ксилофона)
        self.bricks = [snd(_tone(f, f * 0.98, 0.09, 0.22, "square", decay=2.5))
                       for f in (1047, 988, 880, 784, 698, 659, 587, 523, 494, 440, 392, 349, 330, 294)]

    def play(self, name):
        if self.enabled and self.ok:
            self.sounds[name].play()

    def brick(self, row):
        if self.enabled and self.ok:
            self.bricks[row % len(self.bricks)].play()
