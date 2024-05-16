from PodSixNet.Server import Server
from PodSixNet.Channel import Channel
import random
import pygame
import math

# Define colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)

# Define size constants
PLAYER_SIZE = 100
ENEMY_SIZE = 100

# Define damage constants
PROJECTILE_DAMAGE = 10
LASER_DAMAGE = 30


class ClientChannel(Channel):
    def __init__(self, *args, **kwargs):
        self.player = Player(0, 0, PLAYER_SIZE, RED, 300, "", Money())
        Channel.__init__(self, *args, **kwargs)

    def Network_move(self, data):
        self.player.x = data["x"]
        self.player.y = data["y"]
        self.player.name = data["name"]

    def Network_projectile(self, data):
        projectile = Projectile(
            data["x"], data["y"], 5, RED, 400, data["velocity"], data["name"]
        )
        self._server.projectiles.append(projectile)

    def Network_laser_beam(self, data):
        laser_beam = LaserBeam(data["x"], data["y"], 2, RED, 0, data["angle"], 0.5)
        self._server.laser_beams.append(laser_beam)

    def Network_chat(self, data):
        message = data["message"]
        sender = data["sender"]
        self._server.broadcast_chat(message, sender)

    def Close(self):
        self._server.remove_player(self)


class GameServer(Server):
    channelClass = ClientChannel

    def __init__(self, *args, **kwargs):
        self.players = []
        self.enemy = Enemy(
            random.randint(-400, 400),
            random.randint(-400, 400),
            ENEMY_SIZE,
            GREEN,
            100,
            100,
        )
        self.projectiles = []
        self.laser_beams = []
        self.frame_time = 0
        self.clock = pygame.time.Clock()  # Add this line
        Server.__init__(self, *args, **kwargs)
        print("Server launched")

    def Connected(self, channel, addr):
        print(f"New connection: {channel}")
        self.players.append(channel)

    def remove_player(self, player):
        print(f"Player disconnected: {player}")
        self.players.remove(player)

    def distance(self, obj1, obj2):
        return math.sqrt((obj1.x - obj2.x) ** 2 + (obj1.y - obj2.y) ** 2)

    def update(self):
        self.Pump()

        if not self.players:
            return

        nearest_player = min(
            self.players, key=lambda p: self.distance(p.player, self.enemy)
        )
        self.enemy.move(
            self.frame_time, (nearest_player.player.x, nearest_player.player.y)
        )

        if random.random() < 0.01:  # Adjust the probability of shooting
            angle = math.atan2(
                nearest_player.player.y - self.enemy.y,
                nearest_player.player.x - self.enemy.x,
            )
            velocity = [math.cos(angle) * 400, math.sin(angle) * 400]
            projectile = Projectile(
                self.enemy.x + self.enemy.size // 2,
                self.enemy.y + self.enemy.size // 2,
                5,
                RED,
                400,
                velocity,
                "enemy",
            )
            self.projectiles.append(projectile)

        for projectile in self.projectiles:
            projectile.move(self.frame_time)

            if projectile.owner == "enemy":
                for player in self.players:
                    if (
                        player.player.x
                        < projectile.x
                        < player.player.x + player.player.size
                        and player.player.y
                        < projectile.y
                        < player.player.y + player.player.size
                    ):
                        player.player.health -= PROJECTILE_DAMAGE
                        self.projectiles.remove(projectile)
                        break
            elif self.enemy.color != RED:
                if (
                    self.enemy.x < projectile.x < self.enemy.x + self.enemy.size
                    and self.enemy.y < projectile.y < self.enemy.y + self.enemy.size
                ):
                    self.enemy.hit_projectile()
                    self.projectiles.remove(projectile)

                    if self.enemy.health <= 0:
                        self.players[0].player.money.gain(100)
                        self.enemy.respawn(
                            (self.players[0].player.x, self.players[0].player.y)
                        )
                        self.enemy.health = 100

        for laser_beam in self.laser_beams:
            laser_beam.move()

            if laser_beam.check_collision((self.enemy.x, self.enemy.y)):
                self.enemy.hit_laser()

                if self.enemy.health <= 0:
                    self.players[0].player.money.gain(100)
                    self.enemy.respawn(
                        (self.players[0].player.x, self.players[0].player.y)
                    )
                    self.enemy.health = 100

            if laser_beam.is_faded():
                self.laser_beams.remove(laser_beam)

        self.enemy.update(self.frame_time)

        self.projectiles = [
            p
            for p in self.projectiles
            if abs(p.x - self.players[0].player.x) <= 1000
            and abs(p.y - self.players[0].player.y) <= 1000
        ]

        game_state = {
            "players": [
                {
                    "x": player.player.x,
                    "y": player.player.y,
                    "money": player.player.money.amount,
                    "has_laser_beam": player.player.has_laser_beam,
                    "name": player.player.name,
                    "health": player.player.health,
                }
                for player in self.players
            ],
            "enemy": {
                "x": self.enemy.x,
                "y": self.enemy.y,
                "color": self.enemy.color,
                "health": self.enemy.health,
            },
            "projectiles": [
                {"x": projectile.x, "y": projectile.y, "name": projectile.owner}
                for projectile in self.projectiles
            ],
            "laser_beams": [
                {
                    "start_point": laser_beam.start_point,
                    "angle": laser_beam.angle,
                }
                for laser_beam in self.laser_beams
            ],
        }

        self.send_to_all(game_state)

    def send_to_all(self, data):
        for player in self.players:
            player.Send({"action": "game_state", "data": data})

    def broadcast_chat(self, message, sender):
        for player in self.players:
            if player.player.name != sender:
                player.Send({"action": "chat", "message": message, "sender": sender})


class GameObject:
    def __init__(self, x, y, size, color, speed):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.speed = speed

    def draw(self, screen, offset_x, offset_y):
        pygame.draw.rect(
            screen,
            self.color,
            (int(self.x - offset_x), int(self.y - offset_y), self.size, self.size),
        )


class Player(GameObject):
    def __init__(self, x, y, size, color, speed, name, money, health=100):
        super().__init__(x, y, size, color, speed)
        self.name = name
        self.has_laser_beam = False
        self.money = money
        self.health = health


class Enemy(GameObject):
    def __init__(self, x, y, size, color, speed, minimap_radius, health=100):
        super().__init__(x, y, size, color, speed)
        self.hit_timer = 0
        self.minimap_radius = minimap_radius
        self.health = health

    def move(self, dt, player_pos):
        if self.x < player_pos[0]:
            self.x += self.speed * dt
        if self.x > player_pos[0]:
            self.x -= self.speed * dt
        if self.y < player_pos[1]:
            self.y += self.speed * dt
        if self.y > player_pos[1]:
            self.y -= self.speed * dt

    def hit_projectile(self):
        self.health -= PROJECTILE_DAMAGE
        self.hit_timer = 30
        self.color = RED

    def hit_laser(self):
        self.health -= LASER_DAMAGE
        self.hit_timer = 30
        self.color = RED

    def respawn(self, player_pos):
        minimap_left = player_pos[0] - self.minimap_radius
        minimap_right = player_pos[0] + self.minimap_radius
        minimap_top = player_pos[1] - self.minimap_radius
        minimap_bottom = player_pos[1] + self.minimap_radius

        while True:
            self.x = player_pos[0] + random.randint(-1000, 1000)
            self.y = player_pos[1] + random.randint(-1000, 1000)

            if (
                self.x < minimap_left
                or self.x > minimap_right
                or self.y < minimap_top
                or self.y > minimap_bottom
            ):
                break

        self.color = GREEN
        self.hit_count = 0
        self.hit_timer = 0

    def update(self, dt):
        if self.hit_timer > 0:
            self.hit_timer -= 1
            if self.hit_timer == 0:
                self.color = GREEN


class Projectile(GameObject):
    def __init__(self, x, y, size, color, speed, velocity, owner):
        super().__init__(x, y, size, color, speed)
        self.velocity = velocity
        self.owner = owner

    def move(self, dt):
        self.x += self.velocity[0] * dt
        self.y += self.velocity[1] * dt


class Money:
    def __init__(self):
        self.amount = 0

    def gain(self, amount):
        self.amount += amount


class LaserBeam(GameObject):
    def __init__(self, x, y, size, color, speed, angle, fade_duration):
        super().__init__(x, y, size, color, speed)
        self.angle = angle
        self.fade_duration = fade_duration * 1000
        self.fade_timer = 0
        self.spawn_time = pygame.time.get_ticks()
        self.start_point = (x, y)
        self.end_point = (x + math.cos(angle) * 1000, y + math.sin(angle) * 1000)

    def move(self):
        current_time = pygame.time.get_ticks()
        self.fade_timer = current_time - self.spawn_time

    def is_faded(self):
        return self.fade_timer > self.fade_duration

    def check_collision(self, point):
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        x0, y0 = point

        dn = (x0 - x2) * (x1 - x2) + (y0 - y2) * (y1 - y2)
        dd = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)
        cx = (dn / dd) * (x1 - x2)
        cy = (dn / dd) * (y1 - y2)
        ex = (x0 - x2) - cx
        ey = (y0 - y2) - cy

        d = math.sqrt(ex**2 + ey**2)

        if d < ENEMY_SIZE:
            return True
        return False


def main():
    server = GameServer(localaddr=("0.0.0.0", 12345))

    while True:
        server.frame_time = server.clock.tick(60) / 1000.0
        server.update()


if __name__ == "__main__":
    main()
