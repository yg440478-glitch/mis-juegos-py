"""PONG IA ULTRA - arcade Pong mejorado.

Requisitos: Python 3.10+ y pygame.
Todo el arte y los efectos de sonido se generan por código; no necesita assets externos.
"""
from __future__ import annotations

import json
import math
import random
import sys
from array import array
from collections import deque
from pathlib import Path

import pygame

# -------------------------- Inicio -----------------------------------------
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

WIDTH, HEIGHT = 1040, 650
FPS = 60
BALL_RADIUS = 10
PADDLE_W, PADDLE_H = 18, 112
LEFT_X, RIGHT_X = 42, WIDTH - 42 - PADDLE_W
PLAYER_SPEED = 470.0  # píxeles/segundo
BALL_START = 410.0
BALL_MAX = 790.0
WIN_CHOICES = (5, 7, 11)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PONG IA ULTRA | Tú vs. Computador")
clock = pygame.time.Clock()

# Colores
BG = (6, 10, 24)
PANEL = (13, 23, 43)
GRID = (16, 28, 49)
WHITE = (239, 247, 255)
MUTED = (139, 160, 190)
CYAN = (54, 224, 255)
CYAN_LIGHT = (177, 247, 255)
RED = (255, 81, 121)
RED_LIGHT = (255, 190, 204)
GREEN = (98, 255, 176)
YELLOW = (255, 218, 105)
PURPLE = (181, 131, 255)

FONT_HUGE = pygame.font.SysFont("arial", 68, bold=True)
FONT_TITLE = pygame.font.SysFont("arial", 45, bold=True)
FONT_SCORE = pygame.font.SysFont("arial", 62, bold=True)
FONT_MED = pygame.font.SysFont("arial", 25, bold=True)
FONT_SMALL = pygame.font.SysFont("arial", 19)
FONT_TINY = pygame.font.SysFont("arial", 15)

DIFFICULTIES = {
    1: {"name": "FÁCIL", "speed": 375.0, "error": 88.0, "reaction": 0.16},
    2: {"name": "NORMAL", "speed": 475.0, "error": 38.0, "reaction": 0.09},
    3: {"name": "DIFÍCIL", "speed": 580.0, "error": 8.0, "reaction": 0.035},
}

difficulty = 2
mode = "ai"  # ai | versus
win_score = 7
muted = False

# Archivo de estadísticas junto al .py (si no se puede escribir, el juego sigue).
RECORD_PATH = Path(__file__).with_name("pong_ia_record.json")
def load_records() -> dict:
    try:
        data = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
        return {
            "wins": max(0, int(data.get("wins", 0))),
            "losses": max(0, int(data.get("losses", 0))),
            "best_margin": max(0, int(data.get("best_margin", 0))),
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"wins": 0, "losses": 0, "best_margin": 0}

records = load_records()
def save_records() -> None:
    try:
        RECORD_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except OSError:
        pass

# -------------------------- Sonido sintético ------------------------------
sound_ready = False
sounds: dict[str, pygame.mixer.Sound] = {}

def make_tone(start_hz: float, duration: float = 0.08, volume: float = 0.2,
              end_hz: float | None = None, wave: str = "sine"):
    if not sound_ready:
        return None
    sample_rate = 22050
    count = max(1, int(sample_rate * duration))
    output = array("h")
    end_hz = start_hz if end_hz is None else end_hz
    for i in range(count):
        t = i / sample_rate
        progress = i / max(1, count - 1)
        freq = start_hz + (end_hz - start_hz) * progress
        phase = 2 * math.pi * freq * t
        signal = math.sin(phase) if wave == "sine" else (2 * (phase / (2 * math.pi) % 1) - 1)
        envelope = min(1.0, i / max(1, sample_rate * 0.008))
        envelope *= min(1.0, (count - i) / max(1, sample_rate * 0.028))
        output.append(int(32767 * volume * envelope * signal))
    try:
        return pygame.mixer.Sound(buffer=output.tobytes())
    except pygame.error:
        return None

try:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()
    sound_ready = pygame.mixer.get_init() is not None
except pygame.error:
    sound_ready = False

if sound_ready:
    sounds = {
        "paddle": make_tone(470, 0.055, 0.18, 790),
        "wall": make_tone(290, 0.045, 0.12, 220),
        "score": make_tone(440, 0.2, 0.2, 155),
        "point": make_tone(360, 0.19, 0.2, 920),
        "start": make_tone(350, 0.22, 0.18, 760),
        "win": make_tone(450, 0.48, 0.2, 1100),
        "menu": make_tone(600, 0.07, 0.12, 850),
    }

def play_sound(name: str) -> None:
    sound = sounds.get(name)
    if not muted and sound_ready and sound is not None:
        try:
            sound.play()
        except pygame.error:
            pass

# -------------------------- Efectos visuales -----------------------------
class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int]):
        self.x, self.y = x, y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(55, 260)
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = self.max_life = random.uniform(0.18, 0.48)
        self.color = color
        self.radius = random.randint(2, 5)

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt

    def draw(self, surface: pygame.Surface) -> None:
        if self.life <= 0:
            return
        radius = max(1, round(self.radius * self.life / self.max_life))
        pygame.draw.circle(surface, self.color, (round(self.x), round(self.y)), radius)

particles: list[Particle] = []
trail: deque[tuple[float, float]] = deque(maxlen=14)
stars = [(random.randrange(WIDTH), random.randrange(HEIGHT), random.choice((1, 1, 1, 2))) for _ in range(125)]


def add_particles(x: float, y: float, color: tuple[int, int, int], count: int = 14) -> None:
    particles.extend(Particle(x, y, color) for _ in range(count))


def draw_text(text: str, font: pygame.font.Font, color: tuple[int, int, int],
              center: tuple[int, int], surface: pygame.Surface = screen) -> None:
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=center))


def draw_text_at(text: str, font: pygame.font.Font, color: tuple[int, int, int],
                 pos: tuple[int, int], surface: pygame.Surface = screen) -> None:
    surface.blit(font.render(text, True, color), pos)


def clamp_paddle(paddle: pygame.Rect) -> None:
    paddle.y = max(104, min(HEIGHT - 26 - paddle.height, paddle.y))

# -------------------------- Partida ----------------------------------------
def reset_match() -> None:
    global player, opponent, ball_x, ball_y, ball_vx, ball_vy
    global player_score, opponent_score, state, serve_timer, serve_direction
    global aim_offset, rally_hits, point_message, match_time, particles, trail
    player = pygame.Rect(LEFT_X, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    opponent = pygame.Rect(RIGHT_X, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ball_x, ball_y = WIDTH / 2, HEIGHT / 2
    ball_vx = ball_vy = 0.0
    player_score = opponent_score = 0
    state = "menu"
    serve_timer = 0.0
    serve_direction = random.choice((-1, 1))
    aim_offset = 0.0
    rally_hits = 0
    point_message = ""
    match_time = 0.0
    particles = []
    trail = deque(maxlen=14)


def prepare_serve(direction: int) -> None:
    global ball_x, ball_y, ball_vx, ball_vy, serve_timer, serve_direction, state, aim_offset, rally_hits, trail
    ball_x, ball_y = WIDTH / 2, HEIGHT / 2
    ball_vx = ball_vy = 0.0
    serve_direction = direction
    serve_timer = 1.25
    aim_offset = random.uniform(-DIFFICULTIES[difficulty]["error"], DIFFICULTIES[difficulty]["error"])
    rally_hits = 0
    trail.clear()
    state = "serve"


def launch_ball() -> None:
    global ball_vx, ball_vy, state
    angle = random.uniform(-0.52, 0.52)
    if abs(angle) < 0.13:
        angle = random.choice((-0.22, 0.22))
    ball_vx = math.cos(angle) * BALL_START * serve_direction
    ball_vy = math.sin(angle) * BALL_START
    state = "playing"
    play_sound("start")


def projected_y_at_x() -> float:
    """Predice la altura de la pelota al llegar a la pala derecha, incluyendo rebotes."""
    if ball_vx <= 0:
        return HEIGHT / 2
    travel = (opponent.left - BALL_RADIUS - ball_x) / max(1.0, ball_vx)
    y = ball_y + ball_vy * travel
    low, span = BALL_RADIUS + 1, HEIGHT - 2 * (BALL_RADIUS + 1)
    reflected = (y - low) % (2 * span)
    if reflected > span:
        reflected = 2 * span - reflected
    return low + reflected


def move_ai(dt: float) -> None:
    settings = DIFFICULTIES[difficulty]
    if ball_vx > 0:
        target = projected_y_at_x() + aim_offset
    else:
        target = HEIGHT / 2 + math.sin(pygame.time.get_ticks() * 0.0013) * 45
    target = max(104 + PADDLE_H / 2, min(HEIGHT - 26 - PADDLE_H / 2, target))
    diff = target - opponent.centery
    # La velocidad de reacción cambia por dificultad; no es infalible.
    max_move = settings["speed"] * dt
    if abs(diff) > 5:
        opponent.centery += max(-max_move, min(max_move, diff))
    clamp_paddle(opponent)


def paddle_bounce(paddle: pygame.Rect, is_player: bool) -> None:
    global ball_vx, ball_vy, rally_hits, aim_offset
    offset = (ball_y - paddle.centery) / (paddle.height / 2)
    offset = max(-1.0, min(1.0, offset))
    speed = min(BALL_MAX, math.hypot(ball_vx, ball_vy) * 1.045)
    # Golpear cerca de los extremos produce un ángulo más pronunciado.
    angle = offset * 0.94
    direction = 1 if is_player else -1
    ball_vx = math.cos(angle) * speed * direction
    ball_vy = math.sin(angle) * speed
    if is_player:
        ball_x = paddle.right + BALL_RADIUS + 1
        add_particles(paddle.right, ball_y, CYAN, 15)
        aim_offset = random.uniform(-DIFFICULTIES[difficulty]["error"], DIFFICULTIES[difficulty]["error"])
    else:
        ball_x = paddle.left - BALL_RADIUS - 1
        add_particles(paddle.left, ball_y, RED, 15)
    rally_hits += 1
    play_sound("paddle")


def finish_match(player_won: bool) -> None:
    global state
    state = "gameover"
    if mode == "ai":
        if player_won:
            records["wins"] += 1
            records["best_margin"] = max(records["best_margin"], player_score - opponent_score)
        else:
            records["losses"] += 1
        save_records()
    play_sound("win" if player_won else "score")

# -------------------------- Dibujos ----------------------------------------
def draw_background() -> None:
    screen.fill(BG)
    for x in range(0, WIDTH, 52):
        pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 52):
        pygame.draw.line(screen, GRID, (0, y), (WIDTH, y), 1)
    for sx, sy, radius in stars:
        pygame.draw.circle(screen, (35, 51, 78), (sx, sy), radius)
    for y in range(120, HEIGHT - 25, 28):
        pygame.draw.rect(screen, (44, 64, 91), (WIDTH // 2 - 2, y, 4, 14), border_radius=2)
    pygame.draw.line(screen, (30, 46, 70), (24, 100), (WIDTH - 24, 100), 1)
    pygame.draw.line(screen, (30, 46, 70), (24, HEIGHT - 25), (WIDTH - 24, HEIGHT - 25), 1)


def draw_paddle(rect: pygame.Rect, color: tuple[int, int, int]) -> None:
    halo = pygame.Surface((rect.width + 26, rect.height + 18), pygame.SRCALPHA)
    pygame.draw.rect(halo, (*color, 32), halo.get_rect(), border_radius=11)
    screen.blit(halo, (rect.x - 13, rect.y - 9))
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, (245, 250, 255), rect.inflate(-7, -16), 2, border_radius=5)
    for yy in (rect.y + 15, rect.bottom - 19):
        pygame.draw.circle(screen, WHITE, (rect.centerx, yy), 2)


def draw_ball() -> None:
    # Rastro de la pelota.
    for i, (tx, ty) in enumerate(trail):
        ratio = (i + 1) / max(1, len(trail))
        color = (int(30 + 40 * ratio), int(90 + 130 * ratio), int(135 + 120 * ratio))
        pygame.draw.circle(screen, color, (int(tx), int(ty)), max(1, int(BALL_RADIUS * ratio * 0.78)))
    glow = pygame.Surface((BALL_RADIUS * 8, BALL_RADIUS * 8), pygame.SRCALPHA)
    c = glow.get_width() // 2, glow.get_height() // 2
    pygame.draw.circle(glow, (54, 224, 255, 24), c, BALL_RADIUS * 3)
    pygame.draw.circle(glow, (54, 224, 255, 52), c, BALL_RADIUS * 2)
    screen.blit(glow, (int(ball_x - c[0]), int(ball_y - c[1])))
    pygame.draw.circle(screen, WHITE, (int(ball_x), int(ball_y)), BALL_RADIUS)
    pygame.draw.circle(screen, CYAN_LIGHT, (int(ball_x - 3), int(ball_y - 3)), 4)


def draw_hud() -> None:
    left_label = "JUGADOR 1" if mode == "versus" else "TÚ"
    right_label = "JUGADOR 2" if mode == "versus" else "COMPUTADOR IA"
    draw_text(left_label, FONT_SMALL, CYAN, (LEFT_X + 45, 38))
    draw_text(right_label, FONT_SMALL, RED, (WIDTH - LEFT_X - (75 if mode == "ai" else 50), 38))
    draw_text(str(player_score), FONT_SCORE, CYAN, (WIDTH // 2 - 85, 54))
    draw_text(":", FONT_MED, MUTED, (WIDTH // 2, 53))
    draw_text(str(opponent_score), FONT_SCORE, RED, (WIDTH // 2 + 85, 54))
    sub = f"DIFICULTAD: {DIFFICULTIES[difficulty]['name']}" if mode == "ai" else "MODO DOS JUGADORES"
    draw_text(sub, FONT_TINY, MUTED, (WIDTH // 2, HEIGHT - 15))
    draw_text(f"META: {win_score} PUNTOS", FONT_TINY, MUTED, (WIDTH // 2, HEIGHT - 36))
    draw_text_at("M: sonido  |  P: pausa  |  R: reiniciar", FONT_TINY, MUTED, (22, HEIGHT - 23))


def draw_overlay(title: str, rows: list[tuple[str, tuple[int, int, int]]], color=WHITE) -> None:
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((2, 5, 15, 205))
    screen.blit(shade, (0, 0))
    height = min(490, 152 + len(rows) * 34)
    panel = pygame.Rect(WIDTH // 2 - 342, HEIGHT // 2 - height // 2, 684, height)
    pygame.draw.rect(screen, PANEL, panel, border_radius=24)
    pygame.draw.rect(screen, (50, 81, 119), panel, 2, border_radius=24)
    draw_text(title, FONT_TITLE, color, (WIDTH // 2, panel.y + 52))
    y = panel.y + 108
    for text, row_color in rows:
        draw_text(text, FONT_SMALL, row_color, (WIDTH // 2, y))
        y += 32

# -------------------------- Bucle principal -------------------------------
reset_match()
running = True
previous_state = "playing"

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.035)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "menu":
                    running = False
                else:
                    state = "menu"
            elif event.key == pygame.K_m:
                muted = not muted
                if not muted:
                    play_sound("menu")
            elif event.key == pygame.K_1:
                difficulty = 1
                play_sound("menu")
            elif event.key == pygame.K_2:
                difficulty = 2
                play_sound("menu")
            elif event.key == pygame.K_3:
                difficulty = 3
                play_sound("menu")
            elif event.key == pygame.K_v and state in ("menu", "gameover"):
                mode = "versus" if mode == "ai" else "ai"
                play_sound("menu")
            elif event.key == pygame.K_t and state in ("menu", "gameover"):
                index = WIN_CHOICES.index(win_score)
                win_score = WIN_CHOICES[(index + 1) % len(WIN_CHOICES)]
                play_sound("menu")
            elif event.key == pygame.K_RETURN:
                if state in ("menu", "gameover"):
                    reset_match()
                    prepare_serve(random.choice((-1, 1)))
                elif state == "paused":
                    state = previous_state
            elif event.key == pygame.K_p:
                if state in ("playing", "serve"):
                    previous_state = state
                    state = "paused"
                elif state == "paused":
                    state = previous_state
            elif event.key == pygame.K_r:
                reset_match()
                prepare_serve(random.choice((-1, 1)))

    keys = pygame.key.get_pressed()

    if state in ("playing", "serve"):
        # Movimiento de la pala izquierda. Controles: flechas o W/S.
        move_player = 0.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_player -= PLAYER_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_player += PLAYER_SPEED
        player.y += move_player * dt
        clamp_paddle(player)

        if mode == "ai":
            # Actualiza el cálculo de interceptación solo cuando la pelota va hacia la IA.
            if state == "playing":
                settings = DIFFICULTIES[difficulty]
                if ball_vx > 0:
                    target = projected_y_at_x() + aim_offset
                else:
                    target = HEIGHT / 2 + math.sin(pygame.time.get_ticks() * 0.0011) * 32
                target = max(104 + PADDLE_H / 2, min(HEIGHT - 26 - PADDLE_H / 2, target))
                error = target - opponent.centery
                # Reacción deliberadamente limitada: incluso la dificultad máxima puede fallar.
                effective_speed = settings["speed"] * (0.88 if ball_vx <= 0 else 1.0)
                step = max(-effective_speed * dt, min(effective_speed * dt, error))
                opponent.centery += step
            else:
                target = HEIGHT / 2
                error = target - opponent.centery
                step = max(-DIFFICULTIES[difficulty]["speed"] * dt, min(DIFFICULTIES[difficulty]["speed"] * dt, error))
                opponent.centery += step
        else:
            move_opponent = 0.0
            if keys[pygame.K_i]:
                move_opponent -= PLAYER_SPEED
            if keys[pygame.K_k]:
                move_opponent += PLAYER_SPEED
            opponent.y += move_opponent * dt
        clamp_paddle(opponent)

        if state == "serve":
            serve_timer -= dt
            if serve_timer <= 0:
                launch_ball()
        elif state == "playing":
            match_time += dt
            trail.append((ball_x, ball_y))
            ball_x += ball_vx * dt
            ball_y += ball_vy * dt

            # Rebotar en paredes superior/inferior.
            if ball_y - BALL_RADIUS <= 103:
                ball_y = 103 + BALL_RADIUS
                ball_vy = abs(ball_vy)
                play_sound("wall")
                add_particles(ball_x, ball_y, CYAN, 6)
            elif ball_y + BALL_RADIUS >= HEIGHT - 25:
                ball_y = HEIGHT - 25 - BALL_RADIUS
                ball_vy = -abs(ball_vy)
                play_sound("wall")
                add_particles(ball_x, ball_y, CYAN, 6)

            ball_box = pygame.Rect(int(ball_x - BALL_RADIUS), int(ball_y - BALL_RADIUS), BALL_RADIUS * 2, BALL_RADIUS * 2)
            if ball_box.colliderect(player) and ball_vx < 0:
                ball_x = player.right + BALL_RADIUS + 1
                offset = (ball_y - player.centery) / (PADDLE_H / 2)
                offset = max(-1.0, min(1.0, offset))
                speed = min(BALL_MAX, math.hypot(ball_vx, ball_vy) * 1.045)
                angle = offset * 0.94
                ball_vx = math.cos(angle) * speed
                ball_vy = math.sin(angle) * speed
                rally_hits += 1
                play_sound("paddle")
                add_particles(player.right, ball_y, CYAN, 16)
                aim_offset = random.uniform(-DIFFICULTIES[difficulty]["error"], DIFFICULTIES[difficulty]["error"])

            ball_box = pygame.Rect(int(ball_x - BALL_RADIUS), int(ball_y - BALL_RADIUS), BALL_RADIUS * 2, BALL_RADIUS * 2)
            if ball_box.colliderect(opponent) and ball_vx > 0:
                ball_x = opponent.left - BALL_RADIUS - 1
                offset = (ball_y - opponent.centery) / (PADDLE_H / 2)
                offset = max(-1.0, min(1.0, offset))
                speed = min(BALL_MAX, math.hypot(ball_vx, ball_vy) * 1.04)
                angle = offset * 0.91 + (random.uniform(-0.08, 0.08) if mode == "ai" else 0.0)
                ball_vx = -math.cos(angle) * speed
                ball_vy = math.sin(angle) * speed
                rally_hits += 1
                play_sound("paddle")
                add_particles(opponent.left, ball_y, RED, 16)

            if ball_x < -BALL_RADIUS:
                player_score += 0
                opponent_score += 1
                play_sound("score")
                add_particles(WIDTH // 2, HEIGHT // 2, RED, 30)
                if opponent_score >= win_score:
                    finish_match(False)
                else:
                    prepare_serve(1)
            elif ball_x > WIDTH + BALL_RADIUS:
                player_score += 1
                play_sound("point")
                add_particles(WIDTH // 2, HEIGHT // 2, GREEN, 30)
                if player_score >= win_score:
                    finish_match(True)
                else:
                    prepare_serve(-1)

    for particle in particles[:]:
        particle.update(dt)
        if particle.life <= 0:
            particles.remove(particle)

    # ---------------- Dibujar todo ----------------------------------------
    draw_background()
    draw_paddle(player, CYAN)
    draw_paddle(opponent, RED)
    if state != "menu" or player_score or opponent_score:
        draw_ball()
    else:
        # Pelota decorativa en el menú.
        pygame.draw.circle(screen, WHITE, (int(WIDTH / 2 + math.sin(pygame.time.get_ticks() * 0.002) * 80), HEIGHT // 2), BALL_RADIUS)
    draw_hud()
    for particle in particles:
        particle.draw(screen)

    if state == "menu":
        mode_label = "MODO: TÚ VS COMPUTADOR" if mode == "ai" else "MODO: DOS JUGADORES"
        mode_color = GREEN if mode == "ai" else PURPLE
        draw_overlay("PONG IA ULTRA", [
            (mode_label + "   (V para cambiar)", mode_color),
            (f"Dificultad: {DIFFICULTIES[difficulty]['name']}   |   1 fácil, 2 normal, 3 difícil", YELLOW),
            (f"Primero a {win_score} puntos   (T para cambiar meta)", WHITE),
            ("Jugador 1: ↑ / ↓ o W / S", CYAN),
            ("Jugador 2: I / K   (solo en modo dos jugadores)", RED),
            ("ENTER: empezar     M: sonido     ESC: salir", GREEN),
            (f"Victorias: {records['wins']}   Derrotas: {records['losses']}   Mejor margen: {records['best_margin']}", MUTED),
        ], CYAN)
    elif state == "serve":
        draw_text(str(max(1, math.ceil(serve_timer))), FONT_HUGE, YELLOW, (WIDTH // 2, HEIGHT // 2 - 35))
        draw_text("PREPÁRATE", FONT_MED, WHITE, (WIDTH // 2, HEIGHT // 2 + 35))
    elif state == "paused":
        draw_overlay("PAUSA", [
            ("La partida está detenida", WHITE),
            ("P o ENTER: continuar", GREEN),
            ("R: reiniciar la partida", YELLOW),
            ("ESC: volver al menú", MUTED),
        ], YELLOW)
    elif state == "gameover":
        if player_score > opponent_score:
            title, c = ("¡VICTORIA!" if mode == "ai" else "¡GANA JUGADOR 1!"), GREEN
        else:
            title, c = ("GANA EL COMPUTADOR" if mode == "ai" else "¡GANA JUGADOR 2!"), RED
        draw_overlay(title, [
            (f"Resultado final: {player_score}  -  {opponent_score}", WHITE),
            (f"Duración: {int(match_time)} segundos   |   Rebotes: {rally_hits}", CYAN),
            ("ENTER o R: jugar de nuevo", GREEN),
            ("V: cambiar modo   |   1/2/3: dificultad   |   T: meta", YELLOW),
            ("ESC: volver al menú", MUTED),
        ], c)

    audio_status = "SONIDO: OFF" if muted or not sound_ready else "SONIDO: ON"
    draw_text_at(audio_status, FONT_TINY, MUTED, (WIDTH - 110, HEIGHT - 23))
    pygame.display.flip()

pygame.quit()
sys.exit()
