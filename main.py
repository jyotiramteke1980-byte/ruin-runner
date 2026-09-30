import math
import random
import sys

import pygame


pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 960, 640
FPS = 60

TITLE_OPTIONS = ["Ruin Runner", "Ancient Escape", "Cursed Sprint", "Artifact Chase"]
ACTIVE_SKILLS = {
    "shield": "Shield",
    "magnet": "Magnet",
    "boost": "Speed Burst",
    "slow": "Slow Time",
}

ROAD_LEFT = 240
ROAD_RIGHT = 720
LANE_X = [ROAD_LEFT + (ROAD_RIGHT - ROAD_LEFT) * (i / 2 + 0.25) for i in range(3)]

COLORS = {
    "bg_top": (16, 18, 28),
    "bg_bottom": (38, 30, 22),
    "road": (38, 38, 42),
    "road_edge": (200, 160, 100),
    "player": (112, 203, 255),
    "player_dark": (52, 99, 141),
    "enemy": (128, 18, 38),
    "gold": (246, 201, 66),
    "shield": (86, 177, 255),
    "magnet": (149, 104, 255),
    "boost": (255, 164, 76),
    "slow": (120, 225, 165),
    "ui": (245, 245, 255),
    "danger": (255, 90, 90),
    "hit": (255, 207, 94),
}


class Player:
    def __init__(self):
        self.lane = 1
        self.target_lane = 1
        self.screen_x = LANE_X[1]
        self.y = HEIGHT - 170
        self.vy = 0
        self.jump_strength = 650
        self.gravity = 1700
        self.slide_timer = 0
        self.health = 3
        self.score = 0
        self.shield_timer = 0
        self.magnet_timer = 0
        self.boost_timer = 0
        self.slow_timer = 0
        self.invincible_timer = 0
        self.flash_timer = 0
        self.hit_sfx_timer = 0

    @property
    def is_jumping(self):
        return self.y < HEIGHT - 170

    def set_lane(self, direction):
        self.target_lane = max(0, min(2, self.target_lane + direction))

    def jump(self):
        if self.slide_timer <= 0 and not self.is_jumping:
            self.vy = -self.jump_strength

    def slide(self):
        if not self.is_jumping:
            self.slide_timer = 0.55

    def update(self, dt):
        self.screen_x += (LANE_X[self.target_lane] - self.screen_x) * min(1.0, 12 * dt)
        if self.is_jumping:
            self.y += self.vy * dt
            self.vy += self.gravity * dt
            if self.y >= HEIGHT - 170:
                self.y = HEIGHT - 170
                self.vy = 0
        if self.slide_timer > 0:
            self.slide_timer -= dt
        self.shield_timer = max(0, self.shield_timer - dt)
        self.magnet_timer = max(0, self.magnet_timer - dt)
        self.boost_timer = max(0, self.boost_timer - dt)
        self.slow_timer = max(0, self.slow_timer - dt)
        self.invincible_timer = max(0, self.invincible_timer - dt)
        self.flash_timer = max(0, self.flash_timer - dt)
        self.hit_sfx_timer = max(0, self.hit_sfx_timer - dt)

    def hurt(self):
        if self.invincible_timer > 0 or self.shield_timer > 0:
            self.invincible_timer = 1.0
            self.shield_timer = 0
            return False
        self.health -= 1
        self.flash_timer = 0.3
        self.invincible_timer = 1.2
        return True


class Obstacle:
    def __init__(self, lane, kind, z):
        self.lane = lane
        self.kind = kind
        self.z = z


class Pickup:
    def __init__(self, lane, kind, z):
        self.lane = lane
        self.kind = kind
        self.z = z
        self.bob = random.uniform(0, math.tau)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.big_font = pygame.font.SysFont("arial", 54, bold=True)
        self.small_font = pygame.font.SysFont("arial", 20, bold=True)
        self.title_font = pygame.font.SysFont("arial", 72, bold=True)
        self.state = "menu"
        self.player = Player()
        self.obstacles = []
        self.pickups = []
        self.spawn_timer = 1.2
        self.pickup_timer = 4.5
        self.enemy_distance = 200
        self.base_speed = 360
        self.game_speed = self.base_speed
        self.score = 0
        self.best_score = 0
        self.title = random.choice(TITLE_OPTIONS)

    def reset(self):
        self.player = Player()
        self.obstacles = []
        self.pickups = []
        self.spawn_timer = 1.1
        self.pickup_timer = 4.5
        self.enemy_distance = 200
        self.base_speed = 360
        self.game_speed = self.base_speed
        self.score = 0
        self.title = random.choice(TITLE_OPTIONS)

    def start_game(self):
        self.reset()
        self.state = "playing"

    def spawn_obstacle(self):
        lane = random.randint(0, 2)
        kind = random.choice(["barrier", "pit", "low"])
        self.obstacles.append(Obstacle(lane, kind, 1500))

    def spawn_pickup(self):
        lane = random.randint(0, 2)
        kind = random.choice(["shield", "magnet", "boost", "slow"])
        self.pickups.append(Pickup(lane, kind, 1400))

    def collect_pickup(self, pickup):
        if pickup.kind == "shield":
            self.player.shield_timer = 8.0
        elif pickup.kind == "magnet":
            self.player.magnet_timer = 8.0
        elif pickup.kind == "boost":
            self.player.boost_timer = 5.0
        elif pickup.kind == "slow":
            self.player.slow_timer = 5.0
        self.pickups.remove(pickup)
        self.score += 100

    def handle_collision(self, obstacle):
        if obstacle.lane != self.player.target_lane:
            return

        if obstacle.kind == "barrier":
            if self.player.is_jumping:
                return
        elif obstacle.kind == "pit":
            if self.player.is_jumping:
                return
        elif obstacle.kind == "low":
            if self.player.slide_timer > 0:
                return

        if self.player.shield_timer > 0:
            self.player.shield_timer = 0
            self.player.invincible_timer = 1.2
            self.obstacles.remove(obstacle)
            self.score += 75
            return

        if self.player.invincible_timer > 0:
            self.obstacles.remove(obstacle)
            return

        if self.player.hurt():
            self.enemy_distance = max(18, self.enemy_distance - 40)
            self.obstacles.remove(obstacle)
            if self.player.health <= 0:
                self.state = "gameover"
                self.best_score = max(self.best_score, int(self.score))

    def update(self, dt):
        if self.state != "playing":
            return

        self.score += dt * 20
        self.player.update(dt)

        world_speed = self.game_speed * (0.58 if self.player.slow_timer > 0 else 1.0)
        if self.player.boost_timer > 0:
            world_speed *= 1.45

        self.game_speed = self.base_speed + self.score * 1.6
        self.enemy_distance -= dt * (24 + self.score * 0.04)
        if self.enemy_distance <= 0:
            self.state = "gameover"
            self.best_score = max(self.best_score, int(self.score))

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_obstacle()
            self.spawn_timer = max(0.8, 1.45 - self.score * 0.006)

        self.pickup_timer -= dt
        if self.pickup_timer <= 0:
            self.spawn_pickup()
            self.pickup_timer = random.uniform(5.0, 9.0)

        for pickup in list(self.pickups):
            pickup.z -= world_speed * dt
            if pickup.lane == self.player.target_lane and pickup.z <= 90 and pickup.z >= 10:
                self.collect_pickup(pickup)
            if pickup.z < -80:
                self.pickups.remove(pickup)

        for obstacle in list(self.obstacles):
            obstacle.z -= world_speed * dt
            if obstacle.lane == self.player.target_lane and obstacle.z <= 100 and obstacle.z >= -20:
                self.handle_collision(obstacle)
            if obstacle.z < -120:
                self.obstacles.remove(obstacle)

        if self.player.magnet_timer > 0:
            for pickup in self.pickups:
                if pickup.lane != self.player.target_lane and abs(pickup.z - 60) < 500:
                    pickup.lane = self.player.target_lane

    def draw_road(self, surf):
        horizon_y = 130
        road_top_y = 155
        road_bottom_y = HEIGHT
        points = [
            (ROAD_LEFT, road_top_y),
            (ROAD_RIGHT, road_top_y),
            (WIDTH - 70, road_bottom_y),
            (70, road_bottom_y),
        ]
        pygame.draw.polygon(surf, COLORS["road"], points)
        edge_color = COLORS["road_edge"]
        for i in range(1, 3):
            x = ROAD_LEFT + (ROAD_RIGHT - ROAD_LEFT) * (i / 3)
            pygame.draw.line(surf, edge_color, (x, road_top_y), (x, road_bottom_y), 3)
        for i in range(1, 9):
            y = int(road_top_y + (road_bottom_y - road_top_y) * (i / 9))
            pygame.draw.line(surf, (85, 85, 90), (ROAD_LEFT, y), (ROAD_RIGHT, y), 1)

    def draw_background(self, surf):
        gradient = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            color = (
                int(COLORS["bg_top"][0] * (1 - ratio) + COLORS["bg_bottom"][0] * ratio),
                int(COLORS["bg_top"][1] * (1 - ratio) + COLORS["bg_bottom"][1] * ratio),
                int(COLORS["bg_top"][2] * (1 - ratio) + COLORS["bg_bottom"][2] * ratio),
            )
            pygame.draw.line(gradient, color, (0, y), (WIDTH, y))
        surf.blit(gradient, (0, 0))

        for i in range(5):
            x = 50 + i * 170
            y = 80 + (i % 2) * 20
            pygame.draw.polygon(surf, (75, 70, 68), [(x, y), (x + 30, y - 50), (x + 60, y)])

    def draw_pickups(self, surf):
        for pickup in self.pickups:
            depth = 1 - (pickup.z / 1500)
            x = LANE_X[pickup.lane]
            y = int(140 + (1 - depth) * 400)
            size = int(14 + depth * 22)
            color = COLORS[pickup.kind]
            if pickup.kind == "shield":
                pygame.draw.circle(surf, color, (x, y), size, 3)
                pygame.draw.circle(surf, color, (x, y), size - 6, 2)
            elif pickup.kind == "magnet":
                pygame.draw.rect(surf, color, (x - size, y - size, size * 2, size * 2), 3)
                pygame.draw.line(surf, color, (x - size, y), (x + size, y), 3)
            elif pickup.kind == "boost":
                pygame.draw.polygon(surf, color, [(x, y - size), (x + size, y), (x, y + size), (x - size, y)])
            elif pickup.kind == "slow":
                pygame.draw.circle(surf, color, (x, y), size, 3)
                pygame.draw.line(surf, color, (x, y - size), (x, y + size), 3)

    def draw_obstacles(self, surf):
        for obstacle in self.obstacles:
            depth = 1 - (obstacle.z / 1500)
            x = LANE_X[obstacle.lane]
            y = int(180 + (1 - depth) * 360)
            scale = 1 + depth * 1.6
            if obstacle.kind == "barrier":
                rect = pygame.Rect(x - 34 * scale, y - 28 * scale, 68 * scale, 60 * scale)
                pygame.draw.rect(surf, (80, 95, 110), rect)
                pygame.draw.rect(surf, (243, 154, 74), rect.inflate(-10, -10))
            elif obstacle.kind == "pit":
                rect = pygame.Rect(x - 38 * scale, y - 14 * scale, 76 * scale, 56 * scale)
                pygame.draw.rect(surf, (20, 22, 30), rect)
                pygame.draw.line(surf, (60, 80, 90), (x - 42 * scale, y + 10 * scale), (x + 42 * scale, y + 10 * scale), 4)
            elif obstacle.kind == "low":
                rect = pygame.Rect(x - 52 * scale, y - 8 * scale, 104 * scale, 34 * scale)
                pygame.draw.rect(surf, (160, 87, 68), rect)

    def draw_player(self, surf):
        x = int(self.player.screen_x)
        y = int(self.player.y)
        if self.player.flash_timer > 0:
            color = (255, 224, 130)
        else:
            color = COLORS["player"]
        body_rect = pygame.Rect(x - 28, y - 26, 56, 52)
        if self.player.slide_timer > 0:
            body_rect = pygame.Rect(x - 34, y - 8, 68, 32)
        if self.player.is_jumping:
            body_rect = pygame.Rect(x - 22, y - 40, 44, 56)

        if self.player.shield_timer > 0:
            pygame.draw.circle(surf, (90, 190, 255), (x, y - 18), 42, 5)
        if self.player.invincible_timer > 0:
            pygame.draw.circle(surf, (255, 210, 112), (x, y - 18), 46, 3)

        pygame.draw.rect(surf, color, body_rect)
        pygame.draw.circle(surf, (250, 250, 250), (x, y - 44), 18)
        pygame.draw.rect(surf, COLORS["player_dark"], (x - 10, y + 18, 20, 20))

    def draw_enemy(self, surf):
        enemy_screen = max(0.1, self.enemy_distance / 200)
        x = WIDTH // 2
        y = HEIGHT - 70 + (1 - enemy_screen) * 70
        width = 110 + (1 - enemy_screen) * 40
        height = 72 + (1 - enemy_screen) * 50
        enemy_rect = pygame.Rect(int(x - width / 2), int(y - height / 2), int(width), int(height))
        pygame.draw.rect(surf, COLORS["enemy"], enemy_rect)
        eye_y = enemy_rect.centery - 8
        pygame.draw.circle(surf, (0, 0, 0), (enemy_rect.centerx - 16, eye_y), 6)
        pygame.draw.circle(surf, (0, 0, 0), (enemy_rect.centerx + 16, eye_y), 6)
        pygame.draw.line(surf, (20, 20, 20), (enemy_rect.left + 18, enemy_rect.bottom - 8), (enemy_rect.right - 18, enemy_rect.bottom - 8), 5)

    def draw_hud(self, surf):
        score_label = self.font.render(f"Score: {int(self.score)}", True, COLORS["ui"])
        surf.blit(score_label, (20, 20))

        health_text = self.font.render("Lives: " + "♥ " * self.player.health, True, COLORS["danger"])
        surf.blit(health_text, (20, 58))

        active = []
        for key, name in ACTIVE_SKILLS.items():
            timer = getattr(self.player, key + "_timer")
            if timer > 0:
                active.append(f"{name} {timer:.1f}s")
        if active:
            active_text = self.font.render(" | ".join(active), True, COLORS["ui"])
            surf.blit(active_text, (WIDTH - 360, 20))

        enemy_label = self.small_font.render(f"Enemy Distance: {max(0, int(self.enemy_distance))}m", True, COLORS["hit"])
        surf.blit(enemy_label, (WIDTH - 260, HEIGHT - 36))

    def draw_menu(self, surf):
        surf.fill((12, 16, 24))
        title = self.title_font.render(self.title, True, (246, 205, 88))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 140))

        subtitle = self.small_font.render("Temple Run-inspired endless runner", True, (220, 220, 230))
        surf.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 225))

        instructions = [
            "A / D or Left / Right: change lane",
            "W / Up: jump",
            "S / Down: slide",
            "Space: activate your active skill",
            "Enter: start the run",
        ]
        for i, line in enumerate(instructions):
            label = self.font.render(line, True, (240, 240, 240))
            surf.blit(label, (WIDTH // 2 - label.get_width() // 2, 290 + i * 38))

        tag = self.font.render("Enemy: Shadow Guardian | Skills: Shield, Magnet, Speed Burst, Slow Time", True, (128, 218, 255))
        surf.blit(tag, (WIDTH // 2 - tag.get_width() // 2, 520))

    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))

        game_over = self.big_font.render("Run Failed", True, (255, 125, 125))
        surf.blit(game_over, (WIDTH // 2 - game_over.get_width() // 2, 180))

        summary = self.font.render(f"Score: {int(self.score)}   Best: {self.best_score}", True, (255, 255, 255))
        surf.blit(summary, (WIDTH // 2 - summary.get_width() // 2, 250))

        restart = self.font.render("Press Enter to restart", True, (244, 223, 128))
        surf.blit(restart, (WIDTH // 2 - restart.get_width() // 2, 315))

    def draw(self):
        self.draw_background(self.screen)
        self.draw_road(self.screen)
        self.draw_pickups(self.screen)
        self.draw_obstacles(self.screen)
        self.draw_enemy(self.screen)
        self.draw_player(self.screen)
        self.draw_hud(self.screen)

        if self.state == "menu":
            self.draw_menu(self.screen)
        elif self.state == "gameover":
            self.draw_gameover(self.screen)

        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    sys.exit()
                if self.state == "menu" and event.key == pygame.K_RETURN:
                    self.start_game()
                    return
                if self.state == "gameover" and event.key == pygame.K_RETURN:
                    self.start_game()
                    return

                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.player.set_lane(-1)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.player.set_lane(1)
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.player.jump()
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self.player.slide()
                if event.key == pygame.K_SPACE:
                    if self.player.boost_timer > 0:
                        self.game_speed += 150
                    elif self.player.shield_timer > 0:
                        self.player.shield_timer = 8
                    elif self.player.magnet_timer > 0:
                        self.player.magnet_timer = 8
                    elif self.player.slow_timer > 0:
                        self.player.slow_timer = 5
                    else:
                        self.player.boost_timer = 2.0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.events()
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    game = Game()
    game.run()
