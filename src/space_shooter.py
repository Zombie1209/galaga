import pygame
import sqlite3
import sys
import random

# Constants
SCREEN_W, SCREEN_H = 800, 600
FPS = 60
TITLE = "Space Shooter"

C_BLACK  = (  0,   0,   0)
C_WHITE  = (255, 255, 255)
C_GRAY   = (100, 100, 120)
C_DARK   = (  8,   8,  25)
C_CYAN   = (  0, 210, 235)
C_RED    = (215,  45,  45)
C_ORANGE = (255, 135,   0)
C_GREEN  = ( 60, 210,  90)
C_YELLOW = (255, 215,   0)

PLAYER_SPEED  = 5
BULLET_SPD_P  = 9
BULLET_SPD_E  = 4
SHOOT_CD      = 280     # ms between player shots
PLAYER_LIVES  = 3
WAVE_BONUS    = 150     # bonus pts for clearing a wave

# Wave configs: [rows, cols]
WAVES = [
    [2, 5],
    [3, 5],
    [4, 6]
]

# DatabaseLogger
class DatabaseLogger:
    def __init__(self, path: str = "scores.db"):
        self._conn = sqlite3.connect(path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                score INTEGER NOT NULL,
                won   INTEGER NOT NULL DEFAULT 0,
                ts    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def save(self, name: str, score: int, won: bool) -> None:
        self._conn.execute(
            "INSERT INTO scores (name, score, won) VALUES (?, ?, ?)",
            (name, score, int(won))
        )
        self._conn.commit()

    def top5(self) -> list:
        cur = self._conn.execute(
            "SELECT name, score, won FROM scores ORDER BY score DESC LIMIT 5"
        )
        return cur.fetchall()

    def close(self) -> None:
        self._conn.close()


# Bullet
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int, direction: int,
                 color: tuple, speed: int):
        super().__init__()
        self.direction = direction
        self.speed = speed
        self.image = pygame.Surface((4, 12))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.y += self.direction * self.speed
        if self.rect.bottom < 0 or self.rect.top > SCREEN_H:
            self.kill()


# Player
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.image.load("assets/player.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (50, 54))
        self.rect  = self.image.get_rect(center=(SCREEN_W // 2, SCREEN_H - 80))
        self.lives      = PLAYER_LIVES
        self.score      = 0
        self._last_shot = 0

    def handle_input(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]:  dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx =  PLAYER_SPEED
        if keys[pygame.K_UP]:    dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy =  PLAYER_SPEED
        self.rect.move_ip(dx, dy)
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))

    def shoot(self, now: int) -> "Bullet | None":
        if now - self._last_shot >= SHOOT_CD:
            self._last_shot = now
            return Bullet(self.rect.centerx, self.rect.top + 4,
                          -1, C_CYAN, BULLET_SPD_P)
        return None

    def take_hit(self):
        self.lives -= 1


# Enemy
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int, wave: int):
        super().__init__()
        self.wave    = wave
        self.hp      = wave + 1
        self.pts     = 10 * (wave + 1)
        self.shoot_p = 0.001 + (wave * 0.001)  # Scales based on wave
        
        self.image = pygame.image.load("assets/enemy.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (44, 40))
        self._base   = self.image.copy()
        self.rect    = self.image.get_rect(topleft=(x, y))

    def try_shoot(self) -> "Bullet | None":
        if random.random() < self.shoot_p:
            return Bullet(self.rect.centerx, self.rect.bottom,
                          +1, C_RED, BULLET_SPD_E)
        return None

    def take_hit(self) -> bool:
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
            return True
        flash = pygame.Surface(self._base.get_size(), pygame.SRCALPHA)
        flash.fill((255, 255, 255, 160))
        self.image = self._base.copy()
        self.image.blit(flash, (0, 0))
        return False


# Game
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock  = pygame.time.Clock()
        self.db     = DatabaseLogger()
        self.name   = ""

        self.font = pygame.font.SysFont("arial", 32)
        self.small = pygame.font.SysFont("arial", 20)

    # Internal draw helpers
    def _bg(self):
        self.screen.fill(C_DARK)

    def _txt(self, text, font, color, cx, cy):
        s = font.render(str(text), True, color)
        self.screen.blit(s, s.get_rect(center=(cx, cy)))

    def _txt_l(self, text, font, color, x, y):
        self.screen.blit(font.render(str(text), True, color), (x, y))

    def _quit(self, event):
        if event.type == pygame.QUIT:
            self.db.close()
            pygame.quit()
            sys.exit()

    def _draw_hud(self, player, wave):
        self._txt_l(f"Lives: {player.lives}", self.small, C_WHITE, 10, 10)
        self._txt_l(f"Score: {player.score}", self.small, C_WHITE, 10, 40)
        self._txt_l(f"Wave: {wave + 1}", self.small, C_WHITE, 650, 10)

    # Screen 1: Name Entry
    def screen_name_entry(self):
        name  = ""
        error = ""
        blink = True
        bt    = 0

        while True:
            now = pygame.time.get_ticks()
            if now - bt > 530:
                blink = not blink
                bt = now

            for e in pygame.event.get():
                self._quit(e)
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        n = name.strip()
                        if len(n) < 2:
                            error = "At least 2 characters, pilot!"
                        elif len(n) > 16:
                            error = "Max 16 characters."
                        else:
                            self.name = n
                            return
                    elif e.key == pygame.K_BACKSPACE:
                        name = name[:-1]; error = ""
                    elif e.unicode.isprintable() and len(name) < 16:
                        name += e.unicode; error = ""

            self._bg()
            self._txt("SPACE  SHOOTER", self.font, C_CYAN,  SCREEN_W // 2, 72)
            self._txt("Enter your callsign, pilot:",
                      self.small, C_WHITE, SCREEN_W // 2, 162)

            box = pygame.Rect(SCREEN_W // 2 - 200, 188, 400, 52)
            pygame.draw.rect(self.screen, (18, 18, 55), box, border_radius=8)
            pygame.draw.rect(self.screen, C_CYAN,       box, 2, border_radius=8)
            self._txt(name + ("|" if blink else " "),
                      self.small, C_WHITE, SCREEN_W // 2, 215)

            self._txt("Press ENTER to confirm",
                      self.small, C_GRAY, SCREEN_W // 2, 264)
            if error:
                self._txt(error, self.small, C_RED, SCREEN_W // 2, 300)

            pygame.display.flip()
            self.clock.tick(FPS)

    # Screen 2: Main Menu
    def screen_main_menu(self):
        while True:
            for e in pygame.event.get():
                self._quit(e)
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return
                    if e.key == pygame.K_ESCAPE:
                        self.db.close(); pygame.quit(); sys.exit()

            self._bg()
            self._txt("SPACE  SHOOTER", self.font, C_CYAN, SCREEN_W // 2, 95)
            self._txt(f"Welcome aboard, {self.name}!",
                      self.small, C_YELLOW, SCREEN_W // 2, 148)

            rows = [
                (220, "ARROWS - MOVE", C_WHITE),
                (260, "SPACE - SHOOT", C_WHITE),
                (320, "DESTROY ALL ENEMIES", C_WHITE),
            ]
            for y, txt, col in rows:
                self._txt(txt, self.small, col, SCREEN_W // 2, y)

            self._txt("PRESS SPACE", self.small, C_CYAN, SCREEN_W // 2, 500)

            pygame.display.flip()
            self.clock.tick(FPS)

    # Screen 3: Gameplay
    def screen_gameplay(self):
        player         = Player()
        player_bullets = pygame.sprite.Group()
        enemy_bullets  = pygame.sprite.Group()
        enemies        = pygame.sprite.Group()

        wave     = 0
        enemy_dx = 1 + wave
        wave_ts  = [pygame.time.get_ticks()]

        def spawn_wave(w: int):
            nonlocal enemy_dx
            enemies.empty()
            enemy_bullets.empty()
            enemy_dx = 1 + w
            wave_ts[0] = pygame.time.get_ticks()
            rows = WAVES[w][0]
            cols = WAVES[w][1]
            x_start = (SCREEN_W - cols * 72) // 2
            for r in range(rows):
                for c in range(cols):
                    e = Enemy(x_start + c * 72, 70 + r * 64, w)
                    enemies.add(e)

        spawn_wave(0)
        won = False
        
        while True:
            now = pygame.time.get_ticks()
            self.clock.tick(FPS)

            # Events
            for e in pygame.event.get():
                self._quit(e)
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    return False, player.score

            keys = pygame.key.get_pressed()
            player.handle_input(keys)

            if keys[pygame.K_SPACE]:
                b = player.shoot(now)
                if b:
                    player_bullets.add(b)

            # Enemy group movement
            if enemies:
                left_edge  = min(e.rect.left  for e in enemies)
                right_edge = max(e.rect.right for e in enemies)
                if right_edge >= SCREEN_W - 8 or left_edge <= 8:
                    enemy_dx = -enemy_dx
                    for en in enemies:
                        en.rect.y += 18
                for en in enemies:
                    en.rect.x += enemy_dx
                    b = en.try_shoot()
                    if b:
                        enemy_bullets.add(b)

            # Bullet updates
            player_bullets.update()
            enemy_bullets.update()

            # Collision: player bullets → enemies
            hits = pygame.sprite.groupcollide(enemies, player_bullets,
                                              False, True)
            for en in hits:
                if en.take_hit():
                    player.score += en.pts

            # Collision: enemy bullets → player
            if pygame.sprite.spritecollide(player, enemy_bullets, True):
                player.take_hit()

            # Enemy reaches bottom → instant loss
            for en in enemies:
                if en.rect.bottom >= SCREEN_H - 10:
                    player.lives = 0

            # Check lose
            if player.lives <= 0:
                won = False
                break

            # Check wave cleared
            if not enemies:
                player.score += WAVE_BONUS
                wave += 1
                if wave >= len(WAVES):
                    won = True
                    break
                spawn_wave(wave)

            # Draw
            self._bg()
            enemies.draw(self.screen)
            player_bullets.draw(self.screen)
            enemy_bullets.draw(self.screen)
            self.screen.blit(player.image, player.rect)
            self._draw_hud(player, wave)

            # Controls hint
            if wave == 0 and now - wave_ts[0] < 5000:
                hint = "ARROWS: Move | SPACE: Shoot | Destroy all aliens!"
                self._txt(hint, self.small, C_GRAY, SCREEN_W // 2, SCREEN_H - 18)

            # Wave banners
            if now - wave_ts[0] < 2500:
                banners = [
                    "Wave 1",
                    "Wave 2",
                    "Wave 3 - FINAL",
                ]
                self._txt(banners[wave], self.small, C_YELLOW,
                          SCREEN_W // 2, SCREEN_H // 2)

            pygame.display.flip()

        return won, player.score

    # Screen 4: Result
    def screen_result(self, won: bool, score: int):
        self.db.save(self.name, score, won)

        while True:
            for e in pygame.event.get():
                self._quit(e)
                if e.type == pygame.KEYDOWN and \
                        e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return

            self._bg()

            if won:
                self._txt("YOU WIN", self.font, C_GREEN, SCREEN_W // 2, 200)
            else:
                self._txt("GAME OVER", self.font, C_RED, SCREEN_W // 2, 200)

            self._txt(f"Score: {score}", self.small, C_WHITE, SCREEN_W // 2, 280)
            self._txt("Press SPACE", self.small, C_WHITE, SCREEN_W // 2, 340)

            pygame.display.flip()
            self.clock.tick(FPS)

    # Screen 5: Leaderboard
    def screen_leaderboard(self):
        records = self.db.top5()

        while True:
            for e in pygame.event.get():
                self._quit(e)
                if e.type == pygame.KEYDOWN and e.key in (
                        pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    return

            self._bg()
            self._txt("TOP 5 PILOTS", self.font, C_CYAN, SCREEN_W // 2, 120)

            if not records:
                self._txt("No scores on record yet!",
                          self.small, C_GRAY, SCREEN_W // 2, 290)
            else:
                for i, (name, sc, won_flag) in enumerate(records):
                    text = f"{i+1}. {name} - {sc}"
                    self._txt(text, self.small, C_WHITE, SCREEN_W // 2, 180 + i * 40)

            self._txt("SPACE / ENTER -> Play again",
                      self.small, C_GRAY, SCREEN_W // 2, 560)

            pygame.display.flip()
            self.clock.tick(FPS)

    # Main entry point
    def run(self):
        self.screen_name_entry()
        while True:
            self.screen_main_menu()
            won, score = self.screen_gameplay()
            self.screen_result(won, score)
            self.screen_leaderboard()

