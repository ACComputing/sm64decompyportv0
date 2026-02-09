#!/usr/bin/env python3
"""
SUPER MARIO 64 PC PORT v0
3D Platformer - All 15 Courses + Castle Hub + Bowser Levels
Pure Python + Pygame Software 3D Renderer | Files: OFF
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

# Colors
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_RED = (220, 40, 20)
C_BLUE = (30, 30, 200)
C_DBLUE = (20, 20, 140)
C_GREEN = (34, 139, 34)
C_DGREEN = (20, 100, 20)
C_BROWN = (139, 90, 43)
C_DBROWN = (100, 60, 30)
C_GRAY = (140, 140, 140)
C_DGRAY = (90, 90, 90)
C_LGRAY = (180, 180, 180)
C_YELLOW = (255, 220, 40)
C_ORANGE = (240, 140, 20)
C_SAND = (210, 180, 120)
C_SNOW = (230, 240, 255)
C_ICE = (180, 220, 255)
C_LAVA = (220, 60, 10)
C_PURPLE = (120, 40, 160)
C_PINK = (240, 140, 180)
C_CYAN = (40, 200, 220)
C_WATER = (40, 80, 200)
C_DWATER = (20, 40, 140)
C_CASTLE = (160, 150, 130)
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
    v = [V3(x, y, z), V3(x + w, y, z), V3(x + w, y + h, z), V3(x, y + h, z),
         V3(x, y, z + d), V3(x + w, y, z + d), V3(x + w, y + h, z + d), V3(x, y + h, z + d)]
    return [
        ([v[0], v[1], v[2], v[3]], shade(color, 1.0), V3(0, 0, -1)),
        ([v[5], v[4], v[7], v[6]], shade(color, 0.75), V3(0, 0, 1)),
        ([v[4], v[0], v[3], v[7]], shade(color, 0.85), V3(-1, 0, 0)),
        ([v[1], v[5], v[6], v[2]], shade(color, 0.80), V3(1, 0, 0)),
        ([v[3], v[2], v[6], v[7]], shade(color, 1.15), V3(0, 1, 0)),
        ([v[0], v[4], v[5], v[1]], shade(color, 0.60), V3(0, -1, 0)),
    ]


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
    def __init__(self, x, y, z, w, h, d, color):
        self.x, self.y, self.z = x, y, z
        self.w, self.h, self.d = w, h, d
        self.color = color
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


# ============================================================
# COURSE DATA - All 15 Courses + Hub + 3 Bowser
# ============================================================

def _hub():
    p = [
        (-60, -2, -60, 120, 2, 120, C_GREEN),
        (-15, 0, -40, 30, 15, 20, C_CASTLE),
        (-15, 15, -40, 8, 12, 8, C_CASTLE),
        (7, 15, -40, 8, 12, 8, C_CASTLE),
        (-5, 15, -38, 10, 8, 10, C_CASTLE),
        (-5, 0, -20, 10, 1, 5, C_BRICK),
        (-4, 0, -15, 8, 0.5, 15, C_LGRAY),
        (25, 0, 10, 6, 2, 6, C_RED),
        (35, 0, -5, 6, 2, 6, C_GRAY),
        (35, 0, -20, 6, 2, 6, C_WATER),
        (25, 0, -35, 6, 2, 6, C_SNOW),
        (10, 0, -45, 6, 2, 6, C_PURPLE),
        (-35, 0, 10, 6, 2, 6, C_DGRAY),
        (-45, 0, -5, 6, 2, 6, C_LAVA),
        (-45, 0, -20, 6, 2, 6, C_SAND),
        (-35, 0, -35, 6, 2, 6, C_DWATER),
        (-20, 0, -45, 6, 2, 6, C_ICE),
        (30, 0, 25, 6, 2, 6, C_CYAN),
        (-5, 0, 35, 6, 2, 6, C_BROWN),
        (-40, 0, 25, 6, 2, 6, C_DGREEN),
        (15, 0, 35, 6, 2, 6, C_ORANGE),
        (-25, 0, 35, 6, 2, 6, C_PINK),
        (-3, 0, 45, 6, 3, 6, C_DGRAY),
    ]
    return p, [], []


def _c1():
    return [
        (-50, -2, -50, 100, 2, 100, C_GREEN),
        (-20, 0, -20, 10, 2, 10, C_DBROWN),
        (-15, 2, -15, 8, 3, 8, C_BROWN),
        (-12, 5, -12, 6, 3, 6, C_BROWN),
        (-10, 8, -10, 4, 2, 4, C_DGRAY),
        (15, 0, 10, 12, 1, 4, C_BROWN),
        (15, 0, -15, 8, 3, 8, C_GREEN),
        (-30, 0, 20, 10, 1.5, 10, C_GREEN),
        (30, 0, -30, 8, 2, 8, C_GREEN),
        (-10, 0, 30, 15, 1, 3, C_BROWN),
        (20, 0, 25, 6, 4, 6, C_GRAY),
        (-35, 0, -10, 6, 1, 6, C_DGREEN),
    ], [V3(-8, 11, -8)], \
       [V3(10, 2, 10), V3(-10, 2, 10), V3(20, 2, -20), V3(-30, 2, 25), V3(0, 2, 0)]


def _c2():
    return [
        (-20, -2, -20, 40, 2, 40, C_GRAY),
        (-8, 0, -8, 16, 3, 16, C_LGRAY),
        (-6, 3, -6, 12, 3, 12, C_GRAY),
        (-4, 6, -4, 8, 3, 8, C_LGRAY),
        (-3, 9, -3, 6, 3, 6, C_GRAY),
        (-2, 12, -2, 4, 2, 4, C_LGRAY),
        (10, 0, 5, 5, 6, 3, C_BROWN),
        (-15, 0, 10, 4, 4, 4, C_GRAY),
        (8, 3, 12, 6, 1, 3, C_BROWN),
        (-12, 0, -15, 5, 2, 5, C_DGRAY),
        (15, 0, -10, 3, 8, 3, C_LGRAY),
    ], [V3(0, 15, 0)], \
       [V3(5, 2, 5), V3(-5, 2, -5), V3(12, 2, 8), V3(-12, 2, 12)]


def _c3():
    return [
        (-40, -2, -40, 80, 2, 80, C_SAND),
        (-35, -6, -35, 70, 4, 70, C_WATER),
        (-10, 0, -10, 20, 1.5, 20, C_SAND),
        (20, 0, 0, 8, 2, 12, C_BROWN),
        (-25, 0, 15, 6, 1, 6, C_SAND),
        (15, -3, 20, 10, 3, 8, C_DGRAY),
        (-20, -2, -25, 8, 2, 8, C_GRAY),
        (0, 0, 25, 5, 5, 3, C_BROWN),
        (-30, 0, -5, 4, 3, 4, C_GRAY),
        (25, 0, -20, 5, 1, 5, C_SAND),
    ], [V3(17, 6, 22)], \
       [V3(0, 2, 0), V3(10, 2, 5), V3(-20, 2, 18), V3(22, 2, -15)]


def _c4():
    return [
        (-30, -2, -30, 60, 2, 60, C_SNOW),
        (-5, 0, -5, 10, 15, 10, C_SNOW),
        (-3, 15, -3, 6, 2, 6, C_ICE),
        (15, 0, 0, 8, 6, 8, C_SNOW),
        (-20, 0, 10, 6, 3, 6, C_ICE),
        (0, 0, 20, 10, 1, 3, C_BROWN),
        (-15, 0, -20, 5, 8, 5, C_SNOW),
        (20, 0, -15, 4, 4, 10, C_SNOW),
        (10, 0, 15, 3, 2, 3, C_ICE),
        (-25, 0, -10, 8, 1.5, 8, C_SNOW),
    ], [V3(0, 18, 0)], \
       [V3(5, 2, 5), V3(-15, 2, -15), V3(18, 2, 3), V3(-22, 2, 12)]


def _c5():
    return [
        (-25, -2, -25, 50, 2, 50, C_DGREEN),
        (-10, 0, -10, 20, 8, 20, C_DGRAY),
        (-8, 8, -8, 16, 6, 16, C_GRAY),
        (-5, 14, -5, 10, 4, 10, C_DGRAY),
        (-3, 18, -3, 6, 2, 6, C_GRAY),
        (15, 0, 5, 4, 12, 4, C_DGRAY),
        (-20, 0, 15, 6, 3, 6, C_PURPLE),
        (10, 0, -18, 5, 2, 5, C_DGRAY),
        (-18, 0, -15, 3, 5, 3, C_GRAY),
        (0, 0, 18, 8, 1, 3, C_BROWN),
    ], [V3(0, 21, 0)], \
       [V3(5, 2, 5), V3(-15, 2, 10), V3(12, 2, -12), V3(-18, 2, -10)]


def _c6():
    return [
        (-35, -2, -35, 70, 2, 70, C_DGRAY),
        (-15, 0, -15, 30, 8, 30, C_GRAY),
        (-10, 0, -10, 20, 1.5, 20, C_BROWN),
        (15, 0, 5, 8, 4, 8, C_DGRAY),
        (-25, 0, 10, 6, 3, 6, C_GRAY),
        (0, 0, 20, 10, 2, 5, C_BROWN),
        (-20, 0, -20, 5, 6, 5, C_DGRAY),
        (20, 0, -15, 4, 5, 4, C_GRAY),
        (-5, 2, 0, 10, 1, 10, C_BROWN),
        (25, 0, 20, 6, 2, 6, C_DGRAY),
    ], [V3(0, 4, 0)], \
       [V3(5, 2, 5), V3(-10, 2, 15), V3(18, 2, -10), V3(-22, 2, 12)]


def _c7():
    return [
        (-40, -4, -40, 80, 2, 80, C_LAVA),
        (-5, -2, -5, 10, 2, 10, C_DGRAY),
        (15, -2, 0, 6, 2, 6, C_GRAY),
        (-18, -2, 10, 5, 2, 5, C_DGRAY),
        (0, -2, 20, 8, 2, 4, C_GRAY),
        (20, -2, -15, 5, 2, 5, C_DGRAY),
        (-25, -2, -10, 6, 2, 6, C_GRAY),
        (10, -2, 15, 4, 2, 4, C_DGRAY),
        (-10, -2, -20, 5, 2, 5, C_GRAY),
        (-5, -2, 30, 8, 2, 8, C_DGRAY),
        (0, 0, 0, 4, 8, 4, C_BROWN),
        (25, -2, 20, 5, 2, 5, C_GRAY),
    ], [V3(1, 9, 1)], \
       [V3(17, 1, 2), V3(-16, 1, 12), V3(2, 1, 22), V3(22, 1, -13)]


def _c8():
    return [
        (-45, -2, -45, 90, 2, 90, C_SAND),
        (-5, 0, -5, 10, 12, 10, C_SAND),
        (-3, 12, -3, 6, 8, 6, C_SAND),
        (-2, 20, -2, 4, 4, 4, C_SAND),
        (20, 0, 10, 8, 3, 8, C_BROWN),
        (-25, 0, 0, 6, 2, 6, C_SAND),
        (15, 0, -20, 5, 4, 5, C_BROWN),
        (-15, 0, 25, 8, 1.5, 8, C_SAND),
        (30, 0, -10, 4, 6, 4, C_BROWN),
        (-30, 0, -25, 6, 2, 6, C_SAND),
    ], [V3(0, 25, 0)], \
       [V3(10, 2, 10), V3(-20, 2, 5), V3(25, 2, -15), V3(-12, 2, 28)]


def _c9():
    return [
        (-35, -6, -35, 70, 4, 70, C_DWATER),
        (-30, -2, -30, 60, 2, 60, C_WATER),
        (-8, 0, -8, 16, 1.5, 16, C_GRAY),
        (15, 0, 0, 10, 2, 6, C_BROWN),
        (-20, 0, 10, 6, 3, 6, C_GRAY),
        (0, 0, 20, 8, 1, 4, C_BROWN),
        (20, -3, 15, 12, 3, 8, C_DGRAY),
        (-15, 0, -18, 5, 2, 5, C_GRAY),
        (10, 0, -15, 4, 4, 4, C_BROWN),
        (-25, 0, -5, 3, 5, 3, C_GRAY),
    ], [V3(22, 1, 17)], \
       [V3(0, 2, 0), V3(10, 2, 5), V3(-15, 2, 12), V3(17, 2, -10)]


def _c10():
    return [
        (-35, -2, -35, 70, 2, 70, C_SNOW),
        (-5, 0, -5, 10, 16, 10, C_SNOW),
        (-3, 16, -3, 6, 6, 6, C_WHITE),
        (20, 0, 0, 8, 3, 8, C_ICE),
        (-20, 0, 15, 6, 2, 6, C_SNOW),
        (10, 0, 20, 5, 5, 5, C_ICE),
        (-15, 0, -20, 8, 1.5, 8, C_SNOW),
        (25, 0, -15, 4, 4, 4, C_ICE),
        (0, 0, 28, 6, 1, 4, C_BROWN),
        (-28, 0, 0, 5, 6, 5, C_SNOW),
    ], [V3(0, 23, 0)], \
       [V3(10, 2, 5), V3(-15, 2, 18), V3(22, 2, -10), V3(-25, 2, 3)]


def _c11():
    return [
        (-30, -2, -30, 60, 2, 60, C_LGRAY),
        (-5, 0, -5, 10, 4, 10, C_CYAN),
        (10, 0, 0, 6, 8, 6, C_LGRAY),
        (-15, 0, 10, 5, 12, 5, C_GRAY),
        (0, 0, 15, 8, 6, 4, C_CYAN),
        (20, 0, -10, 4, 10, 4, C_LGRAY),
        (-20, 0, -15, 6, 3, 6, C_GRAY),
        (5, 4, 5, 8, 1, 8, C_CYAN),
        (-10, 8, -10, 6, 1, 6, C_LGRAY),
        (15, 6, 10, 4, 1, 4, C_GRAY),
    ], [V3(-13, 13, 12)], \
       [V3(0, 2, 0), V3(12, 2, 3), V3(-8, 2, 12), V3(18, 2, -8)]


def _c12():
    return [
        (-30, -2, -30, 60, 2, 60, C_GREEN),
        (-8, 0, -8, 16, 5, 16, C_BROWN),
        (-6, 5, -6, 12, 5, 12, C_BROWN),
        (-5, 10, -5, 10, 5, 10, C_GRAY),
        (-4, 15, -4, 8, 5, 8, C_GRAY),
        (-3, 20, -3, 6, 5, 6, C_LGRAY),
        (-2, 25, -2, 4, 3, 4, C_SNOW),
        (15, 0, 10, 6, 3, 6, C_GREEN),
        (-20, 0, 5, 5, 7, 5, C_BROWN),
        (10, 5, 15, 4, 1, 8, C_BROWN),
        (20, 0, -15, 8, 2, 8, C_GREEN),
    ], [V3(0, 29, 0)], \
       [V3(5, 2, 5), V3(-15, 2, 8), V3(18, 2, 12), V3(-8, 6, -5)]


def _c13():
    return [
        (-40, -2, -40, 80, 2, 80, C_GREEN),
        (-10, 0, -10, 20, 3, 20, C_BROWN),
        (20, 0, 5, 12, 2, 12, C_GREEN),
        (-25, 0, 15, 8, 4, 8, C_BROWN),
        (10, 0, 25, 6, 6, 6, C_GREEN),
        (-15, 0, -25, 10, 2, 10, C_DGREEN),
        (25, 0, -20, 5, 8, 5, C_BROWN),
        (0, 3, 5, 6, 1, 6, C_GREEN),
        (-30, 0, -10, 4, 5, 4, C_BROWN),
        (0, 0, 30, 8, 1.5, 4, C_BROWN),
    ], [V3(12, 7, 27)], \
       [V3(5, 2, 5), V3(-20, 2, 18), V3(22, 2, -15), V3(-12, 2, -22)]


def _c14():
    return [
        (-15, -2, -15, 30, 2, 30, C_ORANGE),
        (-4, 0, -4, 8, 3, 8, C_DGRAY),
        (-3, 3, -3, 6, 3, 6, C_LGRAY),
        (-2, 6, -2, 4, 3, 4, C_DGRAY),
        (-1, 9, -1, 2, 4, 2, C_GRAY),
        (8, 0, 0, 4, 6, 4, C_ORANGE),
        (-10, 0, 5, 3, 8, 3, C_LGRAY),
        (5, 3, 8, 6, 1, 3, C_DGRAY),
        (-8, 4, -8, 4, 1, 4, C_ORANGE),
        (0, 6, 10, 5, 1, 5, C_LGRAY),
        (10, 8, -5, 3, 1, 3, C_DGRAY),
    ], [V3(0, 14, 0)], \
       [V3(6, 2, 3), V3(-8, 2, 7), V3(9, 2, -3), V3(-5, 5, -5)]


def _c15():
    return [
        (-5, -2, -5, 10, 2, 10, C_PINK),
        (10, 1, 0, 6, 1, 5, C_CYAN),
        (20, 4, -5, 5, 1, 5, C_YELLOW),
        (28, 7, 0, 6, 1, 5, C_PINK),
        (22, 10, 8, 5, 1, 5, C_CYAN),
        (12, 13, 10, 6, 1, 5, C_YELLOW),
        (5, 16, 5, 5, 1, 5, C_PINK),
        (-5, 19, 0, 6, 1, 6, C_CYAN),
        (-12, 22, -5, 5, 1, 5, C_YELLOW),
        (-5, 25, -10, 8, 1, 8, C_PINK),
        (0, 10, 15, 4, 1, 4, C_STAR),
    ], [V3(-2, 27, -7)], \
       [V3(12, 3, 2), V3(22, 6, -2), V3(14, 15, 12), V3(-10, 24, -3)]


def _bowser1():
    return [
        (-5, -2, -5, 10, 2, 10, C_DGRAY),
        (8, 0, 0, 5, 1, 4, C_GRAY),
        (16, 1, -3, 4, 1, 4, C_DGRAY),
        (22, 2, 0, 5, 1, 5, C_GRAY),
        (15, 3, 8, 4, 1, 4, C_DGRAY),
        (8, 4, 12, 6, 1, 4, C_GRAY),
        (0, 5, 15, 5, 1, 5, C_DGRAY),
        (-8, 6, 10, 4, 1, 4, C_GRAY),
        (-12, 7, 2, 5, 1, 5, C_DGRAY),
        (-5, 8, -5, 8, 1, 8, C_ORANGE),
    ], [V3(-2, 10, -2)], []


def _bowser2():
    return [
        (-5, -2, -5, 10, 2, 10, C_DGRAY),
        (-30, -6, -30, 60, 2, 60, C_LAVA),
        (10, 0, 0, 4, 1, 4, C_GRAY),
        (18, 1, 5, 5, 1, 5, C_DGRAY),
        (25, 2, -2, 4, 1, 4, C_GRAY),
        (20, 3, -10, 5, 1, 5, C_DGRAY),
        (10, 4, -15, 4, 1, 4, C_GRAY),
        (0, 5, -20, 6, 1, 6, C_DGRAY),
        (-10, 6, -15, 4, 1, 4, C_GRAY),
        (-15, 7, -5, 8, 1, 8, C_ORANGE),
    ], [V3(-12, 9, -2)], []


def _bowser3():
    return [
        (-5, -2, -5, 10, 2, 10, C_DGRAY),
        (8, 1, 2, 4, 1, 4, C_LGRAY),
        (15, 3, 0, 5, 1, 5, C_GRAY),
        (22, 5, 5, 4, 1, 4, C_LGRAY),
        (18, 7, 12, 5, 1, 5, C_GRAY),
        (10, 9, 15, 4, 1, 4, C_LGRAY),
        (2, 11, 12, 5, 1, 5, C_GRAY),
        (-5, 13, 8, 4, 1, 4, C_LGRAY),
        (-10, 15, 0, 6, 1, 6, C_GRAY),
        (-5, 17, -8, 10, 1, 10, C_STAR),
    ], [V3(-1, 19, -4)], []


COURSE_FUNCS = [
    ("Peach's Castle", _hub),
    ("Bob-omb Battlefield", _c1),
    ("Whomp's Fortress", _c2),
    ("Jolly Roger Bay", _c3),
    ("Cool Cool Mountain", _c4),
    ("Big Boo's Haunt", _c5),
    ("Hazy Maze Cave", _c6),
    ("Lethal Lava Land", _c7),
    ("Shifting Sand Land", _c8),
    ("Dire Dire Docks", _c9),
    ("Snowman's Land", _c10),
    ("Wet-Dry World", _c11),
    ("Tall Tall Mountain", _c12),
    ("Tiny-Huge Island", _c13),
    ("Tick Tock Clock", _c14),
    ("Rainbow Ride", _c15),
    ("Bowser Dark World", _bowser1),
    ("Bowser Fire Sea", _bowser2),
    ("Bowser in the Sky", _bowser3),
]

SKY_COLORS = [
    ((100, 160, 255), (180, 220, 255)),
    ((100, 160, 255), (180, 220, 255)),
    ((100, 160, 255), (200, 210, 220)),
    ((60, 120, 200), (140, 180, 220)),
    ((140, 160, 200), (200, 210, 230)),
    ((30, 10, 40), (60, 30, 70)),
    ((40, 30, 30), (80, 60, 50)),
    ((80, 20, 0), (160, 60, 10)),
    ((200, 170, 100), (240, 210, 150)),
    ((30, 60, 120), (60, 100, 160)),
    ((160, 180, 200), (200, 220, 240)),
    ((100, 160, 255), (180, 220, 255)),
    ((100, 160, 255), (140, 200, 240)),
    ((100, 160, 255), (180, 220, 255)),
    ((60, 40, 20), (120, 80, 40)),
    ((140, 100, 200), (200, 160, 240)),
    ((10, 0, 20), (40, 10, 50)),
    ((40, 0, 0), (100, 20, 0)),
    ((20, 20, 60), (80, 60, 140)),
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
        faces += make_box_faces(x - s * 0.5, y, z - s * 0.5, s, s * 1.0, s, C_MARIO_B)
        faces += make_box_faces(x - s * 0.4, y + s * 1.0, z - s * 0.4,
                                s * 0.8, s * 0.8, s * 0.8, C_MARIO_R)
        faces += make_box_faces(x - s * 0.3, y + s * 1.0, z - s * 0.5,
                                s * 0.6, s * 0.5, s * 0.1, C_MARIO_S)
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
        x, y, z = self.pos.x, self.pos.y + bob, self.pos.z
        return make_box_faces(x - 0.8, y, z - 0.8, 1.6, 1.6, 1.6, C_STAR)

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
        pygame.display.set_caption("SUPER MARIO 64 PC PORT v0")
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
        self.mario = None
        self.camera = Camera()
        self.course_portals = []
        self.running = True
        self.flash_timer = 0
        self.msg = ""
        self.msg_timer = 0

    def load_course(self, idx):
        self.current_course = idx
        _, func = COURSE_FUNCS[idx]
        plat_data, star_data, coin_data = func()
        self.platforms = [Platform(*p) for p in plat_data]
        self.stars = [Star(s) for s in star_data]
        self.coins_list = [Coin(c) for c in coin_data]
        for s in self.stars:
            key = (idx, round(s.pos.x), round(s.pos.z))
            if key in self.stars_collected:
                s.collected = True
        self.mario = Mario(0, 5, 5)
        self.camera = Camera()
        self.camera.yaw = 0
        self.msg = COURSE_FUNCS[idx][0]
        self.msg_timer = 120
        if idx == 0:
            self._setup_hub_portals()

    def _setup_hub_portals(self):
        portal_plats = [
            (25, 10, 1), (35, -5, 2), (35, -20, 3), (25, -35, 4), (10, -45, 5),
            (-35, 10, 6), (-45, -5, 7), (-45, -20, 8), (-35, -35, 9), (-20, -45, 10),
            (30, 25, 11), (-5, 35, 12), (-40, 25, 13), (15, 35, 14), (-25, 35, 15),
            (-3, 45, 16),
        ]
        self.course_portals = [(x + 3, z + 3, c) for x, z, c in portal_plats]

    def draw_sky(self, top_color, bottom_color):
        for y in range(0, SH, 2):
            t = y / SH
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SW, y))
            pygame.draw.line(self.screen, (r, g, b), (0, y + 1), (SW, y + 1))

    def draw_hud(self):
        name = COURSE_FUNCS[self.current_course][0]
        s = pygame.Surface((SW, 36), pygame.SRCALPHA)
        s.fill((0, 0, 0, 140))
        self.screen.blit(s, (0, 0))
        star_txt = self.font_hud.render(f"STARS {self.total_stars}/15", True, C_STAR)
        self.screen.blit(star_txt, (10, 8))
        coin_txt = self.font_hud.render(f"COINS {self.coins}", True, C_COIN)
        self.screen.blit(coin_txt, (200, 8))
        name_txt = self.font_hud.render(name, True, C_WHITE)
        self.screen.blit(name_txt, (SW // 2 - name_txt.get_width() // 2, 8))
        lives_txt = self.font_hud.render(f"x{self.lives}", True, C_WHITE)
        self.screen.blit(lives_txt, (SW - 60, 8))
        if self.msg_timer > 0:
            self.msg_timer -= 1
            msg_s = self.font_big.render(self.msg, True, C_WHITE)
            self.screen.blit(msg_s, (SW // 2 - msg_s.get_width() // 2, SH // 2 - 60))

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
        for i in range(20):
            x = (t // 50 + i * 100) % (SW + 200) - 100
            y = 100 + int(math.sin(t / 1000 + i) * 50) + i * 25
            sz = 3 + int(math.sin(t / 800 + i * 2) * 2)
            pygame.draw.circle(self.screen, C_STAR, (int(x), int(y) % SH), sz)
        title = self.font_title.render("SUPER MARIO 64", True, C_TITLE)
        sub = self.font_big.render("PC PORT v0", True, C_WHITE)
        self.screen.blit(title, (SW // 2 - title.get_width() // 2, 80))
        self.screen.blit(sub, (SW // 2 - sub.get_width() // 2, 140))
        items = ["START GAME", "CONTROLS", "ABOUT", "EXIT"]
        for i, item in enumerate(items):
            c = C_SEL if i == self.menu_sel else C_MENU
            txt = self.font_med.render(item, True, c)
            r = txt.get_rect(center=(SW // 2, 240 + i * 50))
            self.screen.blit(txt, r)
            if i == self.menu_sel:
                a = self.font_med.render("> ", True, C_TITLE)
                self.screen.blit(a, (r.x - 30, r.y))
        press = self.font_sm.render("Press SPACE to select", True, C_MENU)
        if (t // 500) % 2 == 0:
            self.screen.blit(press, (SW // 2 - press.get_width() // 2, SH - 50))
        ft = self.font_sm.render(
            "All 15 Courses + Bowser Levels | 3D Software Renderer | Files: OFF",
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
            "  SPACE          - Jump (press multiple times for double/triple jump)",
            "",
            "CAMERA:",
            "  LEFT / RIGHT   - Rotate camera around Mario",
            "  UP / DOWN      - Adjust camera pitch",
            "",
            "OTHER:",
            "  ESC            - Return to menu / hub",
            "  R              - Respawn (if stuck)",
            "",
            "TIPS:",
            "  - Walk onto colored platforms in the castle to enter courses",
            "  - Collect the golden Star in each course to clear it",
            "  - Triple jump (3 quick Space presses) goes very high!",
            "  - Run + Jump for maximum distance",
            "  - Collect 15 stars to access the final Bowser level",
        ])

    def do_about(self):
        self.do_info("ABOUT", [
            "SUPER MARIO 64 PC PORT v0",
            "",
            "A tribute to Super Mario 64 (1996, Nintendo 64)",
            "Original game by Nintendo EAD / Shigeru Miyamoto",
            "",
            "Features:",
            "  - Software 3D renderer (no OpenGL needed)",
            "  - All 15 main courses with unique themes",
            "  - 3 Bowser challenge levels",
            "  - Peach's Castle hub world with course portals",
            "  - SM64-style movement (triple jump, running)",
            "  - Star and coin collection",
            "  - Orbiting 3D camera",
            "  - No external files required",
            "",
            "Built entirely with Python + Pygame",
            "",
            "#cat's SM64 PC Port v0",
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

        for coin in self.coins_list:
            if coin.check_collect(self.mario.pos):
                self.coins += 1

        if self.current_course == 0:
            for px, pz, cidx in self.course_portals:
                dx = self.mario.pos.x - px
                dz = self.mario.pos.z - pz
                if dx * dx + dz * dz < 12 and self.mario.on_ground:
                    if cidx >= 16 and self.total_stars < 8:
                        self.msg = f"Need {8 - self.total_stars} more stars!"
                        self.msg_timer = 90
                    elif cidx == 18 and self.total_stars < 15:
                        self.msg = "Need all 15 stars for final Bowser!"
                        self.msg_timer = 90
                    else:
                        self.load_course(cidx)
                        return

        if self.total_stars >= 15 and self.current_course == 18:
            for star in self.stars:
                if star.collected:
                    self.state = 'win'
                    return

        self.camera.update(self.mario.pos)

        sky_top, sky_bottom = SKY_COLORS[min(self.current_course, len(SKY_COLORS) - 1)]
        self.draw_sky(sky_top, sky_bottom)

        all_faces = []
        cam_pos = self.camera.pos
        cam_yaw = self.camera.yaw
        cam_pitch = self.camera.pitch

        for plat in self.platforms:
            cx = plat.x + plat.w / 2
            cz = plat.z + plat.d / 2
            dx = cx - cam_pos.x
            dz = cz - cam_pos.z
            if dx * dx + dz * dz < 10000:
                all_faces.extend(plat.get_faces())

        t_ms = pygame.time.get_ticks()
        for star in self.stars:
            all_faces.extend(star.get_faces(t_ms))
        for coin in self.coins_list:
            all_faces.extend(coin.get_faces(t_ms))

        if not self.mario.dead or self.mario.death_timer < 40:
            all_faces.extend(self.mario.get_faces())

        render_faces(self.screen, all_faces, cam_pos, cam_yaw, cam_pitch)

        shadow_pos = V3(self.mario.pos.x, 0.1, self.mario.pos.z)
        for plat in self.platforms:
            if plat.contains_xz(self.mario.pos.x, self.mario.pos.z):
                shadow_pos.y = plat.top_y() + 0.05
                break
        sp, _ = project(shadow_pos, cam_pos, cam_yaw, cam_pitch)
        if sp and 0 < sp[0] < SW and 0 < sp[1] < SH:
            r = max(2, int(8 - abs(self.mario.pos.y - shadow_pos.y) * 0.3))
            pygame.draw.circle(self.screen, (0, 0, 0), sp, r)

        if self.flash_timer > 0:
            self.flash_timer -= 1
            flash_s = pygame.Surface((SW, SH), pygame.SRCALPHA)
            flash_s.fill((255, 255, 200, min(self.flash_timer * 8, 100)))
            self.screen.blit(flash_s, (0, 0))

        self.draw_hud()

        if self.current_course == 0:
            portal_names = [
                "1:BoB", "2:WF", "3:JRB", "4:CCM", "5:BBH",
                "6:HMC", "7:LLL", "8:SSL", "9:DDD", "10:SL",
                "11:WDW", "12:TTM", "13:THI", "14:TTC", "15:RR",
                "BOWSER"]
            for i, (px, pz, cidx) in enumerate(self.course_portals):
                pp, depth = project(V3(px, 4, pz), cam_pos, cam_yaw, cam_pitch)
                if pp and 0 < pp[0] < SW and 0 < pp[1] < SH and depth > 0:
                    label = portal_names[min(i, len(portal_names) - 1)]
                    collected = any(k[0] == cidx for k in self.stars_collected)
                    color = C_STAR if collected else C_WHITE
                    lt = self.font_sm.render(label, True, color)
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
        go = self.font_big.render("GAME OVER", True, C_WHITE)
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
        for i in range(30):
            x = (t // 30 + i * 80) % (SW + 100) - 50
            y = (i * 47 + int(math.sin(t / 600 + i) * 30)) % SH
            pygame.draw.circle(self.screen, C_STAR, (int(x), y), 2 + i % 3)
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
