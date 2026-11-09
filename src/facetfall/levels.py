"""Генератор 50 геометричних рівнів зі зростаючою складністю.

Кожен рівень — візерунок (маска) на сітці 13×12 плюс розподіл типів блоків.
Генерація детермінована: рівень N завжди однаковий для всіх гравців.
"""

import math
import random

TOTAL_LEVELS = 50
CHECKPOINT_EVERY = 5
COLS, ROWS = 13, 12
MID = (COLS - 1) / 2

# Типи блоків
NORMAL, TOUGH2, TOUGH3, STEEL, BOMB = "n", "t2", "t3", "steel", "bomb"


def _ring(d, k):
    return int(d * k) % 2 == 0


# Візерунки: функція (c, r, u, v, rows, phase) -> bool. u, v у межах [-1, 1].
PATTERNS = [
    lambda c, r, u, v, rows, p: r % 3 != 2 or rows <= 6,                    # смуги
    lambda c, r, u, v, rows, p: abs(u) + abs(v) <= 1.05,                     # ромб
    lambda c, r, u, v, rows, p: (c + r) % 2 == 0,                            # шахівниця
    lambda c, r, u, v, rows, p: abs(c - MID) <= r + 0.5,                     # піраміда
    lambda c, r, u, v, rows, p: _ring(math.hypot(u, v), 3.2) and math.hypot(u, v) <= 1.15,  # кільця
    lambda c, r, u, v, rows, p: abs(abs(u) - abs(v)) < 0.28 or abs(v) < 0.12,  # зірка-хрест
    lambda c, r, u, v, rows, p: abs(v - 0.65 * math.sin(u * math.pi * 1.4 + p)) < 0.42,  # хвиля
    lambda c, r, u, v, rows, p: _ring(max(abs(u), abs(v)), 3.4),             # рамки
    lambda c, r, u, v, rows, p: abs(u) <= abs(v) + 0.12,                     # пісочний годинник
    lambda c, r, u, v, rows, p: c % 3 != 1,                                  # колони
    lambda c, r, u, v, rows, p: ((math.atan2(v, u) / math.tau) + math.hypot(u, v) * 1.3 + p) % 1 < 0.5,  # спіраль
    lambda c, r, u, v, rows, p: abs(u) * 0.87 + abs(v) * 0.5 <= 0.95 and abs(v) <= 0.98,  # шестикутник
    lambda c, r, u, v, rows, p: (r + abs(c - MID)) % 4 < 2,                 # шеврони
    lambda c, r, u, v, rows, p: (c + r) % 4 < 2,                             # діагоналі
]


def _mask(level, rows):
    n = len(PATTERNS)
    i = (level - 1) % n
    phase = level * 0.7
    first = PATTERNS[i]
    loop = (level - 1) // n
    if loop == 0:
        combine = lambda a, b: a                        # noqa: E731  (перший прохід — чисті фігури)
    elif loop == 1:
        combine = lambda a, b: a or b                   # noqa: E731  (об'єднання двох фігур)
    elif loop == 2:
        combine = lambda a, b: a != b                   # noqa: E731  (XOR — складні орнаменти)
    else:
        combine = lambda a, b: a and not b              # noqa: E731
    second = PATTERNS[(i * 5 + 3) % n]
    cells = set()
    for r in range(rows):
        for c in range(COLS):
            u = (c - MID) / MID
            v = (r - (rows - 1) / 2) / max(1, (rows - 1) / 2)
            if combine(first(c, r, u, v, rows, phase), second(c, r, u, v, rows, phase + 1)):
                cells.add((c, r))
    return cells


def build_level(level):
    """Повертає словник {(колонка, ряд): (тип, відтінок, бонус)} і параметри рівня."""
    rng = random.Random(level * 7919)
    d = (level - 1) / (TOTAL_LEVELS - 1)            # 0.0 … 1.0 — складність
    rows = min(ROWS - 1, 5 + (level - 1) // 3)
    cells = _mask(level, rows)
    # Пізні рівні не мають ставати коротшими: добираємо фігури, доки не буде досить блоків
    need = 40 + int(45 * d)
    extra = 1
    while len(cells) < need and extra < 6:
        cells |= _mask(level + extra * 3, rows)
        extra += 1

    p_steel = 0 if level < 8 else 0.03 + 0.10 * d
    p_t3 = 0 if level < 10 else 0.05 + 0.22 * d
    p_t2 = 0.06 + 0.28 * d
    p_bomb = 0.03 + 0.04 * d
    p_bonus = 0.07 + 0.05 * d
    hue0 = (level * 47) % 360

    bricks = {}
    for (c, r) in cells:
        x = rng.random()
        if x < p_steel:
            kind = STEEL
        elif x < p_steel + p_t3:
            kind = TOUGH3
        elif x < p_steel + p_t3 + p_t2:
            kind = TOUGH2
        elif x < p_steel + p_t3 + p_t2 + p_bomb:
            kind = BOMB
        else:
            kind = NORMAL
        hue = (hue0 + r * 22) % 360
        bonus = kind != STEEL and rng.random() < p_bonus
        bricks[(c, r)] = (kind, hue, bonus)

    # Сталевий бар'єр під візерунком із проходами — з 15-го рівня кожен 4-й рівень
    if level >= 15 and level % 4 == 3:
        gaps = set(rng.sample(range(COLS), 3 if level < 35 else 2))
        for c in range(COLS):
            if c not in gaps:
                bricks[(c, rows)] = (STEEL, 0, False)

    # Хоча б один блок має бути руйнівним
    if not any(k != STEEL for k, _h, _b in bricks.values()):
        bricks[(int(MID), 0)] = (NORMAL, hue0, True)

    params = {
        "ball_speed": 330 + 5.5 * level,
        "drop_chance": 0.10 + 0.10 * d,
        "difficulty": d,
    }
    return bricks, params
