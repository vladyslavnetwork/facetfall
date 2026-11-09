"""Бонуси: які існують, як часто випадають і як виглядають (власні геометричні значки)."""

import math
import random

import pygame

from .i18n import _

# вид: (корисний?, з якого рівня, вага на 1-му рівні, вага на 50-му, тривалість у секундах або None)
POWERUPS = {
    "points":  (True, 1, 30, 14, None),
    "wide":    (True, 1, 14, 10, 20),
    "multi":   (True, 1, 12, 12, None),
    "shield":  (True, 1, 10, 10, 15),
    "slow":    (True, 1, 10, 6, 12),
    "sticky":  (True, 3, 8, 8, 20),
    "life":    (True, 4, 3, 4, None),
    "laser":   (True, 6, 6, 9, 15),
    "magnet":  (True, 8, 5, 6, 20),
    "fire":    (True, 10, 4, 8, 10),
    "mega":    (True, 12, 3, 6, 15),
    "split":   (True, 15, 3, 7, None),
    "shrink":  (False, 5, 5, 9, 15),
    "fast":    (False, 7, 4, 8, 10),
    "reverse": (False, 20, 2, 4, 7),
}
OPPOSITES = {"wide": "shrink", "shrink": "wide", "slow": "fast", "fast": "slow"}

COLORS = {
    "points": (255, 205, 70), "wide": (80, 200, 255), "multi": (120, 255, 140),
    "shield": (110, 160, 255), "slow": (160, 220, 255), "sticky": (230, 170, 255),
    "life": (255, 110, 160), "laser": (255, 90, 90), "magnet": (255, 160, 60),
    "fire": (255, 120, 30), "mega": (200, 200, 255), "split": (100, 255, 220),
    "shrink": (200, 60, 60), "fast": (200, 60, 60), "reverse": (200, 60, 60),
}


def names():
    return {
        "points": _("Bonus points"), "wide": _("Wide paddle"), "multi": _("Three balls"),
        "shield": _("Shield"), "slow": _("Slow ball"), "sticky": _("Sticky paddle"),
        "life": _("Extra life"), "laser": _("Laser"), "magnet": _("Magnet"),
        "fire": _("Fireball"), "mega": _("Mega ball"), "split": _("Split balls"),
        "shrink": _("Narrow paddle"), "fast": _("Fast ball"), "reverse": _("Reversed controls"),
    }


def duration(kind, difficulty):
    good, _lvl, _w0, _w1, dur = POWERUPS[kind]
    if dur is None:
        return None
    return dur * (1 + 0.6 * difficulty) if good else dur


def pick(level, difficulty, rng=random):
    """Випадковий бонус із вагами, що залежать від рівня: що далі, то крутіші бонуси."""
    kinds, weights = [], []
    for kind, (_good, min_level, w0, w1, _dur) in POWERUPS.items():
        if level >= min_level:
            kinds.append(kind)
            weights.append(w0 + (w1 - w0) * difficulty)
    return rng.choices(kinds, weights)[0]


def draw_capsule(surf, kind, center, w=36, h=18):
    good = POWERUPS[kind][0]
    color = COLORS[kind]
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (int(center[0]), int(center[1]))
    fill = (40, 14, 14) if not good else tuple(c // 5 for c in color)
    pygame.draw.rect(surf, fill, rect, border_radius=h // 2)
    pygame.draw.rect(surf, color, rect, 2, border_radius=h // 2)
    draw_icon(surf, kind, rect.center, h - 6, (255, 255, 255) if good else (255, 200, 200))


def draw_icon(surf, kind, center, s, col):
    cx, cy = center
    h = s // 2
    line = lambda a, b, w=2: pygame.draw.line(surf, col, a, b, w)  # noqa: E731
    poly = lambda pts: pygame.draw.polygon(surf, col, pts)          # noqa: E731
    if kind == "points":
        pts = []
        for i in range(10):
            r = h if i % 2 == 0 else h * 0.45
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        poly(pts)
    elif kind in ("wide", "shrink"):
        line((cx - h + 2, cy), (cx + h - 2, cy))
        if kind == "wide":
            poly([(cx - h - 3, cy), (cx - h + 2, cy - 4), (cx - h + 2, cy + 4)])
            poly([(cx + h + 3, cy), (cx + h - 2, cy - 4), (cx + h - 2, cy + 4)])
        else:
            poly([(cx - 3, cy), (cx - h, cy - 4), (cx - h, cy + 4)])
            poly([(cx + 3, cy), (cx + h, cy - 4), (cx + h, cy + 4)])
    elif kind == "multi":
        for dx in (-h + 1, 0, h - 1):
            pygame.draw.circle(surf, col, (cx + dx, cy), 3)
    elif kind == "shield":
        line((cx - h - 2, cy + 3), (cx + h + 2, cy + 3), 3)
        pygame.draw.arc(surf, col, (cx - h + 2, cy - h + 1, s - 4, s - 2), 0, math.pi, 2)
    elif kind in ("slow", "fast"):
        for k in ((-3, 3) if kind == "fast" else (0,)):
            pts = [(cx - 4 + k, cy - 4), (cx + 2 + k, cy), (cx - 4 + k, cy + 4)]
            pygame.draw.lines(surf, col, False, pts, 2)
        if kind == "slow":
            pygame.draw.circle(surf, col, (cx + 5, cy), 2)
    elif kind == "sticky":
        line((cx - h - 1, cy + 4), (cx + h + 1, cy + 4), 3)
        pygame.draw.circle(surf, col, (cx, cy - 1), 3)
        line((cx, cy + 2), (cx, cy + 4), 2)
    elif kind == "life":
        pygame.draw.circle(surf, col, (cx - 3, cy - 2), 3)
        pygame.draw.circle(surf, col, (cx + 3, cy - 2), 3)
        poly([(cx - 6, cy - 1), (cx + 6, cy - 1), (cx, cy + 5)])
    elif kind == "laser":
        line((cx - 5, cy - h + 1), (cx - 5, cy + h - 1))
        line((cx + 5, cy - h + 1), (cx + 5, cy + h - 1))
    elif kind == "magnet":
        pygame.draw.arc(surf, col, (cx - 6, cy - 6, 12, 12), math.pi, math.tau, 3)
        line((cx - 5, cy), (cx - 5, cy - 5), 3)
        line((cx + 5, cy), (cx + 5, cy - 5), 3)
    elif kind == "fire":
        poly([(cx, cy - h - 1), (cx + 5, cy + 2), (cx, cy + h), (cx - 5, cy + 2)])
    elif kind == "mega":
        pygame.draw.circle(surf, col, (cx, cy), h)
    elif kind == "split":
        pygame.draw.circle(surf, col, (cx, cy + 3), 2)
        line((cx, cy + 1), (cx - 5, cy - 4))
        line((cx, cy + 1), (cx + 5, cy - 4))
    elif kind == "reverse":
        line((cx - 6, cy - 2), (cx + 6, cy - 2))
        poly([(cx + 7, cy - 2), (cx + 3, cy - 5), (cx + 3, cy + 1)])
        line((cx - 6, cy + 3), (cx + 6, cy + 3))
        poly([(cx - 7, cy + 3), (cx - 3, cy), (cx - 3, cy + 6)])
