import pygame
import random
import sys
import math

# ─── INIT ────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🚀 Space Invaders")
clock = pygame.time.Clock()

# ─── COLORS ──────────────────────────────────────────
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
GREEN      = (0, 255, 100)
RED        = (255, 60, 60)
YELLOW     = (255, 255, 0)
CYAN       = (0, 255, 255)
MAGENTA    = (255, 0, 255)
ORANGE     = (255, 165, 0)
DARK_BG    = (5, 5, 20)
STAR_COLOR = (100, 100, 140)

# ─── FONTS ───────────────────────────────────────────
font_sm = pygame.font.SysFont("consolas", 18)
font_md = pygame.font.SysFont("consolas", 28)
font_lg = pygame.font.SysFont("consolas", 52, bold=True)
font_xl = pygame.font.SysFont("consolas", 72, bold=True)

# ─── SOUND GENERATION (no external files needed) ─────
def make_sound(frequency, duration_ms=100, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n_samples * 2)
    for i in range(n_samples):
        t = i / sample_rate
        # Decaying sine wave
        decay = max(0, 1 - i / n_samples)
        val = int(32767 * volume * decay * math.sin(2 * math.pi * frequency * t))
        val = max(-32768, min(32767, val))
        buf[i * 2] = val & 0xFF
        buf[i * 2 + 1] = (val >> 8) & 0xFF
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

try:
    snd_shoot     = make_sound(880, 80, 0.2)
    snd_explosion = make_sound(150, 200, 0.3)
    snd_hit       = make_sound(220, 150, 0.25)
    snd_powerup   = make_sound(1200, 150, 0.2)
    sound_enabled = True
except Exception:
    sound_enabled = False

def play_sound(sound):
    if sound_enabled:
        sound.play()

# ─── STARS (background) ─────────────────────────────
stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.3, 1.5)) for _ in range(120)]

def draw_stars():
    for i, (x, y, speed) in enumerate(stars):
        brightness = int(80 + 60 * speed)
        pygame.draw.circle(screen, (brightness, brightness, brightness + 30), (int(x), int(y)), 1)
        stars[i] = (x, (y + speed) % HEIGHT, speed)

# ─── DRAW HELPERS ────────────────────────────────────
def draw_player(x, y):
    # Ship body
    points = [(x, y - 18), (x - 16, y + 12), (x + 16, y + 12)]
    pygame.draw.polygon(screen, CYAN, points)
    pygame.draw.polygon(screen, WHITE, points, 2)
    # Cockpit
    pygame.draw.circle(screen, WHITE, (x, y - 4), 4)
    # Engine glow
    glow_h = random.randint(4, 8)
    pygame.draw.polygon(screen, ORANGE, [(x - 6, y + 12), (x, y + 12 + glow_h), (x + 6, y + 12)])

def draw_enemy(x, y, kind=0):
    colors = [GREEN, MAGENTA, ORANGE]
    color = colors[kind % 3]
    # Body
    pygame.draw.rect(screen, color, (x - 14, y - 8, 28, 16), border_radius=4)
    # Eyes
    pygame.draw.circle(screen, WHITE, (x - 5, y - 2), 3)
    pygame.draw.circle(screen, WHITE, (x + 5, y - 2), 3)
    pygame.draw.circle(screen, BLACK, (x - 5, y - 1), 1)
    pygame.draw.circle(screen, BLACK, (x + 5, y - 1), 1)
    # Antennae
    pygame.draw.line(screen, color, (x - 8, y - 8), (x - 12, y - 14), 2)
    pygame.draw.line(screen, color, (x + 8, y - 8), (x + 12, y - 14), 2)

def draw_shield_bar(x, y, current, maximum, color):
    bar_w, bar_h = 100, 10
    pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h), border_radius=3)
    fill = int(bar_w * current / maximum)
    if fill > 0:
        pygame.draw.rect(screen, color, (x, y, fill, bar_h), border_radius=3)
    pygame.draw.rect(screen, WHITE, (x, y, bar_w, bar_h), 1, border_radius=3)

# ─── PARTICLE SYSTEM ────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(15, 35)
        self.color = color
        self.size = random.randint(1, 3)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self):
        alpha = max(0, self.life / 35)
        c = tuple(int(ch * alpha) for ch in self.color)
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.size)

particles = []

def spawn_explosion(x, y, color, count=15):
    for _ in range(count):
        particles.append(Particle(x, y, color))

# ─── GAME OBJECTS ────────────────────────────────────
class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 50
        self.speed = 6
        self.lives = 3
        self.score = 0
        self.shoot_cooldown = 0
        self.invincible = 0  # frames of invincibility after hit

    def update(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x = max(20, self.x - self.speed)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x = min(WIDTH - 20, self.x + self.speed)
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincible > 0:
            self.invincible -= 1

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 12
            play_sound(snd_shoot)
            return Bullet(self.x, self.y - 20, -10)
        return None

    def draw(self):
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return  # blink effect
        draw_player(self.x, self.y)

class Enemy:
    def __init__(self, x, y, kind=0):
        self.x = x
        self.y = y
        self.kind = kind
        self.base_x = x
        self.alive = True
        self.hp = kind + 1
        self.points = (kind + 1) * 100
        self.time = random.uniform(0, 6.28)

    def update(self, direction, speed, move_down):
        self.x += direction * speed
        self.time += 0.05
        if move_down:
            self.y += 20

    def draw(self):
        draw_enemy(int(self.x), int(self.y), self.kind)

    def can_shoot(self):
        return random.random() < 0.002

class Bullet:
    def __init__(self, x, y, vy, color=YELLOW, is_enemy=False):
        self.x = x
        self.y = y
        self.vy = vy
        self.color = color
        self.is_enemy = is_enemy
        self.alive = True

    def update(self):
        self.y += self.vy
        if self.y < -10 or self.y > HEIGHT + 10:
            self.alive = False

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x - 2, self.y - 5, 4, 10), border_radius=2)
        # glow
        glow_surf = pygame.Surface((10, 16), pygame.SRCALPHA)
        glow_color = (*self.color[:3], 50)
        pygame.draw.ellipse(glow_surf, glow_color, (0, 0, 10, 16))
        screen.blit(glow_surf, (self.x - 5, self.y - 8))

# ─── GAME STATE ──────────────────────────────────────
class Game:
    def __init__(self):
        self.state = "menu"  # menu, playing, gameover
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.wave = 0
        self.direction = 1
        self.enemy_speed = 1
        self.move_down = False
        self.wave_clear_timer = 0
        self.high_score = 0
        self.spawn_wave()

    def spawn_wave(self):
        self.wave += 1
        self.enemies.clear()
        rows = min(3 + self.wave // 2, 6)
        cols = min(6 + self.wave // 3, 10)
        self.enemy_speed = 1 + self.wave * 0.3
        self.direction = 1

        start_x = WIDTH // 2 - (cols - 1) * 25
        start_y = 60

        for row in range(rows):
            kind = min(2, row // 2)
            for col in range(cols):
                x = start_x + col * 50
                y = start_y + row * 40
                self.enemies.append(Enemy(x, y, kind))

    def update(self):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys)
        if keys[pygame.K_SPACE]:
            bullet = self.player.shoot()
            if bullet:
                self.bullets.append(bullet)

        # Update bullets
        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # Update enemies
        self.move_down = False
        alive_enemies = [e for e in self.enemies if e.alive]

        if alive_enemies:
            leftmost = min(e.x for e in alive_enemies)
            rightmost = max(e.x for e in alive_enemies)
            if rightmost >= WIDTH - 30 and self.direction == 1:
                self.direction = -1
                self.move_down = True
            elif leftmost <= 30 and self.direction == -1:
                self.direction = 1
                self.move_down = True

            for e in alive_enemies:
                e.update(self.direction, self.enemy_speed, self.move_down)
                # Enemy shooting
                if e.can_shoot():
                    self.bullets.append(Bullet(e.x, e.y + 10, 5, RED, is_enemy=True))
                # Enemy reached bottom
                if e.y >= HEIGHT - 80:
                    self.state = "gameover"
                    self.high_score = max(self.high_score, self.player.score)

        # Collision: player bullets vs enemies
        for b in self.bullets:
            if b.is_enemy or not b.alive:
                continue
            for e in alive_enemies:
                if abs(b.x - e.x) < 18 and abs(b.y - e.y) < 14:
                    b.alive = False
                    e.hp -= 1
                    if e.hp <= 0:
                        e.alive = False
                        self.player.score += e.points
                        spawn_explosion(e.x, e.y, GREEN, 20)
                        play_sound(snd_explosion)
                    else:
                        spawn_explosion(e.x, e.y, YELLOW, 5)
                        play_sound(snd_hit)
                    break

        # Collision: enemy bullets vs player
        if self.player.invincible <= 0:
            for b in self.bullets:
                if not b.is_enemy or not b.alive:
                    continue
                if abs(b.x - self.player.x) < 16 and abs(b.y - self.player.y) < 16:
                    b.alive = False
                    self.player.lives -= 1
                    self.player.invincible = 90
                    spawn_explosion(self.player.x, self.player.y, RED, 25)
                    play_sound(snd_hit)
                    if self.player.lives <= 0:
                        self.state = "gameover"
                        self.high_score = max(self.high_score, self.player.score)
                    break

        # Particles
        for p in particles[:]:
            if not p.update():
                particles.remove(p)

        # Wave cleared
        if not any(e.alive for e in self.enemies):
            self.wave_clear_timer += 1
            if self.wave_clear_timer > 60:
                self.spawn_wave()
                self.wave_clear_timer = 0
        else:
            self.wave_clear_timer = 0

    def draw(self):
        screen.fill(DARK_BG)
        draw_stars()

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "gameover":
            self.draw_gameover()

        # Particles always draw
        for p in particles:
            p.draw()

        pygame.display.flip()

    def draw_menu(self):
        # Title
        title = font_xl.render("SPACE INVADERS", True, CYAN)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 140))

        # Decorative enemies
        for i, cx in enumerate([WIDTH//2 - 80, WIDTH//2, WIDTH//2 + 80]):
            draw_enemy(cx, 280, i)

        # Instructions
        prompt = font_md.render("Press ENTER to Start", True, WHITE)
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 370))

        controls = font_sm.render("Arrow Keys / A-D = Move   |   Space = Shoot", True, (150, 150, 170))
        screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, 430))

        if self.high_score > 0:
            hs = font_sm.render(f"High Score: {self.high_score}", True, YELLOW)
            screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, 480))

    def draw_game(self):
        # Draw enemies
        for e in self.enemies:
            if e.alive:
                e.draw()

        # Draw bullets
        for b in self.bullets:
            b.draw()

        # Draw player
        self.player.draw()

        # HUD
        score_txt = font_md.render(f"Score: {self.player.score}", True, WHITE)
        screen.blit(score_txt, (15, 10))

        wave_txt = font_sm.render(f"Wave {self.wave}", True, CYAN)
        screen.blit(wave_txt, (WIDTH // 2 - wave_txt.get_width() // 2, 12))

        # Lives
        for i in range(self.player.lives):
            draw_player(WIDTH - 30 - i * 35, 22)

        # Wave clear message
        if not any(e.alive for e in self.enemies):
            msg = font_lg.render("WAVE CLEAR!", True, GREEN)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 30))

    def draw_gameover(self):
        over = font_xl.render("GAME OVER", True, RED)
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, 180))

        score = font_lg.render(f"Score: {self.player.score}", True, WHITE)
        screen.blit(score, (WIDTH // 2 - score.get_width() // 2, 290))

        if self.player.score >= self.high_score:
            hs = font_md.render("NEW HIGH SCORE!", True, YELLOW)
            screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, 360))

        restart = font_md.render("Press ENTER to Play Again", True, (180, 180, 200))
        screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, 420))

        menu_txt = font_sm.render("Press ESC for Menu", True, (120, 120, 140))
        screen.blit(menu_txt, (WIDTH // 2 - menu_txt.get_width() // 2, 470))

    def reset(self):
        self.player = Player()
        self.bullets.clear()
        self.enemies.clear()
        self.wave = 0
        self.wave_clear_timer = 0
        particles.clear()
        self.spawn_wave()

# ─── MAIN LOOP ───────────────────────────────────────
def main():
    game = Game()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if game.state == "menu":
                        game.reset()
                        game.state = "playing"
                    elif game.state == "gameover":
                        game.reset()
                        game.state = "playing"
                if event.key == pygame.K_ESCAPE:
                    if game.state == "gameover":
                        game.state = "menu"
                    elif game.state == "playing":
                        game.state = "menu"

        game.update()
        game.draw()
        clock.tick(FPS)

if __name__ == "__main__":
    main()

