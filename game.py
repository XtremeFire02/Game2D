import pygame
import random
import math
from PodSixNet.Connection import ConnectionListener, connection

DEBUG_MODE = True
BORDERLESS_FULLSCREEN = False
WINDOWED = True

# Initialize Pygame
pygame.init()
width = 0
height = 0
screen = None

if BORDERLESS_FULLSCREEN:
    info = pygame.display.Info()
    width = info.current_w
    height = info.current_h
    screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
    pygame.display.set_caption("Untitled Game")

if WINDOWED:
    width = 800
    height = 600
    screen = pygame.display.set_mode((width, height), pygame.SHOWN)
    pygame.display.set_caption("Untitled Game")


# Define colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)

# Define font
font = pygame.font.Font(None, 36)

# Define size constants
PLAYER_SIZE = 100
ENEMY_SIZE = 100
LASER_BEAM_SIZE = 2
LASER_FADE_DURATION = 0.5

# Define damage constants
PROJECTILE_DAMAGE = 10
LASER_DAMAGE = 30


class GameObject:
    def __init__(self, x, y, size, color, speed, sprite_path=None, frame_images=None):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.speed = speed
        self.sprite_path = sprite_path
        self.frame_images = frame_images
        self.animation_frames = []
        self.current_frame = 0
        self.animation_speed = 0.2
        self.elapsed_time = 0

        if self.sprite_path:
            self.sprite = pygame.image.load(sprite_path).convert_alpha()
            self.sprite = pygame.transform.smoothscale(self.sprite, (size, size))
        elif self.frame_images:
            for frame_image in self.frame_images:
                loaded_image = pygame.image.load(frame_image).convert_alpha()
                scaled_image = pygame.transform.smoothscale(loaded_image, (size, size))
                self.animation_frames.append(scaled_image)

    def draw(self, screen, offset_x, offset_y):
        if self.sprite_path:
            screen.blit(self.sprite, (int(self.x - offset_x), int(self.y - offset_y)))
        elif self.frame_images:
            current_frame_image = self.animation_frames[self.current_frame]
            screen.blit(
                current_frame_image, (int(self.x - offset_x), int(self.y - offset_y))
            )

    def update(self, dt):
        if self.frame_images:
            self.elapsed_time += dt
            if self.elapsed_time >= self.animation_speed:
                self.current_frame = (self.current_frame + 1) % len(
                    self.animation_frames
                )
                self.elapsed_time = 0

    def draw_health_bar(self, screen, offset_x, offset_y):
        health_bar_width = self.size
        health_bar_height = 10
        health_bar_x = self.x - offset_x
        health_bar_y = self.y - offset_y - 30

        health_percentage = self.health / 100
        health_bar_fill_width = int(health_bar_width * health_percentage)

        # Draw the health bar background
        pygame.draw.rect(
            screen,
            RED,
            (health_bar_x, health_bar_y, health_bar_width, health_bar_height),
        )

        # Draw the health bar fill
        pygame.draw.rect(
            screen,
            GREEN,
            (health_bar_x, health_bar_y, health_bar_fill_width, health_bar_height),
        )


class Player(GameObject):
    def __init__(self, x, y, size, color, speed, name, money):
        super().__init__(
            x,
            y,
            size,
            color,
            speed,
            frame_images=[
                "resources/player1.png",
                "resources/player2.png",
                "resources/player3.png",
                "resources/player2.png",
            ],
        )
        self.name = str(name) if name else ""
        self.has_laser_beam = False
        self.money = money
        self.health = 100

    def draw(self, screen, offset_x, offset_y):
        super().draw(screen, offset_x, offset_y)
        name_text = font.render(self.name, True, BLACK)
        name_rect = name_text.get_rect(
            center=(
                int(self.x - offset_x + self.size // 2),
                int(self.y - offset_y - 10),
            )
        )
        screen.blit(name_text, name_rect)

    def move(self, dt, keys, entity, game):
        if game.chat_active:
            return

        if keys[pygame.K_w]:
            self.y -= self.speed * dt
        if keys[pygame.K_s]:
            self.y += self.speed * dt
        if keys[pygame.K_a]:
            self.x -= self.speed * dt
        if keys[pygame.K_d]:
            self.x += self.speed * dt
        connection.Send(
            {"action": "move", "x": entity.x, "y": entity.y, "name": self.name}
        )


class Enemy(GameObject):
    def __init__(self, x, y, size, color, speed, minimap_radius):
        super().__init__(
            x,
            y,
            size,
            color,
            speed,
            frame_images=["resources/enemy1.png"],
        )
        self.hit_count = 0
        self.hit_timer = 0
        self.minimap_radius = minimap_radius
        self.health = 100

    def move(self, dt, player_pos):
        if self.x < player_pos[0]:
            self.x += self.speed * dt
        if self.x > player_pos[0]:
            self.x -= self.speed * dt
        if self.y < player_pos[1]:
            self.y += self.speed * dt
        if self.y > player_pos[1]:
            self.y -= self.speed * dt
        # connection.Send({"action": "move", "x": self.player.x, "y": self.player.y})

    def hit(self):
        self.hit_count += 1
        self.hit_timer = 30  # Set the timer for 30 frames (0.5 seconds at 60 FPS)
        self.color = RED

    def respawn(self, player_pos):
        if DEBUG_MODE:
            return

        # Calculate the bounds of the minimap
        minimap_left = player_pos[0] - self.minimap_radius
        minimap_right = player_pos[0] + self.minimap_radius
        minimap_top = player_pos[1] - self.minimap_radius
        minimap_bottom = player_pos[1] + self.minimap_radius

        # Generate random coordinates outside the minimap bounds
        while True:
            self.x = player_pos[0] + random.randint(-1000, 1000)
            self.y = player_pos[1] + random.randint(-1000, 1000)

            # Check if the enemy is outside the minimap bounds
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
        super().update(dt)
        if self.hit_timer > 0:
            self.hit_timer -= 1
            if self.hit_timer == 0:
                self.color = GREEN


class ShopScreen:
    def __init__(self, player):
        self.player = player
        self.font = pygame.font.Font(None, 36)
        self.laser_beam_purchased = self.player.has_laser_beam
        self.in_shop = False

    def draw(self, screen):
        screen.fill(WHITE)
        title_text = self.font.render("Shop", True, BLACK)
        title_rect = title_text.get_rect(center=(width // 2, height // 4))
        screen.blit(title_text, title_rect)

        laser_beam_text = self.font.render("Laser Beam - $500", True, BLACK)
        laser_beam_rect = laser_beam_text.get_rect(center=(width // 2, height // 2))
        screen.blit(laser_beam_text, laser_beam_rect)

        if self.laser_beam_purchased:
            purchased_text = self.font.render("Laser Beam purchased!", True, GREEN)
            purchased_rect = purchased_text.get_rect(
                center=(width // 2, height // 2 + 50)
            )
            screen.blit(purchased_text, purchased_rect)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.in_shop = False
                    self.laser_beam_purchased = self.player.has_laser_beam
                    return True  # Return True to keep the game running
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = event.pos
                    laser_beam_text_rect = pygame.Rect(
                        width // 2 - 100, height // 2 - 20, 200, 40
                    )
                    if (
                        laser_beam_text_rect.collidepoint(mouse_pos)
                        and not self.laser_beam_purchased
                    ):
                        if self.player.money.amount >= 500 or DEBUG_MODE:
                            self.player.money.amount -= 500
                            self.player.has_laser_beam = True
                            self.laser_beam_purchased = True
        return True

    def is_open(self):
        return self.in_shop

    def open_shop(self):
        self.in_shop = True


class Minimap:
    def __init__(self, width, height, position, color, scale):
        self.width = width
        self.height = height
        self.position = position
        self.color = color
        self.scale = scale

    def draw(self, screen, player, enemy):
        pygame.draw.rect(
            screen,
            self.color,
            (self.position[0], self.position[1], self.width, self.height),
        )
        pygame.draw.rect(
            screen,
            BLACK,
            (self.position[0], self.position[1], self.width, self.height),
            2,
        )  # Add border

        # Calculate the center of the minimap
        center_x = self.position[0] + self.width // 2
        center_y = self.position[1] + self.height // 2

        # Calculate the relative positions of the player and enemy
        player_x = center_x + (player.x - player.x) // self.scale
        player_y = center_y + (player.y - player.y) // self.scale
        enemy_x = center_x + (enemy.x - player.x) // self.scale
        enemy_y = center_y + (enemy.y - player.y) // self.scale

        # Check if the enemy is within the minimap boundaries
        if (
            self.position[0] <= enemy_x <= self.position[0] + self.width
            and self.position[1] <= enemy_y <= self.position[1] + self.height
        ):
            # Draw the enemy on the minimap only if it's within the boundaries
            pygame.draw.circle(
                screen, enemy.color, (enemy_x, enemy_y), enemy.size // self.scale
            )

        # Draw the player at the center of the minimap
        pygame.draw.circle(
            screen, player.color, (player_x, player_y), player.size // self.scale
        )


class Projectile(GameObject):
    def __init__(self, x, y, size, color, speed, velocity):
        super().__init__(x, y, size, color, speed)
        self.velocity = velocity

    def move(self, dt):
        self.x += self.velocity[0] * dt
        self.y += self.velocity[1] * dt
        return

    def draw(self, screen, offset_x, offset_y):
        pygame.draw.rect(
            screen,
            self.color,
            (int(self.x - offset_x), int(self.y - offset_y), self.size, self.size),
        )


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

    def draw(self, screen, offset_x, offset_y):
        start_x = self.start_point[0] - offset_x
        start_y = self.start_point[1] - offset_y
        end_x = self.end_point[0] - offset_x
        end_y = self.end_point[1] - offset_y

        if self.fade_timer > 0:
            alpha = (self.fade_duration - self.fade_timer) / self.fade_duration * 255
            color = self.color + (alpha,)
        else:
            color = self.color

        pygame.draw.line(screen, color, (start_x, start_y), (end_x, end_y), self.size)

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


class ChatBox:
    def __init__(self, x, y, width, height, font, bg_color, text_color):
        self.x = x
        self.y = y
        self.width = width
        self.inactive_height = height - 10
        self.active_height = height * 2 - 10
        self.height = height
        self.font = font
        self.bg_color = bg_color
        self.text_color = text_color
        self.input_text = ""
        self.chat_log = []
        self.active = False
        self.typing_indicator = ""
        self.typing_indicator_visible = True
        self.typing_indicator_timer = 0
        self.typing_indicator_interval = 500

    def draw(self, screen):
        # Draw semi-transparent background
        bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg_surface.fill(self.bg_color)
        screen.blit(bg_surface, (self.x, self.y))

        input_height = self.font.get_height() + 10
        available_height = self.height - input_height - 20
        max_lines = available_height // self.font.get_height()
        lines = []
        for message in self.chat_log:
            line = ""
            for char in message:
                test_line = line + char
                if self.font.size(test_line)[0] <= self.width - 20:
                    line = test_line
                else:
                    lines.append(line)
                    line = char
            if line:
                lines.append(line)

        # Get the last max_lines lines from the chat log
        recent_lines = lines[-max_lines:]
        y = self.y + self.height - input_height - 20
        for line in reversed(recent_lines):
            text_surface = self.font.render(line, True, self.text_color)
            screen.blit(text_surface, (self.x + 10, y))
            y -= self.font.get_height()

        # Draw input bar
        input_width = self.width - 20
        truncated_input_text = self.truncate_input_text(self.input_text, input_width)
        input_surface = self.font.render(truncated_input_text, True, BLACK)
        input_height = self.font.get_height() + 10
        input_bg_color = GRAY if self.active else WHITE
        pygame.draw.rect(
            screen, input_bg_color, (self.x, self.y + self.height - 30, self.width, 30)
        )
        screen.blit(input_surface, (self.x + 10, self.y + self.height - 25))
        pygame.draw.rect(
            screen, BLACK, (self.x, self.y + self.height - 30, self.width, 30), 1
        )

        # Draw input bar border
        border_color = BLACK if self.active else GRAY
        pygame.draw.rect(
            screen, border_color, (self.x, self.y + self.height - 30, self.width, 30), 1
        )

        # Update typing indicator visibility
        current_time = pygame.time.get_ticks()
        if (
            self.active
            and current_time - self.typing_indicator_timer
            >= self.typing_indicator_interval
        ):
            self.typing_indicator_visible = not self.typing_indicator_visible
            self.typing_indicator_timer = current_time

        # Display typing indicator at the end of the input text
        if self.active and self.typing_indicator_visible:
            typing_indicator_x = self.x + 10 + input_surface.get_width()
            typing_indicator_y = self.y + self.height - 25
            typing_indicator_surface = self.font.render(
                self.typing_indicator, True, BLACK
            )
            screen.blit(
                typing_indicator_surface, (typing_indicator_x, typing_indicator_y)
            )

    def truncate_input_text(self, text, width):
        truncated_text = ""
        for char in reversed(text):
            test_text = truncated_text
            test_text = char + test_text
            if self.font.size(test_text)[0] <= width:
                truncated_text = test_text
            else:
                break
        return truncated_text

    def update(self, event, player, game):
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    if self.input_text:
                        self.chat_log.append(f"{player.name}: {self.input_text}")
                        connection.Send(
                            {
                                "action": "chat",
                                "message": self.input_text,
                                "sender": player.name,
                            }
                        )
                        self.input_text = ""
                    self.active = False
                    game.chat_active = False
                    self.typing_indicator = ""
                    self.height = self.inactive_height
                    self.y = height - self.inactive_height - 10
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    self.input_text += event.unicode
                    self.typing_indicator = "_"
            elif event.key == pygame.K_t:
                self.active = True
                game.chat_active = True
                self.typing_indicator = "_"
                self.height = self.active_height
                self.y = height - self.active_height - 10
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if not (
                self.x < event.pos[0] < self.x + self.width
                and self.y < event.pos[1] < self.y + self.height
            ):
                self.active = False
                game.chat_active = False
                self.typing_indicator = ""
                self.height = self.inactive_height
                self.y = height - self.inactive_height - 10


class Game(ConnectionListener):

    def __init__(self):
        self.money = Money()
        self.player = Player(
            0, 0, PLAYER_SIZE, RED, 300, "Player", self.money
        )  # Initialize the player with a default name
        self.players = dict()
        self.enemy = None
        self.projectiles = []
        self.own_projectiles = []
        self.laser_beams = []
        self.font = pygame.font.Font(None, 36)
        self.running = False
        self.offset_x = 0
        self.offset_y = 0
        self.player_name = ""
        self.ip_address = ""
        minimap_width = 200
        minimap_height = 200
        minimap_x = width - minimap_width
        minimap_y = 0
        self.minimap = Minimap(
            minimap_width, minimap_height, (minimap_x, minimap_y), WHITE, 10
        )
        self.shop_screen = ShopScreen(self.player)
        self.connected = False
        self.chat_font = pygame.font.Font(
            None, 24
        )  # Create a new font with a smaller size
        self.chat_box = ChatBox(
            10, height - 160, 300, 140, self.chat_font, (0, 0, 0, 128), WHITE
        )
        self.chat_active = False

    def Network(self, data):
        print("Received data:", data)

    def start_screen(self, player_name="", ip_address=""):
        start_screen = True

        name_input_box = pygame.Rect(width // 2 - 100, height // 2 - 22, 200, 40)
        ip_input_box = pygame.Rect(width // 2 - 100, height // 2 + 22, 200, 40)
        color_inactive = pygame.Color("lightskyblue3")
        color_active = pygame.Color("dodgerblue2")
        name_color = color_inactive
        ip_color = color_inactive
        name_active = True
        ip_active = False

        input_boxes = [name_input_box, ip_input_box]
        active_input_index = 0

        play_text = font.render("Play", True, BLACK)
        play_rect = play_text.get_rect(center=(width // 2, height * 3 // 4))

        while start_screen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    start_screen = False
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if name_input_box.collidepoint(event.pos):
                        name_active = True
                        ip_active = False
                        active_input_index = 0
                    elif ip_input_box.collidepoint(event.pos):
                        name_active = False
                        ip_active = True
                        active_input_index = 1
                    else:
                        name_active = False
                        ip_active = False

                    if play_rect.collidepoint(event.pos):
                        start_screen = False
                        self.player.name = player_name
                        self.ip_address = ip_address
                        self.player_name = player_name
                        minimap_radius = (
                            min(self.minimap.width, self.minimap.height) // 2
                        )
                        self.enemy = Enemy(
                            random.randint(-400, 400),
                            random.randint(-400, 400),
                            ENEMY_SIZE,
                            GREEN,
                            100,
                            minimap_radius,
                        )
                        self.Connect((ip_address, 12345))
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        active_input_index = (active_input_index + 1) % len(input_boxes)
                        name_active = active_input_index == 0
                        ip_active = active_input_index == 1
                    elif event.key == pygame.K_RETURN:
                        start_screen = False
                        self.player.name = player_name
                        self.ip_address = ip_address
                        self.player_name = player_name
                        minimap_radius = (
                            min(self.minimap.width, self.minimap.height) // 2
                        )
                        self.enemy = Enemy(
                            random.randint(-400, 400),
                            random.randint(-400, 400),
                            ENEMY_SIZE,
                            GREEN,
                            100,
                            minimap_radius,
                        )
                        self.Connect((ip_address, 12345))
                    elif name_active:
                        if event.key == pygame.K_RETURN:
                            print(player_name)
                        elif event.key == pygame.K_BACKSPACE:
                            player_name = player_name[:-1]
                        else:
                            player_name += event.unicode
                    elif ip_active:
                        if event.key == pygame.K_RETURN:
                            print(ip_address)
                        elif event.key == pygame.K_BACKSPACE:
                            ip_address = ip_address[:-1]
                        else:
                            ip_address += event.unicode

            name_color = color_active if name_active else color_inactive
            ip_color = color_active if ip_active else color_inactive

            screen.fill(WHITE)
            title_text = font.render("ProGame", True, BLACK)
            title_rect = title_text.get_rect(center=(width // 2, height // 4))
            screen.blit(title_text, title_rect)

            name_label = font.render("Name:", True, BLACK)
            name_label_rect = name_label.get_rect(
                midright=(name_input_box.left - 10, name_input_box.centery)
            )
            screen.blit(name_label, name_label_rect)

            pygame.draw.rect(screen, name_color, name_input_box, 2)
            name_text = font.render(player_name, True, BLACK)
            screen.blit(name_text, (name_input_box.x + 5, name_input_box.y + 5))
            name_input_box.w = max(200, name_text.get_width() + 10)

            ip_label = font.render("IP:", True, BLACK)
            ip_label_rect = ip_label.get_rect(
                midright=(ip_input_box.left - 10, ip_input_box.centery)
            )
            screen.blit(ip_label, ip_label_rect)

            pygame.draw.rect(screen, ip_color, ip_input_box, 2)
            ip_text = font.render(ip_address, True, BLACK)
            screen.blit(ip_text, (ip_input_box.x + 5, ip_input_box.y + 5))
            ip_input_box.w = max(200, ip_text.get_width() + 10)

            pygame.draw.rect(screen, GREEN, play_rect, 2)
            screen.blit(play_text, play_rect)

            pygame.display.flip()

    def Network_game_state(self, data):
        game_state = data["data"]

        server_player_names = set(p["name"] for p in game_state["players"])
        self.players = {
            name: player
            for name, player in self.players.items()
            if name in server_player_names
        }
        for p in game_state["players"]:
            if self.players.get(p["name"]) is None:
                self.players[p["name"]] = Player(
                    p["x"], p["y"], PLAYER_SIZE, RED, 300, p["name"], Money()
                )
            
            if p["name"] == self.player.name:
                self.player.health = p["health"]

            player = self.players[p["name"]]
            player.x = p["x"]
            player.y = p["y"]
            player.health = p["health"]

        self.enemy.x = game_state["enemy"]["x"]
        self.enemy.y = game_state["enemy"]["y"]
        self.enemy.color = tuple(game_state["enemy"]["color"])
        self.enemy.health = game_state["enemy"]["health"]
        self.projectiles = [
            Projectile(p["x"], p["y"], 5, RED, 0, [0, 0])
            for p in game_state["projectiles"]
            if p["name"] != self.player.name
        ]

        self.laser_beams = [
            LaserBeam(
                lb["start_point"][0],
                lb["start_point"][1],
                LASER_BEAM_SIZE,
                RED,
                0,
                lb["angle"],
                LASER_FADE_DURATION,
            )
            for lb in game_state["laser_beams"]
        ]

    def Network_chat(self, data):
        message = data["message"]
        sender = data["sender"]
        if sender != self.player.name:
            self.chat_box.chat_log.append(f"{sender}: {message}")

    def draw_grid(self):
        # Calculate the nearest multiple of 50 to the player's position
        start_x = round(self.player.x / 50) * 50
        start_y = round(self.player.y / 50) * 50

        # Calculate the range of x values to cover the entire screen
        min_x = start_x - (width // 2) - 50
        max_x = start_x + (width // 2) + 50

        # Draw vertical lines
        for x in range(min_x - 500, max_x + 500, 50):
            pygame.draw.line(
                screen,
                GRAY,
                (x - self.player.x + width // 2, 0),
                (x - self.player.x + width // 2, height),
            )

        # Draw horizontal lines
        for y in range(start_y - 1000, start_y + 1000, 50):
            pygame.draw.line(
                screen,
                GRAY,
                (0, y - self.player.y + height // 2),
                (width, y - self.player.y + height // 2),
            )

    def run(self):
        self.running = True
        clock = pygame.time.Clock()

        while True:
            if self.player_name == "" or self.ip_address == "":
                self.start_screen()
            else:
                self.start_screen(self.player_name, self.ip_address)
                self.running = True

            while self.running:
                dt = clock.tick(60) / 1000
                self.Pump()
                connection.Pump()

                if self.shop_screen.is_open():
                    events = pygame.event.get()
                    keep_open = self.shop_screen.handle_events(events)
                    if not keep_open:
                        self.running = False
                    self.shop_screen.draw(screen)
                    pygame.display.flip()
                    continue
                
                if self.player.health <= 0:
                    self.running = False
                    return

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        return
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:  # Left click
                            mouse_pos = pygame.mouse.get_pos()
                            angle = math.atan2(
                                mouse_pos[1] - height // 2, mouse_pos[0] - width // 2
                            )
                            velocity = [math.cos(angle) * 400, math.sin(angle) * 400]
                            projectile = Projectile(
                                self.player.x + self.player.size // 2,
                                self.player.y + self.player.size // 2,
                                5,
                                RED,
                                400,
                                velocity,
                            )
                            self.own_projectiles.append(projectile)
                            connection.Send(
                                {
                                    "action": "projectile",
                                    "x": self.player.x + self.player.size // 2,
                                    "y": self.player.y + self.player.size // 2,
                                    "velocity": velocity,
                                    "name": self.player.name,
                                }
                            )
                        elif (
                            event.button == 3 and self.player.has_laser_beam
                        ):  # Right click
                            mouse_pos = pygame.mouse.get_pos()
                            angle = math.atan2(
                                mouse_pos[1] - height // 2, mouse_pos[0] - width // 2
                            )
                            laser_beam = LaserBeam(
                                self.player.x + self.player.size // 2,
                                self.player.y + self.player.size // 2,
                                LASER_BEAM_SIZE,
                                RED,
                                0,
                                angle,
                                LASER_FADE_DURATION,
                            )
                            self.laser_beams.append(laser_beam)
                            connection.Send(
                                {
                                    "action": "laser_beam",
                                    "x": self.player.x + self.player.size // 2,
                                    "y": self.player.y + self.player.size // 2,
                                    "angle": angle,
                                    "name": self.player.name,
                                }
                            )
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.shop_screen.open_shop()
                        elif (
                            event.key == pygame.K_ESCAPE
                            and not self.shop_screen.is_open()
                        ):
                            self.shop_screen.open_shop()
                    self.chat_box.update(event, self.player, self)

                keys = pygame.key.get_pressed()
                self.player.move(dt, keys, self.player, self)
                self.enemy.move(dt, (self.player.x, self.player.y))

                for projectile in self.own_projectiles:
                    projectile.move(dt)

                for laser_beam in self.laser_beams:
                    laser_beam.move()

                    # Remove faded laser beams
                    if laser_beam.is_faded():
                        self.laser_beams.remove(laser_beam)

                self.enemy.update(dt)
                self.player.update(dt)
                for player in self.players.values():
                    player.update(dt)

                self.projectiles = [
                    p
                    for p in self.projectiles
                    if abs(p.x - self.player.x) <= 1000
                    and abs(p.y - self.player.y) <= 1000
                ]

                if (
                    not DEBUG_MODE
                    and abs(self.player.x - self.enemy.x) < self.player.size
                    and abs(self.player.y - self.enemy.y) < self.player.size
                ):
                    self.running = False
                    print("Game Over! You lost.")

                self.offset_x = self.player.x - width // 2
                self.offset_y = self.player.y - height // 2

                screen.fill(WHITE)
                self.draw_grid()
                for projectile in self.projectiles:
                    projectile.draw(screen, self.offset_x, self.offset_y)
                for projectile in self.own_projectiles:
                    projectile.draw(screen, self.offset_x, self.offset_y)
                for laser_beam in self.laser_beams:
                    laser_beam.draw(screen, self.offset_x, self.offset_y)

                self.player.draw(screen, self.offset_x, self.offset_y)
                self.player.draw_health_bar(screen, self.offset_x, self.offset_y)
                self.enemy.draw(screen, self.offset_x, self.offset_y)
                self.enemy.draw_health_bar(screen, self.offset_x, self.offset_y)

                for other_player in self.players.values():
                    # Do not draw the current player again
                    if other_player.name == self.player.name:
                        continue
                    other_player.draw(screen, self.offset_x, self.offset_y)
                    other_player.draw_health_bar(screen, self.offset_x, self.offset_y)

                self.minimap.draw(screen, self.player, self.enemy)

                text = self.font.render(f"Cash: ${self.money.amount}", True, (0, 0, 0))
                text_rect = text.get_rect(center=(width - 75, 220))

                coordinate_text = self.font.render(
                    f"X: {int(self.player.x)//10}, Y: {int(self.player.y)//10}",
                    True,
                    (0, 0, 0),
                )
                coordinate_text_rect = coordinate_text.get_rect(
                    center=(width - 100, 260)
                )
                screen.blit(coordinate_text, coordinate_text_rect)

                self.chat_box.draw(screen)
                screen.blit(text, text_rect)
                pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()

pygame.quit()
