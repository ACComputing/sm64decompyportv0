#!/usr/bin/env python3
"""
SUPER MARIO 64 PC PORT v1
Enhanced 3D Platformer - Accurate Castle Hub + All 15 Courses + Bowser Levels
Pure Python + Pygame Software 3D Renderer | Single File | 60 FPS Target
"""

import pygame
import sys
import math
import random

# ============================================================
# CONSTANTS
# ============================================================
SW, SH = 800, 600
FPS = 60
FOV = 400
NEAR_CLIP = 0.5

# Colors - SM64 Palette
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_RED = (220, 40, 20)
C_BLUE = (30, 30, 200)
C_DBLUE = (20, 20, 140)
C_GREEN = (34, 139, 34)
C_DGREEN = (20, 100, 20)
C_LGREEN = (80, 180, 60)
C_BROWN = (139, 90, 43)
C_DBROWN = (100, 60, 30)
C_LBROWN = (170, 120, 60)
C_GRAY = (140, 140, 140)
C_DGRAY = (90, 90, 90)
C_LGRAY = (180, 180, 180)
C_YELLOW = (255, 220, 40)
C_ORANGE = (240, 140, 20)
C_SAND = (210, 180, 120)
C_DSAND = (180, 150, 90)
C_SNOW = (230, 240, 255)
C_ICE = (180, 220, 255)
C_LAVA = (220, 60, 10)
C_DLAVA = (160, 30, 0)
C_PURPLE = (120, 40, 160)
C_DPURPLE = (80, 20, 110)
C_PINK = (240, 140, 180)
C_CYAN = (40, 200, 220)
C_WATER = (40, 80, 200)
C_DWATER = (20, 40, 140)
C_LWATER = (80, 140, 220)

# Castle-specific colors
C_CASTLE_WALL = (200, 190, 170)       # Main castle walls - cream/beige
C_CASTLE_WALL2 = (180, 170, 150)      # Darker wall shade
C_CASTLE_ROOF = (140, 40, 40)         # Red/maroon roof
C_CASTLE_ROOF2 = (120, 30, 30)        # Darker roof
C_CASTLE_DOOR = (100, 60, 30)         # Wooden door
C_CASTLE_TRIM = (160, 155, 140)       # Stone trim
C_CASTLE_TOWER = (190, 180, 165)      # Tower walls
C_CASTLE_SPIRE = (100, 100, 120)      # Spire/cone top
C_CASTLE_FLAG = (220, 40, 40)         # Flag
C_BRIDGE = (140, 110, 70)             # Bridge planks
C_BRIDGE_RAIL = (120, 90, 50)         # Bridge rails
C_MOAT = (30, 70, 180)                # Moat water
C_GRASS_BRIGHT = (50, 170, 50)        # Bright grass
C_GRASS = (40, 140, 40)               # Regular grass
C_GRASS_DARK = (30, 110, 30)          # Dark grass
C_PATH = (180, 165, 130)              # Stone path
C_HILL = (60, 130, 50)                # Hills

C_BRICK = (180, 100, 50)
C_MARIO_R = (220, 40, 20)
C_MARIO_B = (30, 30, 180)
C_MARIO_S = (240, 180, 120)
C_STAR = (255, 230, 50)
C_COIN = (255, 200, 40)
C_TITLE = (255, 220, 60)
C_MENU = (180, 180, 180)
C_SEL = (255, 255, 255)

# Physics
GRAVITY = 0.45
MOVE_SPD = 1.8
RUN_SPD = 3.0
JUMP_FORCE = 7.5
DJUMP_FORCE = 9.0
TJUMP_FORCE = 11.0
AIR_CTRL = 0.6
FRICTION = 0.88
CAM_SPD = 0.04
MAX_FALL = -15


# ============================================================
# 3D MATH
# ============================================================
class V3:
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, o):
        return V3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o):
        return V3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s):
        return V3(self.x * s, self.y * s, self.z * s)

    def __neg__(self):
        return V3(-self.x, -self.y, -self.z)

    def dot(self, o):
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o):
        return V3(self.y * o.z - self.z * o.y,
                  self.z * o.x - self.x * o.z,
                  self.x * o.y - self.y * o.x)

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def xz_len(self):
        return math.sqrt(self.x * self.x + self.z * self.z)

    def normalize(self):
        l = self.length()
        return V3(self.x / l, self.y / l, self.z / l) if l > 1e-6 else V3()

    def copy(self):
        return V3(self.x, self.y, self.z)


def project(pt, cam_pos, cam_yaw, cam_pitch):
    d = pt - cam_pos
    cy, sy = math.cos(-cam_yaw), math.sin(-cam_yaw)
    rx = d.x * cy - d.z * sy
    rz = d.x * sy + d.z * cy
    ry = d.y
    cp, sp = math.cos(-cam_pitch), math.sin(-cam_pitch)
    ry2 = ry * cp - rz * sp
    rz2 = ry * sp + rz * cp
    if rz2 < NEAR_CLIP:
        return None, rz2
    sx = SW / 2 + rx * FOV / rz2
    sy_ = SH / 2 - ry2 * FOV / rz2
    return (int(sx), int(sy_)), rz2


def shade(color, factor):
    return (max(0, min(255, int(color[0] * factor))),
            max(0, min(255, int(color[1] * factor))),
            max(0, min(255, int(color[2] * factor))))


def make_box_faces(x, y, z, w, h, d, color):
    """Generate 6 quad faces for an axis-aligned box."""
    v = [V3(x, y, z), V3(x + w, y, z), V3(x + w, y + h, z), V3(x, y + h, z),
         V3(x, y, z + d), V3(x + w, y, z + d), V3(x + w, y + h, z + d), V3(x, y + h, z + d)]
    return [
        ([v[0], v[1], v[2], v[3]], shade(color, 1.0), V3(0, 0, -1)),   # front
        ([v[5], v[4], v[7], v[6]], shade(color, 0.75), V3(0, 0, 1)),   # back
        ([v[4], v[0], v[3], v[7]], shade(color, 0.85), V3(-1, 0, 0)),  # left
        ([v[1], v[5], v[6], v[2]], shade(color, 0.80), V3(1, 0, 0)),   # right
        ([v[3], v[2], v[6], v[7]], shade(color, 1.15), V3(0, 1, 0)),   # top
        ([v[0], v[4], v[5], v[1]], shade(color, 0.60), V3(0, -1, 0)),  # bottom
    ]


def make_pyramid_faces(cx, y, cz, base_w, base_d, height, color):
    """Generate triangular faces for a pyramid."""
    hw, hd = base_w / 2, base_d / 2
    top = V3(cx, y + height, cz)
    bl = V3(cx - hw, y, cz - hd)
    br = V3(cx + hw, y, cz - hd)
    fl = V3(cx - hw, y, cz + hd)
    fr = V3(cx + hw, y, cz + hd)
    return [
        ([bl, br, top], shade(color, 1.0), V3(0, 0, -1)),
        ([fr, fl, top], shade(color, 0.75), V3(0, 0, 1)),
        ([fl, bl, top], shade(color, 0.85), V3(-1, 0, 0)),
        ([br, fr, top], shade(color, 0.80), V3(1, 0, 0)),
        ([bl, fl, fr, br], shade(color, 0.60), V3(0, -1, 0)),
    ]


def make_wedge_faces(x, y, z, w, h, d, color, direction='z+'):
    """Generate faces for a triangular prism/wedge (for roofs)."""
    faces = []
    if direction == 'z+':
        # Ridge runs along X, slopes down along Z
        v0 = V3(x, y, z)
        v1 = V3(x + w, y, z)
        v2 = V3(x + w, y, z + d)
        v3 = V3(x, y, z + d)
        v4 = V3(x, y + h, z + d / 2)
        v5 = V3(x + w, y + h, z + d / 2)
        # Two sloped faces
        faces.append(([v0, v1, v5, v4], shade(color, 1.0), V3(0, 0.5, -0.5)))
        faces.append(([v3, v2, v5, v4], shade(color, 0.85), V3(0, 0.5, 0.5)))  # flipped
        # correct winding for back slope
        faces[-1] = ([v2, v3, v4, v5], shade(color, 0.85), V3(0, 0.5, 0.5))
        # Two triangular ends
        faces.append(([v0, v3, v4], shade(color, 0.75), V3(-1, 0, 0)))
        faces.append(([v1, v2, v5], shade(color, 0.80), V3(1, 0, 0)))
        # Bottom
        faces.append(([v0, v1, v2, v3], shade(color, 0.60), V3(0, -1, 0)))
    elif direction == 'x+':
        # Ridge runs along Z, slopes down along X
        v0 = V3(x, y, z)
        v1 = V3(x + w, y, z)
        v2 = V3(x + w, y, z + d)
        v3 = V3(x, y, z + d)
        v4 = V3(x + w / 2, y + h, z)
        v5 = V3(x + w / 2, y + h, z + d)
        faces.append(([v0, v1, v4], shade(color, 1.0), V3(0, 0.5, -0.5)))
        faces.append(([v1, v2, v5, v4], shade(color, 0.85), V3(1, 0.5, 0)))
        faces.append(([v3, v0, v4, v5], shade(color, 0.80), V3(-1, 0.5, 0)))
        faces.append(([v2, v3, v5], shade(color, 0.75), V3(0, 0.5, 0.5)))
        faces.append(([v0, v1, v2, v3], shade(color, 0.60), V3(0, -1, 0)))
    return faces


def render_faces(surface, faces, cam_pos, cam_yaw, cam_pitch):
    projected_faces = []
    for verts, color, normal in faces:
        face_center = V3(
            sum(v.x for v in verts) / len(verts),
            sum(v.y for v in verts) / len(verts),
            sum(v.z for v in verts) / len(verts))
        to_cam = cam_pos - face_center
        if normal.dot(to_cam) < 0:
            continue
        screen_pts = []
        total_depth = 0
        all_visible = True
        for v in verts:
            pt, depth = project(v, cam_pos, cam_yaw, cam_pitch)
            if pt is None:
                all_visible = False
                break
            screen_pts.append(pt)
            total_depth += depth
        if not all_visible or len(screen_pts) < 3:
            continue
        avg_depth = total_depth / len(screen_pts)
        projected_faces.append((avg_depth, screen_pts, color))
    projected_faces.sort(key=lambda f: -f[0])
    for _, pts, color in projected_faces:
        if all(-500 < p[0] < SW + 500 and -500 < p[1] < SH + 500 for p in pts):
            try:
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, shade(color, 0.7), pts, 1)
            except:
                pass


# ============================================================
# PLATFORM / COLLISION
# ============================================================
class Platform:
    def __init__(self, x, y, z, w, h, d, color, is_portal=False, portal_id=-1):
        self.x, self.y, self.z = x, y, z
        self.w, self.h, self.d = w, h, d
        self.color = color
        self.is_portal = is_portal
        self.portal_id = portal_id
        self._faces = None

    def get_faces(self):
        if self._faces is None:
            self._faces = make_box_faces(self.x, self.y, self.z,
                                         self.w, self.h, self.d, self.color)
        return self._faces

    def top_y(self):
        return self.y + self.h

    def contains_xz(self, px, pz, margin=0.5):
        return (self.x - margin <= px <= self.x + self.w + margin and
                self.z - margin <= pz <= self.z + self.d + margin)

    def collide_side(self, px, pz, radius=1.5):
        cx = max(self.x, min(px, self.x + self.w))
        cz = max(self.z, min(pz, self.z + self.d))
        dx = px - cx
        dz = pz - cz
        dist = math.sqrt(dx * dx + dz * dz)
        if dist < radius and dist > 0.001:
            nx = dx / dist
            nz = dz / dist
            px = cx + nx * radius
            pz = cz + nz * radius
        return px, pz


class DecoFace:
    """Non-collidable decorative geometry (roofs, trim, etc.)."""
    def __init__(self, faces_data):
        self.faces = faces_data  # list of (verts, color, normal)


# ============================================================
# CASTLE HUB - Accurate SM64 Peach's Castle
# ============================================================

def _build_castle_hub():
    """
    Build Peach's Castle hub world matching SM64 layout:
    - Castle faces SOUTH (toward player start)
    - Large grounds with hills
    - Moat around castle
    - Bridge to entrance
    - Main hall, two side towers, central tower
    - Course painting portals in surrounding area
    """
    platforms = []
    deco_faces = []

    # === GROUND TERRAIN ===
    # Main grassy grounds - large flat area
    platforms.append((-80, -2, -80, 160, 2, 160, C_GRASS))
    # Slight raised area near castle
    platforms.append((-40, -0.5, -55, 80, 0.5, 30, C_GRASS_DARK))

    # Hills around perimeter
    # Left hill cluster
    platforms.append((-70, 0, 30, 20, 4, 15, C_HILL))
    platforms.append((-65, 0, 35, 12, 7, 10, C_HILL))
    platforms.append((-60, 0, 40, 8, 10, 6, C_DGREEN))
    # Right hill cluster
    platforms.append((50, 0, 30, 20, 4, 15, C_HILL))
    platforms.append((55, 0, 35, 12, 7, 10, C_HILL))
    platforms.append((60, 0, 40, 8, 10, 6, C_DGREEN))
    # Back hills
    platforms.append((-50, 0, -70, 15, 5, 10, C_HILL))
    platforms.append((35, 0, -70, 15, 5, 10, C_HILL))
    # Far back hills
    platforms.append((-70, 0, -65, 10, 8, 8, C_DGREEN))
    platforms.append((60, 0, -65, 10, 8, 8, C_DGREEN))

    # === MOAT ===
    # Water around castle (lower sections)
    platforms.append((-30, -4, -45, 60, 2, 8, C_MOAT))     # Front moat
    platforms.append((-30, -4, -45, 8, 2, 50, C_MOAT))      # Left moat
    platforms.append((22, -4, -45, 8, 2, 50, C_MOAT))       # Right moat
    platforms.append((-30, -4, -2, 60, 2, 8, C_MOAT))       # Back moat

    # Moat banks (sloped edges - simplified as steps)
    platforms.append((-32, -3, -47, 64, 1, 2, C_GRASS_DARK))
    platforms.append((-32, -3, -1, 64, 1, 2, C_GRASS_DARK))
    platforms.append((-32, -3, -45, 2, 1, 50, C_GRASS_DARK))
    platforms.append((30, -3, -45, 2, 1, 50, C_GRASS_DARK))

    # === BRIDGE ===
    # Stone bridge from south to castle entrance
    platforms.append((-4, -1, -45, 8, 1, 12, C_BRIDGE))
    # Bridge railings (thin tall boxes)
    platforms.append((-4, 0, -45, 1, 2, 12, C_BRIDGE_RAIL))
    platforms.append((3, 0, -45, 1, 2, 12, C_BRIDGE_RAIL))
    # Path from bridge to player start
    platforms.append((-3, -0.5, -50, 6, 0.5, 8, C_PATH))
    platforms.append((-4, -0.3, -56, 8, 0.3, 8, C_PATH))

    # === MAIN CASTLE BUILDING ===
    # The castle faces SOUTH. Player approaches from south (positive Z decreasing).
    # Castle centered around x=0, front wall at z=-33, back at z=-5

    # Main body - wide rectangular structure
    CX, CZ = -18, -33  # Castle origin (bottom-left corner)
    CW, CD = 36, 28     # Width and depth
    CH = 16              # Wall height

    # Main walls
    platforms.append((CX, 0, CZ, CW, CH, CD, C_CASTLE_WALL))

    # Front entrance alcove (recessed doorway)
    platforms.append((-4, 0, -35, 8, 10, 2, C_CASTLE_DOOR))
    # Steps leading to door
    platforms.append((-6, 0, -35, 12, 1, 3, C_CASTLE_TRIM))
    platforms.append((-5, 0, -36, 10, 0.5, 1, C_CASTLE_TRIM))

    # === CASTLE TOWERS (Two flanking towers like SM64) ===
    TW = 8  # Tower width

    # Left tower
    LTX, LTZ = CX - 2, CZ + 2
    platforms.append((LTX, 0, LTZ, TW, CH + 10, TW, C_CASTLE_TOWER))
    # Left tower battlement top
    platforms.append((LTX - 1, CH + 10, LTZ - 1, TW + 2, 2, TW + 2, C_CASTLE_TRIM))
    # Left tower spire
    deco_faces.extend(make_pyramid_faces(
        LTX + TW / 2, CH + 12, LTZ + TW / 2, TW + 2, TW + 2, 8, C_CASTLE_ROOF))

    # Right tower
    RTX, RTZ = CX + CW - TW + 2, CZ + 2
    platforms.append((RTX, 0, RTZ, TW, CH + 10, TW, C_CASTLE_TOWER))
    # Right tower battlement
    platforms.append((RTX - 1, CH + 10, RTZ - 1, TW + 2, 2, TW + 2, C_CASTLE_TRIM))
    # Right tower spire
    deco_faces.extend(make_pyramid_faces(
        RTX + TW / 2, CH + 12, RTZ + TW / 2, TW + 2, TW + 2, 8, C_CASTLE_ROOF))

    # === CENTRAL TOWER / KEEP ===
    # Taller central section above main body
    platforms.append((-8, CH, -28, 16, 10, 18, C_CASTLE_WALL2))
    # Central tower battlement
    platforms.append((-9, CH + 10, -29, 18, 2, 20, C_CASTLE_TRIM))
    # Central spire (tall pointed roof)
    deco_faces.extend(make_pyramid_faces(
        0, CH + 12, -19, 16, 18, 14, C_CASTLE_ROOF))

    # === MAIN ROOF ===
    # Roof sections on main body (sloped)
    deco_faces.extend(make_wedge_faces(
        CX, CH, CZ, CW, 6, CD, C_CASTLE_ROOF2, 'z+'))

    # === CASTLE DETAILS ===
    # Window columns on front face (decorative vertical strips)
    for wx in [-12, -6, 6, 12]:
        platforms.append((wx - 0.5, 6, CZ - 0.3, 1, 6, 0.3, C_CASTLE_TRIM))

    # Balcony above entrance
    platforms.append((-6, 10, CZ - 1, 12, 0.5, 2, C_CASTLE_TRIM))
    platforms.append((-6, 10, CZ - 1, 1, 3, 1, C_CASTLE_TRIM))
    platforms.append((5, 10, CZ - 1, 1, 3, 1, C_CASTLE_TRIM))

    # Front arch decoration over door
    platforms.append((-5, 10, CZ - 0.5, 10, 2, 0.5, C_CASTLE_TRIM))

    # Flag pole on central tower
    platforms.append((-0.3, CH + 26, -19, 0.6, 5, 0.6, C_DGRAY))
    # Flag
    platforms.append((0.3, CH + 28, -19, 3, 2, 0.2, C_CASTLE_FLAG))

    # === COURTYARD (Behind castle) ===
    platforms.append((-15, 0, -5, 30, 0.3, 15, C_PATH))
    # Small garden walls
    platforms.append((-15, 0, 10, 30, 1, 1, C_CASTLE_TRIM))
    platforms.append((-15, 0, -5, 1, 1, 16, C_CASTLE_TRIM))
    platforms.append((14, 0, -5, 1, 1, 16, C_CASTLE_TRIM))
    # Boo courtyard entrance (right side)
    platforms.append((18, 0, -10, 4, 3, 4, C_DGRAY))

    # === COURSE PORTAL PLATFORMS ===
    # SM64 has paintings inside the castle, but for gameplay we place
    # colored portal pads around the grounds

    # --- Courses 1-3: Near front-left area ---
    # Bob-omb Battlefield portal (Course 1) - left of bridge
    platforms.append((-20, 0, -55, 5, 0.5, 5, C_GREEN))
    # Whomp's Fortress portal (Course 2) - further left
    platforms.append((-30, 0, -50, 5, 0.5, 5, C_LGRAY))
    # Jolly Roger Bay portal (Course 3)
    platforms.append((-35, 0, -40, 5, 0.5, 5, C_WATER))

    # --- Courses 4-6: Front-right area ---
    # Cool Cool Mountain (Course 4)
    platforms.append((15, 0, -55, 5, 0.5, 5, C_SNOW))
    # Big Boo's Haunt (Course 5)
    platforms.append((25, 0, -50, 5, 0.5, 5, C_PURPLE))
    # Hazy Maze Cave (Course 6)
    platforms.append((30, 0, -40, 5, 0.5, 5, C_DGRAY))

    # --- Courses 7-9: Left side ---
    # Lethal Lava Land (Course 7)
    platforms.append((-45, 0, -20, 5, 0.5, 5, C_LAVA))
    # Shifting Sand Land (Course 8)
    platforms.append((-50, 0, -10, 5, 0.5, 5, C_SAND))
    # Dire Dire Docks (Course 9)
    platforms.append((-45, 0, 0, 5, 0.5, 5, C_DWATER))

    # --- Courses 10-12: Right side ---
    # Snowman's Land (Course 10)
    platforms.append((40, 0, -20, 5, 0.5, 5, C_ICE))
    # Wet-Dry World (Course 11)
    platforms.append((45, 0, -10, 5, 0.5, 5, C_CYAN))
    # Tall Tall Mountain (Course 12)
    platforms.append((40, 0, 0, 5, 0.5, 5, C_BROWN))

    # --- Courses 13-15: Back area ---
    # Tiny-Huge Island (Course 13)
    platforms.append((-25, 0, 15, 5, 0.5, 5, C_LGREEN))
    # Tick Tock Clock (Course 14)
    platforms.append((0, 0, 20, 5, 0.5, 5, C_ORANGE))
    # Rainbow Ride (Course 15)
    platforms.append((20, 0, 15, 5, 0.5, 5, C_PINK))

    # --- Bowser levels: Raised platforms ---
    # Bowser 1 - Dark World
    platforms.append((-40, 0, 25, 6, 1.5, 6, C_DGRAY))
    # Bowser 2 - Fire Sea
    platforms.append((0, 0, 35, 6, 1.5, 6, C_DLAVA))
    # Bowser 3 - In the Sky (final - near big star on top)
    platforms.append((35, 0, 25, 6, 1.5, 6, C_DPURPLE))

    # === DECORATIVE TREES ===
    # Tree trunks (collidable) and tops (deco)
    tree_positions = [
        (-40, 20), (-50, 30), (-30, 40), (40, 20), (50, 30), (30, 40),
        (-55, -30), (55, -30), (-45, 50), (45, 50), (0, 55),
        (-60, 0), (60, 0), (-35, -60), (35, -60),
    ]
    for tx, tz in tree_positions:
        # Trunk
        platforms.append((tx - 1, 0, tz - 1, 2, 6, 2, C_DBROWN))
        # Canopy (deco)
        deco_faces.extend(make_box_faces(tx - 3, 6, tz - 3, 6, 5, 6, C_DGREEN))
        deco_faces.extend(make_box_faces(tx - 2, 11, tz - 2, 4, 3, 4, C_GREEN))

    # Convert to Platform objects and build portal list
    plat_objects = [Platform(*p[:7]) for p in platforms]

    # Portal definitions: (center_x, center_z, course_index)
    portal_list = [
        (-17.5, -52.5, 1),   # BoB
        (-27.5, -47.5, 2),   # WF
        (-32.5, -37.5, 3),   # JRB
        (17.5, -52.5, 4),    # CCM
        (27.5, -47.5, 5),    # BBH
        (32.5, -37.5, 6),    # HMC
        (-42.5, -17.5, 7),   # LLL
        (-47.5, -7.5, 8),    # SSL
        (-42.5, 2.5, 9),     # DDD
        (42.5, -17.5, 10),   # SL
        (47.5, -7.5, 11),    # WDW
        (42.5, 2.5, 12),     # TTM
        (-22.5, 17.5, 13),   # THI
        (2.5, 22.5, 14),     # TTC
        (22.5, 17.5, 15),    # RR
        (-37, 28, 16),       # Bowser 1
        (3, 38, 17),         # Bowser 2
        (38, 28, 18),        # Bowser 3
    ]

    return plat_objects, [], [], deco_faces, portal_list


# ============================================================
# COURSE DATA - All 15 Courses + 3 Bowser Levels
# ============================================================

def _c1_bobomb():
    """Bob-omb Battlefield - Rolling hills, mountain, chain chomp area"""
    p = [
        # Main ground
        (-60, -2, -60, 120, 2, 120, C_GREEN),
        # Central mountain (stepped)
        (-12, 0, -12, 24, 5, 24, C_BROWN),
        (-10, 5, -10, 20, 5, 20, C_BROWN),
        (-8, 10, -8, 16, 5, 16, C_DBROWN),
        (-6, 15, -6, 12, 3, 12, C_BROWN),
        (-4, 18, -4, 8, 2, 8, C_DBROWN),
        # Summit platform
        (-3, 20, -3, 6, 1, 6, C_GRAY),
        # Rolling hills
        (-40, 0, 10, 15, 3, 12, C_GREEN),
        (-35, 0, 25, 10, 2, 10, C_DGREEN),
        (25, 0, 15, 12, 4, 10, C_GREEN),
        (30, 0, 28, 8, 2, 8, C_DGREEN),
        # Chain chomp area (fenced pen)
        (30, 0, -20, 15, 1, 15, C_DGREEN),
        (30, 1, -20, 15, 2, 1, C_BROWN),  # fence
        (30, 1, -6, 15, 2, 1, C_BROWN),   # fence
        (30, 1, -20, 1, 2, 15, C_BROWN),  # fence
        (44, 1, -20, 1, 2, 15, C_BROWN),  # fence
        # Bridge
        (-3, 0, 15, 6, 0.5, 20, C_BROWN),
        # Cannons area
        (-40, 0, -20, 8, 1, 8, C_DGRAY),
        # Path up mountain
        (10, 0, -5, 3, 1, 10, C_DBROWN),
        (10, 2, 0, 8, 1, 3, C_DBROWN),
        # Water area
        (-45, -3, 35, 25, 1, 20, C_WATER),
        # Platforms scattered
        (40, 0, 0, 6, 2, 6, C_GREEN),
        (-30, 0, -30, 8, 1.5, 8, C_DGREEN),
        (-50, 0, -10, 6, 1, 6, C_GREEN),
    ]
    stars = [V3(0, 22, 0)]
    coins = [V3(5, 2, 5), V3(-5, 2, 5), V3(15, 2, -15), V3(-25, 2, 20),
             V3(35, 2, 20), V3(-35, 2, -25), V3(0, 6, 0), V3(-40, 2, 15)]
    return p, stars, coins


def _c2_whomp():
    """Whomp's Fortress - Tall fortress with ramps and platforms"""
    p = [
        # Base area
        (-25, -2, -25, 50, 2, 50, C_GRAY),
        # Main fortress tower (stepped)
        (-10, 0, -10, 20, 5, 20, C_LGRAY),
        (-8, 5, -8, 16, 5, 16, C_GRAY),
        (-6, 10, -6, 12, 4, 12, C_LGRAY),
        (-4, 14, -4, 8, 4, 8, C_GRAY),
        (-3, 18, -3, 6, 3, 6, C_LGRAY),
        # Top platform
        (-4, 21, -4, 8, 1, 8, C_GRAY),
        # Ramp system
        (10, 0, 5, 3, 1, 12, C_LGRAY),
        (10, 2, 12, 8, 1, 3, C_GRAY),
        (14, 3, 5, 3, 1, 10, C_LGRAY),
        (14, 5, 3, 8, 1, 3, C_GRAY),
        # Side platforms
        (-18, 0, -18, 5, 3, 5, C_DGRAY),
        (15, 0, -15, 6, 6, 4, C_LGRAY),
        (-15, 0, 10, 5, 4, 5, C_GRAY),
        # Thwomp area
        (5, 8, 0, 4, 1, 4, C_DGRAY),
        # Piranha plant ledges
        (-12, 6, 5, 3, 1, 3, C_GREEN),
        (-15, 8, 8, 3, 1, 3, C_GREEN),
        # Whomp area at top
        (-2, 18, -8, 4, 1, 4, C_LGRAY),
    ]
    stars = [V3(0, 23, 0)]
    coins = [V3(5, 2, 5), V3(-5, 2, -5), V3(12, 3, 8), V3(-12, 2, 12),
             V3(16, 2, -10), V3(-15, 5, 6)]
    return p, stars, coins


def _c3_jrb():
    """Jolly Roger Bay - Ocean with ship, caves, underwater area"""
    p = [
        # Ocean floor
        (-50, -8, -50, 100, 2, 100, C_DWATER),
        # Water surface (thin)
        (-50, -2, -50, 100, 0.5, 100, C_WATER),
        # Starting shore
        (-15, -2, -15, 30, 2, 15, C_SAND),
        (-10, 0, -5, 20, 1, 10, C_SAND),
        # Ship (blocky representation)
        (15, -1, 10, 18, 4, 6, C_BROWN),
        (15, 3, 11, 18, 2, 4, C_DBROWN),
        (14, 3, 10, 1, 6, 6, C_BROWN),   # mast base
        # Dock/pier
        (-5, -1, 5, 3, 1, 20, C_BROWN),
        # Cave entrance rocks
        (-30, -2, 15, 12, 8, 8, C_DGRAY),
        (-28, -2, 17, 8, 6, 4, C_GRAY),
        # Underwater pillars
        (0, -7, 20, 4, 5, 4, C_DGRAY),
        (10, -7, 25, 3, 4, 3, C_GRAY),
        (-15, -7, 30, 5, 6, 5, C_DGRAY),
        # Rock platforms
        (30, -1, -5, 8, 3, 8, C_GRAY),
        (-35, 0, -10, 6, 2, 6, C_DGRAY),
        # Treasure chest area
        (20, -6, 30, 6, 1, 6, C_DGRAY),
        # Clam area
        (-10, -6, 35, 8, 1, 8, C_DSAND),
    ]
    stars = [V3(25, 6, 13)]
    coins = [V3(0, 1, 0), V3(10, 1, 5), V3(-8, 1, 8), V3(20, 1, -3),
             V3(-25, 1, 18), V3(32, 2, -2)]
    return p, stars, coins


def _c4_ccm():
    """Cool Cool Mountain - Snowy mountain with slide, cabin at bottom"""
    p = [
        # Mountain base / snowy ground
        (-50, -2, -50, 100, 2, 100, C_SNOW),
        # Mountain structure (large stepped pyramid)
        (-15, 0, -15, 30, 6, 30, C_SNOW),
        (-12, 6, -12, 24, 6, 24, C_SNOW),
        (-9, 12, -9, 18, 5, 18, C_ICE),
        (-6, 17, -6, 12, 4, 12, C_SNOW),
        (-4, 21, -4, 8, 3, 8, C_SNOW),
        # Summit
        (-3, 24, -3, 6, 1, 6, C_ICE),
        # Slide path (series of platforms going down)
        (15, 18, -8, 5, 1, 5, C_ICE),
        (22, 14, -5, 5, 1, 5, C_SNOW),
        (28, 10, 0, 5, 1, 5, C_ICE),
        (25, 6, 8, 5, 1, 5, C_SNOW),
        (18, 3, 15, 6, 1, 6, C_ICE),
        # Cabin at bottom
        (30, 0, 25, 8, 5, 6, C_BROWN),
        (30, 5, 25, 8, 3, 6, C_DBROWN),  # roof area
        # Bridge over gap
        (-5, 0, 20, 10, 0.5, 3, C_BROWN),
        # Snowman area
        (-30, 0, 10, 10, 3, 10, C_SNOW),
        # Ice platforms
        (-25, 0, -20, 6, 2, 6, C_ICE),
        (35, 0, -15, 5, 1, 5, C_ICE),
        # Penguin area
        (-35, 0, 25, 8, 1, 8, C_SNOW),
    ]
    stars = [V3(0, 26, 0)]
    coins = [V3(5, 2, 5), V3(-10, 2, 10), V3(20, 2, 18), V3(30, 2, -10),
             V3(-25, 2, -15), V3(17, 20, -5), V3(25, 8, 5)]
    return p, stars, coins


def _c5_bbh():
    """Big Boo's Haunt - Haunted mansion with multiple floors"""
    p = [
        # Dark grounds
        (-40, -2, -40, 80, 2, 80, C_DGRAY),
        # Mansion - main floor
        (-15, 0, -15, 30, 8, 25, C_DPURPLE),
        # Second floor
        (-13, 8, -13, 26, 7, 21, C_PURPLE),
        # Attic / top floor
        (-10, 15, -10, 20, 5, 15, C_DPURPLE),
        # Tower on top
        (-4, 20, -6, 8, 6, 6, C_PURPLE),
        (-3, 26, -5, 6, 1, 4, C_DPURPLE),
        # Front porch
        (-10, 0, -18, 20, 0.5, 5, C_DGRAY),
        # Front steps
        (-5, 0, -20, 10, 0.3, 3, C_GRAY),
        # Side wings
        (-25, 0, -5, 10, 6, 15, C_DPURPLE),
        (15, 0, -5, 10, 6, 15, C_DPURPLE),
        # Balcony
        (-12, 8, -15, 24, 0.5, 3, C_BROWN),
        # Graveyard area
        (-35, 0, 15, 15, 0.5, 15, C_DGREEN),
        # Tombstones
        (-33, 0, 18, 2, 3, 1, C_LGRAY),
        (-28, 0, 22, 2, 3, 1, C_LGRAY),
        (-23, 0, 18, 2, 3, 1, C_LGRAY),
        (-33, 0, 26, 2, 3, 1, C_LGRAY),
        # Fence around graveyard
        (-35, 0, 15, 15, 1.5, 0.5, C_DBROWN),
        (-35, 0, 15, 0.5, 1.5, 15, C_DBROWN),
        # Boo carousel
        (25, 0, 20, 10, 1, 10, C_DGRAY),
    ]
    stars = [V3(0, 28, -3)]
    coins = [V3(5, 2, 0), V3(-10, 2, 5), V3(18, 2, 5), V3(-20, 2, -10),
             V3(-30, 2, 20), V3(0, 9, -5)]
    return p, stars, coins


def _c6_hmc():
    """Hazy Maze Cave - Underground cave with maze-like passages"""
    p = [
        # Cave floor
        (-45, -2, -45, 90, 2, 90, C_DGRAY),
        # Cave ceiling (high up, creates enclosed feeling)
        (-45, 18, -45, 90, 2, 90, C_DBROWN),
        # Main cavern area
        (-10, 0, -10, 20, 1.5, 20, C_GRAY),
        # Maze walls
        (-30, 0, -5, 18, 6, 2, C_DGRAY),
        (-30, 0, 10, 18, 6, 2, C_DGRAY),
        (-30, 0, -5, 2, 6, 17, C_GRAY),
        (-14, 0, -5, 2, 6, 8, C_DGRAY),
        # Underground lake
        (15, -3, 10, 25, 1, 20, C_DWATER),
        # Elevated platforms
        (-20, 0, -20, 8, 4, 8, C_GRAY),
        (20, 0, -15, 6, 3, 6, C_DGRAY),
        (-25, 0, 20, 10, 2, 10, C_GRAY),
        # Metal cap area
        (30, 0, -25, 8, 1, 8, C_LGRAY),
        # Rolling rocks path
        (-5, 0, 25, 10, 1, 3, C_DBROWN),
        (-5, 0, 30, 10, 1, 3, C_DBROWN),
        # Dorrie's lake platform
        (20, -2, 15, 10, 2, 8, C_GRAY),
        # Emergency exit
        (35, 0, 0, 5, 8, 5, C_BROWN),
    ]
    stars = [V3(22, 1, 18)]
    coins = [V3(0, 2, 0), V3(-20, 2, 5), V3(15, 2, -10), V3(-25, 2, -15),
             V3(25, 2, -20), V3(-5, 2, 28)]
    return p, stars, coins


def _c7_lll():
    """Lethal Lava Land - Volcanic area with lava and floating platforms"""
    p = [
        # Lava ocean
        (-50, -6, -50, 100, 2, 100, C_LAVA),
        # More lava (bright top layer)
        (-50, -4, -50, 100, 0.5, 100, C_DLAVA),
        # Starting island
        (-8, -2, -8, 16, 2, 16, C_DGRAY),
        # Volcano (central mountain)
        (-6, 0, -6, 12, 8, 12, C_DBROWN),
        (-4, 8, -4, 8, 6, 8, C_BROWN),
        (-3, 14, -3, 6, 4, 6, C_DBROWN),
        # Volcano crater (top has lava)
        (-2, 18, -2, 4, 0.5, 4, C_LAVA),
        # Platform path to volcano
        (12, -2, 0, 5, 2, 5, C_GRAY),
        (20, -2, -3, 4, 2, 4, C_DGRAY),
        (27, -2, 0, 5, 2, 5, C_GRAY),
        # Puzzle platforms
        (-20, -2, 10, 6, 2, 6, C_DGRAY),
        (-28, -2, 5, 5, 2, 5, C_GRAY),
        (-25, -2, -10, 6, 2, 6, C_DGRAY),
        # Rolling log area
        (15, -2, 15, 8, 2, 4, C_BROWN),
        (15, -2, 22, 8, 2, 4, C_BROWN),
        # Bully platform
        (25, -2, 20, 8, 2, 8, C_GRAY),
        # Wing cap area
        (-15, -2, -25, 6, 2, 6, C_DGRAY),
        # Floating platforms (small)
        (0, -2, 25, 4, 2, 4, C_GRAY),
        (-10, -2, 30, 4, 2, 4, C_DGRAY),
        (35, -2, -15, 5, 2, 5, C_GRAY),
    ]
    stars = [V3(0, 20, 0)]
    coins = [V3(14, 1, 2), V3(22, 1, -1), V3(-18, 1, 12), V3(17, 1, 17),
             V3(27, 1, 22), V3(-23, 1, -8)]
    return p, stars, coins


def _c8_ssl():
    """Shifting Sand Land - Desert with pyramid and oasis"""
    p = [
        # Desert floor
        (-60, -2, -60, 120, 2, 120, C_SAND),
        # Main pyramid (stepped)
        (-12, 0, -12, 24, 6, 24, C_DSAND),
        (-10, 6, -10, 20, 6, 20, C_SAND),
        (-8, 12, -8, 16, 5, 16, C_DSAND),
        (-6, 17, -6, 12, 4, 12, C_SAND),
        (-4, 21, -4, 8, 3, 8, C_DSAND),
        (-3, 24, -3, 6, 2, 6, C_SAND),
        # Pyramid top
        (-2, 26, -2, 4, 1, 4, C_DSAND),
        # Oasis area
        (30, -1, 25, 15, 0.5, 12, C_WATER),
        (28, 0, 23, 19, 0.3, 16, C_DGREEN),
        # Oasis palm tree bases
        (32, 0, 28, 2, 6, 2, C_DBROWN),
        (40, 0, 30, 2, 6, 2, C_DBROWN),
        # Pillars / ruins
        (-35, 0, 10, 4, 8, 4, C_DSAND),
        (-40, 0, -15, 3, 10, 3, C_SAND),
        (25, 0, -20, 4, 6, 4, C_DSAND),
        (35, 0, -30, 3, 8, 3, C_SAND),
        # Quicksand pit (lower area)
        (-30, -4, 25, 15, 2, 12, C_DSAND),
        # Klepto area
        (40, 0, 0, 8, 1, 8, C_SAND),
        # Fly guy area
        (-45, 0, -30, 6, 1, 6, C_DSAND),
        # Tox boxes path
        (-5, 0, 25, 10, 0.5, 3, C_LGRAY),
        (-5, 0, 30, 10, 0.5, 3, C_LGRAY),
        (-5, 0, 35, 10, 0.5, 3, C_LGRAY),
    ]
    stars = [V3(0, 28, 0)]
    coins = [V3(10, 2, 10), V3(-20, 2, 5), V3(30, 2, -15), V3(-35, 2, 12),
             V3(42, 2, 3), V3(-42, 2, -28), V3(33, 1, 28)]
    return p, stars, coins


def _c9_ddd():
    """Dire Dire Docks - Underwater dock area with submarine"""
    p = [
        # Water
        (-45, -8, -45, 90, 4, 90, C_DWATER),
        (-45, -4, -45, 90, 2, 90, C_WATER),
        # Dock platforms
        (-15, -2, -20, 30, 2, 10, C_GRAY),
        (-10, 0, -15, 20, 0.5, 5, C_LGRAY),
        # Dock wooden platforms
        (-12, 0, -10, 6, 0.5, 15, C_BROWN),
        (6, 0, -10, 6, 0.5, 15, C_BROWN),
        # Submarine (blocky)
        (15, -3, 10, 20, 5, 8, C_DGRAY),
        (14, -1, 11, 22, 3, 6, C_GRAY),
        (13, 2, 12, 4, 2, 4, C_DGRAY),   # conning tower
        # Tunnel entrance
        (-30, -2, 0, 10, 8, 10, C_DGRAY),
        # Underwater cage
        (20, -6, -15, 8, 4, 8, C_GRAY),
        # Poles
        (0, -6, 20, 2, 8, 2, C_BROWN),
        (-8, -6, 25, 2, 8, 2, C_BROWN),
        # Rock platforms
        (-25, -2, 15, 8, 3, 6, C_DGRAY),
        (30, -2, -10, 6, 2, 6, C_GRAY),
        # Manta ray area
        (-20, -6, 30, 10, 1, 10, C_DWATER),
        # Chest area deep underwater
        (10, -7, 30, 8, 1, 8, C_DGRAY),
    ]
    stars = [V3(25, 3, 13)]
    coins = [V3(0, 1, -10), V3(-8, 1, 5), V3(10, 1, -12), V3(-22, 1, 18),
             V3(32, 1, -8), V3(5, -4, 22)]
    return p, stars, coins


def _c10_sl():
    """Snowman's Land - Large snowman, icy platforms, igloo"""
    p = [
        # Snowy ground
        (-50, -2, -50, 100, 2, 100, C_SNOW),
        # Snowman mountain (central, tall)
        (-8, 0, -8, 16, 10, 16, C_SNOW),
        (-6, 10, -6, 12, 8, 12, C_ICE),
        (-4, 18, -4, 8, 6, 8, C_SNOW),
        # Snowman head (top)
        (-3, 24, -3, 6, 4, 6, C_WHITE),
        (-2, 28, -2, 4, 1, 4, C_SNOW),
        # Igloo
        (25, 0, 20, 8, 4, 8, C_SNOW),
        (26, 4, 21, 6, 2, 6, C_ICE),
        # Frozen pond
        (-30, -1, 15, 15, 0.5, 12, C_ICE),
        # Ice platforms
        (20, 0, -15, 6, 3, 6, C_ICE),
        (30, 0, -25, 5, 2, 5, C_SNOW),
        (-20, 0, -20, 8, 2, 8, C_ICE),
        # Bridge to snowman
        (8, 0, 0, 12, 0.5, 3, C_BROWN),
        # Chill Bully arena
        (-30, 0, -20, 10, 1, 10, C_ICE),
        # Spindrift area
        (30, 0, 5, 8, 1.5, 8, C_SNOW),
        # Shell ride area
        (-40, 0, 0, 8, 0.5, 8, C_ICE),
    ]
    stars = [V3(0, 30, 0)]
    coins = [V3(10, 2, 5), V3(-15, 2, 18), V3(22, 2, -12), V3(-25, 2, -15),
             V3(32, 2, 8), V3(-35, 1, -18), V3(27, 2, 22)]
    return p, stars, coins


def _c11_wdw():
    """Wet-Dry World - City-like blocks with variable water level"""
    p = [
        # Base floor
        (-35, -2, -35, 70, 2, 70, C_LGRAY),
        # Water (mid level)
        (-35, 3, -35, 70, 0.5, 70, C_LWATER),
        # City blocks / buildings
        (-10, 0, -10, 8, 12, 8, C_CYAN),
        (5, 0, -8, 6, 8, 6, C_LGRAY),
        (-5, 0, 8, 10, 6, 6, C_CYAN),
        (10, 0, 5, 6, 15, 6, C_LGRAY),
        (-15, 0, -20, 8, 10, 5, C_CYAN),
        (15, 0, -15, 5, 5, 5, C_GRAY),
        # Walkways between buildings
        (-2, 6, -2, 12, 0.5, 3, C_LGRAY),
        (-10, 8, 2, 5, 0.5, 8, C_GRAY),
        (8, 5, -5, 3, 0.5, 12, C_LGRAY),
        # Crystal switches (raised platforms)
        (-25, 0, 10, 4, 2, 4, C_YELLOW),
        (20, 0, 15, 4, 4, 4, C_YELLOW),
        (-20, 0, -25, 4, 6, 4, C_YELLOW),
        # Wire mesh platforms
        (0, 10, 10, 8, 0.3, 4, C_GRAY),
        (-8, 12, -15, 6, 0.3, 4, C_GRAY),
        # Upper area
        (15, 8, 10, 5, 0.5, 5, C_LGRAY),
        (-15, 10, 5, 4, 0.5, 4, C_CYAN),
        # Downtown
        (20, 0, -25, 10, 3, 8, C_LGRAY),
    ]
    stars = [V3(12, 16, 7)]
    coins = [V3(0, 4, 0), V3(8, 2, 3), V3(-8, 2, 12), V3(18, 2, -12),
             V3(-22, 3, 12), V3(22, 2, 17)]
    return p, stars, coins


def _c12_ttm():
    """Tall Tall Mountain - Very tall mountain with multiple tiers"""
    p = [
        # Ground
        (-40, -2, -40, 80, 2, 80, C_GREEN),
        # Mountain (very tall, many steps)
        (-12, 0, -12, 24, 5, 24, C_BROWN),
        (-10, 5, -10, 20, 5, 20, C_DGREEN),
        (-8, 10, -8, 16, 5, 16, C_BROWN),
        (-7, 15, -7, 14, 5, 14, C_GREEN),
        (-6, 20, -6, 12, 5, 12, C_BROWN),
        (-5, 25, -5, 10, 5, 10, C_DGREEN),
        (-4, 30, -4, 8, 4, 8, C_BROWN),
        (-3, 34, -3, 6, 3, 6, C_GRAY),
        # Summit
        (-2, 37, -2, 4, 1, 4, C_LGRAY),
        # Slide entrance (side cave)
        (12, 15, 0, 6, 5, 5, C_DGRAY),
        # Mushroom platforms
        (20, 5, 10, 4, 1, 4, C_RED),
        (25, 8, 15, 3, 1, 3, C_RED),
        (20, 11, 20, 4, 1, 4, C_RED),
        # Waterfall (blue wall on mountain)
        (12, 0, -8, 2, 25, 4, C_WATER),
        # Log bridge
        (-5, 0, 15, 10, 0.5, 2, C_BROWN),
        # Monty mole area
        (-30, 0, 15, 10, 1, 10, C_DGREEN),
        # Wind area
        (25, 0, -15, 8, 2, 8, C_GREEN),
        # Chuckya area
        (-25, 0, -20, 8, 1.5, 8, C_GREEN),
        # Hidden path
        (-20, 10, -5, 3, 0.5, 10, C_DBROWN),
    ]
    stars = [V3(0, 39, 0)]
    coins = [V3(5, 2, 5), V3(-10, 2, 8), V3(22, 7, 12), V3(15, 2, -5),
             V3(-25, 2, -15), V3(-28, 2, 18), V3(0, 16, 2)]
    return p, stars, coins


def _c13_thi():
    """Tiny-Huge Island - Two-scale island with hills and water"""
    p = [
        # Island ground
        (-50, -2, -50, 100, 2, 100, C_GREEN),
        # Central hill
        (-10, 0, -10, 20, 6, 20, C_DGREEN),
        (-8, 6, -8, 16, 4, 16, C_GREEN),
        # Beach area
        (20, -1, 20, 25, 0.5, 20, C_SAND),
        (20, -3, 25, 25, 1, 15, C_WATER),
        # Giant pipe
        (-25, 0, 5, 6, 8, 6, C_GREEN),
        # Wiggler cave
        (-20, 0, -25, 12, 5, 8, C_DGRAY),
        # Piranha plant field
        (15, 0, -20, 15, 0.5, 12, C_DGREEN),
        # Koopa race path
        (-5, 0, 15, 3, 0.5, 25, C_PATH),
        (5, 0, 30, 20, 0.5, 3, C_PATH),
        # Tiny mushrooms
        (30, 0, -10, 3, 2, 3, C_RED),
        (35, 0, -5, 2, 3, 2, C_RED),
        # Huge blocks
        (-35, 0, 20, 10, 4, 10, C_BROWN),
        (-40, 0, -10, 8, 6, 8, C_BROWN),
        # Platforms in water
        (25, -2, 30, 5, 2, 5, C_GRAY),
        (35, -2, 35, 4, 2, 4, C_GRAY),
    ]
    stars = [V3(-3, 11, -3)]
    coins = [V3(5, 2, 5), V3(-22, 2, 8), V3(25, 1, -15), V3(-15, 2, -20),
             V3(30, 2, 25), V3(0, 2, 25)]
    return p, stars, coins


def _c14_ttc():
    """Tick Tock Clock - Clock interior with moving platforms (static repr.)"""
    p = [
        # Clock base
        (-18, -2, -18, 36, 2, 36, C_DGRAY),
        # Central shaft (open in middle)
        (-3, 0, -3, 6, 40, 6, C_ORANGE),
        # Platforms at various heights (clock hands / gears)
        (-12, 2, -5, 8, 1, 4, C_LGRAY),
        (6, 4, -8, 5, 1, 5, C_ORANGE),
        (-10, 6, 4, 6, 1, 6, C_LGRAY),
        (8, 8, 5, 4, 1, 4, C_ORANGE),
        (-8, 10, -10, 5, 1, 5, C_LGRAY),
        (5, 12, 0, 6, 1, 3, C_ORANGE),
        (-6, 14, 6, 4, 1, 4, C_LGRAY),
        (8, 16, -5, 5, 1, 5, C_ORANGE),
        (-10, 18, 0, 6, 1, 4, C_LGRAY),
        (4, 20, 6, 5, 1, 5, C_ORANGE),
        (-8, 22, -8, 4, 1, 4, C_LGRAY),
        (6, 24, 3, 5, 1, 4, C_ORANGE),
        (-5, 26, -5, 8, 1, 3, C_LGRAY),
        (3, 28, -3, 4, 1, 4, C_ORANGE),
        (-7, 30, 2, 5, 1, 5, C_LGRAY),
        (5, 32, -2, 4, 1, 4, C_ORANGE),
        (-4, 34, -6, 6, 1, 4, C_LGRAY),
        (2, 36, 4, 5, 1, 5, C_ORANGE),
        # Top platform
        (-5, 38, -5, 10, 1, 10, C_LGRAY),
        # Gear decorations
        (-15, 5, -15, 3, 3, 3, C_YELLOW),
        (12, 10, 12, 3, 3, 3, C_YELLOW),
        (-14, 20, -14, 3, 3, 3, C_YELLOW),
        (13, 25, 13, 3, 3, 3, C_YELLOW),
        # Pendulum area
        (0, 15, 12, 3, 1, 3, C_GRAY),
    ]
    stars = [V3(0, 40, 0)]
    coins = [V3(-8, 4, -3), V3(8, 6, -5), V3(-7, 12, 2), V3(6, 18, -3),
             V3(-9, 24, -6), V3(4, 30, -1), V3(0, 36, 5)]
    return p, stars, coins


def _c15_rr():
    """Rainbow Ride - Platforms floating in the sky, rainbow paths"""
    rainbow_colors = [C_RED, C_ORANGE, C_YELLOW, C_GREEN, C_CYAN, C_BLUE, C_PURPLE, C_PINK]
    p = [
        # Starting platform
        (-5, -2, -5, 10, 2, 10, C_LGRAY),
        # Rainbow bridge path (series of colored platforms)
        (8, 1, -2, 5, 1, 4, C_RED),
        (15, 3, 0, 5, 1, 4, C_ORANGE),
        (22, 5, -3, 5, 1, 4, C_YELLOW),
        (28, 7, 2, 5, 1, 4, C_GREEN),
        (25, 9, 8, 5, 1, 4, C_CYAN),
        (18, 11, 10, 5, 1, 4, C_BLUE),
        (12, 13, 8, 5, 1, 4, C_PURPLE),
        (6, 15, 5, 5, 1, 5, C_PINK),
        # Flying ship
        (-10, 18, 15, 16, 2, 6, C_BROWN),
        (-10, 20, 16, 16, 1, 4, C_DBROWN),
        (-11, 20, 15, 2, 5, 6, C_BROWN),    # mast
        # House in the sky
        (-20, 20, -5, 10, 7, 8, C_RED),
        (-19, 27, -4, 8, 4, 6, C_BROWN),     # roof
        # Floating blocks
        (30, 12, -10, 4, 1, 4, C_CYAN),
        (35, 15, -5, 4, 1, 4, C_PINK),
        (32, 18, 0, 4, 1, 4, C_YELLOW),
        # Swing platform area
        (-15, 10, -15, 5, 1, 5, C_BLUE),
        (-22, 13, -12, 5, 1, 5, C_PURPLE),
        (-18, 16, -8, 5, 1, 5, C_CYAN),
        # Carpet ride endpoints
        (5, 20, -10, 5, 1, 5, C_STAR),
        # Final platform (high up)
        (-8, 25, -10, 8, 1, 8, C_PINK),
        # Tricky triangles
        (20, 20, 15, 4, 1, 4, C_GREEN),
        (15, 22, 20, 4, 1, 4, C_YELLOW),
    ]
    stars = [V3(-5, 27, -7)]
    coins = [V3(10, 3, 0), V3(24, 7, 0), V3(20, 13, 10), V3(-7, 20, 17),
             V3(32, 14, -8), V3(-17, 12, -12), V3(-18, 22, -2)]
    return p, stars, coins


def _bowser1():
    """Bowser in the Dark World - Dark platforming gauntlet"""
    p = [
        (-6, -2, -6, 12, 2, 12, C_DGRAY),
        (9, 0, 0, 5, 1, 5, C_GRAY),
        (17, 1, -3, 5, 1, 5, C_DGRAY),
        (24, 2, 2, 5, 1, 5, C_GRAY),
        (20, 3, 10, 5, 1, 5, C_DGRAY),
        (12, 4, 14, 5, 1, 5, C_GRAY),
        (5, 5, 18, 5, 1, 5, C_DGRAY),
        (-3, 6, 15, 5, 1, 5, C_GRAY),
        (-10, 7, 10, 5, 1, 5, C_DGRAY),
        (-14, 8, 3, 6, 1, 6, C_GRAY),
        (-8, 9, -5, 6, 1, 6, C_DGRAY),
        # Bowser arena
        (-6, 10, -12, 12, 1, 10, C_ORANGE),
    ]
    stars = [V3(0, 12, -8)]
    coins = []
    return p, stars, coins


def _bowser2():
    """Bowser in the Fire Sea - Lava-filled path"""
    p = [
        (-6, -2, -6, 12, 2, 12, C_DGRAY),
        (-40, -8, -40, 80, 2, 80, C_LAVA),
        (10, 0, 2, 5, 1, 5, C_GRAY),
        (18, 1, 6, 5, 1, 5, C_DGRAY),
        (26, 2, 2, 5, 1, 5, C_GRAY),
        (24, 3, -6, 5, 1, 5, C_DGRAY),
        (16, 4, -10, 5, 1, 5, C_GRAY),
        (8, 5, -15, 6, 1, 6, C_DGRAY),
        (0, 6, -22, 6, 1, 6, C_GRAY),
        (-8, 7, -18, 5, 1, 5, C_DGRAY),
        (-14, 8, -10, 6, 1, 6, C_GRAY),
        # Bowser arena
        (-18, 9, -5, 14, 1, 14, C_ORANGE),
    ]
    stars = [V3(-12, 11, 2)]
    coins = []
    return p, stars, coins


def _bowser3():
    """Bowser in the Sky - Final boss, high altitude platforms"""
    p = [
        (-6, -2, -6, 12, 2, 12, C_DGRAY),
        (9, 1, 3, 5, 1, 5, C_LGRAY),
        (17, 3, 1, 5, 1, 5, C_GRAY),
        (24, 5, 6, 5, 1, 5, C_LGRAY),
        (20, 7, 14, 5, 1, 5, C_GRAY),
        (12, 9, 18, 5, 1, 5, C_LGRAY),
        (4, 11, 15, 5, 1, 5, C_GRAY),
        (-4, 13, 10, 5, 1, 5, C_LGRAY),
        (-10, 15, 3, 5, 1, 5, C_GRAY),
        (-6, 17, -5, 6, 1, 6, C_LGRAY),
        # Final Bowser arena
        (-8, 19, -14, 16, 1, 16, C_STAR),
    ]
    stars = [V3(0, 21, -7)]
    coins = []
    return p, stars, coins


COURSE_FUNCS = [
    ("Peach's Castle", None),                # 0 - Hub (special)
    ("Bob-omb Battlefield", _c1_bobomb),     # 1
    ("Whomp's Fortress", _c2_whomp),         # 2
    ("Jolly Roger Bay", _c3_jrb),            # 3
    ("Cool Cool Mountain", _c4_ccm),         # 4
    ("Big Boo's Haunt", _c5_bbh),            # 5
    ("Hazy Maze Cave", _c6_hmc),             # 6
    ("Lethal Lava Land", _c7_lll),           # 7
    ("Shifting Sand Land", _c8_ssl),         # 8
    ("Dire Dire Docks", _c9_ddd),            # 9
    ("Snowman's Land", _c10_sl),             # 10
    ("Wet-Dry World", _c11_wdw),             # 11
    ("Tall Tall Mountain", _c12_ttm),        # 12
    ("Tiny-Huge Island", _c13_thi),          # 13
    ("Tick Tock Clock", _c14_ttc),           # 14
    ("Rainbow Ride", _c15_rr),               # 15
    ("Bowser Dark World", _bowser1),         # 16
    ("Bowser Fire Sea", _bowser2),           # 17
    ("Bowser in the Sky", _bowser3),         # 18
]

SKY_COLORS = [
    ((100, 160, 255), (180, 220, 255)),   # 0  Hub - bright blue
    ((100, 160, 255), (180, 220, 255)),   # 1  BoB - bright blue
    ((100, 160, 255), (200, 210, 220)),   # 2  WF
    ((60, 120, 200), (140, 180, 220)),    # 3  JRB - ocean blue
    ((140, 160, 200), (200, 210, 230)),   # 4  CCM - overcast
    ((30, 10, 40), (60, 30, 70)),         # 5  BBH - dark purple
    ((40, 30, 30), (80, 60, 50)),         # 6  HMC - cave brown
    ((80, 20, 0), (160, 60, 10)),         # 7  LLL - volcanic
    ((200, 170, 100), (240, 210, 150)),   # 8  SSL - desert sun
    ((30, 60, 120), (60, 100, 160)),      # 9  DDD - deep blue
    ((160, 180, 200), (200, 220, 240)),   # 10 SL - snowy
    ((100, 160, 255), (180, 220, 255)),   # 11 WDW
    ((100, 160, 255), (140, 200, 240)),   # 12 TTM
    ((100, 160, 255), (180, 220, 255)),   # 13 THI
    ((60, 40, 20), (120, 80, 40)),        # 14 TTC - dark interior
    ((140, 100, 200), (200, 160, 240)),   # 15 RR - rainbow sky
    ((10, 0, 20), (40, 10, 50)),          # 16 Bowser 1 - dark
    ((40, 0, 0), (100, 20, 0)),           # 17 Bowser 2 - fiery
    ((20, 20, 60), (80, 60, 140)),        # 18 Bowser 3 - cosmic
]


# ============================================================
# CAMERA
# ============================================================
class Camera:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.35
        self.dist = 35.0
        self.height = 15.0
        self.pos = V3()
        self.target = V3()

    def update(self, target):
        self.target = target.copy()
        self.pos = V3(
            self.target.x - math.sin(self.yaw) * self.dist,
            self.target.y + self.height,
            self.target.z - math.cos(self.yaw) * self.dist)


# ============================================================
# MARIO
# ============================================================
class Mario:
    def __init__(self, x=0, y=5, z=0):
        self.pos = V3(x, y, z)
        self.vel = V3()
        self.on_ground = False
        self.jump_count = 0
        self.facing = 0.0
        self.dead = False
        self.death_timer = 0
        self.size = 1.5
        self._jump_timer = 0

    def update(self, keys, cam_yaw, platforms):
        if self.dead:
            self.death_timer += 1
            self.vel.y -= GRAVITY
            self.pos.y += self.vel.y * 0.05
            return

        fwd = V3(math.sin(cam_yaw), 0, math.cos(cam_yaw))
        right = V3(math.cos(cam_yaw), 0, -math.sin(cam_yaw))

        move = V3()
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        spd = RUN_SPD if running else MOVE_SPD

        if keys[pygame.K_w]:
            move = move + fwd
        if keys[pygame.K_s]:
            move = move - fwd
        if keys[pygame.K_a]:
            move = move - right
        if keys[pygame.K_d]:
            move = move + right

        if move.xz_len() > 0.01:
            move = move.normalize()
            self.facing = math.atan2(move.x, move.z)
            if self.on_ground:
                self.vel.x = move.x * spd
                self.vel.z = move.z * spd
            else:
                self.vel.x += move.x * spd * AIR_CTRL * 0.1
                self.vel.z += move.z * spd * AIR_CTRL * 0.1
                xz_spd = math.sqrt(self.vel.x ** 2 + self.vel.z ** 2)
                if xz_spd > spd:
                    self.vel.x *= spd / xz_spd
                    self.vel.z *= spd / xz_spd
        else:
            if self.on_ground:
                self.vel.x *= FRICTION
                self.vel.z *= FRICTION

        if keys[pygame.K_SPACE] and self.on_ground:
            self.jump_count += 1
            if self.jump_count >= 3:
                self.vel.y = TJUMP_FORCE
                self.jump_count = 0
            elif self.jump_count == 2:
                self.vel.y = DJUMP_FORCE
            else:
                self.vel.y = JUMP_FORCE
            self.on_ground = False

        self.vel.y -= GRAVITY
        if self.vel.y < MAX_FALL:
            self.vel.y = MAX_FALL

        self.pos.x += self.vel.x * 0.16
        self.pos.z += self.vel.z * 0.16

        for plat in platforms:
            if self.pos.y > plat.y and self.pos.y < plat.y + plat.h + 3:
                self.pos.x, self.pos.z = plat.collide_side(
                    self.pos.x, self.pos.z, self.size)

        self.pos.y += self.vel.y * 0.16
        self.on_ground = False

        for plat in platforms:
            if plat.contains_xz(self.pos.x, self.pos.z):
                top = plat.top_y()
                if self.pos.y <= top + 0.5 and self.pos.y >= top - 2 and self.vel.y <= 0:
                    self.pos.y = top
                    self.vel.y = 0
                    self.on_ground = True

        if self.on_ground and not keys[pygame.K_SPACE]:
            self._jump_timer += 1
            if self._jump_timer > 15:
                self.jump_count = 0
        else:
            self._jump_timer = 0

        if self.pos.y < -30:
            self.die()

    def die(self):
        self.dead = True
        self.vel = V3(0, 8, 0)
        self.death_timer = 0

    def get_faces(self):
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        s = 1.2
        faces = []
        # Body (blue overalls)
        faces += make_box_faces(x - s * 0.5, y, z - s * 0.5, s, s * 1.0, s, C_MARIO_B)
        # Head/hat (red)
        faces += make_box_faces(x - s * 0.4, y + s * 1.0, z - s * 0.4,
                                s * 0.8, s * 0.8, s * 0.8, C_MARIO_R)
        # Face (skin tone front)
        faces += make_box_faces(x - s * 0.3, y + s * 1.0, z - s * 0.5,
                                s * 0.6, s * 0.5, s * 0.1, C_MARIO_S)
        # Hat brim
        faces += make_box_faces(x - s * 0.5, y + s * 1.5, z - s * 0.55,
                                s * 1.0, s * 0.15, s * 0.2, C_MARIO_R)
        return faces


# ============================================================
# COLLECTIBLES
# ============================================================
class Star:
    def __init__(self, pos):
        self.pos = pos
        self.collected = False
        self.bob_offset = random.uniform(0, 6.28)

    def get_faces(self, time_ms):
        if self.collected:
            return []
        bob = math.sin(time_ms / 500 + self.bob_offset) * 0.5
        spin = time_ms / 300
        x, y, z = self.pos.x, self.pos.y + bob, self.pos.z
        # Rotating star (two intersecting boxes for star shape)
        faces = make_box_faces(x - 0.8, y, z - 0.8, 1.6, 1.6, 1.6, C_STAR)
        # Add glow effect (slightly larger translucent box)
        glow_s = 0.3 * math.sin(time_ms / 200) + 0.3
        faces += make_box_faces(x - 1.0 - glow_s, y - glow_s, z - 1.0 - glow_s,
                                2.0 + glow_s * 2, 2.0 + glow_s * 2, 2.0 + glow_s * 2,
                                (255, 255, 180))
        return faces

    def check_collect(self, player_pos):
        if self.collected:
            return False
        dx = player_pos.x - self.pos.x
        dy = player_pos.y - self.pos.y
        dz = player_pos.z - self.pos.z
        if dx * dx + dy * dy + dz * dz < 16:
            self.collected = True
            return True
        return False


class Coin:
    def __init__(self, pos):
        self.pos = pos
        self.collected = False
        self.bob_offset = random.uniform(0, 6.28)

    def get_faces(self, time_ms):
        if self.collected:
            return []
        bob = math.sin(time_ms / 400 + self.bob_offset) * 0.3
        x, y, z = self.pos.x, self.pos.y + bob + 1, self.pos.z
        return make_box_faces(x - 0.4, y, z - 0.4, 0.8, 0.8, 0.8, C_COIN)

    def check_collect(self, player_pos):
        if self.collected:
            return False
        dx = player_pos.x - self.pos.x
        dy = player_pos.y - (self.pos.y + 1)
        dz = player_pos.z - self.pos.z
        if dx * dx + dy * dy + dz * dz < 9:
            self.collected = True
            return True
        return False


# ============================================================
# GAME
# ============================================================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("SUPER MARIO 64 PC PORT v1")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont('Arial', 48, bold=True)
        self.font_big = pygame.font.SysFont('Arial', 32)
        self.font_med = pygame.font.SysFont('Arial', 22)
        self.font_sm = pygame.font.SysFont('Arial', 16)
        self.font_hud = pygame.font.SysFont('Courier', 20, bold=True)
        self.state = 'menu'
        self.menu_sel = 0
        self.current_course = 0
        self.total_stars = 0
        self.stars_collected = set()
        self.coins = 0
        self.lives = 4
        self.platforms = []
        self.stars = []
        self.coins_list = []
        self.deco_faces = []
        self.mario = None
        self.camera = Camera()
        self.portal_list = []
        self.running = True
        self.flash_timer = 0
        self.msg = ""
        self.msg_timer = 0

    def load_course(self, idx):
        self.current_course = idx
        self.deco_faces = []

        if idx == 0:
            # Hub world - special builder
            plats, stars, coins, deco, portals = _build_castle_hub()
            self.platforms = plats
            self.stars = [Star(s) for s in stars]
            self.coins_list = [Coin(c) for c in coins]
            self.deco_faces = deco
            self.portal_list = portals
            self.mario = Mario(0, 5, -58)  # Start south of bridge
            self.camera = Camera()
            self.camera.yaw = 0
        else:
            _, func = COURSE_FUNCS[idx]
            plat_data, star_data, coin_data = func()
            self.platforms = [Platform(*p[:7]) for p in plat_data]
            self.stars = [Star(s) for s in star_data]
            self.coins_list = [Coin(c) for c in coin_data]
            self.portal_list = []
            self.mario = Mario(0, 5, 5)
            self.camera = Camera()
            self.camera.yaw = 0

        # Check already collected stars
        for s in self.stars:
            key = (idx, round(s.pos.x), round(s.pos.z))
            if key in self.stars_collected:
                s.collected = True

        self.msg = COURSE_FUNCS[idx][0]
        self.msg_timer = 120

    def draw_sky(self, top_color, bottom_color):
        for y in range(0, SH, 3):
            t = y / SH
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SW, y))
            pygame.draw.line(self.screen, (r, g, b), (0, y + 1), (SW, y + 1))
            pygame.draw.line(self.screen, (r, g, b), (0, y + 2), (SW, y + 2))

    def draw_hud(self):
        name = COURSE_FUNCS[self.current_course][0]
        # HUD background
        s = pygame.Surface((SW, 40), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        self.screen.blit(s, (0, 0))

        # Star icon + count
        pygame.draw.polygon(self.screen, C_STAR,
                            [(22, 8), (26, 18), (37, 18), (28, 24), (31, 34), (22, 28),
                             (13, 34), (16, 24), (7, 18), (18, 18)])
        star_txt = self.font_hud.render(f"x {self.total_stars}", True, C_WHITE)
        self.screen.blit(star_txt, (42, 10))

        # Coin icon + count
        pygame.draw.circle(self.screen, C_COIN, (130, 20), 10)
        pygame.draw.circle(self.screen, (200, 160, 20), (130, 20), 7)
        coin_txt = self.font_hud.render(f"x {self.coins}", True, C_WHITE)
        self.screen.blit(coin_txt, (145, 10))

        # Course name
        name_txt = self.font_hud.render(name, True, C_WHITE)
        self.screen.blit(name_txt, (SW // 2 - name_txt.get_width() // 2, 10))

        # Lives
        lives_txt = self.font_hud.render(f"MARIO x{self.lives}", True, C_WHITE)
        self.screen.blit(lives_txt, (SW - lives_txt.get_width() - 15, 10))

        # Course enter message
        if self.msg_timer > 0:
            self.msg_timer -= 1
            alpha = min(255, self.msg_timer * 4)
            msg_s = self.font_big.render(self.msg, True, C_WHITE)
            bg = pygame.Surface((msg_s.get_width() + 20, msg_s.get_height() + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, min(140, alpha)))
            self.screen.blit(bg, (SW // 2 - bg.get_width() // 2, SH // 2 - 70))
            self.screen.blit(msg_s, (SW // 2 - msg_s.get_width() // 2, SH // 2 - 65))

    def do_menu(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_sel = (self.menu_sel - 1) % 4
                elif event.key == pygame.K_DOWN:
                    self.menu_sel = (self.menu_sel + 1) % 4
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.menu_sel == 0:
                        self.total_stars = 0
                        self.stars_collected = set()
                        self.coins = 0
                        self.lives = 4
                        self.load_course(0)
                        self.state = 'play'
                    elif self.menu_sel == 1:
                        self.state = 'controls'
                    elif self.menu_sel == 2:
                        self.state = 'about'
                    elif self.menu_sel == 3:
                        self.running = False
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

        self.screen.fill(C_BLACK)
        t = pygame.time.get_ticks()

        # Animated stars background
        for i in range(25):
            x = (t // 50 + i * 100) % (SW + 200) - 100
            y = 100 + int(math.sin(t / 1000 + i) * 50) + i * 20
            sz = 3 + int(math.sin(t / 800 + i * 2) * 2)
            pygame.draw.circle(self.screen, C_STAR, (int(x), int(y) % SH), sz)

        # Title
        shadow = self.font_title.render("SUPER MARIO 64", True, (80, 40, 0))
        self.screen.blit(shadow, (SW // 2 - shadow.get_width() // 2 + 3, 83))
        title = self.font_title.render("SUPER MARIO 64", True, C_TITLE)
        self.screen.blit(title, (SW // 2 - title.get_width() // 2, 80))
        sub = self.font_big.render("PC PORT v1", True, C_WHITE)
        self.screen.blit(sub, (SW // 2 - sub.get_width() // 2, 140))

        # Menu items
        items = ["START GAME", "CONTROLS", "ABOUT", "EXIT"]
        for i, item in enumerate(items):
            c = C_SEL if i == self.menu_sel else C_MENU
            txt = self.font_med.render(item, True, c)
            r = txt.get_rect(center=(SW // 2, 240 + i * 50))
            self.screen.blit(txt, r)
            if i == self.menu_sel:
                # Animated arrow
                offset = int(math.sin(t / 200) * 3)
                a = self.font_med.render(">", True, C_TITLE)
                self.screen.blit(a, (r.x - 30 + offset, r.y))

        # Blinking prompt
        if (t // 500) % 2 == 0:
            press = self.font_sm.render("Press SPACE to select", True, C_MENU)
            self.screen.blit(press, (SW // 2 - press.get_width() // 2, SH - 50))

        ft = self.font_sm.render(
            "15 Courses + Castle Hub + Bowser | Software 3D | 60 FPS",
            True, (100, 100, 100))
        self.screen.blit(ft, (SW // 2 - ft.get_width() // 2, SH - 25))

    def do_info(self, title_text, lines):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                    self.state = 'menu'
                    return
        self.screen.fill(C_BLACK)
        t = self.font_big.render(title_text, True, C_TITLE)
        self.screen.blit(t, (SW // 2 - t.get_width() // 2, 40))
        for i, line in enumerate(lines):
            txt = self.font_sm.render(line, True, C_WHITE)
            self.screen.blit(txt, (60, 100 + i * 26))
        back = self.font_sm.render("Press ESC or SPACE to go back", True, C_MENU)
        self.screen.blit(back, (SW // 2 - back.get_width() // 2, SH - 30))

    def do_controls(self):
        self.do_info("CONTROLS", [
            "MOVEMENT:",
            "  W / S          - Move forward / backward (camera-relative)",
            "  A / D          - Strafe left / right",
            "  SHIFT          - Run (hold while moving)",
            "  SPACE          - Jump (press again for double/triple jump)",
            "",
            "CAMERA:",
            "  LEFT / RIGHT   - Rotate camera around Mario",
            "  UP / DOWN      - Adjust camera pitch",
            "",
            "OTHER:",
            "  ESC            - Return to hub / menu",
            "  R              - Respawn if stuck",
            "",
            "TIPS:",
            "  - Walk onto colored pads near the castle to enter courses",
            "  - Collect the golden Star in each course",
            "  - Triple jump (3 quick SPACE presses) goes very high!",
            "  - Run + Jump for maximum distance",
            "  - 8 stars to access Bowser 1 & 2, 15 for final Bowser",
        ])

    def do_about(self):
        self.do_info("ABOUT", [
            "SUPER MARIO 64 PC PORT v1 - Enhanced Edition",
            "",
            "A tribute to Super Mario 64 (1996, Nintendo 64)",
            "Original game by Nintendo EAD / Shigeru Miyamoto",
            "",
            "Features:",
            "  - Detailed Peach's Castle hub with towers & moat",
            "  - All 15 main courses with themed level design",
            "  - 3 Bowser challenge levels",
            "  - SM64-style movement (triple jump, running)",
            "  - Star and coin collection",
            "  - Software 3D renderer - no OpenGL needed",
            "  - Orbiting 3D camera system",
            "  - 60 FPS target",
            "  - No external files required",
            "",
            "Built with Python + Pygame | Single file",
        ])

    def do_play(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_course == 0:
                        self.state = 'menu'
                    else:
                        self.load_course(0)
                    return
                if event.key == pygame.K_r:
                    if self.current_course == 0:
                        self.mario.pos = V3(0, 5, -58)
                    else:
                        self.mario.pos = V3(0, 5, 5)
                    self.mario.vel = V3()
                    self.mario.dead = False
                    self.mario.on_ground = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.camera.yaw -= CAM_SPD
        if keys[pygame.K_RIGHT]:
            self.camera.yaw += CAM_SPD
        if keys[pygame.K_UP]:
            self.camera.pitch = min(1.2, self.camera.pitch + CAM_SPD * 0.5)
        if keys[pygame.K_DOWN]:
            self.camera.pitch = max(-0.2, self.camera.pitch - CAM_SPD * 0.5)

        self.mario.update(keys, self.camera.yaw, self.platforms)

        if self.mario.dead and self.mario.death_timer > 60:
            self.lives -= 1
            if self.lives <= 0:
                self.state = 'gameover'
                return
            else:
                self.load_course(self.current_course if self.current_course > 0 else 0)
                return

        # Star collection
        for star in self.stars:
            if star.check_collect(self.mario.pos):
                key = (self.current_course, round(star.pos.x), round(star.pos.z))
                if key not in self.stars_collected:
                    self.stars_collected.add(key)
                    self.total_stars += 1
                self.msg = f"GOT STAR! ({self.total_stars}/15)"
                self.msg_timer = 120
                self.flash_timer = 30
                if self.current_course > 0:
                    self.load_course(0)
                    return

        # Coin collection
        for coin in self.coins_list:
            if coin.check_collect(self.mario.pos):
                self.coins += 1

        # Portal detection (hub only)
        if self.current_course == 0:
            for px, pz, cidx in self.portal_list:
                dx = self.mario.pos.x - px
                dz = self.mario.pos.z - pz
                if dx * dx + dz * dz < 14 and self.mario.on_ground:
                    if cidx >= 16 and self.total_stars < 8:
                        self.msg = f"Need {8 - self.total_stars} more stars!"
                        self.msg_timer = 90
                    elif cidx == 18 and self.total_stars < 15:
                        self.msg = "Need all 15 stars for final Bowser!"
                        self.msg_timer = 90
                    else:
                        self.load_course(cidx)
                        return

        # Win condition
        if self.total_stars >= 15 and self.current_course == 18:
            for star in self.stars:
                if star.collected:
                    self.state = 'win'
                    return

        self.camera.update(self.mario.pos)

        # === RENDERING ===
        sky_top, sky_bottom = SKY_COLORS[min(self.current_course, len(SKY_COLORS) - 1)]
        self.draw_sky(sky_top, sky_bottom)

        all_faces = []
        cam_pos = self.camera.pos
        cam_yaw = self.camera.yaw
        cam_pitch = self.camera.pitch

        # Distance culling for platforms
        for plat in self.platforms:
            cx = plat.x + plat.w / 2
            cz = plat.z + plat.d / 2
            dx = cx - cam_pos.x
            dz = cz - cam_pos.z
            if dx * dx + dz * dz < 12000:
                all_faces.extend(plat.get_faces())

        # Decorative faces (castle geometry, trees, etc.)
        for df in self.deco_faces:
            if isinstance(df, tuple) and len(df) == 3:
                verts, color, normal = df
                face_center = V3(
                    sum(v.x for v in verts) / len(verts),
                    sum(v.y for v in verts) / len(verts),
                    sum(v.z for v in verts) / len(verts))
                dx = face_center.x - cam_pos.x
                dz = face_center.z - cam_pos.z
                if dx * dx + dz * dz < 12000:
                    all_faces.append(df)

        # Collectibles
        t_ms = pygame.time.get_ticks()
        for star in self.stars:
            all_faces.extend(star.get_faces(t_ms))
        for coin in self.coins_list:
            all_faces.extend(coin.get_faces(t_ms))

        # Mario
        if not self.mario.dead or self.mario.death_timer < 40:
            all_faces.extend(self.mario.get_faces())

        render_faces(self.screen, all_faces, cam_pos, cam_yaw, cam_pitch)

        # Shadow
        shadow_pos = V3(self.mario.pos.x, 0.1, self.mario.pos.z)
        for plat in self.platforms:
            if plat.contains_xz(self.mario.pos.x, self.mario.pos.z):
                shadow_pos.y = plat.top_y() + 0.05
                break
        sp, _ = project(shadow_pos, cam_pos, cam_yaw, cam_pitch)
        if sp and 0 < sp[0] < SW and 0 < sp[1] < SH:
            r = max(2, int(8 - abs(self.mario.pos.y - shadow_pos.y) * 0.3))
            shadow_surf = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100), (0, 0, r * 2, r))
            self.screen.blit(shadow_surf, (sp[0] - r, sp[1] - r // 2))

        # Flash effect on star collect
        if self.flash_timer > 0:
            self.flash_timer -= 1
            flash_s = pygame.Surface((SW, SH), pygame.SRCALPHA)
            flash_s.fill((255, 255, 200, min(self.flash_timer * 8, 100)))
            self.screen.blit(flash_s, (0, 0))

        self.draw_hud()

        # Portal labels (hub only)
        if self.current_course == 0:
            portal_names = [
                "1: Bob-omb BF", "2: Whomp's", "3: Jolly Roger",
                "4: Cool Cool Mt", "5: Boo's Haunt", "6: Hazy Maze",
                "7: Lethal Lava", "8: Sand Land", "9: Dire Docks",
                "10: Snowman's", "11: Wet-Dry", "12: Tall Mt",
                "13: Tiny-Huge", "14: Tick Tock", "15: Rainbow",
                "BOWSER 1", "BOWSER 2", "BOWSER 3",
            ]
            for i, (px, pz, cidx) in enumerate(self.portal_list):
                pp, depth = project(V3(px, 3.5, pz), cam_pos, cam_yaw, cam_pitch)
                if pp and 0 < pp[0] < SW and 0 < pp[1] < SH and depth > 0 and depth < 80:
                    label = portal_names[min(i, len(portal_names) - 1)]
                    collected = any(k[0] == cidx for k in self.stars_collected)
                    color = C_STAR if collected else C_WHITE
                    lt = self.font_sm.render(label, True, color)
                    # Background for readability
                    bg = pygame.Surface((lt.get_width() + 4, lt.get_height() + 2), pygame.SRCALPHA)
                    bg.fill((0, 0, 0, 120))
                    self.screen.blit(bg, (pp[0] - lt.get_width() // 2 - 2, pp[1] - 22))
                    self.screen.blit(lt, (pp[0] - lt.get_width() // 2, pp[1] - 20))

    def do_gameover(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = 'menu'
                    self.menu_sel = 0
        self.screen.fill(C_BLACK)
        go = self.font_big.render("GAME OVER", True, C_RED)
        self.screen.blit(go, (SW // 2 - go.get_width() // 2, SH // 2 - 60))
        sc = self.font_med.render(f"Stars: {self.total_stars}/15", True, C_STAR)
        self.screen.blit(sc, (SW // 2 - sc.get_width() // 2, SH // 2))
        cn = self.font_med.render(f"Coins: {self.coins}", True, C_COIN)
        self.screen.blit(cn, (SW // 2 - cn.get_width() // 2, SH // 2 + 35))
        pr = self.font_sm.render("Press SPACE to continue", True, C_MENU)
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            self.screen.blit(pr, (SW // 2 - pr.get_width() // 2, SH // 2 + 90))

    def do_win(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = 'menu'
                    self.menu_sel = 0
        self.screen.fill(C_BLACK)
        t = pygame.time.get_ticks()
        # Celebration particles
        for i in range(30):
            x = (t // 30 + i * 80) % (SW + 100) - 50
            y = (i * 47 + int(math.sin(t / 600 + i) * 30)) % SH
            colors = [C_RED, C_YELLOW, C_GREEN, C_CYAN, C_PINK, C_STAR]
            pygame.draw.circle(self.screen, colors[i % len(colors)], (int(x), y), 2 + i % 3)
        cg = self.font_title.render("CONGRATULATIONS!", True, C_TITLE)
        self.screen.blit(cg, (SW // 2 - cg.get_width() // 2, 80))
        w1 = self.font_big.render("You collected all 15 Stars!", True, C_WHITE)
        self.screen.blit(w1, (SW // 2 - w1.get_width() // 2, 160))
        w2 = self.font_big.render("and defeated Bowser!", True, C_WHITE)
        self.screen.blit(w2, (SW // 2 - w2.get_width() // 2, 200))
        w3 = self.font_big.render("SUPER MARIO 64", True, C_TITLE)
        self.screen.blit(w3, (SW // 2 - w3.get_width() // 2, 280))
        cn = self.font_med.render(f"Total Coins: {self.coins}", True, C_COIN)
        self.screen.blit(cn, (SW // 2 - cn.get_width() // 2, 350))
        th = self.font_med.render("Thank you so much for-a playing my game!", True, C_WHITE)
        self.screen.blit(th, (SW // 2 - th.get_width() // 2, 420))
        # Animated Mario
        mx = SW // 2 - 10 + int(math.sin(t / 300) * 40)
        pygame.draw.rect(self.screen, C_MARIO_R, (mx, 480, 20, 12))
        pygame.draw.rect(self.screen, C_MARIO_B, (mx, 492, 20, 13))
        pygame.draw.rect(self.screen, C_MARIO_S, (mx + 4, 482, 12, 8))
        pr = self.font_sm.render("Press SPACE to return to menu", True, C_MENU)
        if (t // 500) % 2 == 0:
            self.screen.blit(pr, (SW // 2 - pr.get_width() // 2, SH - 40))

    def run(self):
        while self.running:
            if self.state == 'menu':
                self.do_menu()
            elif self.state == 'controls':
                self.do_controls()
            elif self.state == 'about':
                self.do_about()
            elif self.state == 'play':
                self.do_play()
            elif self.state == 'gameover':
                self.do_gameover()
            elif self.state == 'win':
                self.do_win()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
