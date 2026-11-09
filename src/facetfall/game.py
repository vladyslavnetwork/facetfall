"""Facetfall — геометричний арканоїд: 50 рівнів, 15 бонусів, контрольні точки."""

import math
import random

import pygame

from . import i18n, powerups
from .about import About
from .i18n import _
from .levels import (BOMB, CHECKPOINT_EVERY, COLS, NORMAL, STEEL, TOTAL_LEVELS, TOUGH2,
                     TOUGH3, build_level)

W, H = 768, 720
FPS = 60
TOP_Y = 56
BW, BH, GAP = 52, 22, 4
GRID_X = (W - (COLS * (BW + GAP) - GAP)) // 2
GRID_Y = 100
PADDLE_Y = 664
PADDLE_H = 14
PADDLE_W = 104
SHIELD_Y = 704
BALL_R = 7
EXTRA_LIFE_EVERY = 25000
MAX_BALLS = 24

BG = (8, 8, 22)
WHITE = (235, 235, 245)
GREY = (140, 140, 165)
DIM = (70, 70, 100)
YELLOW = (255, 215, 90)
RED = (255, 90, 90)
GREEN = (110, 255, 160)
STEEL_COL = (150, 160, 175)

POINTS = {NORMAL: 50, TOUGH2: 100, TOUGH3: 150, BOMB: 80}
HP = {NORMAL: 1, TOUGH2: 2, TOUGH3: 3, BOMB: 1, STEEL: 10 ** 9}
MENU_ITEMS = ["start", "continue", "help", "language", "sound", "fullscreen", "about", "quit"]
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def hue_color(hue, sat=70, val=95):
    c = pygame.Color(0)
    c.hsva = (hue % 360, sat, val, 100)
    return (c.r, c.g, c.b)


class Brick:
    __slots__ = ("col", "row", "kind", "hp", "hue", "bonus", "flash")

    def __init__(self, col, row, kind, hue, bonus):
        self.col, self.row, self.kind, self.hue, self.bonus = col, row, kind, hue, bonus
        self.hp = HP[kind]
        self.flash = 0.0

    @property
    def rect(self):
        return pygame.Rect(GRID_X + self.col * (BW + GAP), GRID_Y + self.row * (BH + GAP), BW, BH)


class Ball:
    __slots__ = ("x", "y", "vx", "vy", "stuck")

    def __init__(self, x, y, vx=0.0, vy=0.0, stuck=None):
        self.x, self.y, self.vx, self.vy, self.stuck = x, y, vx, vy, stuck


class Game:
    def __init__(self, screen, settings, audio):
        self.screen = screen
        self.settings = settings
        self.audio = audio
        self.running = True
        self.time = 0.0
        self.fonts = {}
        self.held = set()
        self.mouse_buttons = False
        self.state = "menu"
        self.menu_index = 0
        self.state_timer = 0.0
        self.score = 0
        self.level = 1
        self.lives = 3
        self.new_record = False
        self.paused_from = "playing"
        self.about = About()
        self.balls, self.bricks, self.capsules, self.bolts = [], {}, [], []
        self.particles, self.floaters, self.effects = [], [], {}
        self.paddle_x = W / 2
        self.paddle_w = PADDLE_W
        self.next_life = EXTRA_LIFE_EVERY
        self.params = build_level(1)[1]
        rnd = random.Random(3)
        self.stars = [(rnd.randrange(W), rnd.randrange(TOP_Y, H), rnd.random() * 6.28)
                      for _ in range(60)]

    # ---------- допоміжне ----------

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        return self.fonts[size]

    def text(self, msg, size, color, **pos):
        img = self.font(size).render(msg, True, color)
        rect = img.get_rect(**pos)
        self.screen.blit(img, rect)
        return rect

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass
        self.settings.save()

    def set_state(self, state, timer=0.0):
        self.state, self.state_timer = state, timer

    def checkpoint(self):
        return max(1, min(int(self.settings["checkpoint"]), TOTAL_LEVELS))

    # ---------- гра ----------

    def new_game(self, start_level=1):
        self.score = 0
        self.lives = 3
        self.next_life = EXTRA_LIFE_EVERY
        self.new_record = False
        self.level = start_level
        self.start_level()

    def start_level(self):
        layout, self.params = build_level(self.level)
        self.bricks = {pos: Brick(pos[0], pos[1], k, h, b) for pos, (k, h, b) in layout.items()}
        self.reset_round()
        self.set_state("ready")

    def reset_round(self):
        self.capsules.clear()
        self.bolts.clear()
        self.effects.clear()
        self.paddle_w = PADDLE_W
        self.speed_boost = 1.0
        self.combo = 0
        self.laser_cd = 0.0
        self.balls = [Ball(self.paddle_x, PADDLE_Y - BALL_R - 1, stuck=0.0)]

    def has(self, effect):
        return self.effects.get(effect, 0) > 0

    def ball_radius(self):
        return BALL_R * 1.7 if self.has("mega") else BALL_R

    def target_speed(self):
        s = self.params["ball_speed"] * self.speed_boost
        if self.has("slow"):
            s *= 0.68
        if self.has("fast"):
            s *= 1.35
        return min(s, 900)

    def paddle_rect(self):
        return pygame.Rect(int(self.paddle_x - self.paddle_w / 2), PADDLE_Y, int(self.paddle_w), PADDLE_H)

    def add_score(self, points):
        self.score += int(points)
        while self.score >= self.next_life:
            self.next_life += EXTRA_LIFE_EVERY
            self.lives += 1
            self.floater(_("Extra life"), self.paddle_x, PADDLE_Y - 30, GREEN)
            self.audio.play("good")
        if self.score > self.settings["high_score"]:
            self.settings["high_score"] = self.score
            self.new_record = True

    def floater(self, msg, x, y, color):
        self.floaters.append([msg, float(x), float(y), 1.4, color])

    def burst(self, rect, color, n=10):
        for _ in range(n):
            self.particles.append([rect.centerx + random.uniform(-rect.w / 2, rect.w / 2),
                                   rect.centery + random.uniform(-rect.h / 2, rect.h / 2),
                                   random.uniform(-160, 160), random.uniform(-220, 60),
                                   random.uniform(0.4, 0.8), color])

    def launch(self):
        launched = False
        for b in self.balls:
            if b.stuck is not None:
                angle = math.radians(max(-50, min(50, b.stuck / (self.paddle_w / 2) * 50)) or -12)
                s = self.target_speed()
                b.vx, b.vy = s * math.sin(angle), -s * math.cos(angle)
                b.stuck = None
                launched = True
        if launched:
            self.audio.play("launch")
            if self.state == "ready":
                self.set_state("playing")

    def fire(self):
        if self.has("laser") and self.laser_cd <= 0 and self.state == "playing":
            r = self.paddle_rect()
            self.bolts += [pygame.Rect(r.left + 6, r.top - 12, 3, 12),
                           pygame.Rect(r.right - 9, r.top - 12, 3, 12)]
            self.laser_cd = 0.28
            self.audio.play("laser")

    def action(self):
        """Клік / пробіл: запуск м'яча, інакше — постріл лазером."""
        if any(b.stuck is not None for b in self.balls):
            self.launch()
        else:
            self.fire()

    # ---------- події ----------

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            self.settings.save()
            self.running = False
            return
        if ev.type == pygame.MOUSEMOTION and self.state in ("ready", "playing"):
            x = ev.pos[0]
            self.paddle_x = W - x if self.has("reverse") else x
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.mouse_buttons = True
            if self.state in ("ready", "playing"):
                self.action()
            return
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.mouse_buttons = False
            return
        if ev.type == pygame.KEYUP:
            self.held.discard(ev.key)
            return
        if ev.type != pygame.KEYDOWN:
            return
        self.held.add(ev.key)
        key = ev.key
        if key == pygame.K_F11:
            self.toggle_fullscreen()
        elif self.state == "menu":
            self.menu_key(key)
        elif self.state == "help":
            self.set_state("menu")
        elif self.state == "about":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.about.activate(self.settings["fullscreen"])
            else:
                self.set_state("menu")
        elif self.state == "paused":
            if key in (pygame.K_p, pygame.K_PAUSE) or key in CONFIRM_KEYS:
                self.set_state(self.paused_from, self.state_timer)
            elif key == pygame.K_ESCAPE:
                self.settings.save()
                self.set_state("menu")
        elif self.state in ("game_over", "victory"):
            if self.state_timer <= 0 and (key in CONFIRM_KEYS or key == pygame.K_ESCAPE):
                self.set_state("menu")
        elif key in (pygame.K_p, pygame.K_PAUSE, pygame.K_ESCAPE):
            self.paused_from = self.state
            self.set_state("paused", self.state_timer)
        elif key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            self.action()

    def menu_items(self):
        return [m for m in MENU_ITEMS if m != "continue" or self.checkpoint() > 1]

    def menu_key(self, key):
        items = self.menu_items()
        self.menu_index %= len(items)
        item = items[self.menu_index]
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(items)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(items)
        elif key == pygame.K_ESCAPE:
            self.settings.save()
            self.running = False
        elif key in LEFT_KEYS + RIGHT_KEYS + CONFIRM_KEYS:
            delta = -1 if key in LEFT_KEYS else 1
            if item == "language":
                codes = i18n.CODES
                code = codes[(codes.index(i18n.current_language()) + delta) % len(codes)]
                i18n.set_language(code)
                self.settings["language"] = code
                self.settings.save()
            elif item == "sound":
                self.settings["sound"] = self.audio.enabled = not self.audio.enabled
                self.settings.save()
            elif item == "fullscreen":
                self.toggle_fullscreen()
            elif key in CONFIRM_KEYS:
                if item == "start":
                    self.new_game(1)
                elif item == "continue":
                    self.new_game(self.checkpoint())
                elif item == "help":
                    self.set_state("help")
                elif item == "about":
                    self.about.status = None
                    self.set_state("about")
                elif item == "quit":
                    self.settings.save()
                    self.running = False

    # ---------- оновлення ----------

    def update(self, dt):
        self.time += dt
        if self.state in ("menu", "paused", "help", "about"):
            return
        self.update_fx(dt)
        if self.state in ("game_over", "victory"):
            self.state_timer -= dt
            return
        if self.state == "level_clear":
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self.level >= TOTAL_LEVELS:
                    self.settings.save()
                    self.set_state("victory", 1.5)
                else:
                    self.level += 1
                    if (self.level - 1) % CHECKPOINT_EVERY == 0 and self.level > self.checkpoint():
                        self.settings["checkpoint"] = self.level
                        self.settings.save()
                    self.start_level()
            return

        # ракетка: клавіатура
        move = any(k in self.held for k in RIGHT_KEYS) - any(k in self.held for k in LEFT_KEYS)
        if self.has("reverse"):
            move = -move
        self.paddle_x += move * 560 * dt
        target_w = PADDLE_W * (1.55 if self.has("wide") else 0.62 if self.has("shrink") else 1.0)
        self.paddle_w += (target_w - self.paddle_w) * min(1.0, dt * 10)
        half = self.paddle_w / 2
        self.paddle_x = max(half + 4, min(W - half - 4, self.paddle_x))

        for b in self.balls:
            if b.stuck is not None:
                b.stuck = max(-half + 4, min(half - 4, b.stuck))
                b.x = self.paddle_x + b.stuck
                b.y = PADDLE_Y - self.ball_radius() - 1

        if self.state == "ready":
            return

        # ефекти з таймером
        for k in list(self.effects):
            self.effects[k] -= dt
            if self.effects[k] <= 0:
                del self.effects[k]
                if k == "sticky":
                    self.launch()

        self.laser_cd -= dt
        if self.has("laser") and (self.mouse_buttons or pygame.K_SPACE in self.held):
            if not any(b.stuck is not None for b in self.balls):
                self.fire()

        self.update_balls(dt)
        self.update_bolts(dt)
        self.update_capsules(dt)

        if not any(b.kind != STEEL for b in self.bricks.values()):
            self.audio.play("clear")
            self.add_score(1000 * self.level)
            self.capsules.clear()
            self.set_state("level_clear", 2.0)
            return

        if not self.balls:
            self.lives -= 1
            self.audio.play("lose")
            if self.lives <= 0:
                self.settings.save()
                self.set_state("game_over", 1.2)
            else:
                self.reset_round()
                self.set_state("ready")

    def update_fx(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 600 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[2] -= 40 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        for b in self.bricks.values():
            b.flash = max(0.0, b.flash - dt)

    def update_balls(self, dt):
        r = self.ball_radius()
        speed = self.target_speed()
        for ball in list(self.balls):
            if ball.stuck is not None:
                continue
            # нормалізуємо швидкість і не даємо м'ячу літати майже горизонтально
            cur = math.hypot(ball.vx, ball.vy) or 1
            ball.vx, ball.vy = ball.vx / cur * speed, ball.vy / cur * speed
            if abs(ball.vy) < speed * 0.28:
                ball.vy = math.copysign(speed * 0.28, ball.vy or -1)
                ball.vx = math.copysign(math.sqrt(speed ** 2 - ball.vy ** 2), ball.vx or 1)
            steps = max(1, int(speed * dt / 4) + 1)
            for _ in range(steps):
                ball.x += ball.vx * dt / steps
                ball.y += ball.vy * dt / steps
                if not self.step_ball(ball, r):
                    if ball in self.balls:
                        self.balls.remove(ball)
                    break
                if ball.stuck is not None:
                    break

    def step_ball(self, ball, r):
        """Один крок фізики. Повертає False, якщо м'яч упав."""
        if ball.x < r:
            ball.x, ball.vx = r, abs(ball.vx)
            self.audio.play("wall")
        elif ball.x > W - r:
            ball.x, ball.vx = W - r, -abs(ball.vx)
            self.audio.play("wall")
        if ball.y < TOP_Y + r:
            ball.y, ball.vy = TOP_Y + r, abs(ball.vy)
            self.audio.play("wall")

        pr = self.paddle_rect()
        if ball.vy > 0 and pr.left - r <= ball.x <= pr.right + r and \
                PADDLE_Y - r <= ball.y <= PADDLE_Y + PADDLE_H / 2:
            rel = max(-1.0, min(1.0, (ball.x - self.paddle_x) / (self.paddle_w / 2)))
            angle = math.radians(rel * 62)
            s = math.hypot(ball.vx, ball.vy)
            ball.vx, ball.vy = s * math.sin(angle), -s * math.cos(angle)
            ball.y = PADDLE_Y - r - 0.5
            self.combo = 0
            self.speed_boost = min(1.3, self.speed_boost + 0.006)
            self.audio.play("paddle")
            if self.has("sticky"):
                ball.stuck = ball.x - self.paddle_x
            return True

        if self.has("shield") and ball.vy > 0 and ball.y + r >= SHIELD_Y:
            ball.y, ball.vy = SHIELD_Y - r, -abs(ball.vy)
            self.audio.play("wall")
            return True
        if ball.y - r > H:
            return False

        if GRID_Y - r <= ball.y <= GRID_Y + 13 * (BH + GAP) + r:
            self.collide_bricks(ball, r)
        return True

    def collide_bricks(self, ball, r):
        step_x, step_y = BW + GAP, BH + GAP
        c0, c1 = int((ball.x - r - GRID_X) // step_x), int((ball.x + r - GRID_X) // step_x)
        r0, r1 = int((ball.y - r - GRID_Y) // step_y), int((ball.y + r - GRID_Y) // step_y)
        best, best_d = None, None
        for row in range(r0, r1 + 1):
            for col in range(c0, c1 + 1):
                b = self.bricks.get((col, row))
                if not b:
                    continue
                rect = b.rect
                cx = max(rect.left, min(ball.x, rect.right))
                cy = max(rect.top, min(ball.y, rect.bottom))
                d = (ball.x - cx) ** 2 + (ball.y - cy) ** 2
                if d <= r * r and (best_d is None or d < best_d):
                    best, best_d = (b, cx, cy), d
        if not best:
            return
        b, cx, cy = best
        passes = self.has("fire") and b.kind != STEEL
        if not passes:
            dx, dy = ball.x - cx, ball.y - cy
            if dx == 0 and dy == 0:
                ball.vy = -ball.vy
            elif abs(dx) > abs(dy):
                ball.vx = math.copysign(abs(ball.vx), dx)
                ball.x = cx + math.copysign(r + 0.5, dx)
            else:
                ball.vy = math.copysign(abs(ball.vy), dy)
                ball.y = cy + math.copysign(r + 0.5, dy)
        damage = 99 if self.has("fire") else (2 if self.has("mega") else 1)
        self.hit_brick(b, damage)

    def hit_brick(self, b, damage):
        if b.kind == STEEL:
            b.flash = 0.15
            self.audio.play("steel")
            return
        b.hp -= damage
        b.flash = 0.12
        self.audio.brick(b.row)
        if b.hp > 0:
            return
        self.destroy_brick(b)

    def destroy_brick(self, b):
        if (b.col, b.row) not in self.bricks:
            return
        del self.bricks[(b.col, b.row)]
        rect = b.rect
        self.combo += 1
        mult = 1 + min(self.combo - 1, 20) * 0.1
        self.add_score(POINTS[b.kind] * (1 + (self.level - 1) * 0.05) * mult)
        self.burst(rect, hue_color(b.hue), 8)
        if b.bonus or random.random() < self.params["drop_chance"]:
            if len(self.capsules) < 5:
                kind = powerups.pick(self.level, self.params["difficulty"])
                self.capsules.append([float(rect.centerx), float(rect.centery), kind])
        if b.kind == BOMB:
            self.audio.play("explode")
            self.burst(rect.inflate(60, 40), (255, 140, 40), 24)
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    nb = self.bricks.get((b.col + dc, b.row + dr))
                    if nb and nb.kind != STEEL:
                        nb.hp = 0
                        self.destroy_brick(nb)

    def update_bolts(self, dt):
        for bolt in list(self.bolts):
            bolt.y -= int(900 * dt) or 1
            if bolt.bottom < TOP_Y:
                self.bolts.remove(bolt)
                continue
            col = (bolt.centerx - GRID_X) // (BW + GAP)
            row = (bolt.top - GRID_Y) // (BH + GAP)
            b = self.bricks.get((col, row))
            if b and b.rect.colliderect(bolt):
                self.bolts.remove(bolt)
                self.hit_brick(b, 1)

    def update_capsules(self, dt):
        pr = self.paddle_rect()
        for cap in list(self.capsules):
            cap[1] += 150 * dt
            if self.has("magnet"):
                cap[0] += (self.paddle_x - cap[0]) * min(1.0, dt * 2.5)
            rect = pygame.Rect(0, 0, 36, 18)
            rect.center = (int(cap[0]), int(cap[1]))
            if rect.colliderect(pr):
                self.capsules.remove(cap)
                self.apply(cap[2])
            elif rect.top > H:
                self.capsules.remove(cap)

    def apply(self, kind):
        good = powerups.POWERUPS[kind][0]
        name = powerups.names()[kind]
        self.audio.play("good" if good else "bad")
        color = powerups.COLORS[kind] if good else RED
        d = self.params["difficulty"]
        if kind == "points":
            pts = random.choice((100, 250, 500)) * (1 + self.level // 10)
            self.add_score(pts)
            name = _("+{n} points").format(n=pts)
        elif kind == "life":
            self.lives += 1
        elif kind == "multi":
            self.spawn_balls(per_ball=False)
        elif kind == "split":
            self.spawn_balls(per_ball=True)
        else:
            opposite = powerups.OPPOSITES.get(kind)
            if opposite:
                self.effects.pop(opposite, None)
            self.effects[kind] = powerups.duration(kind, d)
        self.floater(name, self.paddle_x, PADDLE_Y - 30, color)

    def spawn_balls(self, per_ball):
        free = [b for b in self.balls if b.stuck is None] or self.balls
        sources = free if per_ball else free[:1]
        for src in sources:
            base = math.atan2(src.vx, -src.vy) if src.stuck is None else 0.0
            s = self.target_speed()
            for da in ((-0.45, 0.45) if not per_ball else (0.5,)):
                if len(self.balls) >= MAX_BALLS:
                    return
                a = base + da
                self.balls.append(Ball(src.x, src.y if src.stuck is None else src.y - 4,
                                       s * math.sin(a), -abs(s * math.cos(a))))

    # ---------- малювання ----------

    def draw(self):
        s = self.screen
        s.fill(BG)
        for x, y, ph in self.stars:
            lv = int(50 + 25 * (1 + math.sin(ph + self.time * 1.3)))
            s.set_at((x, y), (lv, lv, lv + 30))
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "help":
            self.draw_help()
        elif self.state == "about":
            self.about.draw(self, W, H, (WHITE, GREY, YELLOW, RED))
        else:
            self.draw_play()
        pygame.display.flip()

    def draw_menu(self):
        self.text(_("HI-SCORE") + f"  {self.settings['high_score']:06d}", 24, GREY, center=(W // 2, 26))
        # Назва з «гранями»: кожна літера свого кольору
        title = "FACETFALL"
        f = self.font(100)
        widths = [f.size(ch)[0] for ch in title]
        x = W // 2 - sum(widths) // 2
        for i, ch in enumerate(title):
            bob = int(5 * math.sin(self.time * 2.2 + i * 0.6))
            img = f.render(ch, True, hue_color(200 + i * 18, 60, 100))
            self.screen.blit(f.render(ch, True, (40, 30, 80)), (x + 4, 72 + 4 + bob))
            self.screen.blit(img, (x, 72 + bob))
            x += widths[i]
        self.text(_("Break every facet. Don't let the ball fall!"), 26, WHITE, center=(W // 2, 165))

        on, off = _("On"), _("Off")
        labels = {
            "start": _("New game"),
            "continue": _("Continue from level {n}").format(n=self.checkpoint()),
            "help": _("Bonuses"),
            "language": _("Language: {name}").format(name=i18n.language_name(i18n.current_language())),
            "sound": _("Sound: {state}").format(state=on if self.audio.enabled else off),
            "fullscreen": _("Fullscreen: {state}").format(state=on if self.settings["fullscreen"] else off),
            "about": _("About"),
            "quit": _("Quit"),
        }
        items = self.menu_items()
        self.menu_index %= len(items)
        for i, item in enumerate(items):
            y = 232 + i * 44
            sel = i == self.menu_index
            label = labels[item]
            if sel and item in ("language", "sound", "fullscreen"):
                label = f"<  {label}  >"
            rect = self.text(label, 36, YELLOW if sel else GREY, center=(W // 2, y))
            if sel:
                pw = 60
                pygame.draw.rect(self.screen, GREEN, (rect.left - pw - 24, y - 5, pw, 10), border_radius=5)
                pygame.draw.circle(self.screen, WHITE, (rect.left - 24 - pw // 2, y - 13 + int(3 * math.sin(self.time * 6))), 6)
        self.text(_("{n} levels · checkpoint every {k} levels").format(n=TOTAL_LEVELS, k=CHECKPOINT_EVERY),
                  22, DIM, center=(W // 2, H - 58))
        self.text(_("MOUSE or ARROWS move    CLICK or SPACE launch/fire    P pause    F11 fullscreen"),
                  20, GREY, center=(W // 2, H - 30))

    def draw_help(self):
        self.text(_("Bonuses"), 52, YELLOW, center=(W // 2, 60))
        names = powerups.names()
        kinds = list(powerups.POWERUPS)
        good = [k for k in kinds if powerups.POWERUPS[k][0]]
        bad = [k for k in kinds if not powerups.POWERUPS[k][0]]
        for i, k in enumerate(good):
            col, row = i % 2, i // 2
            x, y = 70 + col * 350, 130 + row * 44
            powerups.draw_capsule(self.screen, k, (x, y), 44, 22)
            self.text(names[k], 26, WHITE, midleft=(x + 34, y))
        y0 = 130 + ((len(good) + 1) // 2) * 44 + 24
        self.text(_("Avoid:"), 26, RED, midleft=(48, y0))
        for i, k in enumerate(bad):
            x, y = 70 + (i % 2) * 350, y0 + 40 + (i // 2) * 44
            powerups.draw_capsule(self.screen, k, (x, y), 44, 22)
            self.text(names[k], 26, (255, 180, 180), midleft=(x + 34, y))
        self.text(_("The further you get, the stronger the bonuses."), 24, GREY, center=(W // 2, H - 70))
        self.text(_("Press any key to return"), 22, DIM, center=(W // 2, H - 36))

    def draw_brick(self, b):
        rect = b.rect
        s = self.screen
        if b.kind == STEEL:
            base = STEEL_COL if b.flash <= 0 else WHITE
            pygame.draw.rect(s, base, rect, border_radius=3)
            pygame.draw.line(s, (210, 215, 225), rect.topleft, (rect.right - 1, rect.top), 2)
            pygame.draw.line(s, (90, 95, 110), (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 2)
            for dx in (8, rect.w - 8):
                pygame.draw.circle(s, (100, 105, 120), (rect.left + dx, rect.centery), 2)
            return
        color = hue_color(b.hue, 65, 95) if b.flash <= 0 else WHITE
        pygame.draw.rect(s, color, rect, border_radius=3)
        light = tuple(min(255, c + 60) for c in color)
        dark = tuple(c // 2 for c in color)
        # «Грань»: світлий трикутник зверху-зліва, темний знизу-справа
        pygame.draw.polygon(s, light, [rect.topleft, (rect.right - 1, rect.top), (rect.left + 10, rect.top + 7), (rect.left, rect.top + 7)])
        pygame.draw.polygon(s, dark, [(rect.right - 1, rect.top + 6), (rect.right - 1, rect.bottom - 1), (rect.left + 6, rect.bottom - 1)])
        if b.kind in (TOUGH2, TOUGH3):
            pygame.draw.rect(s, WHITE, rect, 2, border_radius=3)
            cracks = HP[b.kind] - b.hp
            for i in range(cracks):
                x = rect.left + 14 + i * 20
                pygame.draw.lines(s, (30, 30, 40), False, [(x, rect.top + 2), (x + 5, rect.centery), (x - 2, rect.bottom - 3)], 2)
        if b.kind == BOMB:
            pygame.draw.circle(s, (30, 20, 20), rect.center, 7)
            spark = (255, 220, 80) if int(self.time * 6) % 2 else (255, 120, 40)
            pygame.draw.circle(s, spark, (rect.centerx + 5, rect.centery - 6), 3)
        if b.bonus:
            glow = int(120 + 120 * (0.5 + 0.5 * math.sin(self.time * 5 + b.col)))
            pygame.draw.rect(s, (glow, glow, 255), rect.inflate(2, 2), 1, border_radius=4)

    def draw_play(self):
        s = self.screen
        # верхня панель
        self.text(_("SCORE"), 20, GREY, topleft=(16, 8))
        self.text(f"{self.score:06d}", 32, WHITE, topleft=(16, 26))
        self.text(_("HI-SCORE"), 20, GREY, topright=(W - 16, 8))
        self.text(f"{self.settings['high_score']:06d}", 32, WHITE, topright=(W - 16, 26))
        self.text(_("LEVEL {n}").format(n=self.level) + f" / {TOTAL_LEVELS}", 24, YELLOW, center=(W // 2, 16))
        for i in range(min(self.lives - 1, 8)):
            x = W // 2 - (min(self.lives - 1, 8) * 30) // 2 + i * 30
            pygame.draw.rect(s, GREEN, (x, 36, 24, 7), border_radius=3)
        pygame.draw.line(s, DIM, (0, TOP_Y), (W, TOP_Y), 1)

        # активні бонуси з таймерами
        x = 12
        for kind, left in sorted(self.effects.items()):
            powerups.draw_capsule(s, kind, (x + 17, TOP_Y + 18), 34, 16)
            total = powerups.duration(kind, self.params["difficulty"]) or 1
            pygame.draw.rect(s, powerups.COLORS[kind], (x, TOP_Y + 30, int(34 * left / total), 3))
            x += 42
        if self.combo >= 3:
            self.text(f"x{1 + min(self.combo - 1, 20) * 0.1:.1f}", 26, YELLOW, topright=(W - 14, TOP_Y + 8))

        for b in self.bricks.values():
            self.draw_brick(b)
        for p in self.particles:
            s.fill(p[5], (int(p[0]), int(p[1]), 3, 3))
        for cap in self.capsules:
            powerups.draw_capsule(s, cap[2], (cap[0], cap[1]))
        for bolt in self.bolts:
            s.fill((255, 120, 120), bolt)

        if self.has("shield"):
            left = self.effects["shield"]
            if left > 2 or int(self.time * 8) % 2:
                pygame.draw.rect(s, (110, 160, 255), (0, SHIELD_Y, W, 4))
                pygame.draw.rect(s, (60, 90, 200), (0, SHIELD_Y + 4, W, 2))

        if self.state not in ("game_over",):
            pr = self.paddle_rect()
            col = (255, 170, 230) if self.has("sticky") else GREEN
            pygame.draw.rect(s, col, pr, border_radius=7)
            pygame.draw.rect(s, WHITE, (pr.left + 6, pr.top + 2, pr.w - 12, 3), border_radius=2)
            if self.has("laser"):
                for gx in (pr.left + 4, pr.right - 10):
                    pygame.draw.rect(s, RED, (gx, pr.top - 6, 6, 8))

        r = int(self.ball_radius())
        for ball in self.balls:
            col = (255, 150, 40) if self.has("fire") else WHITE
            if self.has("fire"):
                pygame.draw.circle(s, (255, 80, 20), (int(ball.x), int(ball.y)), r + 3)
            pygame.draw.circle(s, col, (int(ball.x), int(ball.y)), r)
            pygame.draw.circle(s, (255, 255, 255), (int(ball.x) - r // 3, int(ball.y) - r // 3), max(1, r // 3))

        for msg, fx, fy, life, color in self.floaters:
            self.text(msg, 26, color, center=(int(fx), int(fy)))

        center = (W // 2, 480)
        if self.state == "ready":
            self.overlay([(_("LEVEL {n}").format(n=self.level), 48, YELLOW),
                          (_("Click or press SPACE to launch"), 26, WHITE)], center)
        elif self.state == "level_clear":
            lines = [(_("Level complete!"), 46, YELLOW)]
            nxt = self.level + 1
            if (nxt - 1) % CHECKPOINT_EVERY == 0 and nxt <= TOTAL_LEVELS:
                lines.append((_("Checkpoint: level {n}").format(n=nxt), 28, GREEN))
            self.overlay(lines, center)
        elif self.state == "paused":
            self.overlay([(_("PAUSED"), 56, YELLOW),
                          (_("P — continue    ESC — main menu"), 26, WHITE)], center)
        elif self.state == "game_over":
            lines = [(_("GAME OVER"), 64, RED)]
            if self.new_record:
                lines.append((_("NEW HIGH SCORE!"), 34, YELLOW))
            if self.state_timer <= 0:
                lines.append((_("Press ENTER to continue"), 26, WHITE))
            self.overlay(lines, center)
        elif self.state == "victory":
            lines = [(_("YOU WIN!"), 64, GREEN),
                     (_("All {n} levels cleared!").format(n=TOTAL_LEVELS), 30, WHITE)]
            if self.state_timer <= 0:
                lines.append((_("Press ENTER to continue"), 26, GREY))
            self.overlay(lines, center)

    def overlay(self, lines, center):
        heights = [self.font(sz).get_linesize() for _t, sz, _c in lines]
        widths = [self.font(sz).size(t)[0] for t, sz, _c in lines]
        box = pygame.Rect(0, 0, max(widths) + 60, sum(heights) + 36)
        box.center = center
        shade = pygame.Surface(box.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 205))
        self.screen.blit(shade, box)
        pygame.draw.rect(self.screen, GREY, box, 2, border_radius=6)
        y = box.top + 18
        for (t, sz, color), h in zip(lines, heights):
            self.text(t, sz, color, center=(box.centerx, y + h // 2))
            y += h


def run(screen, settings, audio):
    game = Game(screen, settings, audio)
    clock = pygame.time.Clock()
    while game.running:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)
        for ev in pygame.event.get():
            game.handle_event(ev)
        game.update(dt)
        game.draw()
    settings.save()
