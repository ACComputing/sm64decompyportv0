import pygame
import math
import sys
import random
import time

# ============================================================================
#  Cat's SM64 Py Port 1.0
#  (C) Nintendo 1996-2026 | (C) AC Corp 1999-2026
#  A Python/Pygame tribute to Super Mario 64
# ============================================================================

# --- Constants & Configuration ---
WIDTH, HEIGHT = 800, 600
FPS = 60
FOV = 400
BG_COLOR = (135, 206, 235)

# Physics - SM64 Feel
GRAVITY = 0.8
JUMP_FORCE = -16
DOUBLE_JUMP_FORCE = -18
TRIPLE_JUMP_FORCE = -22
LONG_JUMP_FORCE = -14
LONG_JUMP_BOOST = 18
ACCELERATION = 0.6
FRICTION = 0.85
MAX_SPEED = 12
ROTATION_SPEED = 0.15
CAM_DISTANCE = 500
CAM_HEIGHT = 250
CAM_SMOOTHING = 0.1

# Game States
STATE_TITLE = 0
STATE_FILE_SELECT = 1
STATE_LETTER = 2
STATE_CASTLE = 3
STATE_LEVEL = 4
STATE_STAR_GET = 5
STATE_PAUSE = 6
STATE_GAME_OVER = 7

# --- Color Palette ---
COL_MARIO_RED = (255, 20, 20)
COL_MARIO_BLUE = (30, 30, 200)
COL_MARIO_SKIN = (255, 200, 150)
COL_GOLD = (255, 215, 0)
COL_COIN = (255, 200, 0)
COL_STAR = (255, 255, 100)
COL_CASTLE_WALL = (220, 210, 190)
COL_CASTLE_ROOF = (180, 50, 50)
COL_CASTLE_DOOR = (120, 80, 40)
COL_GRASS = (34, 180, 34)
COL_DIRT = (139, 90, 43)
COL_STONE = (160, 160, 160)
COL_SNOW = (240, 245, 255)
COL_ICE = (180, 220, 255)
COL_SAND = (230, 210, 150)
COL_LAVA = (255, 80, 20)
COL_WATER = (64, 120, 220)
COL_DARK_WATER = (30, 60, 140)
COL_WOOD = (139, 90, 43)
COL_GHOST = (200, 200, 230)
COL_CAVE = (100, 90, 80)
COL_PURPLE = (120, 50, 180)
COL_RAINBOW1 = (255, 100, 100)
COL_RAINBOW2 = (100, 255, 100)
COL_RAINBOW3 = (100, 100, 255)
COL_CLOCK = (180, 160, 100)

# --- Level Definitions ---
LEVEL_CASTLE_GROUNDS = -1
LEVEL_BOB_OMB = 0        # Bob-omb Battlefield
LEVEL_WHOMP = 1           # Whomp's Fortress
LEVEL_JOLLY = 2           # Jolly Roger Bay
LEVEL_COOL_COOL = 3       # Cool, Cool Mountain
LEVEL_BIG_BOO = 4         # Big Boo's Haunt
LEVEL_HAZY_MAZE = 5       # Hazy Maze Cave
LEVEL_LETHAL_LAVA = 6     # Lethal Lava Land
LEVEL_SHIFTING_SAND = 7   # Shifting Sand Land
LEVEL_DIRE_DOCKS = 8      # Dire, Dire Docks
LEVEL_SNOWMAN = 9          # Snowman's Land
LEVEL_WET_DRY = 10         # Wet-Dry World
LEVEL_TALL_TALL = 11       # Tall, Tall Mountain
LEVEL_TINY_HUGE = 12       # Tiny-Huge Island
LEVEL_TICK_TOCK = 13       # Tick Tock Clock
LEVEL_RAINBOW = 14         # Rainbow Ride

LEVEL_BOWSER_1 = 100       # Bowser in the Dark World
LEVEL_BOWSER_2 = 101       # Bowser in the Fire Sea
LEVEL_BOWSER_3 = 102       # Bowser in the Sky

LEVEL_NAMES = {
    LEVEL_CASTLE_GROUNDS: "Princess Peach's Castle",
    LEVEL_BOB_OMB: "Bob-omb Battlefield",
    LEVEL_WHOMP: "Whomp's Fortress",
    LEVEL_JOLLY: "Jolly Roger Bay",
    LEVEL_COOL_COOL: "Cool, Cool Mountain",
    LEVEL_BIG_BOO: "Big Boo's Haunt",
    LEVEL_HAZY_MAZE: "Hazy Maze Cave",
    LEVEL_LETHAL_LAVA: "Lethal Lava Land",
    LEVEL_SHIFTING_SAND: "Shifting Sand Land",
    LEVEL_DIRE_DOCKS: "Dire, Dire Docks",
    LEVEL_SNOWMAN: "Snowman's Land",
    LEVEL_WET_DRY: "Wet-Dry World",
    LEVEL_TALL_TALL: "Tall, Tall Mountain",
    LEVEL_TINY_HUGE: "Tiny-Huge Island",
    LEVEL_TICK_TOCK: "Tick Tock Clock",
    LEVEL_RAINBOW: "Rainbow Ride",
    LEVEL_BOWSER_1: "Bowser in the Dark World",
    LEVEL_BOWSER_2: "Bowser in the Fire Sea",
    LEVEL_BOWSER_3: "Bowser in the Sky",
}

STAR_NAMES = {
    LEVEL_BOB_OMB: [
        "Big Bob-omb on the Summit",
        "Footrace with Koopa the Quick",
        "Shoot to the Island in the Sky",
        "Find the 8 Red Coins",
        "Mario Wings to the Sky",
        "Behind Chain Chomp's Gate",
        "100 Coins Star"
    ],
    LEVEL_WHOMP: [
        "Chip Off Whomp's Block",
        "To the Top of the Fortress",
        "Shoot into the Wild Blue",
        "Red Coins on the Floating Isle",
        "Fall onto the Caged Island",
        "Blast Away the Wall",
        "100 Coins Star"
    ],
    LEVEL_JOLLY: [
        "Plunder in the Sunken Ship",
        "Can the Eel Come Out to Play?",
        "Treasure of the Ocean Cave",
        "Red Coins on the Ship Afloat",
        "Blast to the Stone Pillar",
        "Through the Jet Stream",
        "100 Coins Star"
    ],
    LEVEL_COOL_COOL: [
        "Slip Slidin' Away",
        "Li'l Penguin Lost",
        "Big Penguin Race",
        "Frosty Slide for 8 Red Coins",
        "Snowman's Lost His Head",
        "Wall Kicks Will Work",
        "100 Coins Star"
    ],
    LEVEL_BIG_BOO: [
        "Go on a Ghost Hunt",
        "Ride Big Boo's Merry-Go-Round",
        "Secret of the Haunted Books",
        "Seek the 8 Red Coins",
        "Big Boo's Balcony",
        "Eye to Eye in the Secret Room",
        "100 Coins Star"
    ],
    LEVEL_HAZY_MAZE: [
        "Swimming Beast in the Cavern",
        "Elevate for 8 Red Coins",
        "Metal-Head Mario Can Move!",
        "Navigating the Toxic Maze",
        "A-Maze-ing Emergency Exit",
        "Watch for Rolling Rocks",
        "100 Coins Star"
    ],
    LEVEL_LETHAL_LAVA: [
        "Boil the Big Bully",
        "Bully the Bullies",
        "8-Coin Puzzle with 15 Pieces",
        "Red-Hot Log Rolling",
        "Hot-Foot-It into the Volcano",
        "Elevator Tour in the Volcano",
        "100 Coins Star"
    ],
    LEVEL_SHIFTING_SAND: [
        "In the Talons of the Big Bird",
        "Shining Atop the Pyramid",
        "Inside the Ancient Pyramid",
        "Stand Tall on the Four Pillars",
        "Free Flying for 8 Red Coins",
        "Pyramid Puzzle",
        "100 Coins Star"
    ],
    LEVEL_DIRE_DOCKS: [
        "Board Bowser's Sub",
        "Chests in the Current",
        "Pole-Jumping for Red Coins",
        "Through the Jet Stream",
        "The Manta Ray's Reward",
        "Collect the Caps...",
        "100 Coins Star"
    ],
    LEVEL_SNOWMAN: [
        "Snowman's Big Head",
        "Chill with the Bully",
        "In the Deep Freeze",
        "Whirl from the Freezing Pond",
        "Shell Shreddin' for Red Coins",
        "Into the Igloo",
        "100 Coins Star"
    ],
    LEVEL_WET_DRY: [
        "Shocking Arrow Lifts!",
        "Top o' the Town",
        "Secrets in the Shallows & Sky",
        "Express Elevator--Hurry Up!",
        "Go to Town for Red Coins",
        "Quick Race Through Downtown!",
        "100 Coins Star"
    ],
    LEVEL_TALL_TALL: [
        "Scale the Mountain",
        "Mystery of the Monkey Cage",
        "Scary 'Shrooms, Red Coins",
        "Mysterious Mountainside",
        "Breathtaking View from Bridge",
        "Blast to the Lonely Mushroom",
        "100 Coins Star"
    ],
    LEVEL_TINY_HUGE: [
        "Pluck the Piranha Flower",
        "The Tip Top of the Huge Island",
        "Rematch with Koopa the Quick",
        "Five Itty Bitty Secrets",
        "Wiggler's Red Coins",
        "Make Wiggler Squirm",
        "100 Coins Star"
    ],
    LEVEL_TICK_TOCK: [
        "Roll into the Cage",
        "The Pit and the Pendulums",
        "Get a Hand",
        "Stomp on the Thwomp",
        "Timed Jumps on Moving Bars",
        "Stop Time for Red Coins",
        "100 Coins Star"
    ],
    LEVEL_RAINBOW: [
        "Cruiser Crossing the Rainbow",
        "The Big House in the Sky",
        "Coins Amassed in a Maze",
        "Swingin' in the Breeze",
        "Tricky Triangles!",
        "Somewhere Over the Rainbow",
        "100 Coins Star"
    ],
}

# ============================================================================
#  3D MATH ENGINE
# ============================================================================

class Vector3:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z

    def add(self, v):
        return Vector3(self.x + v.x, self.y + v.y, self.z + v.z)

    def sub(self, v):
        return Vector3(self.x - v.x, self.y - v.y, self.z - v.z)

    def scale(self, s):
        return Vector3(self.x * s, self.y * s, self.z * s)

    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def copy(self):
        return Vector3(self.x, self.y, self.z)


def rotate_point_y(x, z, cx, cz, angle):
    dx, dz = x - cx, z - cz
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return dx * cos_a - dz * sin_a + cx, dx * sin_a + dz * cos_a + cz


def lerp(a, b, t):
    return a + (b - a) * t


def angle_lerp(current, target, t):
    diff = target - current
    while diff > math.pi: diff -= 2 * math.pi
    while diff < -math.pi: diff += 2 * math.pi
    return current + diff * t


class Face:
    __slots__ = ('vertices', 'color', 'avg_z')
    def __init__(self, vertices, color):
        self.vertices = vertices
        self.color = color
        self.avg_z = 0


class Object3D:
    def __init__(self, x, y, z, color=(255, 255, 255)):
        self.x, self.y, self.z = x, y, z
        self.faces = []
        self.color = color

    def add_box(self, w, h, d, color=None, ox=0, oy=0, oz=0):
        c = color if color else self.color
        hw, hh, hd = w/2, h/2, d/2
        verts = [
            Vector3(-hw+ox, -hh+oy, -hd+oz), Vector3(hw+ox, -hh+oy, -hd+oz),
            Vector3(hw+ox, hh+oy, -hd+oz), Vector3(-hw+ox, hh+oy, -hd+oz),
            Vector3(-hw+ox, -hh+oy, hd+oz), Vector3(hw+ox, -hh+oy, hd+oz),
            Vector3(hw+ox, hh+oy, hd+oz), Vector3(-hw+ox, hh+oy, hd+oz),
        ]
        indices = [
            [0,1,2,3],[5,4,7,6],[4,0,3,7],[1,5,6,2],[3,2,6,7],[4,5,1,0]
        ]
        shades = [1.0, 0.85, 0.9, 0.95, 1.05, 0.75]
        for i, idx_list in enumerate(indices):
            shade = shades[i]
            sc = tuple(max(0, min(255, int(ch * shade))) for ch in c)
            face_verts = [verts[j] for j in idx_list]
            self.faces.append(Face(face_verts, sc))

    def add_pyramid(self, base_w, h, base_d, color=None, ox=0, oy=0, oz=0):
        c = color if color else self.color
        hw, hd = base_w/2, base_d/2
        top = Vector3(ox, oy - h, oz)
        b1 = Vector3(-hw+ox, oy, -hd+oz)
        b2 = Vector3(hw+ox, oy, -hd+oz)
        b3 = Vector3(hw+ox, oy, hd+oz)
        b4 = Vector3(-hw+ox, oy, hd+oz)
        self.faces.append(Face([b1,b2,top], c))
        shade = tuple(max(0,min(255,int(ch*0.85))) for ch in c)
        self.faces.append(Face([b2,b3,top], shade))
        shade2 = tuple(max(0,min(255,int(ch*0.9))) for ch in c)
        self.faces.append(Face([b3,b4,top], shade2))
        shade3 = tuple(max(0,min(255,int(ch*0.95))) for ch in c)
        self.faces.append(Face([b4,b1,top], shade3))
        self.faces.append(Face([b4,b3,b2,b1], tuple(max(0,min(255,int(ch*0.7))) for ch in c)))


# ============================================================================
#  COLLECTIBLES
# ============================================================================

class Coin:
    def __init__(self, x, y, z, coin_type=0):
        self.x, self.y, self.z = x, y, z
        self.collected = False
        self.coin_type = coin_type  # 0=yellow(1), 1=red(2), 2=blue(5)
        self.bob_offset = random.random() * math.pi * 2
        self.size = 12

    def get_value(self):
        return [1, 2, 5][self.coin_type]

    def get_color(self):
        return [(255, 200, 0), (255, 50, 50), (80, 80, 255)][self.coin_type]

    def get_faces(self, game_time):
        if self.collected: return []
        bob = math.sin(game_time * 3 + self.bob_offset) * 5
        y = self.y + bob - self.size
        s = self.size
        c = self.get_color()
        angle = game_time * 4 + self.bob_offset
        hw = abs(math.sin(angle)) * s
        if hw < 2: hw = 2
        faces = []
        v1 = Vector3(self.x - hw, y - s, self.z)
        v2 = Vector3(self.x + hw, y - s, self.z)
        v3 = Vector3(self.x + hw, y + s, self.z)
        v4 = Vector3(self.x - hw, y + s, self.z)
        faces.append(Face([v1, v2, v3, v4], c))
        return faces


class Star:
    def __init__(self, x, y, z, star_id=0):
        self.x, self.y, self.z = x, y, z
        self.collected = False
        self.star_id = star_id
        self.bob_offset = random.random() * math.pi * 2
        self.size = 20

    def get_faces(self, game_time):
        if self.collected: return []
        bob = math.sin(game_time * 2 + self.bob_offset) * 8
        y = self.y + bob - self.size
        s = self.size
        angle = game_time * 2
        faces = []
        # Simple diamond shape for star
        c1 = COL_STAR
        c2 = (255, 230, 50)
        hw = abs(math.cos(angle)) * s + 5
        v1 = Vector3(self.x, y - s * 1.5, self.z)
        v2 = Vector3(self.x + hw, y, self.z)
        v3 = Vector3(self.x, y + s * 0.5, self.z)
        v4 = Vector3(self.x - hw, y, self.z)
        faces.append(Face([v1, v2, v3, v4], c1))
        # Sparkle
        v5 = Vector3(self.x, y - s, self.z - hw)
        v6 = Vector3(self.x, y - s, self.z + hw)
        v7 = Vector3(self.x, y + s*0.3, self.z)
        faces.append(Face([v5, v6, v7], c2))
        return faces


class PaintingPortal:
    """A painting on a castle wall that serves as a level entrance"""
    def __init__(self, x, y, z, w, h, level_id, facing='z'):
        self.x, self.y, self.z = x, y, z
        self.w, self.h = w, h
        self.level_id = level_id
        self.facing = facing
        self.trigger_radius = 80

    def get_faces(self, game_time):
        hw, hh = self.w/2, self.h/2
        # Painting frame shimmer
        wobble = math.sin(game_time * 3) * 0.1
        # Different colors for different levels
        palette = [
            (60, 180, 60),   # Bob-omb - green
            (160, 140, 120), # Whomp - stone
            (40, 100, 200),  # Jolly Roger - blue
            (200, 220, 255), # Cool Cool - ice
            (100, 60, 120),  # Big Boo - purple
            (90, 80, 70),    # Hazy Maze - dark
            (220, 60, 20),   # Lethal Lava - red
            (220, 200, 130), # Shifting Sand - sand
            (30, 60, 160),   # Dire Docks - deep blue
            (210, 230, 255), # Snowman - white
            (100, 150, 200), # Wet Dry - blue-grey
            (60, 140, 60),   # Tall Tall - green
            (80, 180, 80),   # Tiny Huge - bright green
            (180, 150, 80),  # Tick Tock - gold
            (255, 120, 120), # Rainbow - rainbow
        ]
        idx = self.level_id if 0 <= self.level_id < len(palette) else 0
        c = palette[idx]
        c2 = (100, 70, 40)  # Frame

        faces = []
        if self.facing == 'z':
            # Frame
            faces.append(Face([
                Vector3(self.x - hw - 8, self.y - hh - 8, self.z - 1),
                Vector3(self.x + hw + 8, self.y - hh - 8, self.z - 1),
                Vector3(self.x + hw + 8, self.y + hh + 8, self.z - 1),
                Vector3(self.x - hw - 8, self.y + hh + 8, self.z - 1),
            ], c2))
            # Painting surface
            faces.append(Face([
                Vector3(self.x - hw, self.y - hh, self.z),
                Vector3(self.x + hw, self.y - hh, self.z),
                Vector3(self.x + hw, self.y + hh, self.z),
                Vector3(self.x - hw, self.y + hh, self.z),
            ], c))
        else:
            faces.append(Face([
                Vector3(self.x - 1, self.y - hh - 8, self.z - hw - 8),
                Vector3(self.x - 1, self.y - hh - 8, self.z + hw + 8),
                Vector3(self.x - 1, self.y + hh + 8, self.z + hw + 8),
                Vector3(self.x - 1, self.y + hh + 8, self.z - hw - 8),
            ], c2))
            faces.append(Face([
                Vector3(self.x, self.y - hh, self.z - hw),
                Vector3(self.x, self.y - hh, self.z + hw),
                Vector3(self.x, self.y + hh, self.z + hw),
                Vector3(self.x, self.y + hh, self.z - hw),
            ], c))
        return faces


# ============================================================================
#  LEVEL BLOCK (Platform/Wall geometry)
# ============================================================================

class LevelBlock(Object3D):
    def __init__(self, x, y, z, w, h, d, color):
        super().__init__(x, y, z, color)
        self.width, self.height, self.depth = w, h, d
        self.add_box(w, h, d, color)
        self.is_lava = False
        self.is_water = False
        self.is_ice = False
        self.is_sand = False


class PyramidBlock(Object3D):
    def __init__(self, x, y, z, base_w, h, base_d, color):
        super().__init__(x, y, z, color)
        self.width, self.height, self.depth = base_w, h, base_d
        self.add_pyramid(base_w, h, base_d, color)


# ============================================================================
#  PLAYER
# ============================================================================

class Player(Object3D):
    def __init__(self, x, y, z):
        super().__init__(x, y, z, COL_MARIO_RED)
        self.width = 40
        self.height = 60
        self.depth = 40

        self.vel_x = 0
        self.vel_y = 0
        self.vel_z = 0
        self.on_ground = False
        self.facing_angle = 0

        # Advanced Moves
        self.jump_count = 0
        self.jump_timer = 0
        self.is_long_jumping = False
        self.is_ground_pounding = False
        self.ground_pound_delay = 0

        # Stats
        self.health = 8
        self.max_health = 8
        self.coins = 0
        self.lives = 4
        self.total_stars = 0
        self.stars_collected = {}  # {level_id: set(star_ids)}
        self.invincible_timer = 0

        # Build player model
        # Head
        self.add_box(28, 28, 28, COL_MARIO_SKIN, oy=-30)
        # Hat
        self.add_box(30, 10, 32, COL_MARIO_RED, oy=-48)
        # Hat brim
        self.add_box(10, 4, 16, COL_MARIO_RED, oy=-38, oz=-16)
        # Body
        self.add_box(36, 30, 30, COL_MARIO_RED, oy=-8)
        # Overalls
        self.add_box(38, 24, 32, COL_MARIO_BLUE, oy=14)
        # Left arm
        self.add_box(10, 28, 10, COL_MARIO_RED, ox=-24, oy=-5)
        # Right arm
        self.add_box(10, 28, 10, COL_MARIO_RED, ox=24, oy=-5)
        # Gloves
        self.add_box(12, 10, 12, (255, 255, 255), ox=-24, oy=12)
        self.add_box(12, 10, 12, (255, 255, 255), ox=24, oy=12)
        # Shoes
        self.add_box(16, 10, 20, (90, 50, 20), ox=-10, oy=30)
        self.add_box(16, 10, 20, (90, 50, 20), ox=10, oy=30)

    def reset_position(self, x=0, y=-50, z=0):
        self.x, self.y, self.z = x, y, z
        self.vel_x = self.vel_y = self.vel_z = 0
        self.on_ground = False
        self.jump_count = 0
        self.is_long_jumping = False
        self.is_ground_pounding = False

    def collect_coin(self, coin):
        if not coin.collected:
            coin.collected = True
            val = coin.get_value()
            self.coins += val
            # Heal 1 HP per coin
            self.health = min(self.max_health, self.health + 1)

    def collect_star(self, star, level_id):
        if not star.collected:
            star.collected = True
            if level_id not in self.stars_collected:
                self.stars_collected[level_id] = set()
            self.stars_collected[level_id].add(star.star_id)
            self.total_stars = sum(len(v) for v in self.stars_collected.values())
            return True
        return False

    def take_damage(self, amount=1):
        if self.invincible_timer > 0:
            return False
        self.health -= amount
        self.invincible_timer = 90  # 1.5 seconds
        self.vel_y = JUMP_FORCE * 0.5
        if self.health <= 0:
            self.lives -= 1
            return True  # Dead
        return False

    def update(self, keys, map_objects, camera_angle, dt=1):
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        # --- Input ---
        input_x = 0
        input_z = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: input_x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: input_x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: input_z += 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: input_z -= 1

        is_moving = input_x != 0 or input_z != 0

        # --- Ground Pound ---
        if self.is_ground_pounding:
            self.vel_x *= 0.5
            self.vel_z *= 0.5
            if self.ground_pound_delay > 0:
                self.ground_pound_delay -= 1
                self.vel_y = 0
            else:
                self.vel_y = 20  # Slam down
            if self.on_ground:
                self.is_ground_pounding = False
        elif self.is_long_jumping:
            # Long jump: limited steering
            if self.on_ground:
                self.is_long_jumping = False
        else:
            # Normal movement
            if is_moving:
                target_angle = math.atan2(input_x, input_z) + camera_angle
                diff = target_angle - self.facing_angle
                while diff > math.pi: diff -= 2 * math.pi
                while diff < -math.pi: diff += 2 * math.pi
                turn_amount = max(-ROTATION_SPEED, min(ROTATION_SPEED, diff))
                self.facing_angle += turn_amount

                ax = math.sin(self.facing_angle) * ACCELERATION
                az = math.cos(self.facing_angle) * ACCELERATION
                self.vel_x += ax
                self.vel_z += az
            else:
                self.vel_x *= FRICTION
                self.vel_z *= FRICTION

        # Cap speed
        current_speed = math.sqrt(self.vel_x**2 + self.vel_z**2)
        max_spd = LONG_JUMP_BOOST if self.is_long_jumping else MAX_SPEED
        if current_speed > max_spd:
            scale = max_spd / current_speed
            self.vel_x *= scale
            self.vel_z *= scale
        if current_speed < 0.1:
            self.vel_x = self.vel_z = 0

        self.x += self.vel_x
        self.z += self.vel_z

        # --- Jump Logic ---
        if self.jump_timer > 0:
            self.jump_timer -= 1

        if keys[pygame.K_SPACE] and self.on_ground and not self.is_ground_pounding:
            self.jump_count = self.jump_count + 1 if self.jump_timer > 0 else 1
            if self.jump_count >= 3:
                self.vel_y = TRIPLE_JUMP_FORCE
                self.jump_count = 0
            elif self.jump_count == 2:
                self.vel_y = DOUBLE_JUMP_FORCE
            else:
                self.vel_y = JUMP_FORCE
            self.on_ground = False
            self.jump_timer = 20

        # Long Jump: Z + Space while running
        if keys[pygame.K_z] and keys[pygame.K_SPACE] and self.on_ground and current_speed > 5:
            self.vel_y = LONG_JUMP_FORCE
            boost_x = math.sin(self.facing_angle) * LONG_JUMP_BOOST
            boost_z = math.cos(self.facing_angle) * LONG_JUMP_BOOST
            self.vel_x = boost_x
            self.vel_z = boost_z
            self.is_long_jumping = True
            self.on_ground = False

        # Ground Pound: Z in air
        if keys[pygame.K_z] and not self.on_ground and not self.is_long_jumping and not self.is_ground_pounding:
            if not keys[pygame.K_SPACE]:
                self.is_ground_pounding = True
                self.ground_pound_delay = 8
                self.vel_x *= 0.1
                self.vel_z *= 0.1

        # Gravity
        self.vel_y += GRAVITY
        self.y += self.vel_y

        # --- Collision ---
        ground_level = 0
        hit_platform = False
        on_lava = False
        on_ice = False

        for obj in map_objects:
            if not hasattr(obj, 'width'):
                continue
            pw, pd = obj.width / 2 + self.width / 2, obj.depth / 2 + self.depth / 2
            if abs(self.x - obj.x) < pw and abs(self.z - obj.z) < pd:
                top_surface = obj.y - obj.height / 2
                if self.y + self.height / 2 >= top_surface and \
                   self.y + self.height / 2 <= top_surface + 30 and \
                   self.vel_y >= 0:
                    if top_surface - self.height / 2 < ground_level or not hit_platform:
                        ground_level = top_surface - self.height / 2
                        hit_platform = True
                        if hasattr(obj, 'is_lava') and obj.is_lava:
                            on_lava = True
                        if hasattr(obj, 'is_ice') and obj.is_ice:
                            on_ice = True

        if not hit_platform and self.y + self.height / 2 > 0:
            ground_level = -self.height / 2

        # Fall reset
        if self.y > 600:
            self.reset_position(0, -100, 0)
            self.take_damage(2)
            return

        if self.y >= ground_level and self.vel_y >= 0:
            self.y = ground_level
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        if on_lava and self.invincible_timer <= 0:
            self.take_damage(1)
            self.vel_y = JUMP_FORCE

        if on_ice:
            self.vel_x *= 0.98  # Less friction on ice
            self.vel_z *= 0.98


# ============================================================================
#  LEVEL BUILDER - Creates geometry for each level
# ============================================================================

def build_level(level_id):
    """Build map objects, coins, stars, and start position for a level"""
    blocks = []
    coins = []
    stars = []
    paintings = []
    floor_color = COL_GRASS
    sky_color = (135, 206, 235)
    start_pos = (0, -50, 0)

    if level_id == LEVEL_CASTLE_GROUNDS:
        floor_color = COL_GRASS
        sky_color = (135, 206, 235)
        start_pos = (0, -50, -200)

        # Castle front courtyard
        blocks.append(LevelBlock(0, 0, 0, 1200, 20, 1200, COL_GRASS))

        # Path to castle
        blocks.append(LevelBlock(0, -2, -300, 200, 20, 400, COL_STONE))

        # Castle main body
        blocks.append(LevelBlock(0, -80, 200, 500, 160, 300, COL_CASTLE_WALL))
        # Castle roof
        blocks.append(LevelBlock(0, -180, 200, 520, 20, 320, COL_CASTLE_ROOF))
        # Towers
        blocks.append(LevelBlock(-220, -140, 100, 80, 280, 80, COL_CASTLE_WALL))
        blocks.append(LevelBlock(220, -140, 100, 80, 280, 80, COL_CASTLE_WALL))
        blocks.append(LevelBlock(-220, -300, 100, 90, 40, 90, COL_CASTLE_ROOF))
        blocks.append(LevelBlock(220, -300, 100, 90, 40, 90, COL_CASTLE_ROOF))
        # Center tower
        blocks.append(LevelBlock(0, -200, 250, 120, 120, 120, COL_CASTLE_WALL))
        blocks.append(LevelBlock(0, -280, 250, 130, 40, 130, COL_CASTLE_ROOF))
        # Door
        blocks.append(LevelBlock(0, -40, 45, 80, 100, 10, COL_CASTLE_DOOR))

        # Moat (water blocks)
        for i in range(-3, 4):
            wb = LevelBlock(i * 100, 5, -100, 100, 10, 80, COL_WATER)
            wb.is_water = True
            blocks.append(wb)

        # Bridge
        blocks.append(LevelBlock(0, -5, -100, 100, 10, 80, COL_WOOD))

        # --- Paintings (Level Entrances) ---
        # Floor 1 - accessible from start
        paintings.append(PaintingPortal(-180, -60, 51, 60, 50, LEVEL_BOB_OMB, 'z'))
        paintings.append(PaintingPortal(-80, -60, 51, 60, 50, LEVEL_WHOMP, 'z'))
        paintings.append(PaintingPortal(80, -60, 51, 60, 50, LEVEL_JOLLY, 'z'))
        paintings.append(PaintingPortal(180, -60, 51, 60, 50, LEVEL_COOL_COOL, 'z'))

        # Floor 1 - sides  
        paintings.append(PaintingPortal(-249, -60, 200, 60, 50, LEVEL_BIG_BOO, 'x'))
        paintings.append(PaintingPortal(249, -60, 200, 60, 50, LEVEL_HAZY_MAZE, 'x'))

        # Basement levels
        paintings.append(PaintingPortal(-180, -60, 340, 60, 50, LEVEL_LETHAL_LAVA, 'z'))
        paintings.append(PaintingPortal(-80, -60, 340, 60, 50, LEVEL_SHIFTING_SAND, 'z'))
        paintings.append(PaintingPortal(80, -60, 340, 60, 50, LEVEL_DIRE_DOCKS, 'z'))
        paintings.append(PaintingPortal(180, -60, 340, 60, 50, LEVEL_SNOWMAN, 'z'))

        # Upper levels  
        paintings.append(PaintingPortal(-120, -180, 200, 50, 40, LEVEL_WET_DRY, 'z'))
        paintings.append(PaintingPortal(0, -180, 200, 50, 40, LEVEL_TALL_TALL, 'z'))
        paintings.append(PaintingPortal(120, -180, 200, 50, 40, LEVEL_TINY_HUGE, 'z'))
        paintings.append(PaintingPortal(-60, -180, 300, 50, 40, LEVEL_TICK_TOCK, 'z'))
        paintings.append(PaintingPortal(60, -180, 300, 50, 40, LEVEL_RAINBOW, 'z'))

        # Some courtyard coins
        for i in range(-4, 5):
            coins.append(Coin(i * 60, -10, -300))

    elif level_id == LEVEL_BOB_OMB:
        sky_color = (135, 206, 235)
        floor_color = COL_GRASS
        start_pos = (0, -50, 0)

        # Main ground
        blocks.append(LevelBlock(0, 0, 0, 800, 20, 800, COL_GRASS))
        # Path up the mountain
        blocks.append(LevelBlock(0, -30, 200, 150, 40, 200, COL_DIRT))
        blocks.append(LevelBlock(100, -60, 350, 120, 40, 150, COL_DIRT))
        blocks.append(LevelBlock(200, -90, 450, 120, 40, 120, COL_DIRT))
        blocks.append(LevelBlock(150, -120, 550, 150, 40, 120, COL_DIRT))
        blocks.append(LevelBlock(50, -150, 650, 120, 40, 120, COL_DIRT))
        # Summit
        blocks.append(LevelBlock(0, -180, 750, 200, 40, 200, COL_STONE))
        # Bridge
        blocks.append(LevelBlock(-200, -20, 100, 80, 10, 200, COL_WOOD))
        # Island
        blocks.append(LevelBlock(-300, -60, 250, 120, 30, 120, COL_GRASS))

        # Coins along path
        for i in range(8):
            coins.append(Coin(20 + i * 10, -40 - i * 10, 200 + i * 70))
        # Red coins scattered
        for i in range(8):
            angle = i * math.pi / 4
            coins.append(Coin(math.cos(angle) * 200, -10, math.sin(angle) * 200 + 400, 1))

        # Stars
        stars.append(Star(0, -220, 750, 0))  # Summit
        stars.append(Star(-300, -100, 250, 1))  # Island
        stars.append(Star(300, -30, 0, 2))  # Far side

    elif level_id == LEVEL_WHOMP:
        sky_color = (180, 200, 230)
        floor_color = COL_STONE
        start_pos = (0, -50, 0)

        # Base fortress
        blocks.append(LevelBlock(0, 0, 0, 400, 20, 400, COL_STONE))
        # Ramps/steps going up
        for i in range(8):
            blocks.append(LevelBlock(-100 + i*30, -i*30, 100 + i*40, 80, 20, 80, COL_STONE))
        # Fortress walls
        blocks.append(LevelBlock(-150, -60, 200, 20, 120, 200, (140, 140, 140)))
        blocks.append(LevelBlock(150, -60, 200, 20, 120, 200, (140, 140, 140)))
        # Top platform
        blocks.append(LevelBlock(0, -240, 400, 300, 20, 200, COL_STONE))
        # Tower
        blocks.append(LevelBlock(0, -320, 400, 80, 140, 80, (180, 170, 160)))
        # Floating blocks
        blocks.append(LevelBlock(200, -100, 0, 60, 15, 60, COL_STONE))
        blocks.append(LevelBlock(280, -140, 100, 60, 15, 60, COL_STONE))

        for i in range(10):
            coins.append(Coin(-80 + i*20, -i*30 - 10, 100 + i*40))
        stars.append(Star(0, -280, 400, 0))
        stars.append(Star(0, -380, 400, 1))
        stars.append(Star(280, -180, 100, 2))

    elif level_id == LEVEL_JOLLY:
        sky_color = (100, 160, 220)
        floor_color = COL_WATER
        start_pos = (0, -80, -200)

        # Shore
        blocks.append(LevelBlock(0, 0, -300, 400, 20, 200, COL_SAND))
        # Underwater floor
        wb = LevelBlock(0, 40, 200, 800, 20, 600, (60, 100, 160))
        wb.is_water = True
        blocks.append(wb)
        # Sunken ship (boxes)
        blocks.append(LevelBlock(100, 20, 300, 120, 40, 200, COL_WOOD))
        blocks.append(LevelBlock(100, -10, 350, 80, 30, 100, COL_WOOD))
        # Cliffs
        blocks.append(LevelBlock(-250, -40, 0, 80, 100, 200, COL_STONE))
        blocks.append(LevelBlock(-250, -100, 0, 60, 40, 60, COL_STONE))
        # Pillars
        blocks.append(LevelBlock(200, -30, -100, 40, 80, 40, COL_STONE))
        blocks.append(LevelBlock(300, -30, 0, 40, 80, 40, COL_STONE))

        for i in range(6):
            coins.append(Coin(-100 + i*40, -10, -250))
        for i in range(5):
            coins.append(Coin(100, 10, 200 + i*60))
        stars.append(Star(100, -40, 400, 0))
        stars.append(Star(-250, -140, 0, 1))
        stars.append(Star(300, -80, 0, 2))

    elif level_id == LEVEL_COOL_COOL:
        sky_color = (200, 220, 255)
        floor_color = COL_SNOW
        start_pos = (0, -250, 0)

        # Mountain peak (start here)
        blocks.append(LevelBlock(0, -200, 0, 200, 20, 200, COL_SNOW))
        # Slide down
        for i in range(10):
            b = LevelBlock(-50 + i*30, -200 + i*25, i*80, 100, 15, 100, COL_ICE)
            b.is_ice = True
            blocks.append(b)
        # Bottom area
        blocks.append(LevelBlock(200, 0, 800, 500, 20, 400, COL_SNOW))
        # Penguin area
        blocks.append(LevelBlock(300, -20, 900, 100, 30, 100, COL_ICE))
        # Bridge
        blocks.append(LevelBlock(100, -100, 400, 60, 10, 200, COL_WOOD))
        # Snowman
        blocks.append(LevelBlock(-100, -220, -50, 40, 40, 40, COL_SNOW))

        for i in range(8):
            coins.append(Coin(-30 + i*25, -195 + i*25, i * 80 + 20))
        stars.append(Star(200, -40, 900, 0))
        stars.append(Star(-100, -270, -50, 1))
        stars.append(Star(300, -60, 900, 2))

    elif level_id == LEVEL_BIG_BOO:
        sky_color = (40, 20, 60)
        floor_color = (60, 50, 40)
        start_pos = (0, -50, -200)

        # Haunted mansion
        blocks.append(LevelBlock(0, 0, 0, 600, 20, 600, (80, 70, 60)))
        # Mansion walls
        blocks.append(LevelBlock(-250, -80, 0, 20, 160, 400, COL_GHOST))
        blocks.append(LevelBlock(250, -80, 0, 20, 160, 400, COL_GHOST))
        blocks.append(LevelBlock(0, -80, 200, 500, 160, 20, COL_GHOST))
        # Second floor
        blocks.append(LevelBlock(0, -160, 0, 500, 15, 500, (90, 80, 70)))
        # Roof
        blocks.append(LevelBlock(0, -300, 0, 520, 15, 420, (60, 50, 50)))
        # Merry-go-round basement
        blocks.append(LevelBlock(0, 60, 0, 200, 20, 200, (50, 40, 35)))
        # Library shelves
        blocks.append(LevelBlock(-150, -80, -100, 20, 100, 60, COL_WOOD))
        blocks.append(LevelBlock(-150, -80, 50, 20, 100, 60, COL_WOOD))

        for i in range(8):
            angle = i * math.pi / 4
            coins.append(Coin(math.cos(angle)*100, -10, math.sin(angle)*100))
        stars.append(Star(0, -200, 0, 0))
        stars.append(Star(0, 30, 0, 1))
        stars.append(Star(200, -200, 100, 2))

    elif level_id == LEVEL_HAZY_MAZE:
        sky_color = (60, 50, 50)
        floor_color = COL_CAVE
        start_pos = (0, -50, 0)

        # Cave entrance
        blocks.append(LevelBlock(0, 0, 0, 400, 20, 400, COL_CAVE))
        # Maze walls
        blocks.append(LevelBlock(-100, -40, 0, 20, 80, 300, (80, 70, 60)))
        blocks.append(LevelBlock(100, -40, 100, 20, 80, 200, (80, 70, 60)))
        blocks.append(LevelBlock(0, -40, -150, 200, 80, 20, (80, 70, 60)))
        # Rolling rocks area
        blocks.append(LevelBlock(300, 0, 0, 200, 20, 300, COL_CAVE))
        # Cavern with underground lake
        wb = LevelBlock(0, 40, 400, 400, 20, 300, COL_DARK_WATER)
        wb.is_water = True
        blocks.append(wb)
        # Platforms in cavern
        blocks.append(LevelBlock(-100, -20, 400, 80, 20, 80, COL_STONE))
        blocks.append(LevelBlock(100, -40, 500, 80, 20, 80, COL_STONE))
        # Metal cap area
        blocks.append(LevelBlock(0, -60, 600, 100, 20, 100, (120, 130, 140)))

        for i in range(6):
            coins.append(Coin(i*50 - 100, -10, 0))
        stars.append(Star(0, -80, 600, 0))
        stars.append(Star(100, -80, 500, 1))
        stars.append(Star(300, -40, 0, 2))

    elif level_id == LEVEL_LETHAL_LAVA:
        sky_color = (80, 20, 10)
        floor_color = COL_LAVA
        start_pos = (0, -80, -200)

        # Starting platform
        blocks.append(LevelBlock(0, -30, -200, 200, 30, 200, COL_STONE))
        # Lava field
        lava = LevelBlock(0, 10, 200, 800, 10, 800, COL_LAVA)
        lava.is_lava = True
        blocks.append(lava)
        # Platforms over lava
        blocks.append(LevelBlock(-100, -20, 0, 80, 30, 80, COL_STONE))
        blocks.append(LevelBlock(100, -20, 100, 80, 30, 80, COL_STONE))
        blocks.append(LevelBlock(0, -20, 200, 80, 30, 80, COL_STONE))
        blocks.append(LevelBlock(-150, -20, 300, 80, 30, 80, COL_STONE))
        blocks.append(LevelBlock(150, -40, 400, 100, 30, 100, COL_STONE))
        # Bully platform
        blocks.append(LevelBlock(0, -60, 500, 200, 30, 200, COL_STONE))
        # Volcano
        blocks.append(LevelBlock(300, -80, 300, 150, 160, 150, (100, 40, 20)))
        blocks.append(LevelBlock(300, -180, 300, 80, 40, 80, (120, 50, 20)))

        for i in range(5):
            coins.append(Coin(-100 + i*60, -40, i*100))
        stars.append(Star(0, -100, 500, 0))
        stars.append(Star(300, -220, 300, 1))
        stars.append(Star(-150, -60, 300, 2))

    elif level_id == LEVEL_SHIFTING_SAND:
        sky_color = (220, 190, 130)
        floor_color = COL_SAND
        start_pos = (0, -50, -300)

        # Desert floor
        sb = LevelBlock(0, 0, 0, 1000, 20, 1000, COL_SAND)
        sb.is_sand = True
        blocks.append(sb)
        # Oasis
        blocks.append(LevelBlock(-300, -5, -200, 150, 15, 150, COL_GRASS))
        # Pyramid (using boxes stacked)
        blocks.append(LevelBlock(200, -20, 200, 300, 20, 300, COL_SAND))
        blocks.append(LevelBlock(200, -60, 200, 240, 20, 240, (220, 200, 140)))
        blocks.append(LevelBlock(200, -100, 200, 180, 20, 180, (210, 190, 130)))
        blocks.append(LevelBlock(200, -140, 200, 120, 20, 120, (200, 180, 120)))
        blocks.append(LevelBlock(200, -180, 200, 60, 20, 60, (190, 170, 110)))
        # Pillars
        blocks.append(LevelBlock(-200, -40, 200, 40, 80, 40, COL_SAND))
        blocks.append(LevelBlock(-100, -40, 300, 40, 80, 40, COL_SAND))
        blocks.append(LevelBlock(-200, -40, 400, 40, 80, 40, COL_SAND))
        blocks.append(LevelBlock(-100, -40, 100, 40, 80, 40, COL_SAND))

        for i in range(8):
            coins.append(Coin(-100 + i*40, -10, -200))
        stars.append(Star(200, -220, 200, 0))  # Top of pyramid
        stars.append(Star(-300, -30, -200, 1))  # Oasis
        stars.append(Star(-200, -100, 300, 2))

    elif level_id == LEVEL_DIRE_DOCKS:
        sky_color = (30, 40, 80)
        floor_color = COL_DARK_WATER
        start_pos = (0, -50, -200)

        # Dock
        blocks.append(LevelBlock(0, 0, -200, 300, 20, 200, COL_STONE))
        # Water
        water = LevelBlock(0, 20, 200, 600, 10, 600, COL_DARK_WATER)
        water.is_water = True
        blocks.append(water)
        # Submarine bay (boxes)
        blocks.append(LevelBlock(0, 0, 400, 200, 60, 100, (80, 80, 100)))
        blocks.append(LevelBlock(0, -40, 400, 150, 30, 200, (90, 90, 110)))
        # Poles/pillars
        blocks.append(LevelBlock(-200, -30, 100, 30, 80, 30, COL_STONE))
        blocks.append(LevelBlock(200, -30, 100, 30, 80, 30, COL_STONE))
        blocks.append(LevelBlock(-200, -30, 300, 30, 80, 30, COL_STONE))
        blocks.append(LevelBlock(200, -30, 300, 30, 80, 30, COL_STONE))
        # Cage
        blocks.append(LevelBlock(0, -80, 100, 100, 15, 100, (100, 100, 120)))

        for i in range(6):
            coins.append(Coin(i*50 - 100, -10, -150))
        stars.append(Star(0, -60, 400, 0))
        stars.append(Star(0, -120, 100, 1))
        stars.append(Star(-200, -80, 300, 2))

    elif level_id == LEVEL_SNOWMAN:
        sky_color = (200, 215, 240)
        floor_color = COL_SNOW
        start_pos = (0, -50, -200)

        # Snow field
        ice = LevelBlock(0, 0, 0, 600, 20, 600, COL_SNOW)
        ice.is_ice = True
        blocks.append(ice)
        # Frozen pond
        fp = LevelBlock(0, 5, 0, 200, 10, 200, COL_ICE)
        fp.is_ice = True
        blocks.append(fp)
        # Snowman mountain
        blocks.append(LevelBlock(0, -40, 300, 200, 60, 200, COL_SNOW))
        blocks.append(LevelBlock(0, -100, 300, 150, 60, 150, COL_SNOW))
        blocks.append(LevelBlock(0, -160, 300, 100, 60, 100, COL_SNOW))
        blocks.append(LevelBlock(0, -200, 300, 60, 40, 60, COL_SNOW))
        # Igloo
        blocks.append(LevelBlock(-200, -20, -100, 80, 50, 80, COL_ICE))
        # Ice bridges
        ib = LevelBlock(150, -30, 100, 40, 10, 200, COL_ICE)
        ib.is_ice = True
        blocks.append(ib)

        for i in range(8):
            coins.append(Coin(i*30 - 100, -10, -100))
        stars.append(Star(0, -240, 300, 0))
        stars.append(Star(-200, -60, -100, 1))
        stars.append(Star(200, -40, 200, 2))

    elif level_id == LEVEL_WET_DRY:
        sky_color = (160, 180, 220)
        floor_color = COL_WATER
        start_pos = (0, -150, -200)

        # Town blocks at various heights
        blocks.append(LevelBlock(0, 0, 0, 600, 20, 600, COL_STONE))
        blocks.append(LevelBlock(-150, -40, -100, 120, 60, 120, (180, 170, 160)))
        blocks.append(LevelBlock(150, -80, -100, 120, 140, 120, (170, 160, 150)))
        blocks.append(LevelBlock(-150, -80, 150, 120, 140, 120, (175, 165, 155)))
        blocks.append(LevelBlock(150, -40, 150, 120, 60, 120, (180, 170, 160)))
        # Tall pillar
        blocks.append(LevelBlock(0, -120, 0, 60, 220, 60, (190, 180, 170)))
        # Water crystal platforms
        blocks.append(LevelBlock(-200, -100, 0, 40, 10, 40, COL_ICE))
        blocks.append(LevelBlock(200, -140, 0, 40, 10, 40, COL_ICE))
        # Arrow lifts
        blocks.append(LevelBlock(0, -160, -200, 80, 10, 80, (200, 200, 50)))

        for i in range(8):
            coins.append(Coin(i*60 - 200, -30, -200))
        stars.append(Star(0, -180, 0, 0))  # Top of pillar
        stars.append(Star(150, -160, -100, 1))
        stars.append(Star(0, -200, -200, 2))

    elif level_id == LEVEL_TALL_TALL:
        sky_color = (140, 200, 240)
        floor_color = COL_GRASS
        start_pos = (0, -50, -200)

        # Base
        blocks.append(LevelBlock(0, 0, 0, 400, 20, 400, COL_GRASS))
        # Mountain spiral
        for i in range(12):
            angle = i * math.pi / 6
            r = 200
            x = math.cos(angle) * r
            z = math.sin(angle) * r + 200
            blocks.append(LevelBlock(x, -i*30 - 20, z, 80, 15, 80, COL_DIRT))
        # Summit
        blocks.append(LevelBlock(0, -380, 200, 150, 20, 150, COL_STONE))
        # Mushroom platforms
        blocks.append(LevelBlock(-200, -80, 100, 50, 10, 50, (200, 60, 60)))
        blocks.append(LevelBlock(-250, -140, 200, 50, 10, 50, (200, 80, 80)))
        # Waterfall cliff
        blocks.append(LevelBlock(250, -100, 0, 60, 200, 60, COL_STONE))
        wb = LevelBlock(250, 0, 80, 30, 10, 100, COL_WATER)
        wb.is_water = True
        blocks.append(wb)

        for i in range(12):
            angle = i * math.pi / 6
            coins.append(Coin(math.cos(angle)*200, -i*30-10, math.sin(angle)*200+200))
        stars.append(Star(0, -420, 200, 0))
        stars.append(Star(-250, -180, 200, 1))
        stars.append(Star(250, -140, 0, 2))

    elif level_id == LEVEL_TINY_HUGE:
        sky_color = (140, 210, 140)
        floor_color = COL_GRASS
        start_pos = (0, -50, -200)

        # Large island
        blocks.append(LevelBlock(0, 0, 0, 500, 20, 500, COL_GRASS))
        # Hills
        blocks.append(LevelBlock(-100, -30, 100, 150, 40, 150, COL_GRASS))
        blocks.append(LevelBlock(100, -60, 200, 120, 100, 120, COL_DIRT))
        blocks.append(LevelBlock(100, -120, 200, 80, 20, 80, COL_GRASS))
        # Beach
        blocks.append(LevelBlock(0, 5, -300, 300, 10, 100, COL_SAND))
        # Tiny island nearby (scaled small)
        blocks.append(LevelBlock(350, -10, 0, 100, 20, 100, COL_GRASS))
        blocks.append(LevelBlock(350, -25, 0, 60, 20, 60, COL_DIRT))
        # Koopa beach
        blocks.append(LevelBlock(-250, 0, -100, 100, 15, 100, COL_SAND))
        # Winding path
        for i in range(5):
            blocks.append(LevelBlock(-200 + i*50, -10-i*5, 300+i*30, 60, 15, 60, COL_DIRT))

        for i in range(6):
            coins.append(Coin(i*60 - 150, -10, -250))
        stars.append(Star(100, -160, 200, 0))
        stars.append(Star(350, -50, 0, 1))
        stars.append(Star(-200, -40, 450, 2))

    elif level_id == LEVEL_TICK_TOCK:
        sky_color = (80, 70, 60)
        floor_color = COL_CLOCK
        start_pos = (0, -50, 0)

        # Clock interior - vertical level
        blocks.append(LevelBlock(0, 0, 0, 300, 20, 300, COL_CLOCK))
        # Moving platforms (static representation)
        blocks.append(LevelBlock(-80, -50, 0, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(80, -100, 50, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(-60, -150, 100, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(60, -200, 50, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(0, -250, 0, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(-80, -300, -50, 80, 10, 60, (200, 180, 100)))
        blocks.append(LevelBlock(80, -350, 0, 80, 10, 60, (200, 180, 100)))
        # Top
        blocks.append(LevelBlock(0, -400, 0, 200, 20, 200, COL_CLOCK))
        # Gears (decorative boxes)
        blocks.append(LevelBlock(-120, -200, -80, 30, 30, 30, (160, 140, 80)))
        blocks.append(LevelBlock(120, -280, -80, 30, 30, 30, (160, 140, 80)))
        # Pendulum bar
        blocks.append(LevelBlock(0, -180, -100, 10, 80, 10, (120, 100, 60)))

        for i in range(7):
            coins.append(Coin(0, -50 - i*50, 0))
        stars.append(Star(0, -440, 0, 0))
        stars.append(Star(-80, -340, -50, 1))
        stars.append(Star(80, -200, 50, 2))

    elif level_id == LEVEL_RAINBOW:
        sky_color = (100, 150, 255)
        floor_color = (200, 200, 255)
        start_pos = (0, -80, -200)

        # Rainbow platforms - floating in the sky
        colors = [COL_RAINBOW1, COL_RAINBOW2, COL_RAINBOW3, (255,200,100), (200,100,255)]
        blocks.append(LevelBlock(0, -30, -200, 150, 15, 150, colors[0]))
        blocks.append(LevelBlock(150, -60, -100, 100, 15, 80, colors[1]))
        blocks.append(LevelBlock(250, -90, 0, 100, 15, 80, colors[2]))
        blocks.append(LevelBlock(200, -120, 150, 100, 15, 80, colors[3]))
        blocks.append(LevelBlock(100, -150, 250, 100, 15, 80, colors[4]))
        blocks.append(LevelBlock(0, -180, 350, 120, 15, 100, colors[0]))
        blocks.append(LevelBlock(-120, -210, 250, 100, 15, 80, colors[1]))
        blocks.append(LevelBlock(-200, -240, 100, 100, 15, 80, colors[2]))
        blocks.append(LevelBlock(-150, -270, -50, 100, 15, 80, colors[3]))
        blocks.append(LevelBlock(0, -300, -100, 150, 15, 150, colors[4]))
        # Flying carpet area
        blocks.append(LevelBlock(300, -200, 200, 80, 8, 80, (180, 120, 60)))
        # House in the sky
        blocks.append(LevelBlock(-300, -180, 0, 120, 80, 120, (200, 180, 160)))
        blocks.append(LevelBlock(-300, -240, 0, 130, 20, 130, COL_CASTLE_ROOF))

        for i in range(10):
            coins.append(Coin(100 - i*30, -30 - i*25, -200 + i*55))
        stars.append(Star(0, -340, -100, 0))
        stars.append(Star(-300, -260, 0, 1))
        stars.append(Star(300, -240, 200, 2))

    elif level_id == LEVEL_BOWSER_1:
        sky_color = (20, 10, 30)
        floor_color = (40, 30, 40)
        start_pos = (0, -50, 0)
        blocks.append(LevelBlock(0, 0, 0, 200, 20, 200, (80, 60, 80)))
        for i in range(8):
            blocks.append(LevelBlock(i*80, -i*10, i*80+100, 80, 15, 80, COL_PURPLE))
        blocks.append(LevelBlock(640, -80, 800, 200, 20, 200, (100, 40, 40)))
        stars.append(Star(640, -120, 800, 0))

    elif level_id == LEVEL_BOWSER_2:
        sky_color = (40, 10, 5)
        floor_color = COL_LAVA
        start_pos = (0, -50, 0)
        blocks.append(LevelBlock(0, 0, 0, 200, 20, 200, COL_STONE))
        lava = LevelBlock(0, 20, 400, 600, 10, 600, COL_LAVA)
        lava.is_lava = True
        blocks.append(lava)
        for i in range(6):
            blocks.append(LevelBlock(i*100-200, -20-i*10, i*80+100, 70, 15, 70, COL_STONE))
        blocks.append(LevelBlock(200, -80, 600, 200, 20, 200, (120, 40, 40)))
        stars.append(Star(200, -120, 600, 0))

    elif level_id == LEVEL_BOWSER_3:
        sky_color = (10, 5, 20)
        floor_color = (30, 20, 40)
        start_pos = (0, -50, 0)
        blocks.append(LevelBlock(0, 0, 0, 150, 20, 150, COL_STONE))
        for i in range(10):
            angle = i * math.pi / 5
            r = 200 + i * 20
            blocks.append(LevelBlock(math.cos(angle)*r, -i*20, math.sin(angle)*r, 70, 15, 70, COL_PURPLE))
        blocks.append(LevelBlock(0, -200, 500, 250, 20, 250, (140, 40, 40)))
        stars.append(Star(0, -240, 500, 0))

    return blocks, coins, stars, paintings, floor_color, sky_color, start_pos


# ============================================================================
#  RENDERER
# ============================================================================

class Renderer:
    def __init__(self, screen):
        self.screen = screen

    def project_and_draw(self, render_list, camera_pos, render_yaw):
        screen_faces = []
        for face in render_list:
            cam_verts = []
            in_front = True
            for v in face.vertices:
                x = v.x - camera_pos.x
                y = v.y - camera_pos.y
                z = v.z - camera_pos.z
                rx, rz = rotate_point_y(x, z, 0, 0, render_yaw)
                if rz <= 1:
                    in_front = False
                    break
                scale = FOV / rz
                sx = int(rx * scale + WIDTH / 2)
                sy = int(ry * scale + HEIGHT / 2) if 'ry' in dir() else int(y * scale + HEIGHT / 2)
                cam_verts.append((sx, sy, rz))
            if in_front and cam_verts:
                avg_z = sum(v[2] for v in cam_verts) / len(cam_verts)
                pts = [(v[0], v[1]) for v in cam_verts]
                screen_faces.append((avg_z, face.color, pts))

        screen_faces.sort(key=lambda x: x[0], reverse=True)

        for _, color, points in screen_faces:
            if len(points) >= 3:
                pygame.draw.polygon(self.screen, color, points)
                # Edge lines for depth
                pygame.draw.polygon(self.screen, tuple(max(0, c-30) for c in color), points, 1)


def render_scene(screen, player, map_objects, coins, stars, paintings, floor_color,
                 camera_pos, cam_angle, game_time):
    render_yaw = -cam_angle
    render_list = []

    # Player faces
    for face in player.faces:
        world_verts = []
        for v in face.vertices:
            rx, rz = rotate_point_y(v.x, v.z, 0, 0, player.facing_angle)
            world_verts.append(Vector3(rx + player.x, v.y + player.y, rz + player.z))
        render_list.append(Face(world_verts, face.color))

    # Map faces
    for obj in map_objects:
        for face in obj.faces:
            world_verts = []
            for v in face.vertices:
                world_verts.append(Vector3(v.x + obj.x, v.y + obj.y, v.z + obj.z))
            render_list.append(Face(world_verts, face.color))

    # Coins
    for coin in coins:
        for face in coin.get_faces(game_time):
            render_list.append(face)

    # Stars
    for star in stars:
        for face in star.get_faces(game_time):
            render_list.append(face)

    # Paintings
    for painting in paintings:
        for face in painting.get_faces(game_time):
            render_list.append(face)

    # Floor
    render_list.append(Face([
        Vector3(-3000, 0, -3000), Vector3(3000, 0, -3000),
        Vector3(3000, 0, 3000), Vector3(-3000, 0, 3000)
    ], floor_color))

    # Project and draw
    screen_faces = []
    for face in render_list:
        cam_verts = []
        in_front = True
        for v in face.vertices:
            x = v.x - camera_pos.x
            y = v.y - camera_pos.y
            z = v.z - camera_pos.z
            rx, rz = rotate_point_y(x, z, 0, 0, render_yaw)
            if rz <= 1:
                in_front = False
                break
            scale = FOV / rz
            sx = int(rx * scale + WIDTH / 2)
            sy = int(y * scale + HEIGHT / 2)
            cam_verts.append((sx, sy, rz))
        if in_front and cam_verts:
            avg_z = sum(v[2] for v in cam_verts) / len(cam_verts)
            pts = [(v[0], v[1]) for v in cam_verts]
            screen_faces.append((avg_z, face.color, pts))

    screen_faces.sort(key=lambda x: x[0], reverse=True)
    for _, color, points in screen_faces:
        if len(points) >= 3:
            pygame.draw.polygon(screen, color, points)
            edge = tuple(max(0, c - 30) for c in color)
            pygame.draw.polygon(screen, edge, points, 1)


# ============================================================================
#  HUD
# ============================================================================

def draw_hud(screen, player, level_id, font_large, font_small, show_star_name=None, star_name_timer=0):
    # Star count - top left
    star_icon = "★"
    star_text = f"{star_icon} x {player.total_stars}"
    surf = font_large.render(star_text, True, COL_GOLD)
    screen.blit(surf, (20, 15))

    # Coin count
    coin_text = f"Coins: {player.coins}"
    surf2 = font_small.render(coin_text, True, COL_COIN)
    screen.blit(surf2, (20, 50))

    # Lives
    lives_text = f"Lives x {player.lives}"
    surf3 = font_small.render(lives_text, True, (255, 255, 255))
    screen.blit(surf3, (20, 70))

    # Health meter (SM64 pie chart style - simplified as bar)
    health_x, health_y = WIDTH - 180, 20
    pygame.draw.rect(screen, (40, 40, 40), (health_x - 2, health_y - 2, 164, 24))
    bar_w = int(160 * (player.health / player.max_health))
    bar_color = (50, 200, 50) if player.health > 3 else (200, 200, 50) if player.health > 1 else (200, 50, 50)
    pygame.draw.rect(screen, bar_color, (health_x, health_y, bar_w, 20))
    hp_text = font_small.render(f"Power: {player.health}/{player.max_health}", True, (255, 255, 255))
    screen.blit(hp_text, (health_x, health_y + 22))

    # Level name - top center
    name = LEVEL_NAMES.get(level_id, "Unknown")
    name_surf = font_small.render(name, True, (255, 255, 255))
    screen.blit(name_surf, (WIDTH // 2 - name_surf.get_width() // 2, 10))

    # Star acquisition message
    if show_star_name and star_name_timer > 0:
        alpha = min(255, star_name_timer * 4)
        star_surf = font_large.render(f"★ {show_star_name} ★", True, COL_GOLD)
        x = WIDTH // 2 - star_surf.get_width() // 2
        y = HEIGHT // 3
        screen.blit(star_surf, (x, y))


def draw_controls_help(screen, font):
    controls = [
        "Arrow Keys / WASD: Move",
        "Space: Jump (1x/2x/3x)",
        "Z + Space: Long Jump",
        "Z (in air): Ground Pound",
        "Q / E: Rotate Camera",
        "ESC: Pause / Back",
        "Enter: Select / Enter Painting"
    ]
    y = HEIGHT - len(controls) * 18 - 10
    for line in controls:
        surf = font.render(line, True, (200, 200, 200))
        screen.blit(surf, (10, y))
        y += 18


# ============================================================================
#  TITLE SCREEN & MENUS
# ============================================================================

def draw_title_screen(screen, font_title, font_large, font_small, frame):
    # Sky gradient
    for y in range(HEIGHT):
        r = int(20 + 80 * (y / HEIGHT))
        g = int(30 + 100 * (y / HEIGHT))
        b = int(120 + 120 * (y / HEIGHT))
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

    # Animated stars in background
    random.seed(42)
    for i in range(50):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, HEIGHT // 2)
        brightness = int(150 + 100 * math.sin(frame * 0.05 + i))
        brightness = max(50, min(255, brightness))
        pygame.draw.circle(screen, (brightness, brightness, brightness), (sx, sy), 2)

    # Title
    bob = math.sin(frame * 0.03) * 10
    title1 = font_title.render("Cat's SM64", True, COL_GOLD)
    title2 = font_large.render("Python Port 1.0", True, (255, 255, 200))

    # Shadow
    screen.blit(font_title.render("Cat's SM64", True, (80, 60, 0)),
                (WIDTH // 2 - title1.get_width() // 2 + 3, int(100 + bob + 3)))
    screen.blit(title1, (WIDTH // 2 - title1.get_width() // 2, int(100 + bob)))
    screen.blit(title2, (WIDTH // 2 - title2.get_width() // 2, int(170 + bob)))

    # Copyright
    copy1 = font_small.render("© Nintendo 1996-2026", True, (180, 180, 180))
    copy2 = font_small.render("© AC Corp 1999-2026", True, (180, 180, 180))
    screen.blit(copy1, (WIDTH // 2 - copy1.get_width() // 2, 220))
    screen.blit(copy2, (WIDTH // 2 - copy2.get_width() // 2, 240))

    # Blinking prompt
    if (frame // 40) % 2 == 0:
        prompt = font_large.render("Press ENTER to Start", True, (255, 255, 255))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 350))

    # Mario face (simple pixel art)
    cx, cy = WIDTH // 2, 450
    # Hat
    pygame.draw.rect(screen, COL_MARIO_RED, (cx - 30, cy - 40, 60, 20))
    pygame.draw.rect(screen, COL_MARIO_RED, (cx - 40, cy - 30, 80, 10))
    # Face
    pygame.draw.rect(screen, COL_MARIO_SKIN, (cx - 30, cy - 20, 60, 40))
    # Eyes
    pygame.draw.rect(screen, (255, 255, 255), (cx - 20, cy - 15, 12, 12))
    pygame.draw.rect(screen, (255, 255, 255), (cx + 8, cy - 15, 12, 12))
    pygame.draw.rect(screen, (0, 0, 0), (cx - 16, cy - 12, 6, 6))
    pygame.draw.rect(screen, (0, 0, 0), (cx + 12, cy - 12, 6, 6))
    # Mustache
    pygame.draw.rect(screen, (60, 30, 10), (cx - 25, cy + 5, 50, 8))
    # Nose
    pygame.draw.rect(screen, COL_MARIO_SKIN, (cx - 8, cy - 5, 16, 14))

    # Version info
    ver = font_small.render("v1.0 - All 15 Courses + Castle + Bowser Stages", True, (120, 120, 150))
    screen.blit(ver, (WIDTH // 2 - ver.get_width() // 2, HEIGHT - 30))


def draw_file_select(screen, font_title, font_large, font_small, selected, frame):
    screen.fill((40, 30, 60))

    title = font_title.render("Select File", True, COL_GOLD)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

    files = ["File A - Mario", "File B - Luigi", "File C - Wario", "File D - Toad"]
    for i, name in enumerate(files):
        y = 150 + i * 80
        color = (255, 255, 100) if i == selected else (200, 200, 200)
        bg_color = (80, 60, 120) if i == selected else (50, 40, 70)
        pygame.draw.rect(screen, bg_color, (WIDTH // 2 - 150, y - 5, 300, 50), border_radius=8)
        if i == selected:
            pygame.draw.rect(screen, COL_GOLD, (WIDTH // 2 - 150, y - 5, 300, 50), 2, border_radius=8)
        text = font_large.render(name, True, color)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y + 8))

    inst = font_small.render("↑↓ Select  |  Enter: Choose  |  Stars: 0", True, (150, 150, 180))
    screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, HEIGHT - 40))


def draw_letter_screen(screen, font_large, font_small, frame):
    # Parchment background
    screen.fill((240, 220, 180))
    pygame.draw.rect(screen, (200, 180, 140), (40, 40, WIDTH - 80, HEIGHT - 80))
    pygame.draw.rect(screen, (160, 140, 100), (40, 40, WIDTH - 80, HEIGHT - 80), 3)

    lines = [
        "Dear Mario,",
        "",
        "Please come to the castle.",
        "I've baked a cake for you.",
        "",
        "Yours truly,",
        "Princess Toadstool",
        "",
        "     ~ Peach ~",
    ]

    y = 80
    for line in lines:
        color = (80, 40, 20)
        if "Peach" in line:
            color = (200, 80, 120)
        surf = font_large.render(line, True, color)
        screen.blit(surf, (100, y))
        y += 40

    # Seal
    pygame.draw.circle(screen, (200, 50, 50), (WIDTH - 120, HEIGHT - 120), 30)
    pygame.draw.circle(screen, (220, 80, 80), (WIDTH - 120, HEIGHT - 120), 25)
    seal = font_small.render("♛", True, (255, 200, 50))
    screen.blit(seal, (WIDTH - 128, HEIGHT - 130))

    if (frame // 30) % 2 == 0:
        prompt = font_small.render("Press ENTER to continue...", True, (100, 70, 40))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT - 60))


def draw_pause_screen(screen, font_title, font_large, font_small, player, selected):
    # Overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    title = font_title.render("PAUSE", True, (255, 255, 255))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))

    # Star display
    star_text = font_large.render(f"★ Total Stars: {player.total_stars} / 120", True, COL_GOLD)
    screen.blit(star_text, (WIDTH // 2 - star_text.get_width() // 2, 130))

    options = ["Continue", "Exit to Castle", "Exit to Title"]
    for i, opt in enumerate(options):
        y = 220 + i * 60
        color = COL_GOLD if i == selected else (200, 200, 200)
        text = font_large.render(opt, True, color)
        if i == selected:
            text = font_large.render(f"> {opt} <", True, color)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))

    # Course stars breakdown
    y_off = 420
    course_text = font_small.render("Course Stars:", True, (180, 180, 180))
    screen.blit(course_text, (50, y_off))
    y_off += 20
    col = 0
    for lid in range(15):
        name = LEVEL_NAMES.get(lid, "?")
        count = len(player.stars_collected.get(lid, set()))
        short_name = name[:20]
        info = font_small.render(f"{short_name}: {count}/7", True, (150, 150, 150))
        x_pos = 50 + col * 250
        screen.blit(info, (x_pos, y_off))
        y_off += 16
        if y_off > HEIGHT - 30:
            y_off = 440
            col += 1


def draw_star_get_screen(screen, font_title, font_large, font_small, star_name, frame, level_id):
    # Celebration screen
    for y in range(HEIGHT):
        r = int(20 + 40 * math.sin(frame * 0.02 + y * 0.01))
        g = int(20 + 30 * math.sin(frame * 0.03 + y * 0.01))
        b = int(80 + 60 * math.sin(frame * 0.01 + y * 0.01))
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

    # Big star
    bob = math.sin(frame * 0.05) * 20
    star_size = 60 + int(math.sin(frame * 0.1) * 10)
    cx, cy = WIDTH // 2, int(200 + bob)

    # Draw star shape
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = star_size if i % 2 == 0 else star_size // 2
        points.append((cx + int(math.cos(angle) * r), cy + int(math.sin(angle) * r)))
    pygame.draw.polygon(screen, COL_GOLD, points)
    pygame.draw.polygon(screen, (255, 240, 150), points, 2)

    # Course complete
    level_name = LEVEL_NAMES.get(level_id, "Unknown")
    course = font_large.render(f"Course: {level_name}", True, (200, 200, 255))
    screen.blit(course, (WIDTH // 2 - course.get_width() // 2, 320))

    got = font_title.render("GOT A STAR!", True, COL_GOLD)
    screen.blit(got, (WIDTH // 2 - got.get_width() // 2, 370))

    name_surf = font_large.render(star_name, True, (255, 255, 200))
    screen.blit(name_surf, (WIDTH // 2 - name_surf.get_width() // 2, 430))

    if frame > 60 and (frame // 25) % 2 == 0:
        cont = font_small.render("Press ENTER to continue", True, (200, 200, 200))
        screen.blit(cont, (WIDTH // 2 - cont.get_width() // 2, HEIGHT - 50))


def draw_game_over(screen, font_title, font_large, font_small, frame):
    screen.fill((0, 0, 0))
    bob = math.sin(frame * 0.03) * 5

    title = font_title.render("GAME OVER", True, (200, 50, 50))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, int(200 + bob)))

    if (frame // 30) % 2 == 0:
        prompt = font_large.render("Press ENTER", True, (200, 200, 200))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 350))


# ============================================================================
#  MAIN GAME LOOP
# ============================================================================

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cat's SM64 - Python Port 1.0")
    clock = pygame.time.Clock()

    # Fonts
    font_title = pygame.font.SysFont('Arial', 48, bold=True)
    font_large = pygame.font.SysFont('Arial', 24)
    font_small = pygame.font.SysFont('Arial', 16)

    # Game State
    state = STATE_TITLE
    frame = 0
    game_time = 0

    # Player
    player = Player(0, -50, 0)

    # Level data
    current_level = LEVEL_CASTLE_GROUNDS
    map_objects = []
    coins_list = []
    stars_list = []
    paintings_list = []
    floor_color = COL_GRASS
    sky_color = BG_COLOR

    # Camera
    cam_angle = 0
    cam_x, cam_y, cam_z = 0, -200, -400

    # Menu state
    file_selected = 0
    pause_selected = 0

    # Star get state
    star_get_name = ""
    star_get_timer = 0
    star_get_level = 0

    # Star name display
    show_star_name = None
    star_name_timer = 0

    # Key cooldown for menus
    key_cooldown = 0

    def load_level(level_id):
        nonlocal map_objects, coins_list, stars_list, paintings_list, floor_color, sky_color
        nonlocal cam_angle, cam_x, cam_y, cam_z
        blocks, coins, stars, paintings, fc, sc, start = build_level(level_id)
        map_objects = blocks
        coins_list = coins
        stars_list = stars
        paintings_list = paintings
        floor_color = fc
        sky_color = sc
        player.reset_position(*start)
        player.health = player.max_health
        player.coins = 0
        cam_angle = 0
        cam_x = player.x
        cam_y = player.y - CAM_HEIGHT
        cam_z = player.z - CAM_DISTANCE

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        frame += 1
        game_time = frame / FPS
        if key_cooldown > 0:
            key_cooldown -= 1

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if state == STATE_TITLE:
                    if event.key == pygame.K_RETURN:
                        state = STATE_FILE_SELECT
                        key_cooldown = 15

                elif state == STATE_FILE_SELECT:
                    if event.key == pygame.K_UP and key_cooldown == 0:
                        file_selected = (file_selected - 1) % 4
                        key_cooldown = 10
                    elif event.key == pygame.K_DOWN and key_cooldown == 0:
                        file_selected = (file_selected + 1) % 4
                        key_cooldown = 10
                    elif event.key == pygame.K_RETURN and key_cooldown == 0:
                        state = STATE_LETTER
                        key_cooldown = 20

                elif state == STATE_LETTER:
                    if event.key == pygame.K_RETURN and key_cooldown == 0:
                        state = STATE_CASTLE
                        current_level = LEVEL_CASTLE_GROUNDS
                        load_level(current_level)
                        key_cooldown = 20

                elif state == STATE_CASTLE or state == STATE_LEVEL:
                    if event.key == pygame.K_ESCAPE:
                        if state == STATE_LEVEL:
                            state = STATE_PAUSE
                            pause_selected = 0
                            key_cooldown = 15
                        elif state == STATE_CASTLE:
                            state = STATE_PAUSE
                            pause_selected = 0
                            key_cooldown = 15

                    if event.key == pygame.K_RETURN:
                        # Check painting proximity in castle
                        if state == STATE_CASTLE:
                            for p in paintings_list:
                                dx = player.x - p.x
                                dz = player.z - p.z
                                dist = math.sqrt(dx*dx + dz*dz)
                                if dist < p.trigger_radius:
                                    current_level = p.level_id
                                    state = STATE_LEVEL
                                    load_level(current_level)
                                    key_cooldown = 20
                                    break

                elif state == STATE_PAUSE:
                    if event.key == pygame.K_ESCAPE and key_cooldown == 0:
                        state = STATE_LEVEL if current_level != LEVEL_CASTLE_GROUNDS else STATE_CASTLE
                        key_cooldown = 15
                    elif event.key == pygame.K_UP and key_cooldown == 0:
                        pause_selected = (pause_selected - 1) % 3
                        key_cooldown = 10
                    elif event.key == pygame.K_DOWN and key_cooldown == 0:
                        pause_selected = (pause_selected + 1) % 3
                        key_cooldown = 10
                    elif event.key == pygame.K_RETURN and key_cooldown == 0:
                        if pause_selected == 0:  # Continue
                            state = STATE_LEVEL if current_level != LEVEL_CASTLE_GROUNDS else STATE_CASTLE
                        elif pause_selected == 1:  # Exit to castle
                            current_level = LEVEL_CASTLE_GROUNDS
                            state = STATE_CASTLE
                            load_level(current_level)
                        elif pause_selected == 2:  # Exit to title
                            state = STATE_TITLE
                        key_cooldown = 20

                elif state == STATE_STAR_GET:
                    if event.key == pygame.K_RETURN and star_get_timer > 60 and key_cooldown == 0:
                        current_level = LEVEL_CASTLE_GROUNDS
                        state = STATE_CASTLE
                        load_level(current_level)
                        key_cooldown = 20

                elif state == STATE_GAME_OVER:
                    if event.key == pygame.K_RETURN and key_cooldown == 0:
                        state = STATE_TITLE
                        player = Player(0, -50, 0)
                        key_cooldown = 20

        keys = pygame.key.get_pressed()

        # --- Update ---
        if state in (STATE_CASTLE, STATE_LEVEL):
            # Camera control
            if keys[pygame.K_q]: cam_angle -= 0.05
            if keys[pygame.K_e]: cam_angle += 0.05

            player.update(keys, map_objects, cam_angle)

            # Lakitu camera
            target_cx = player.x - math.sin(cam_angle) * CAM_DISTANCE
            target_cz = player.z - math.cos(cam_angle) * CAM_DISTANCE
            target_cy = player.y - CAM_HEIGHT
            cam_x = lerp(cam_x, target_cx, CAM_SMOOTHING)
            cam_y = lerp(cam_y, target_cy, CAM_SMOOTHING)
            cam_z = lerp(cam_z, target_cz, CAM_SMOOTHING)

            camera_pos = Vector3(cam_x, cam_y, cam_z)

            # Coin collection
            for coin in coins_list:
                if not coin.collected:
                    dx = player.x - coin.x
                    dy = player.y - coin.y
                    dz = player.z - coin.z
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if dist < 50:
                        player.collect_coin(coin)

            # Star collection
            for star in stars_list:
                if not star.collected:
                    dx = player.x - star.x
                    dy = player.y - star.y
                    dz = player.z - star.z
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if dist < 60:
                        if player.collect_star(star, current_level):
                            sid = star.star_id
                            names = STAR_NAMES.get(current_level, [])
                            star_get_name = names[sid] if sid < len(names) else f"Star #{sid+1}"
                            star_get_timer = 0
                            star_get_level = current_level
                            state = STATE_STAR_GET
                            key_cooldown = 30

            # Death check
            if player.health <= 0 or player.y > 800:
                if player.lives <= 0:
                    state = STATE_GAME_OVER
                else:
                    player.health = player.max_health
                    load_level(current_level)

            # Star name display timer
            if star_name_timer > 0:
                star_name_timer -= 1

        if state == STATE_STAR_GET:
            star_get_timer += 1

        # --- Render ---
        if state == STATE_TITLE:
            draw_title_screen(screen, font_title, font_large, font_small, frame)

        elif state == STATE_FILE_SELECT:
            draw_file_select(screen, font_title, font_large, font_small, file_selected, frame)

        elif state == STATE_LETTER:
            draw_letter_screen(screen, font_large, font_small, frame)

        elif state in (STATE_CASTLE, STATE_LEVEL):
            screen.fill(sky_color)
            camera_pos = Vector3(cam_x, cam_y, cam_z)
            render_scene(screen, player, map_objects, coins_list, stars_list,
                        paintings_list, floor_color, camera_pos, cam_angle, game_time)
            draw_hud(screen, player, current_level, font_large, font_small,
                    show_star_name, star_name_timer)

            # Show painting labels when near
            if state == STATE_CASTLE:
                for p in paintings_list:
                    dx = player.x - p.x
                    dz = player.z - p.z
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist < p.trigger_radius * 1.5:
                        name = LEVEL_NAMES.get(p.level_id, "???")
                        star_count = len(player.stars_collected.get(p.level_id, set()))
                        label = f"{name} (★{star_count}/7) - ENTER"
                        surf = font_small.render(label, True, COL_GOLD)
                        bg = pygame.Surface((surf.get_width() + 10, surf.get_height() + 6), pygame.SRCALPHA)
                        bg.fill((0, 0, 0, 150))
                        screen.blit(bg, (WIDTH//2 - surf.get_width()//2 - 5, HEIGHT - 80))
                        screen.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT - 77))
                        break

            draw_controls_help(screen, font_small)

        elif state == STATE_PAUSE:
            # Draw game behind pause
            screen.fill(sky_color)
            camera_pos = Vector3(cam_x, cam_y, cam_z)
            render_scene(screen, player, map_objects, coins_list, stars_list,
                        paintings_list, floor_color, camera_pos, cam_angle, game_time)
            draw_pause_screen(screen, font_title, font_large, font_small, player, pause_selected)

        elif state == STATE_STAR_GET:
            draw_star_get_screen(screen, font_title, font_large, font_small,
                               star_get_name, star_get_timer, star_get_level)

        elif state == STATE_GAME_OVER:
            draw_game_over(screen, font_title, font_large, font_small, frame)

        # FPS counter
        fps_text = font_small.render(f"FPS: {int(clock.get_fps())}", True, (200, 200, 200))
        screen.blit(fps_text, (WIDTH - 80, HEIGHT - 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
