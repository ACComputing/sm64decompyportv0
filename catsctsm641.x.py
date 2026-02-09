#!/usr/bin/env python3
"""
============================================================================
 Cat's SM64 Py Port 5.0 — PC Port Edition
 Faithful recreation of the SM64 PC Port (sm64-port / sm64ex)
 All 15 Main Courses + Castle Hub + Bowser Stages + Secret Levels
 60 FPS display / 30 Hz logic (N64-accurate timing)
 Authentic SM64 physics from the decomp, Lakitu camera, proper Mario model
 Procedural SFX, punch combos, slide kicks, proper HUD
 Single-File Build — No external assets required
============================================================================
"""
import pygame, math, sys, random, struct, array, time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Set

# ============================================================================
#  ENGINE CONFIG
# ============================================================================
WIDTH, HEIGHT = 960, 720
FPS = 60
LOGIC_HZ = 30
FRAME_SKIP = FPS // LOGIC_HZ
FOV = 500
NEAR_CLIP = 10
FAR_CLIP = 12000

S16_MAX = 32767

# ============================================================================
#  MATH TYPES
# ============================================================================
@dataclass
class Vec3f:
    x: float = 0.0; y: float = 0.0; z: float = 0.0
    def set(self, x, y, z): self.x, self.y, self.z = x, y, z
    def copy(self): return Vec3f(self.x, self.y, self.z)
    def dist_to(self, o):
        dx, dy, dz = self.x-o.x, self.y-o.y, self.z-o.z
        return math.sqrt(dx*dx+dy*dy+dz*dz)
    def __add__(self, o): return Vec3f(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return Vec3f(self.x-o.x, self.y-o.y, self.z-o.z)
    def scale(self, s): return Vec3f(self.x*s, self.y*s, self.z*s)
    def length(self): return math.sqrt(self.x*self.x+self.y*self.y+self.z*self.z)
    def normalize(self):
        l = self.length()
        if l < 0.0001: return Vec3f(0, 0, 0)
        return Vec3f(self.x/l, self.y/l, self.z/l)

@dataclass
class Vec3s:
    x: int = 0; y: int = 0; z: int = 0

def clamp(v, lo, hi): return max(lo, min(hi, v))
def lerp(a, b, t): return a + (b - a) * t
def approach_f32(cur, tgt, inc):
    if cur < tgt: return min(cur+inc, tgt)
    elif cur > tgt: return max(cur-inc, tgt)
    return cur
def approach_angle(cur, tgt, inc):
    d = (tgt - cur + 180) % 360 - 180
    if d > inc: return cur + inc
    if d < -inc: return cur - inc
    return tgt
def sins(d): return math.sin(math.radians(d))
def coss(d): return math.cos(math.radians(d))
def atan2d(y, x): return math.degrees(math.atan2(y, x))
def _cc(c): return tuple(max(0, min(255, int(v))) for v in c)

class GameState(Enum):
    TITLE=auto(); FILE_SELECT=auto(); LEVEL_SELECT=auto(); GAMEPLAY=auto()
    PAUSE=auto(); DEATH=auto(); STAR_GRAB=auto()

# ============================================================================
#  SM64 ACTIONS — From the decomp
# ============================================================================
ACT_IDLE          = 0x0C400201
ACT_WALKING       = 0x04000440
ACT_DECELERATING  = 0x0400044A
ACT_CROUCH_IDLE   = 0x0C008220
ACT_PUNCHING      = 0x00800380
ACT_PUNCH2        = 0x00800381
ACT_KICK          = 0x00800382
ACT_JUMP          = 0x03000880
ACT_DOUBLE_JUMP   = 0x03000881
ACT_TRIPLE_JUMP   = 0x01000882
ACT_BACKFLIP      = 0x01000883
ACT_LONG_JUMP     = 0x03000888
ACT_WALL_KICK     = 0x03000886
ACT_SIDE_FLIP     = 0x01000887
ACT_FREEFALL      = 0x0100088C
ACT_DIVE          = 0x0188088A
ACT_BELLY_SLIDE   = 0x00020446
ACT_GROUND_POUND  = 0x008008A9
ACT_GP_LAND       = 0x008008AB
ACT_SLIDE_KICK    = 0x018008AA
ACT_SLIDE_KICK_SL = 0x00020449
ACT_KNOCKBACK     = 0x02020C00
ACT_LAVA_BOOST    = 0x00020C02
ACT_STAR_DANCE    = 0x00001302
ACT_DEATH         = 0x00020C04

# Short-form for map keys
_A = {
    'idle': ACT_IDLE, 'walk': ACT_WALKING, 'decel': ACT_DECELERATING,
    'crouch': ACT_CROUCH_IDLE, 'punch': ACT_PUNCHING, 'punch2': ACT_PUNCH2,
    'kick': ACT_KICK,
    'jump': ACT_JUMP, 'djump': ACT_DOUBLE_JUMP, 'triple': ACT_TRIPLE_JUMP,
    'bflip': ACT_BACKFLIP, 'ljump': ACT_LONG_JUMP, 'wkick': ACT_WALL_KICK,
    'sflip': ACT_SIDE_FLIP, 'free': ACT_FREEFALL,
    'dive': ACT_DIVE, 'belly': ACT_BELLY_SLIDE,
    'gp': ACT_GROUND_POUND, 'gpl': ACT_GP_LAND,
    'skick': ACT_SLIDE_KICK, 'sksl': ACT_SLIDE_KICK_SL,
    'knock': ACT_KNOCKBACK, 'lava': ACT_LAVA_BOOST,
    'star': ACT_STAR_DANCE, 'death': ACT_DEATH
}

# Physics constants from the SM64 decomp
GRAVITY = -4.0
MAX_FALL = -75.0
MAX_WALK = 32.0
AIR_DRAG = 0.98
AIR_ACCEL = 0.0
WALL_KICK_VEL = 52.0
JUMP_VEL = 42.0
DBL_JUMP_VEL = 52.0
TRIPLE_VEL = 69.0
BACKFLIP_VEL = 62.0
SIDEFLIP_VEL = 62.0
LONGJUMP_VEL = 30.0
DIVE_VEL = 10.0
GP_FALL_VEL = -60.0
LAVA_BOOST_VEL = 60.0
KNOCKBACK_VEL = 30.0

IN_A = 0x01; IN_B = 0x02; IN_Z = 0x04
IN_A_D = 0x10; IN_B_D = 0x20; IN_Z_D = 0x40

@dataclass
class Controller:
    stick_x: float = 0; stick_y: float = 0; stick_mag: float = 0
    pressed: int = 0; down: int = 0

# ============================================================================
#  SURFACE TYPES
# ============================================================================
SURF_DEFAULT = 0; SURF_LAVA = 1; SURF_SLIP = 2; SURF_DEATH = 3
SURF_WATER = 4; SURF_ICE = 5; SURF_SAND = 6

@dataclass
class Surface:
    verts: List[Vec3f]; normal: Vec3f; stype: int = 0
    color: Tuple[int,int,int] = (200,200,200); warp: int = -1

# ============================================================================
#  OBJECT SYSTEM
# ============================================================================
class ObjType(Enum):
    COIN=auto(); COIN_RED=auto(); COIN_BLUE=auto(); STAR=auto()
    GOOMBA=auto(); BOBOMB=auto(); BULLY=auto(); BOO=auto()
    PIRANHA=auto(); KOOPA=auto(); AMP=auto(); THWOMP=auto()
    CHAIN_CHOMP=auto(); KING_BOB=auto(); BIG_BOO=auto(); BOWSER=auto()
    ONE_UP=auto(); TREE=auto(); PIPE=auto(); BOX=auto()

@dataclass
class Obj:
    type: ObjType; pos: Vec3f; vel: Vec3f = field(default_factory=Vec3f)
    angle: float = 0; radius: float = 50; height: float = 50; hp: int = 1
    active: bool = True; timer: int = 0; state: int = 0; home: Vec3f = field(default_factory=Vec3f)
    color: Tuple[int,int,int] = (255,255,0); collected: bool = False
    irange: float = 80; scale: float = 1.0; dmg: int = 1; coins: int = 0; star_id: int = 0
    warp: int = -1; spd: float = 1.5; pdir: int = 1; bob: float = 0; flash: int = 0

@dataclass
class Particle:
    pos: Vec3f; vel: Vec3f; color: Tuple[int,int,int]; life: int; size: float = 3.0
    kind: int = 0  # 0=normal, 1=sparkle, 2=smoke

class Particles:
    def __init__(self): self.ps: List[Particle] = []
    def emit(self, p, n, c, s=5.0, l=20, sz=3.0, kind=0):
        for _ in range(n):
            v = Vec3f(random.uniform(-s,s), random.uniform(0,s*1.5), random.uniform(-s,s))
            self.ps.append(Particle(p.copy(), v, c, l, sz, kind))
    def emit_sparkle(self, p, n=5):
        for _ in range(n):
            v = Vec3f(random.uniform(-3,3), random.uniform(2,8), random.uniform(-3,3))
            c = random.choice([(255,255,100),(255,200,50),(255,255,200),(255,255,255)])
            self.ps.append(Particle(p.copy(), v, c, random.randint(15,30), random.uniform(2,5), 1))
    def emit_smoke(self, p, n=3):
        for _ in range(n):
            v = Vec3f(random.uniform(-1,1), random.uniform(1,4), random.uniform(-1,1))
            g = random.randint(180,240)
            self.ps.append(Particle(p.copy(), v, (g,g,g), random.randint(10,25), random.uniform(3,8), 2))
    def update(self):
        alive = []
        for p in self.ps:
            p.pos.x += p.vel.x; p.pos.y += p.vel.y; p.pos.z += p.vel.z
            p.vel.y -= 0.3 if p.kind != 2 else -0.1
            p.life -= 1
            if p.kind == 2: p.size *= 1.03; p.vel.x *= 0.95; p.vel.z *= 0.95
            if p.life > 0: alive.append(p)
        self.ps = alive

# ============================================================================
#  MARIO STATE — Matches decomp struct layout
# ============================================================================
@dataclass
class MarioState:
    pos: Vec3f = field(default_factory=Vec3f); vel: Vec3f = field(default_factory=Vec3f)
    fvel: float = 0.0; face: Vec3s = field(default_factory=Vec3s)
    action: int = ACT_IDLE; prev_act: int = ACT_IDLE; astate: int = 0; atimer: int = 0
    health: int = 0x880; coins: int = 0; stars: int = 0; lives: int = 4
    floor: Optional[Surface] = None; floor_y: float = -10000
    wall: Optional[Surface] = None; imag: float = 0; iyaw: int = 0
    peak_y: float = 0; jcount: int = 0; jtimer: int = 0; wktimer: int = 0
    hurt: int = 0; inv: int = 0; lvl_stars: Dict[int,Set[int]] = field(default_factory=dict)
    punch_state: int = 0; punch_timer: int = 0
    squish: float = 1.0; squish_vel: float = 0.0
    anim_frame: int = 0; bob_phase: float = 0.0

    def set_act(self, a, arg=0):
        self.prev_act = self.action; self.action = a; self.astate = 0; self.atimer = 0
        self.anim_frame = 0
    def heal(self, amt): self.health = min(0x880, self.health + amt)
    def take_dmg(self, amt):
        if self.inv > 0: return
        self.health = max(0, self.health - amt); self.hurt = 10; self.inv = 60
    def wedges(self): return (self.health >> 8) & 0xF
    def has_star(self, l, s): return s in self.lvl_stars.get(l, set())
    def get_star(self, l, s):
        if l not in self.lvl_stars: self.lvl_stars[l] = set()
        if s not in self.lvl_stars[l]: self.lvl_stars[l].add(s); self.stars += 1

# ============================================================================
#  AUDIO ENGINE — Procedural SFX
# ============================================================================
AUDIO_RATE = 22050

def _gen_tone(freq, dur, vol=0.3, wave='square'):
    n = int(AUDIO_RATE * dur)
    buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE
        env = max(0, 1.0 - t / dur)
        if wave == 'square':
            v = 1.0 if (t * freq) % 1.0 < 0.5 else -1.0
        elif wave == 'noise':
            v = random.uniform(-1, 1)
        elif wave == 'tri':
            p = (t * freq) % 1.0
            v = 4 * abs(p - 0.5) - 1
        elif wave == 'sine':
            v = math.sin(2 * math.pi * freq * t)
        else:
            v = 0
        buf.append(int(v * vol * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_jump():
    n = int(AUDIO_RATE * 0.15); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE; f = 300 + t * 3000
        env = max(0, 1 - t / 0.15)
        v = 1.0 if (t * f) % 1.0 < 0.5 else -1.0
        buf.append(int(v * 0.2 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_coin():
    n = int(AUDIO_RATE * 0.12); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE
        f = 1500 if t < 0.04 else 2000
        env = max(0, 1 - t / 0.12)
        v = math.sin(2 * math.pi * f * t)
        buf.append(int(v * 0.25 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_stomp():
    n = int(AUDIO_RATE * 0.1); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE; f = 200 - t * 800
        env = max(0, 1 - t / 0.1)
        v = random.uniform(-1, 1) * 0.5 + (1.0 if (t * max(20, f)) % 1.0 < 0.5 else -1.0) * 0.5
        buf.append(int(v * 0.2 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_star():
    n = int(AUDIO_RATE * 0.6); buf = array.array('h')
    notes = [523, 659, 784, 1047, 784, 1047]
    note_len = n // len(notes)
    for i in range(n):
        ni = min(i // note_len, len(notes) - 1)
        t = i / AUDIO_RATE; f = notes[ni]
        env = max(0, 1 - (i % note_len) / note_len * 0.5) * max(0, 1 - t / 0.6 * 0.3)
        v = math.sin(2 * math.pi * f * t) * 0.4 + math.sin(2 * math.pi * f * 2 * t) * 0.15
        buf.append(int(v * 0.25 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_hurt():
    n = int(AUDIO_RATE * 0.2); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE; f = 400 - t * 1200
        env = max(0, 1 - t / 0.2)
        v = random.uniform(-1, 1) * 0.6 + math.sin(2 * math.pi * max(50, f) * t) * 0.4
        buf.append(int(v * 0.2 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_punch():
    n = int(AUDIO_RATE * 0.08); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE
        env = max(0, 1 - t / 0.08)
        v = random.uniform(-1, 1) * 0.7 + math.sin(2 * math.pi * 150 * t) * 0.3
        buf.append(int(v * 0.18 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_1up():
    n = int(AUDIO_RATE * 0.35); buf = array.array('h')
    notes = [523, 659, 784, 1047, 1319]
    note_len = n // len(notes)
    for i in range(n):
        ni = min(i // note_len, len(notes) - 1)
        t = i / AUDIO_RATE; f = notes[ni]
        env = max(0, 1 - (i % note_len) / note_len * 0.3) * max(0, 1 - t / 0.35 * 0.2)
        v = math.sin(2 * math.pi * f * t)
        buf.append(int(v * 0.2 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _gen_wahoo():
    n = int(AUDIO_RATE * 0.25); buf = array.array('h')
    for i in range(n):
        t = i / AUDIO_RATE
        f = 250 + math.sin(t * 15) * 100 + t * 400
        env = max(0, 1 - t / 0.25)
        v = math.sin(2 * math.pi * f * t) * 0.5 + math.sin(2 * math.pi * f * 1.5 * t) * 0.3
        buf.append(int(v * 0.15 * env * 32767))
    return pygame.mixer.Sound(buffer=buf)

sfx = {}

def init_audio():
    global sfx
    try:
        pygame.mixer.init(AUDIO_RATE, -16, 1, 512)
        sfx['jump'] = _gen_jump()
        sfx['coin'] = _gen_coin()
        sfx['stomp'] = _gen_stomp()
        sfx['star'] = _gen_star()
        sfx['hurt'] = _gen_hurt()
        sfx['punch'] = _gen_punch()
        sfx['1up'] = _gen_1up()
        sfx['wahoo'] = _gen_wahoo()
    except:
        pass

def play_sfx(name):
    if name in sfx:
        try: sfx[name].play()
        except: pass

# ============================================================================
#  GLOBALS
# ============================================================================
surfs: List[Surface] = []
objs: List[Obj] = []
cur_lvl = 0; cur_name = ""
ptcl = Particles()
ctrl = Controller()

# ============================================================================
#  GEOMETRY BUILDERS
# ============================================================================
def make_box(x, y, z, w, h, d, col, st=SURF_DEFAULT, wp=-1):
    hw, hh, hd = w/2, h/2, d/2; s = []
    tc = _cc((col[0]*1.12, col[1]*1.12, col[2]*1.12))
    dc = _cc((col[0]*0.78, col[1]*0.78, col[2]*0.78))
    fc = _cc((col[0]*0.88, col[1]*0.88, col[2]*0.88))
    bc = _cc((col[0]*0.82, col[1]*0.82, col[2]*0.82))
    s.append(Surface([Vec3f(x-hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z+hd)], Vec3f(0,1,0), st, tc, wp))
    s.append(Surface([Vec3f(x-hw,y-hh,z+hd), Vec3f(x+hw,y-hh,z+hd), Vec3f(x+hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z+hd)], Vec3f(0,0,1), st, fc, wp))
    s.append(Surface([Vec3f(x+hw,y-hh,z-hd), Vec3f(x-hw,y-hh,z-hd), Vec3f(x-hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z-hd)], Vec3f(0,0,-1), st, bc, wp))
    s.append(Surface([Vec3f(x-hw,y-hh,z-hd), Vec3f(x-hw,y-hh,z+hd), Vec3f(x-hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z-hd)], Vec3f(-1,0,0), st, dc, wp))
    s.append(Surface([Vec3f(x+hw,y-hh,z+hd), Vec3f(x+hw,y-hh,z-hd), Vec3f(x+hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z+hd)], Vec3f(1,0,0), st, dc, wp))
    return s

def make_quad(p1, p2, p3, p4, col, st=SURF_DEFAULT):
    ux, uy, uz = p2.x-p1.x, p2.y-p1.y, p2.z-p1.z
    vx, vy, vz = p3.x-p1.x, p3.y-p1.y, p3.z-p1.z
    nx = uy*vz - uz*vy; ny = uz*vx - ux*vz; nz = ux*vy - uy*vx
    m = math.sqrt(nx*nx + ny*ny + nz*nz)
    if m < 0.0001: m = 1
    return Surface([p1, p2, p3, p4], Vec3f(nx/m, ny/m, nz/m), st, col)

def make_ground(x, z, w, d, y, col, st=SURF_DEFAULT):
    hw, hd = w/2, d/2
    return make_quad(Vec3f(x-hw,y,z-hd), Vec3f(x+hw,y,z-hd), Vec3f(x+hw,y,z+hd), Vec3f(x-hw,y,z+hd), col, st)

def make_slope(x1, y1, z1, x2, y2, z2, w, col, st=SURF_DEFAULT):
    hw = w/2
    return make_quad(Vec3f(x1-hw,y1,z1), Vec3f(x1+hw,y1,z1), Vec3f(x2+hw,y2,z2), Vec3f(x2-hw,y2,z2), col, st)

def make_stairs(x, y, z, n, sw, sh, sd, dr, col):
    r = []
    for i in range(n):
        r.extend(make_box(x+dr[0]*i*sd, y+i*sh+sh/2, z+dr[1]*i*sd, sw, sh, sd, col))
    return r

# ============================================================================
#  SPAWNERS
# ============================================================================
def sp_coin(x, y, z, t=ObjType.COIN):
    cs = {ObjType.COIN:(255,215,0), ObjType.COIN_RED:(255,50,50), ObjType.COIN_BLUE:(50,100,255)}
    vs = {ObjType.COIN:1, ObjType.COIN_RED:2, ObjType.COIN_BLUE:5}
    o = Obj(t, Vec3f(x,y+30,z), radius=30, height=30, color=cs.get(t,(255,215,0)), irange=60)
    o.coins = vs.get(t,1); o.bob = random.uniform(0,6.28); o.home = Vec3f(x,y+30,z); return o

def sp_star(x, y, z, sid=0):
    o = Obj(ObjType.STAR, Vec3f(x,y+50,z), radius=40, height=40, color=(255,255,100), irange=80, star_id=sid)
    o.bob = random.uniform(0,6.28); o.home = Vec3f(x,y+50,z); return o

def sp_goomba(x, y, z):
    o = Obj(ObjType.GOOMBA, Vec3f(x,y,z), radius=40, height=50, color=(150,80,30), irange=60, dmg=1, spd=1.5)
    o.home = Vec3f(x,y,z); return o

def sp_bobomb(x, y, z):
    o = Obj(ObjType.BOBOMB, Vec3f(x,y,z), radius=35, height=45, color=(20,20,20), irange=60, spd=1.0)
    o.home = Vec3f(x,y,z); return o

def sp_bully(x, y, z):
    o = Obj(ObjType.BULLY, Vec3f(x,y,z), radius=50, height=60, color=(80,80,80), irange=70, dmg=0, hp=3, spd=2.0)
    o.home = Vec3f(x,y,z); return o

def sp_boo(x, y, z):
    o = Obj(ObjType.BOO, Vec3f(x,y+30,z), radius=50, height=60, color=(220,220,255), irange=70, dmg=1)
    o.home = Vec3f(x,y+30,z); return o

def sp_piranha(x, y, z):
    o = Obj(ObjType.PIRANHA, Vec3f(x,y,z), radius=40, height=80, color=(20,140,20), irange=70, dmg=2)
    o.home = Vec3f(x,y,z); return o

def sp_koopa(x, y, z):
    o = Obj(ObjType.KOOPA, Vec3f(x,y,z), radius=40, height=55, color=(50,180,50), irange=60, spd=1.8)
    o.home = Vec3f(x,y,z); return o

def sp_amp(x, y, z, r=200):
    o = Obj(ObjType.AMP, Vec3f(x,y,z), radius=30, height=30, color=(30,30,200), irange=50, dmg=1)
    o.home = Vec3f(x,y,z); o.scale = r; return o

def sp_thwomp(x, y, z):
    o = Obj(ObjType.THWOMP, Vec3f(x,y,z), radius=60, height=100, color=(130,130,150), irange=80, dmg=2)
    o.home = Vec3f(x,y,z); return o

def sp_chomp(x, y, z):
    o = Obj(ObjType.CHAIN_CHOMP, Vec3f(x,y,z), radius=60, height=80, color=(20,20,30), irange=90, dmg=3)
    o.home = Vec3f(x,y,z); return o

def sp_1up(x, y, z):
    o = Obj(ObjType.ONE_UP, Vec3f(x,y+30,z), radius=25, height=25, color=(0,200,0), irange=50)
    o.home = Vec3f(x,y+30,z); o.bob = random.uniform(0,6.28); return o

def sp_tree(x, y, z, h=200):
    return Obj(ObjType.TREE, Vec3f(x,y,z), radius=20, height=h, color=(80,50,20), irange=0)

def sp_pipe(x, y, z, tgt):
    o = Obj(ObjType.PIPE, Vec3f(x,y,z), radius=50, height=80, color=(0,180,0), irange=50)
    o.warp = tgt; return o

def sp_ring(x, y, z, r=200, n=8):
    return [sp_coin(x+r*sins(360/n*i), y, z+r*coss(360/n*i)) for i in range(n)]

def sp_line(x, y, z, dx, dy, dz, n=5):
    return [sp_coin(x+dx*i, y+dy*i, z+dz*i) for i in range(n)]

# ============================================================================
#  LEVEL DATA
# ============================================================================
LVL_GROUNDS=0; LVL_INSIDE=1; LVL_BOB=2; LVL_WF=3; LVL_JRB=4; LVL_CCM=5
LVL_BBH=6; LVL_HMC=7; LVL_LLL=8; LVL_SSL=9; LVL_DDD=10; LVL_SL=11
LVL_WDW=12; LVL_TTM=13; LVL_THI=14; LVL_TTC=15; LVL_RR=16
LVL_B1=17; LVL_B2=18; LVL_B3=19; LVL_SA=20; LVL_PSS=21
LVL_TOTWC=22; LVL_COTMC=23; LVL_VCUTM=24; LVL_WMOTR=25; LVL_COURT=26

@dataclass
class LvlInfo:
    name: str; sky: Tuple[int,int,int] = (135,206,235); nstars: int = 7
    start: Vec3f = field(default_factory=lambda: Vec3f(0,200,0))
    music_tempo: float = 1.0

LI = {
    LVL_GROUNDS: LvlInfo("Peach's Castle", (135,206,235), 0, Vec3f(0,200,600)),
    LVL_INSIDE:  LvlInfo("Castle Interior", (60,60,80), 0, Vec3f(0,50,0)),
    LVL_BOB:     LvlInfo("Bob-omb Battlefield", (135,206,235), 7, Vec3f(0,200,800)),
    LVL_WF:      LvlInfo("Whomp's Fortress", (150,200,240), 7, Vec3f(0,200,800)),
    LVL_JRB:     LvlInfo("Jolly Roger Bay", (80,140,200), 7, Vec3f(0,200,800)),
    LVL_CCM:     LvlInfo("Cool, Cool Mountain", (200,220,255), 7, Vec3f(0,1200,-1000)),
    LVL_BBH:     LvlInfo("Big Boo's Haunt", (30,20,50), 7, Vec3f(0,200,800)),
    LVL_HMC:     LvlInfo("Hazy Maze Cave", (50,40,30), 7, Vec3f(0,200,800)),
    LVL_LLL:     LvlInfo("Lethal Lava Land", (80,30,10), 7, Vec3f(0,200,0)),
    LVL_SSL:     LvlInfo("Shifting Sand Land", (230,200,140), 7, Vec3f(0,200,800)),
    LVL_DDD:     LvlInfo("Dire, Dire Docks", (20,40,100), 7, Vec3f(0,200,800)),
    LVL_SL:      LvlInfo("Snowman's Land", (180,200,240), 7, Vec3f(0,200,800)),
    LVL_WDW:     LvlInfo("Wet-Dry World", (170,190,220), 7, Vec3f(0,1000,800)),
    LVL_TTM:     LvlInfo("Tall, Tall Mountain", (130,190,230), 7, Vec3f(0,2000,0)),
    LVL_THI:     LvlInfo("Tiny-Huge Island", (135,206,235), 7, Vec3f(0,200,800)),
    LVL_TTC:     LvlInfo("Tick Tock Clock", (40,30,50), 7, Vec3f(0,200,0)),
    LVL_RR:      LvlInfo("Rainbow Ride", (100,80,180), 7, Vec3f(0,200,0)),
    LVL_B1:      LvlInfo("Bowser in the Dark World", (10,10,30), 1, Vec3f(0,200,800)),
    LVL_B2:      LvlInfo("Bowser in the Fire Sea", (40,10,10), 1, Vec3f(0,200,800)),
    LVL_B3:      LvlInfo("Bowser in the Sky", (50,40,80), 1, Vec3f(0,200,800)),
    LVL_SA:      LvlInfo("Secret Aquarium", (20,60,120), 1, Vec3f(0,200,0)),
    LVL_PSS:     LvlInfo("Princess's Secret Slide", (80,60,120), 2, Vec3f(0,1200,0)),
    LVL_TOTWC:   LvlInfo("Tower of the Wing Cap", (100,160,255), 1, Vec3f(0,200,0)),
    LVL_COTMC:   LvlInfo("Cavern of the Metal Cap", (30,60,30), 1, Vec3f(0,200,800)),
    LVL_VCUTM:   LvlInfo("Vanish Cap Under Moat", (40,40,80), 1, Vec3f(0,200,800)),
    LVL_WMOTR:   LvlInfo("Wing Mario Over Rainbow", (150,100,220), 1, Vec3f(0,200,0)),
    LVL_COURT:   LvlInfo("Castle Courtyard", (80,100,80), 0, Vec3f(0,50,400)),
}

CATS = [
    ("— Castle —", [LVL_GROUNDS, LVL_INSIDE, LVL_COURT]),
    ("— Courses 1-4 —", [LVL_BOB, LVL_WF, LVL_JRB, LVL_CCM]),
    ("— Courses 5-9 —", [LVL_BBH, LVL_HMC, LVL_LLL, LVL_SSL, LVL_DDD]),
    ("— Courses 10-15 —", [LVL_SL, LVL_WDW, LVL_TTM, LVL_THI, LVL_TTC, LVL_RR]),
    ("— Bowser —", [LVL_B1, LVL_B2, LVL_B3]),
    ("— Secrets —", [LVL_SA, LVL_PSS, LVL_TOTWC, LVL_COTMC, LVL_VCUTM, LVL_WMOTR]),
]

# ============================================================================
#  LEVEL BUILDERS — ALL 27 LEVELS
# ============================================================================
def load_level(lid):
    global surfs, objs, cur_lvl, cur_name
    surfs = []; objs = []; cur_lvl = lid
    info = LI.get(lid, LI[0]); cur_name = info.name
    _builders.get(lid, _b_grounds)()

def _b_grounds():
    surfs.append(make_ground(0, 0, 4000, 4000, 0, (34,180,34)))
    surfs.append(make_ground(0, -50, -400, 1200, 400, (40,80,200), SURF_WATER))
    surfs.extend(make_box(0, 10, -350, 250, 20, 500, (139,90,43)))
    surfs.extend(make_box(0, 250, -900, 900, 500, 300, (225,215,195)))
    surfs.extend(make_box(-550, 300, -850, 200, 600, 200, (210,200,180)))
    surfs.extend(make_box(550, 300, -850, 200, 600, 200, (210,200,180)))
    surfs.extend(make_box(0, 550, -900, 250, 400, 200, (230,220,200)))
    surfs.extend(make_box(-550, 630, -850, 150, 60, 150, (180,40,40)))
    surfs.extend(make_box(550, 630, -850, 150, 60, 150, (180,40,40)))
    surfs.extend(make_box(0, 780, -900, 180, 60, 150, (180,40,40)))
    surfs.extend(make_box(-1200, 80, -400, 400, 160, 400, (50,160,50)))
    surfs.extend(make_box(1200, 80, -400, 400, 160, 400, (50,160,50)))
    objs.extend(sp_ring(0, 20, 400, 200, 8))
    for tx, tz in [(-600,400),(600,400),(-900,-200),(900,-200)]:
        objs.append(sp_tree(tx, 0, tz))
    objs.append(sp_pipe(0, 10, -600, LVL_INSIDE))
    objs.append(sp_1up(-1200, 180, -400))

def _b_inside():
    surfs.append(make_ground(0, 0, 0, 2000, 3000, (180,160,130)))
    surfs.extend(make_box(0, 300, -1500, 2000, 600, 20, (160,140,110)))
    surfs.extend(make_box(-1000, 300, 0, 20, 600, 3000, (160,140,110)))
    surfs.extend(make_box(1000, 300, 0, 20, 600, 3000, (160,140,110)))
    surfs.extend(make_box(0, 300, 1500, 2000, 600, 20, (160,140,110)))
    surfs.extend(make_box(0, 5, 0, 200, 5, 2000, (180,30,30)))
    surfs.extend(make_stairs(0, 0, -1200, 8, 400, 40, 60, (0,-1), (170,150,120)))
    surfs.extend(make_box(0, 350, -1300, 800, 20, 200, (190,170,140)))
    pipes = [(-800,-400,LVL_BOB),(-800,-800,LVL_WF),(-800,0,LVL_JRB),(800,-400,LVL_CCM),
             (800,0,LVL_BBH),(0,1200,LVL_HMC),(-400,1200,LVL_LLL),(400,1200,LVL_SSL),
             (-600,1200,LVL_DDD),(-800,-1300,LVL_SL),(-400,-1300,LVL_WDW),(0,-1300,LVL_TTM),
             (400,-1300,LVL_THI),(800,-1300,LVL_TTC),(0,-1400,LVL_RR),
             (-200,-1400,LVL_B1),(200,-1400,LVL_B2),(0,-1500,LVL_B3),
             (600,-1200,LVL_PSS),(-600,-1400,LVL_SA),(0,1400,LVL_GROUNDS)]
    for px, pz, tgt in pipes:
        y = 0 if abs(pz) < 1250 else 360
        objs.append(sp_pipe(px, y, pz, tgt))
    objs.extend(sp_line(-500, 10, -200, 100, 0, 0, 6))

def _b_court():
    surfs.append(make_ground(0, 0, 0, 1200, 1200, (80,130,80)))
    surfs.extend(make_box(0, 150, -600, 1200, 300, 20, (120,120,120)))
    surfs.extend(make_box(0, 150, 600, 1200, 300, 20, (120,120,120)))
    surfs.extend(make_box(-600, 150, 0, 20, 300, 1200, (120,120,120)))
    surfs.extend(make_box(600, 150, 0, 20, 300, 1200, (120,120,120)))
    for bx, bz in [(-200,-200),(200,-200),(0,200),(-300,100),(300,100)]:
        objs.append(sp_boo(bx, 50, bz))
    objs.append(sp_star(0, 100, -400, 0))
    objs.append(sp_pipe(0, 0, 550, LVL_INSIDE))

def _b_bob():
    surfs.append(make_ground(0, 0, 0, 4000, 4000, (90,160,50)))
    for i in range(8):
        w = 1000 - i * 110
        surfs.extend(make_box(0, 50+i*120, -1200, w, 120, w, (139-i*5, 100-i*3, 50)))
    surfs.extend(make_box(0, 1050, -1200, 250, 20, 250, (160,120,60)))
    surfs.extend(make_box(0, 40, -400, 120, 10, 600, (160,120,80)))
    surfs.extend(make_box(-600, 0, 400, 400, 10, 400, (70,140,50)))
    surfs.extend(make_box(500, 20, 0, 200, 40, 800, (120,100,70)))
    surfs.extend(make_box(800, 600, -800, 300, 40, 300, (90,160,90)))
    objs.append(sp_goomba(-200, 0, 300)); objs.append(sp_goomba(200, 0, 300))
    objs.append(sp_goomba(-100, 0, 600)); objs.append(sp_bobomb(-400, 0, 600))
    objs.append(sp_chomp(-600, 0, 400)); objs.append(sp_koopa(500, 60, 200))
    king = sp_bobomb(0, 1070, -1200); king.type = ObjType.KING_BOB; king.hp = 3; king.radius = 80
    king.color = (40,40,40); king.scale = 2.0; king.irange = 100; objs.append(king)
    objs.append(sp_star(0, 1120, -1200, 0)); objs.append(sp_star(500, 80, -200, 1))
    objs.append(sp_star(800, 660, -800, 2)); objs.append(sp_star(-600, 50, 600, 5))
    objs.extend(sp_ring(0, 30, 200, 150, 8))
    for rx, rz in [(-300,-300),(300,-300),(-300,600),(300,600),(-700,0),(700,0),(0,-800),(0,800)]:
        objs.append(sp_coin(rx, 30, rz, ObjType.COIN_RED))
    objs.append(sp_1up(-1000, 30, 600))
    for tx, tz in [(-1000,600),(1000,600),(-800,-400),(800,-400)]:
        objs.append(sp_tree(tx, 0, tz))

def _b_wf():
    surfs.append(make_ground(0, 0, 0, 3000, 3000, (160,160,170)))
    surfs.extend(make_box(0, 150, -400, 1000, 300, 800, (185,185,190)))
    surfs.extend(make_box(0, 400, -400, 700, 200, 600, (175,175,180)))
    surfs.extend(make_box(0, 550, -400, 500, 20, 400, (195,195,200)))
    surfs.extend(make_stairs(-500, 0, -200, 6, 200, 50, 80, (0,-1), (180,180,185)))
    surfs.extend(make_box(600, 300, 0, 200, 20, 200, (160,160,180)))
    surfs.extend(make_box(800, 400, 200, 150, 20, 150, (160,160,180)))
    surfs.extend(make_box(600, 500, 400, 180, 20, 180, (160,160,180)))
    surfs.extend(make_box(-500, 200, -600, 250, 20, 250, (150,150,160)))
    surfs.extend(make_box(0, 650, -500, 150, 200, 150, (190,190,195)))
    objs.append(sp_thwomp(0, 350, -200)); objs.append(sp_piranha(-500, 220, -600))
    objs.append(sp_goomba(300, 0, 300)); objs.append(sp_goomba(-300, 0, 500))
    objs.append(sp_star(0, 770, -500, 0)); objs.append(sp_star(600, 540, 400, 1))
    objs.extend(sp_ring(0, 170, -400, 200, 8))
    for rx, rz in [(-400,300),(400,300),(-200,-800),(200,-800),(-600,-200),(600,-200),(0,600),(0,-600)]:
        objs.append(sp_coin(rx, 30, rz, ObjType.COIN_RED))

def _b_jrb():
    surfs.append(make_ground(0, -300, 0, 4000, 4000, (60,100,140), SURF_WATER))
    surfs.append(make_ground(0, 0, 800, 2000, 800, (180,170,130)))
    surfs.extend(make_box(-800, 100, 600, 400, 200, 400, (140,130,100)))
    surfs.extend(make_box(0, -250, -800, 600, 100, 400, (80,100,120)))
    surfs.extend(make_box(0, -100, -400, 400, 150, 150, (100,70,40)))
    surfs.extend(make_box(0, 0, -400, 300, 20, 120, (110,80,50)))
    objs.append(sp_goomba(-200, 0, 900)); objs.append(sp_koopa(0, 0, 1000))
    objs.append(sp_star(0, 50, -400, 0)); objs.append(sp_star(0, -230, -800, 1))
    objs.append(sp_star(-800, 220, 600, 3))
    objs.extend(sp_ring(0, -250, -600, 150, 8))

def _b_ccm():
    surfs.append(make_ground(0, 0, 0, 4000, 4000, (240,245,255)))
    surfs.append(make_slope(-1000, 1200, -1500, 1000, 0, 1500, 2000, (225,235,255), SURF_SLIP))
    surfs.extend(make_box(0, 1250, -1500, 500, 100, 500, (210,220,240)))
    surfs.extend(make_box(0, 1350, -1500, 300, 200, 300, (100,60,30)))
    surfs.extend(make_box(0, 50, 1200, 250, 150, 200, (90,55,25)))
    surfs.extend(make_box(500, 600, 0, 100, 10, 800, (200,220,255), SURF_SLIP))
    surfs.extend(make_box(-600, 200, 500, 250, 20, 250, (235,240,250)))
    surfs.extend(make_box(-600, 350, 500, 200, 200, 200, (255,255,255)))
    objs.append(sp_goomba(200, 1260, -1400)); objs.append(sp_goomba(0, 10, 600))
    objs.append(sp_star(0, 100, 1200, 0)); objs.append(sp_star(0, 1380, -1500, 1))
    objs.append(sp_star(-600, 540, 500, 2)); objs.append(sp_star(500, 650, 400, 3))
    objs.extend(sp_ring(0, 1270, -1500, 200, 8))
    for rx, rz in [(-300,-500),(300,-500),(-500,200),(500,200),(-200,800),(200,800),(-600,-200),(600,-200)]:
        objs.append(sp_coin(rx, 30, rz, ObjType.COIN_RED))

def _b_bbh():
    surfs.append(make_ground(0, 0, 0, 3000, 3000, (50,60,40)))
    surfs.extend(make_box(0, 300, -600, 1000, 600, 800, (80,70,90)))
    surfs.extend(make_box(0, 650, -600, 1100, 50, 900, (60,50,70)))
    surfs.extend(make_box(0, 50, -600, 800, 100, 600, (100,90,80)))
    surfs.extend(make_box(0, 300, -600, 800, 20, 600, (95,85,75)))
    surfs.extend(make_box(0, 450, -200, 500, 20, 200, (85,75,65)))
    surfs.extend(make_box(500, -80, -800, 300, 20, 300, (75,65,55)))
    for bx, bz in [(-200,200),(200,200),(-300,-300),(300,-300),(0,-400)]:
        objs.append(sp_boo(bx, 100, bz))
    bb = sp_boo(0, 150, -600); bb.type = ObjType.BIG_BOO; bb.hp = 3; bb.radius = 100; bb.scale = 2.0
    bb.color = (240,240,255); objs.append(bb)
    objs.append(sp_star(0, 500, -600, 0)); objs.append(sp_star(0, 350, -600, 1))
    objs.append(sp_star(0, 700, -600, 2)); objs.append(sp_star(500, -50, -800, 4))
    objs.extend(sp_ring(0, 60, -400, 150, 8))

def _b_hmc():
    surfs.append(make_ground(0, 0, 0, 3000, 4000, (80,70,55)))
    surfs.extend(make_box(0, 600, 0, 3000, 20, 4000, (60,50,40)))
    surfs.extend(make_box(0, 100, 0, 600, 200, 600, (100,90,75)))
    for wx, wz in [(-300,-200),(-300,-600),(0,-400),(300,-200),(300,-600)]:
        surfs.extend(make_box(wx, 100, wz, 20, 200, 200, (70,60,50)))
    surfs.append(make_ground(600, 800, -100, 800, 600, (40,60,120), SURF_WATER))
    surfs.extend(make_box(600, -80, 800, 200, 20, 200, (100,140,100)))
    surfs.extend(make_box(-800, 100, -400, 200, 400, 200, (85,75,60)))
    objs.append(sp_goomba(-200, 10, 300)); objs.append(sp_goomba(200, 10, 300))
    objs.append(sp_goomba(0, 10, -500))
    objs.append(sp_star(0, 200, 0, 0)); objs.append(sp_star(-800, 350, -400, 1))
    objs.append(sp_star(600, -50, 800, 2)); objs.append(sp_star(0, 10, -900, 3))
    objs.extend(sp_ring(0, 120, 0, 200, 8))

def _b_lll():
    surfs.append(make_ground(0, -50, 0, 4000, 4000, (200,40,0), SURF_LAVA))
    surfs.extend(make_box(0, 20, 0, 500, 40, 500, (80,80,80)))
    for i in range(6):
        w = 700 - i * 100
        surfs.extend(make_box(0, 50+i*100, -800, w, 100, w, (120-i*8, 50-i*3, 40-i*3)))
    surfs.extend(make_box(0, 700, -800, 200, 20, 200, (100,60,40)))
    for px, pz in [(-300,300),(-500,100),(-700,-100),(-500,-300)]:
        surfs.extend(make_box(px, 20, pz, 100, 20, 100, (90,90,90)))
    surfs.extend(make_box(600, 30, 600, 200, 20, 200, (100,100,100)))
    surfs.extend(make_box(-700, 20, -600, 400, 20, 400, (70,70,75)))
    objs.append(sp_bully(-700, 40, -600)); objs.append(sp_bully(-600, 40, -500))
    bb = sp_bully(-700, 40, -700); bb.hp = 5; bb.radius = 70; bb.scale = 1.5; objs.append(bb)
    objs.append(sp_star(0, 740, -800, 0)); objs.append(sp_star(-700, 60, -700, 1))
    objs.append(sp_star(600, 60, 600, 3)); objs.append(sp_star(600, 60, -500, 4))
    objs.extend(sp_ring(0, 40, 0, 180, 8))
    for rx, rz in [(-300,300),(-500,100),(-700,-100),(-500,-300),(400,-300),(600,-500),(600,600),(-700,-600)]:
        objs.append(sp_coin(rx, 50, rz, ObjType.COIN_RED))

def _b_ssl():
    surfs.append(make_ground(0, 0, 0, 4000, 4000, (220,190,130), SURF_SAND))
    for i in range(8):
        w = 1200 - i * 140
        surfs.extend(make_box(0, i*120, -600, w, 120, w, (200-i*5, 170-i*5, 100-i*3)))
    surfs.extend(make_box(0, 1020, -600, 150, 60, 150, (210,180,110)))
    surfs.append(make_ground(-800, 600, -30, 400, 400, (40,100,180), SURF_WATER))
    surfs.extend(make_box(-800, 0, 600, 500, 10, 500, (60,140,60)))
    surfs.append(make_ground(800, -600, -100, 600, 600, (200,180,100), SURF_DEATH))
    surfs.extend(make_box(-600, 300, -200, 200, 20, 200, (180,160,100)))
    objs.append(sp_goomba(-200, 10, 400)); objs.append(sp_goomba(200, 10, 400))
    objs.append(sp_star(0, 1060, -600, 0)); objs.append(sp_star(-800, 20, 600, 1))
    objs.append(sp_star(-600, 340, -200, 2)); objs.append(sp_star(0, 500, -600, 3))
    objs.extend(sp_ring(0, 30, 0, 300, 8))

def _b_ddd():
    surfs.append(make_ground(0, -400, 0, 4000, 4000, (30,50,100), SURF_WATER))
    surfs.append(make_ground(0, 0, 800, 2000, 800, (120,110,100)))
    surfs.extend(make_box(0, -350, -400, 300, 100, 800, (40,60,110)))
    surfs.extend(make_box(-500, -300, -600, 400, 200, 400, (80,80,90)))
    surfs.extend(make_box(500, -200, -400, 400, 100, 300, (90,90,100)))
    surfs.extend(make_box(500, -150, -400, 300, 80, 150, (60,60,70)))
    surfs.extend(make_box(0, -350, -1000, 400, 20, 400, (50,70,120)))
    objs.append(sp_star(500, -120, -400, 0)); objs.append(sp_star(0, -330, -1000, 1))
    objs.append(sp_star(-500, -200, -600, 2)); objs.append(sp_star(0, 50, 800, 4))
    objs.extend(sp_ring(0, -350, -600, 150, 8))

def _b_sl():
    surfs.append(make_ground(0, 0, 0, 4000, 4000, (230,240,255)))
    for i in range(6):
        w = 800 - i * 120
        surfs.extend(make_box(0, i*150, -800, w, 150, w, (245,248,255)))
    surfs.extend(make_box(0, 1000, -800, 300, 300, 300, (255,255,255)))
    surfs.extend(make_box(-600, 50, 400, 400, 100, 400, (180,210,255), SURF_ICE))
    surfs.extend(make_box(600, 50, 400, 250, 150, 250, (220,230,250)))
    surfs.append(make_ground(0, 600, -10, 500, 500, (160,200,255), SURF_ICE))
    surfs.extend(make_box(0, 50, -200, 100, 10, 400, (200,200,210)))
    surfs.extend(make_box(-600, 80, -400, 300, 20, 300, (210,220,240)))
    objs.append(sp_bully(-600, 100, -400)); objs.append(sp_goomba(300, 10, 300))
    objs.append(sp_star(0, 1150, -800, 0)); objs.append(sp_star(-600, 120, -400, 1))
    objs.append(sp_star(-600, 170, 400, 2)); objs.append(sp_star(600, 100, 400, 3))
    objs.extend(sp_ring(0, 30, 200, 200, 8))

def _b_wdw():
    surfs.append(make_ground(0, -200, 0, 3000, 3000, (60,100,180), SURF_WATER))
    surfs.extend(make_box(-400, 200, -400, 300, 400, 300, (180,180,190)))
    surfs.extend(make_box(400, 300, -400, 250, 600, 250, (170,170,185)))
    surfs.extend(make_box(-400, 150, 400, 350, 300, 350, (175,175,185)))
    surfs.extend(make_box(400, 100, 400, 200, 200, 200, (185,185,195)))
    surfs.extend(make_box(0, 500, 0, 100, 20, 100, (200,200,255)))
    surfs.extend(make_box(0, 100, 0, 1500, 20, 100, (160,160,170)))
    surfs.extend(make_box(0, 100, 0, 100, 20, 1500, (160,160,170)))
    surfs.extend(make_box(0, -180, -1000, 1000, 20, 500, (140,140,150)))
    objs.append(sp_goomba(-200, 210, -300)); objs.append(sp_amp(0, 300, -400, 150))
    objs.append(sp_star(-400, 420, -400, 0)); objs.append(sp_star(400, 620, -400, 1))
    objs.append(sp_star(0, 540, 0, 2)); objs.append(sp_star(0, -160, -1000, 3))
    objs.extend(sp_ring(0, 120, 0, 200, 8))

def _b_ttm():
    surfs.append(make_ground(0, 0, 0, 3000, 3000, (100,140,80)))
    for i in range(10):
        w = 1500 - i * 130
        surfs.extend(make_box(0, i*200, 0, w, 200, w, (120+i*3, 100+i*3, 70+i*2)))
    surfs.extend(make_box(0, 2050, 0, 300, 50, 300, (140,120,90)))
    for mx, my, mz, mr in [(-500,800,400,100),(-700,600,200,80),(-400,400,600,120)]:
        surfs.extend(make_box(mx, my, mz, mr*2, 20, mr*2, (200,60,60)))
        surfs.extend(make_box(mx, my-60, mz, 30, 80, 30, (180,170,140)))
    surfs.extend(make_box(400, 800, -300, 60, 1000, 60, (80,140,220)))
    objs.append(sp_goomba(-200, 10, 400)); objs.append(sp_goomba(300, 600, 200))
    objs.append(sp_koopa(0, 2060, 0))
    objs.append(sp_star(0, 2100, 0, 0)); objs.append(sp_star(-500, 840, 400, 2))
    objs.append(sp_star(-400, 440, 600, 3)); objs.append(sp_star(400, 1350, -300, 4))
    objs.extend(sp_ring(0, 2070, 0, 120, 8))

def _b_thi():
    surfs.append(make_ground(0, 0, 0, 4000, 4000, (90,160,70)))
    surfs.append(make_ground(0, -50, 0, 800, 800, (40,80,180), SURF_WATER))
    surfs.extend(make_box(-600, 150, -600, 500, 300, 500, (100,150,70)))
    surfs.extend(make_box(600, 100, -600, 400, 200, 400, (105,155,75)))
    surfs.extend(make_box(0, 10, 800, 800, 20, 400, (200,180,140)))
    surfs.extend(make_box(-800, 30, 0, 100, 60, 100, (0,180,0)))
    surfs.extend(make_box(800, 30, 0, 100, 60, 100, (0,180,0)))
    objs.append(sp_piranha(-300, 0, 300)); objs.append(sp_piranha(300, 0, 300))
    g = sp_goomba(200, 10, 600); g.radius = 70; g.scale = 2.0; objs.append(g)
    objs.append(sp_koopa(600, 30, 800))
    objs.append(sp_star(-600, 320, -600, 0)); objs.append(sp_star(600, 220, -600, 1))
    objs.append(sp_star(0, 100, 800, 2)); objs.append(sp_star(-800, 60, 0, 4))
    objs.extend(sp_ring(0, 30, 400, 200, 8))

def _b_ttc():
    plats = [(0,0,0,400),(-200,200,100,200),(200,400,-100,200),(0,600,200,250),
             (-150,800,-200,200),(150,1000,100,200),(0,1200,-100,300),(-200,1400,200,200),
             (200,1600,0,200),(0,1800,-200,250),(-100,2000,100,200),(100,2200,-100,200),(0,2400,0,300)]
    for px, py, pz, pw in plats:
        c = _cc((160+py//20, 140+py//30, 100+py//25))
        surfs.extend(make_box(px, py, pz, pw, 20, pw if pw < 300 else 200, c))
    surfs.extend(make_box(0, 500, 0, 300, 10, 20, (120,120,130)))
    surfs.extend(make_box(0, 1100, 0, 20, 10, 250, (120,120,130)))
    objs.append(sp_amp(0, 400, 0, 200)); objs.append(sp_amp(0, 1000, 0, 150))
    objs.append(sp_goomba(-200, 220, 100)); objs.append(sp_thwomp(0, 1400, -100))
    objs.append(sp_star(0, 2450, 0, 0)); objs.append(sp_star(-100, 2040, 100, 1))
    objs.append(sp_star(150, 1640, 0, 2)); objs.append(sp_star(-150, 840, -200, 3))
    for i, (px, py, pz, _) in enumerate(plats):
        if i % 2 == 0: objs.append(sp_coin(px, py+40, pz))
    for rx, ry, rz in [(-200,240,100),(200,440,-100),(0,640,200),(-150,840,-200),
                       (150,1040,100),(0,1240,-100),(-200,1440,200),(200,1640,0)]:
        objs.append(sp_coin(rx, ry, rz, ObjType.COIN_RED))

def _b_rr():
    surfs.extend(make_box(0, 0, 0, 400, 20, 400, (200,180,220)))
    rc = [(255,80,80),(255,165,80),(255,255,80),(80,255,80),(80,80,255),(180,80,255)]
    for i in range(18):
        a = i * 30; d = 300 + i * 100; px = d*sins(a); pz = d*coss(a); py = 100 + i * 80
        surfs.extend(make_box(px, py, pz, 150, 20, 150, rc[i%6]))
    surfs.extend(make_box(800, 1200, -800, 400, 100, 200, (120,80,40)))
    surfs.extend(make_box(-600, 1000, -400, 300, 200, 300, (200,180,160)))
    surfs.extend(make_box(-600, 1130, -400, 320, 60, 320, (180,60,40)))
    for j in range(5):
        surfs.extend(make_box(-300+j*150, 600+j*50, 400, 120, 20, 120, _cc((180+j*10, 160+j*10, 200))))
    objs.append(sp_goomba(0, 30, 200)); objs.append(sp_amp(400, 500, 0, 180))
    objs.append(sp_star(800, 1360, -800, 0)); objs.append(sp_star(-600, 1120, -400, 1))
    objs.append(sp_star(0, 1600, 0, 2)); objs.append(sp_star(-300, 850, 400, 3))
    objs.extend(sp_ring(0, 40, 0, 150, 8))
    for i in range(8):
        a = i * 45; objs.append(sp_coin(300*sins(a), 800+i*30, 300*coss(a), ObjType.COIN_RED))

def _b_b1():
    surfs.append(make_ground(0, -200, 0, 4000, 4000, (180,30,0), SURF_LAVA))
    path = [(0,0,0),(300,50,300),(600,100,200),(800,150,500),(600,200,800),
            (300,250,900),(0,300,700),(-300,350,500),(-500,400,300),(-300,450,0),
            (0,500,-300),(300,550,-500),(0,600,-700)]
    for px, py, pz in path:
        surfs.extend(make_box(px, py, pz, 200, 20, 200, (70+py//10, 50+py//15, 90+py//10)))
    surfs.extend(make_box(0, 650, -1000, 600, 20, 600, (80,40,40)))
    objs.append(sp_goomba(300, 70, 300)); objs.append(sp_amp(0, 300, 700, 150))
    bw = Obj(ObjType.BOWSER, Vec3f(0,680,-1000), radius=100, height=150, color=(20,120,20), irange=120, dmg=3, hp=1)
    bw.home = Vec3f(0,680,-1000); bw.spd = 2.0; objs.append(bw)
    objs.append(sp_star(0, 730, -1000, 0))
    for px, py, pz in path[::2]: objs.append(sp_coin(px, py+40, pz))

def _b_b2():
    surfs.append(make_ground(0, -200, 0, 4000, 4000, (200,50,0), SURF_LAVA))
    for i in range(15):
        a = i * 25; d = 200+i*100; px = d*sins(a); pz = d*coss(a); py = i * 60
        surfs.extend(make_box(px, py, pz, 180, 20, 180, (100,60,40)))
    surfs.extend(make_box(0, 500, -500, 250, 20, 250, (110,70,50)))
    surfs.extend(make_box(0, 900, -1200, 600, 20, 600, (90,50,40)))
    objs.append(sp_goomba(100, 80, 100)); objs.append(sp_bully(0, 520, -500))
    bw = Obj(ObjType.BOWSER, Vec3f(0,930,-1200), radius=100, height=150, color=(20,130,20), irange=120, dmg=3, hp=1)
    bw.home = Vec3f(0,930,-1200); bw.spd = 2.0; objs.append(bw)
    objs.append(sp_star(0, 980, -1200, 0)); objs.extend(sp_ring(0, 920, -1200, 200, 8))

def _b_b3():
    surfs.append(make_ground(0, -500, 0, 100, 100, (0,0,0), SURF_DEATH))
    path = [(0,0,0),(300,100,200),(500,200,500),(300,300,800),(0,400,1000),
            (-300,500,800),(-500,600,500),(-300,700,200),(0,800,0),(300,900,-300),
            (500,1000,-600),(300,1100,-900),(0,1200,-1100),(-200,1300,-1300),(0,1400,-1500)]
    for px, py, pz in path:
        surfs.extend(make_box(px, py, pz, 200, 20, 200, _cc((80+py//20, 60+py//25, 100+py//15))))
    surfs.extend(make_box(0, 1500, -1800, 800, 30, 800, (100,80,120)))
    objs.append(sp_goomba(300, 120, 200)); objs.append(sp_goomba(-300, 520, 800))
    objs.append(sp_amp(0, 600, 500, 200)); objs.append(sp_thwomp(0, 1000, -600))
    bw = Obj(ObjType.BOWSER, Vec3f(0,1540,-1800), radius=120, height=180, color=(30,150,30), irange=150, dmg=3, hp=3)
    bw.home = Vec3f(0,1540,-1800); bw.spd = 2.5; bw.scale = 1.5; objs.append(bw)
    objs.append(sp_star(0, 1600, -1800, 0))
    for px, py, pz in path[::2]: objs.append(sp_coin(px, py+40, pz))

def _b_sa():
    surfs.append(make_ground(0, -400, 0, 1500, 1500, (30,60,130), SURF_WATER))
    surfs.extend(make_box(0, 0, 0, 600, 20, 600, (100,130,160)))
    objs.append(sp_star(0, 50, 0, 0))
    for _ in range(20):
        objs.append(sp_coin(random.randint(-500,500), random.randint(-300,-50), random.randint(-500,500)))

def _b_pss():
    pts = [(0,1200,0),(200,1000,200),(0,800,400),(-200,600,200),(0,400,0),(200,200,-200),(0,0,-400)]
    for i in range(len(pts)-1):
        p1, p2 = pts[i], pts[i+1]
        surfs.append(make_slope(p1[0],p1[1],p1[2], p2[0],p2[1],p2[2], 200, (140,100,180), SURF_SLIP))
    surfs.extend(make_box(0, 1220, 0, 300, 40, 300, (150,110,190)))
    surfs.extend(make_box(0, 10, -400, 300, 20, 300, (160,120,200)))
    objs.append(sp_star(0, 50, -400, 0)); objs.append(sp_star(0, 50, -300, 1))
    for p in pts: objs.append(sp_coin(p[0], p[1]+30, p[2]))

def _b_totwc():
    surfs.extend(make_box(0, 0, 0, 200, 20, 200, (200,180,220)))
    for i in range(8):
        a = i * 45; surfs.extend(make_box(500*sins(a), -100, 500*coss(a), 150, 20, 150, (180,200,255)))
    for i in range(8):
        a = i * 45; objs.append(sp_coin(400*sins(a), 50, 400*coss(a), ObjType.COIN_RED))
    objs.append(sp_star(0, 50, 0, 0)); objs.extend(sp_ring(0, 30, 0, 200, 8))

def _b_cotmc():
    surfs.append(make_ground(0, 0, 0, 2000, 3000, (50,70,50)))
    surfs.append(make_ground(0, -30, 0, 200, 3000, (40,80,150), SURF_WATER))
    for i in range(8):
        surfs.extend(make_box(-300, 30, -1000+i*300, 200, 30, 100, (60,80,60)))
    surfs.extend(make_box(0, 50, -1200, 100, 50, 100, (0,200,0)))
    objs.append(sp_star(0, 80, -1200, 0)); objs.extend(sp_line(-300, 50, -800, 0, 0, 150, 6))

def _b_vcutm():
    surfs.append(make_slope(0, 400, -500, 0, 0, 500, 300, (60,60,100), SURF_SLIP))
    surfs.extend(make_box(0, 420, -500, 400, 40, 300, (70,70,110)))
    surfs.extend(make_box(0, 10, 500, 400, 20, 300, (65,65,105)))
    for i in range(6):
        surfs.extend(make_box(-200+i*80, 200-i*30, 0, 100, 20, 100, (80,80,120)))
    surfs.extend(make_box(0, 50, 800, 100, 50, 100, (100,100,200)))
    objs.append(sp_star(0, 80, 800, 0)); objs.extend(sp_ring(0, 220, -200, 150, 8))

def _b_wmotr():
    surfs.extend(make_box(0, 0, 0, 300, 20, 300, (180,160,220)))
    rc = [(255,80,80),(255,165,80),(255,255,80),(80,255,80),(80,80,255),(180,80,255)]
    for i in range(12):
        a = i * 30; d = 300+i*80; surfs.extend(make_box(d*sins(a), 50+i*60, d*coss(a), 120, 15, 120, rc[i%6]))
    for cx, cy, cz in [(500,400,0),(-400,500,-300),(0,600,-600)]:
        surfs.extend(make_box(cx, cy, cz, 200, 30, 200, (240,240,255)))
    objs.append(sp_star(0, 650, -600, 0))
    for i in range(8):
        a = i * 45; objs.append(sp_coin(350*sins(a), 200+i*30, 350*coss(a), ObjType.COIN_RED))
    objs.extend(sp_ring(0, 40, 0, 120, 8))

_builders = {
    LVL_GROUNDS:_b_grounds, LVL_INSIDE:_b_inside, LVL_COURT:_b_court,
    LVL_BOB:_b_bob, LVL_WF:_b_wf, LVL_JRB:_b_jrb, LVL_CCM:_b_ccm,
    LVL_BBH:_b_bbh, LVL_HMC:_b_hmc, LVL_LLL:_b_lll, LVL_SSL:_b_ssl,
    LVL_DDD:_b_ddd, LVL_SL:_b_sl, LVL_WDW:_b_wdw, LVL_TTM:_b_ttm,
    LVL_THI:_b_thi, LVL_TTC:_b_ttc, LVL_RR:_b_rr,
    LVL_B1:_b_b1, LVL_B2:_b_b2, LVL_B3:_b_b3,
    LVL_SA:_b_sa, LVL_PSS:_b_pss, LVL_TOTWC:_b_totwc,
    LVL_COTMC:_b_cotmc, LVL_VCUTM:_b_vcutm, LVL_WMOTR:_b_wmotr,
}

# ============================================================================
#  COLLISION
# ============================================================================
def find_floor(x, y, z):
    h = -11000.0; fl = None
    for s in surfs:
        mnx = min(v.x for v in s.verts) - 10; mxx = max(v.x for v in s.verts) + 10
        mnz = min(v.z for v in s.verts) - 10; mxz = max(v.z for v in s.verts) + 10
        if x < mnx or x > mxx or z < mnz or z > mxz: continue
        ny = s.normal.y
        if abs(ny) < 0.01: continue
        p1 = s.verts[0]; nx, nz = s.normal.x, s.normal.z
        d = -(x * nx + z * nz - (nx * p1.x + ny * p1.y + nz * p1.z))
        sy = d / ny
        if h < sy <= y + 150: h = sy; fl = s
    return h, fl

def find_wall(x, y, z, dx, dz):
    tx, tz = x + dx * 2, z + dz * 2
    for s in surfs:
        ny = s.normal.y
        if abs(ny) > 0.7: continue
        mny = min(v.y for v in s.verts) - 10; mxy = max(v.y for v in s.verts) + 10
        if y < mny or y > mxy: continue
        p1 = s.verts[0]; nx, nz = s.normal.x, s.normal.z
        d1 = (x - p1.x) * nx + (z - p1.z) * nz
        d2 = (tx - p1.x) * nx + (tz - p1.z) * nz
        if d1 > 0 and d2 <= 0: return s
    return None

# ============================================================================
#  PHYSICS STEPS
# ============================================================================
def update_air(m):
    m.fvel *= AIR_DRAG
    m.vel.x = m.fvel * sins(m.face.y); m.vel.z = m.fvel * coss(m.face.y)
    m.vel.y += GRAVITY
    if m.vel.y < MAX_FALL: m.vel.y = MAX_FALL

def set_fvel(m, s):
    m.fvel = s; m.vel.x = s * sins(m.face.y); m.vel.z = s * coss(m.face.y)

def ground_step(m):
    m.pos.x += m.vel.x; m.pos.z += m.vel.z
    fy, fl = find_floor(m.pos.x, m.pos.y + 100, m.pos.z)
    m.floor = fl; m.floor_y = fy
    if m.pos.y > fy + 10: return 'air'
    m.pos.y = fy; return 'ground'

def air_step(m):
    qx, qy, qz = m.vel.x/4, m.vel.y/4, m.vel.z/4
    for _ in range(4):
        m.pos.x += qx; m.pos.y += qy; m.pos.z += qz
        fy, fl = find_floor(m.pos.x, m.pos.y, m.pos.z)
        m.floor = fl; m.floor_y = fy
        if m.pos.y <= fy:
            m.pos.y = fy
            # Landing squish
            m.squish = 0.6; m.squish_vel = 0.15
            return 'land'
        w = find_wall(m.pos.x, m.pos.y+50, m.pos.z, sins(m.face.y), coss(m.face.y))
        if w: m.wall = w; m.vel.x = 0; m.vel.z = 0; m.fvel = 0; return 'wall'
    return 'air'

# ============================================================================
#  ACTIONS — Faithful to SM64 decomp
# ============================================================================
def a_idle(m, c):
    m.fvel = 0; m.vel.x = m.vel.z = 0
    if c.pressed & IN_A: m.jcount = 0; play_sfx('jump'); return m.set_act(ACT_JUMP)
    if c.pressed & IN_Z: return m.set_act(ACT_CROUCH_IDLE)
    if c.pressed & IN_B: play_sfx('punch'); return m.set_act(ACT_PUNCHING)
    if c.stick_mag > 0: return m.set_act(ACT_WALKING)
    ground_step(m)

def a_walk(m, c):
    m.bob_phase += m.fvel * 0.15
    if c.pressed & IN_A:
        if m.fvel > 10 and c.down & IN_Z_D: play_sfx('jump'); return m.set_act(ACT_LONG_JUMP)
        m.jtimer = 5; m.jcount += 1
        if m.jcount >= 3 and m.fvel > 15: play_sfx('wahoo'); return m.set_act(ACT_TRIPLE_JUMP)
        elif m.jcount >= 2: play_sfx('jump'); return m.set_act(ACT_DOUBLE_JUMP)
        play_sfx('jump'); return m.set_act(ACT_JUMP)
    if c.pressed & IN_B:
        if m.fvel > 8: play_sfx('punch'); return m.set_act(ACT_SLIDE_KICK)
        play_sfx('punch'); return m.set_act(ACT_PUNCHING)
    if c.stick_mag == 0: return m.set_act(ACT_DECELERATING)
    m.face.y = approach_angle(m.face.y, m.iyaw, 11.25)
    tgt = c.stick_mag * MAX_WALK
    m.fvel = min(m.fvel + 1.5, tgt) if m.fvel < tgt else max(m.fvel - 1.0, tgt)
    set_fvel(m, m.fvel)
    if ground_step(m) == 'air': m.set_act(ACT_FREEFALL)
    if m.jtimer > 0: m.jtimer -= 1
    else: m.jcount = 0

def a_decel(m, c):
    if c.pressed & IN_A:
        if m.fvel > 8: play_sfx('jump'); return m.set_act(ACT_SIDE_FLIP)
        play_sfx('jump'); return m.set_act(ACT_JUMP)
    if c.pressed & IN_B: play_sfx('punch'); return m.set_act(ACT_PUNCHING)
    if c.stick_mag > 0: return m.set_act(ACT_WALKING)
    m.fvel = approach_f32(m.fvel, 0, 2.0); set_fvel(m, m.fvel)
    if abs(m.fvel) < 0.5: m.set_act(ACT_IDLE)
    ground_step(m)

def a_crouch(m, c):
    m.fvel = 0; m.vel.x = m.vel.z = 0
    if not (c.down & IN_Z_D): return m.set_act(ACT_IDLE)
    if c.pressed & IN_A: play_sfx('wahoo'); return m.set_act(ACT_BACKFLIP)
    ground_step(m)

def a_punch(m, c):
    m.atimer += 1
    if m.atimer > 8:
        if c.pressed & IN_B:
            if m.punch_state == 0: m.punch_state = 1; play_sfx('punch'); return m.set_act(ACT_PUNCH2)
            elif m.punch_state == 1: m.punch_state = 2; play_sfx('punch'); return m.set_act(ACT_KICK)
        if m.atimer > 20: m.punch_state = 0; m.set_act(ACT_IDLE)
    if m.atimer < 5: m.fvel = 8; set_fvel(m, m.fvel)
    else: m.fvel = approach_f32(m.fvel, 0, 2); set_fvel(m, m.fvel)
    ground_step(m)

def a_punch2(m, c):
    m.atimer += 1
    if m.atimer > 8:
        if c.pressed & IN_B: m.punch_state = 2; play_sfx('punch'); return m.set_act(ACT_KICK)
        if m.atimer > 20: m.punch_state = 0; m.set_act(ACT_IDLE)
    if m.atimer < 5: m.fvel = 10; set_fvel(m, m.fvel)
    else: m.fvel = approach_f32(m.fvel, 0, 2); set_fvel(m, m.fvel)
    ground_step(m)

def a_kick(m, c):
    m.atimer += 1
    if m.atimer > 25: m.punch_state = 0; m.set_act(ACT_IDLE)
    if m.atimer < 8: m.fvel = 15; set_fvel(m, m.fvel)
    else: m.fvel = approach_f32(m.fvel, 0, 1.5); set_fvel(m, m.fvel)
    ground_step(m)

def a_jump(m, c):
    if m.atimer == 0: m.vel.y = JUMP_VEL + abs(m.fvel) * 0.25; m.peak_y = m.pos.y
    if c.pressed & IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed & IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    elif r == 'wall': m.wktimer = 5; m.set_act(ACT_FREEFALL)
    m.atimer += 1

def a_dbl(m, c):
    if m.atimer == 0: m.vel.y = DBL_JUMP_VEL + abs(m.fvel) * 0.2; m.peak_y = m.pos.y
    if c.pressed & IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed & IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    elif r == 'wall': m.wktimer = 5; m.set_act(ACT_FREEFALL)
    m.atimer += 1

def a_triple(m, c):
    if m.atimer == 0: m.vel.y = TRIPLE_VEL; m.peak_y = m.pos.y
    if c.pressed & IN_Z: return m.set_act(ACT_GROUND_POUND)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    m.atimer += 1

def a_backflip(m, c):
    if m.atimer == 0: m.vel.y = BACKFLIP_VEL; m.fvel = -10.0; set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.fvel = 0; m.set_act(ACT_IDLE)
    m.atimer += 1

def a_sideflip(m, c):
    if m.atimer == 0: m.vel.y = SIDEFLIP_VEL; m.face.y = (m.face.y + 180) % 360; m.fvel = 8.0; set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_IDLE)
    m.atimer += 1

def a_longjump(m, c):
    if m.atimer == 0: m.vel.y = LONGJUMP_VEL; m.fvel = min(m.fvel * 1.5, 48.0); set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.fvel = 0; m.set_act(ACT_IDLE)
    m.atimer += 1

def a_freefall(m, c):
    if c.pressed & IN_A and m.wktimer > 0:
        m.face.y = (m.face.y + 180) % 360; m.fvel = 24.0; set_fvel(m, m.fvel)
        play_sfx('jump'); return m.set_act(ACT_WALL_KICK)
    if c.pressed & IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed & IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r = air_step(m)
    if r == 'land':
        play_sfx('stomp')
        m.set_act(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    elif r == 'wall': m.wktimer = 5
    if m.wktimer > 0: m.wktimer -= 1
    m.atimer += 1

def a_wallkick(m, c):
    if m.atimer == 0: m.vel.y = WALL_KICK_VEL
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    m.atimer += 1

def a_dive(m, c):
    if m.atimer == 0: m.vel.y = DIVE_VEL; m.fvel = max(m.fvel, 32.0); set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_BELLY_SLIDE)
    m.atimer += 1

def a_belly(m, c):
    if c.pressed & IN_A: play_sfx('jump'); return m.set_act(ACT_JUMP)
    m.fvel = approach_f32(m.fvel, 0, 1.0); set_fvel(m, m.fvel)
    if abs(m.fvel) < 1.0: m.set_act(ACT_IDLE)
    ground_step(m)

def a_slide_kick(m, c):
    if m.atimer == 0: m.vel.y = 10.0; m.fvel = max(m.fvel, 28.0); set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_SLIDE_KICK_SL)
    m.atimer += 1

def a_slide_kick_slide(m, c):
    if c.pressed & IN_A: play_sfx('jump'); return m.set_act(ACT_JUMP)
    m.fvel = approach_f32(m.fvel, 0, 0.8); set_fvel(m, m.fvel)
    if abs(m.fvel) < 1.0: m.set_act(ACT_IDLE)
    ground_step(m)

def a_gp(m, c):
    if m.astate == 0:
        m.fvel = 0; m.vel.x = m.vel.z = 0; m.vel.y = 0; m.atimer += 1
        if m.atimer > 10: m.astate = 1; m.vel.y = GP_FALL_VEL
    else:
        r = air_step(m)
        if r == 'land':
            play_sfx('stomp')
            ptcl.emit_smoke(m.pos, 6)
            m.set_act(ACT_GP_LAND)

def a_gpl(m, c):
    m.atimer += 1
    if m.atimer > 5:
        if c.pressed & IN_A: play_sfx('jump'); m.set_act(ACT_JUMP)
        elif c.stick_mag > 0: m.set_act(ACT_WALKING)
        elif m.atimer > 15: m.set_act(ACT_IDLE)

def a_knock(m, c):
    if m.atimer == 0: m.vel.y = KNOCKBACK_VEL; m.fvel = -20.0; set_fvel(m, m.fvel)
    update_air(m); r = air_step(m)
    if r == 'land': m.fvel = 0; m.set_act(ACT_IDLE)
    m.atimer += 1

def a_lava(m, c):
    if m.atimer == 0: m.vel.y = LAVA_BOOST_VEL; m.fvel = 0; m.vel.x = m.vel.z = 0; m.take_dmg(0x100)
    update_air(m); r = air_step(m)
    if r == 'land': m.set_act(ACT_IDLE)
    m.atimer += 1

def a_star(m, c):
    m.fvel = 0; m.vel.x = m.vel.y = m.vel.z = 0; m.atimer += 1
    if m.atimer > 90: m.set_act(ACT_IDLE)

def a_death(m, c):
    m.fvel = 0; m.vel.x = m.vel.z = 0; m.vel.y = max(m.vel.y + GRAVITY, MAX_FALL); m.pos.y += m.vel.y

ACT_MAP = {
    ACT_IDLE: a_idle, ACT_WALKING: a_walk, ACT_DECELERATING: a_decel,
    ACT_CROUCH_IDLE: a_crouch,
    ACT_PUNCHING: a_punch, ACT_PUNCH2: a_punch2, ACT_KICK: a_kick,
    ACT_JUMP: a_jump, ACT_DOUBLE_JUMP: a_dbl, ACT_TRIPLE_JUMP: a_triple,
    ACT_BACKFLIP: a_backflip, ACT_SIDE_FLIP: a_sideflip, ACT_LONG_JUMP: a_longjump,
    ACT_WALL_KICK: a_wallkick, ACT_FREEFALL: a_freefall,
    ACT_DIVE: a_dive, ACT_BELLY_SLIDE: a_belly,
    ACT_SLIDE_KICK: a_slide_kick, ACT_SLIDE_KICK_SL: a_slide_kick_slide,
    ACT_GROUND_POUND: a_gp, ACT_GP_LAND: a_gpl,
    ACT_KNOCKBACK: a_knock, ACT_LAVA_BOOST: a_lava,
    ACT_STAR_DANCE: a_star, ACT_DEATH: a_death,
}

# ============================================================================
#  OBJECT AI
# ============================================================================
def update_objs(mario, frame):
    for o in objs:
        if not o.active: continue
        if o.type in (ObjType.COIN, ObjType.COIN_RED, ObjType.COIN_BLUE):
            o.pos.y = o.home.y + 30 + math.sin(frame * 0.08 + o.bob) * 10
            o.angle = (o.angle + 6) % 360
        elif o.type == ObjType.STAR:
            o.pos.y = o.home.y + 50 + math.sin(frame * 0.06 + o.bob) * 15
            o.angle = (o.angle + 3) % 360
        elif o.type == ObjType.ONE_UP:
            o.pos.y = o.home.y + 30 + math.sin(frame * 0.07 + o.bob) * 8
        elif o.type in (ObjType.GOOMBA, ObjType.BOBOMB, ObjType.KOOPA):
            dx = mario.pos.x - o.pos.x; dz = mario.pos.z - o.pos.z
            d = math.sqrt(dx*dx + dz*dz)
            if d < 400 and d > 0:
                o.pos.x += (dx/d) * o.spd; o.pos.z += (dz/d) * o.spd
                o.angle = math.degrees(math.atan2(dx, dz))
            else:
                o.timer += 1
                if o.timer % 120 < 60: o.pos.x += o.spd * o.pdir
                else: o.pos.x -= o.spd * o.pdir
        elif o.type == ObjType.BULLY:
            dx = mario.pos.x - o.pos.x; dz = mario.pos.z - o.pos.z
            d = math.sqrt(dx*dx + dz*dz)
            if d < 200 and d > 0:
                o.pos.x += (dx/d) * o.spd * 1.5; o.pos.z += (dz/d) * o.spd * 1.5
        elif o.type in (ObjType.BOO, ObjType.BIG_BOO):
            dx = mario.pos.x - o.pos.x; dz = mario.pos.z - o.pos.z
            d = math.sqrt(dx*dx + dz*dz)
            facing = abs(math.degrees(math.atan2(dx, dz)) - mario.face.y) < 90
            if not facing and d < 400 and d > 0:
                o.pos.x += (dx/d) * 1.5; o.pos.z += (dz/d) * 1.5
            o.pos.y = o.home.y + math.sin(frame * 0.04) * 20
        elif o.type == ObjType.AMP:
            o.timer += 1; r = o.scale
            o.pos.x = o.home.x + r * sins(o.timer * 3)
            o.pos.z = o.home.z + r * coss(o.timer * 3)
        elif o.type == ObjType.THWOMP:
            dx = abs(mario.pos.x - o.pos.x); dz = abs(mario.pos.z - o.pos.z)
            if o.state == 0:
                if dx < 100 and dz < 100: o.state = 1; o.timer = 0
            elif o.state == 1:
                o.pos.y = approach_f32(o.pos.y, o.home.y - 200, 15)
                if o.pos.y <= o.home.y - 195: o.state = 2; o.timer = 0
            elif o.state == 2:
                o.timer += 1
                if o.timer > 30: o.state = 3
            elif o.state == 3:
                o.pos.y = approach_f32(o.pos.y, o.home.y, 3)
                if o.pos.y >= o.home.y - 1: o.state = 0
        elif o.type == ObjType.CHAIN_CHOMP:
            o.timer += 1
            if o.timer % 90 < 20:
                dx = mario.pos.x - o.home.x; dz = mario.pos.z - o.home.z
                d = math.sqrt(dx*dx + dz*dz)
                if d < 300 and d > 0:
                    o.pos.x = o.home.x + (dx/d) * 100 * (o.timer % 90) / 20
                    o.pos.z = o.home.z + (dz/d) * 100 * (o.timer % 90) / 20
            else:
                o.pos.x = approach_f32(o.pos.x, o.home.x, 3)
                o.pos.z = approach_f32(o.pos.z, o.home.z, 3)
        elif o.type == ObjType.PIRANHA:
            o.timer += 1; cy = o.timer % 120
            if cy < 30: o.pos.y = approach_f32(o.pos.y, o.home.y + 60, 3)
            elif cy > 90: o.pos.y = approach_f32(o.pos.y, o.home.y - 20, 3)
        elif o.type in (ObjType.KING_BOB, ObjType.BOWSER):
            dx = mario.pos.x - o.pos.x; dz = mario.pos.z - o.pos.z
            d = math.sqrt(dx*dx + dz*dz)
            if d < 500 and d > 0:
                o.angle = math.degrees(math.atan2(dx, dz))
                if d > 100: o.pos.x += (dx/d) * o.spd; o.pos.z += (dz/d) * o.spd
        if o.flash > 0: o.flash -= 1

def interact_objs(mario):
    is_attacking = mario.action in (ACT_PUNCHING, ACT_PUNCH2, ACT_KICK, ACT_SLIDE_KICK, ACT_SLIDE_KICK_SL)
    for o in objs:
        if not o.active or o.collected: continue
        dx = mario.pos.x - o.pos.x; dy = mario.pos.y - o.pos.y; dz = mario.pos.z - o.pos.z
        d = math.sqrt(dx*dx + dy*dy + dz*dz)
        if d > o.irange + 30: continue
        if o.type in (ObjType.COIN, ObjType.COIN_RED, ObjType.COIN_BLUE):
            o.collected = True; o.active = False; mario.coins += o.coins; mario.heal(0x40 * o.coins)
            ptcl.emit(o.pos, 8, o.color, 4.0, 15); play_sfx('coin')
        elif o.type == ObjType.STAR:
            if not mario.has_star(cur_lvl, o.star_id):
                o.collected = True; o.active = False
                mario.get_star(cur_lvl, o.star_id)
                mario.set_act(ACT_STAR_DANCE)
                ptcl.emit_sparkle(o.pos, 20); play_sfx('star')
        elif o.type == ObjType.ONE_UP:
            o.collected = True; o.active = False; mario.lives += 1
            ptcl.emit(o.pos, 10, (0,255,0), 3.0, 15); play_sfx('1up')
        elif o.type == ObjType.PIPE:
            if ctrl.pressed & IN_A: return ('warp', o.warp)
        elif o.type in (ObjType.GOOMBA, ObjType.BOBOMB, ObjType.KOOPA, ObjType.PIRANHA):
            if mario.vel.y < -5 and mario.pos.y > o.pos.y + 20:
                o.active = False; mario.vel.y = 30.0; mario.coins += 1
                ptcl.emit(o.pos, 10, o.color, 4.0, 15); play_sfx('stomp')
            elif mario.action in (ACT_DIVE, ACT_GP_LAND) or is_attacking:
                o.active = False; mario.coins += 1
                ptcl.emit(o.pos, 10, o.color, 4.0, 15); play_sfx('stomp')
            else:
                mario.take_dmg(0x100 * o.dmg); mario.set_act(ACT_KNOCKBACK)
                ptcl.emit(mario.pos, 5, (255,50,50), 3.0, 10); play_sfx('hurt')
        elif o.type == ObjType.BULLY:
            if d < o.irange:
                px = dx / max(d,1) * 20; pz = dz / max(d,1) * 20
                mario.pos.x += px; mario.pos.z += pz; mario.fvel = 15
        elif o.type in (ObjType.BOO, ObjType.BIG_BOO):
            fb = abs(math.degrees(math.atan2(o.pos.x-mario.pos.x, o.pos.z-mario.pos.z)) - mario.face.y) > 90
            if fb and (mario.action in (ACT_GROUND_POUND, ACT_GP_LAND) or is_attacking):
                o.hp -= 1; o.flash = 10
                if o.hp <= 0: o.active = False; ptcl.emit(o.pos, 15, (220,220,255), 5.0, 20)
            elif not fb and d < o.irange:
                mario.take_dmg(0x100); mario.set_act(ACT_KNOCKBACK); play_sfx('hurt')
        elif o.type == ObjType.AMP:
            mario.take_dmg(0x100); mario.set_act(ACT_KNOCKBACK); play_sfx('hurt')
        elif o.type == ObjType.THWOMP:
            if o.state == 1 and d < o.irange:
                mario.take_dmg(0x200); mario.set_act(ACT_KNOCKBACK); play_sfx('hurt')
        elif o.type == ObjType.CHAIN_CHOMP:
            mario.take_dmg(0x300); mario.set_act(ACT_KNOCKBACK)
            ptcl.emit(mario.pos, 8, (255,50,50), 4.0, 12); play_sfx('hurt')
        elif o.type in (ObjType.KING_BOB, ObjType.BOWSER):
            if mario.vel.y < -5 and mario.pos.y > o.pos.y + 30:
                o.hp -= 1; o.flash = 15; mario.vel.y = 40.0; play_sfx('stomp')
                if o.hp <= 0: o.active = False; ptcl.emit(o.pos, 25, o.color, 8.0, 30)
            elif is_attacking:
                o.hp -= 1; o.flash = 10; play_sfx('stomp')
                if o.hp <= 0: o.active = False; ptcl.emit(o.pos, 25, o.color, 8.0, 30)
            else:
                mario.take_dmg(0x200); mario.set_act(ACT_KNOCKBACK); play_sfx('hurt')
    return None

# ============================================================================
#  LAKITU CAMERA
# ============================================================================
@dataclass
class LakituCam:
    pos: Vec3f = field(default_factory=lambda: Vec3f(0, 500, 800))
    focus: Vec3f = field(default_factory=Vec3f)
    yaw: float = 0.0
    pitch: float = 15.0
    dist: float = 800.0
    target_dist: float = 800.0

    def update(self, mario, keys, dt=1.0):
        # Camera rotation
        if keys[pygame.K_q] or keys[pygame.K_j]: self.yaw -= 3.0
        if keys[pygame.K_e] or keys[pygame.K_l]: self.yaw += 3.0
        if keys[pygame.K_r]: self.pitch = min(self.pitch + 1.5, 60)
        if keys[pygame.K_f]: self.pitch = max(self.pitch - 1.5, -10)

        # Auto-adjust distance based on speed
        if mario.fvel > 20: self.target_dist = 1000
        elif mario.fvel > 10: self.target_dist = 900
        else: self.target_dist = 800
        self.dist += (self.target_dist - self.dist) * 0.05

        # Focus point (slightly ahead of Mario)
        fx = mario.pos.x + sins(mario.face.y) * 50
        fy = mario.pos.y + 120
        fz = mario.pos.z + coss(mario.face.y) * 50

        # Smooth follow
        self.focus.x += (fx - self.focus.x) * 0.12
        self.focus.y += (fy - self.focus.y) * 0.08
        self.focus.z += (fz - self.focus.z) * 0.12

        # Position camera behind & above Mario
        wx = self.focus.x - sins(self.yaw) * coss(self.pitch) * self.dist
        wy = self.focus.y + sins(self.pitch) * self.dist * 0.5 + 200
        wz = self.focus.z - coss(self.yaw) * coss(self.pitch) * self.dist

        self.pos.x += (wx - self.pos.x) * 0.1
        self.pos.y += (wy - self.pos.y) * 0.1
        self.pos.z += (wz - self.pos.z) * 0.1

# ============================================================================
#  RENDERER — Enhanced 3D
# ============================================================================
def rot_pt(v, cx, cy, cz, ay, ap=0):
    x, y, z = v.x - cx, v.y - cy, v.z - cz
    r = math.radians(ay); c, s = math.cos(r), math.sin(r)
    rx, rz = x*c - z*s, x*s + z*c
    if ap != 0:
        rp = math.radians(ap); cp, sp = math.cos(rp), math.sin(rp)
        ry = y * cp - rz * sp; rz = y * sp + rz * cp
        return rx, ry, rz
    return rx, y, rz

def draw_sky(screen, info, frame):
    sky = info.sky
    for y in range(0, HEIGHT, 4):
        t = y / HEIGHT
        r = int(sky[0] * (1 - t * 0.4) + 10 * t)
        g = int(sky[1] * (1 - t * 0.4) + 10 * t)
        b = int(sky[2] * (1 - t * 0.3) + 20 * t)
        pygame.draw.line(screen, _cc((r, g, b)), (0, y), (WIDTH, y))
        if y < 3:
            pygame.draw.line(screen, _cc((r, g, b)), (0, y+1), (WIDTH, y+1))
            pygame.draw.line(screen, _cc((r, g, b)), (0, y+2), (WIDTH, y+2))
            pygame.draw.line(screen, _cc((r, g, b)), (0, y+3), (WIDTH, y+3))

def render(screen, mario, cam, frame):
    info = LI.get(cur_lvl, LI[0])
    draw_sky(screen, info, frame)
    sky = info.sky

    rlist = []
    for s in surfs: rlist.append(('e', s))
    for o in objs:
        if not o.active: continue
        if o.type == ObjType.TREE:
            for ts in make_box(o.pos.x, o.pos.y+o.height/2, o.pos.z, 25, o.height, 25, (100,65,30)):
                rlist.append(('o', ts))
            for cs in make_box(o.pos.x, o.pos.y+o.height+50, o.pos.z, 100, 100, 100, (30,140,30)):
                rlist.append(('o', cs))
        elif o.type == ObjType.PIPE:
            for ps in make_box(o.pos.x, o.pos.y+40, o.pos.z, 65, 80, 65, o.color):
                rlist.append(('o', ps))
            for ps in make_box(o.pos.x, o.pos.y+85, o.pos.z, 75, 10, 75, _cc((o.color[0]*0.8, o.color[1]*0.8, o.color[2]*0.8))):
                rlist.append(('o', ps))
        else:
            sz = o.radius * o.scale
            col = (255,255,255) if o.flash > 0 and o.flash % 2 == 0 else o.color
            for os in make_box(o.pos.x, o.pos.y+o.height*o.scale/2, o.pos.z, sz, o.height*o.scale, sz, col):
                rlist.append(('o', os))

    # Mario model — proper body parts
    sq = mario.squish
    is_crouch = mario.action in (ACT_CROUCH_IDLE, ACT_BELLY_SLIDE, ACT_SLIDE_KICK_SL)
    is_dive = mario.action in (ACT_DIVE, ACT_SLIDE_KICK)
    mc = (255, 20, 20)
    if mario.hurt > 0: mc = (255, 150, 150) if frame % 4 < 2 else (255, 20, 20)
    elif mario.inv > 0 and mario.inv % 4 < 2: mc = (255, 200, 200)
    skin = (255, 200, 160)
    blue = (30, 30, 180)
    hat_c = mc

    if is_dive:
        bh = 15; by = mario.pos.y + 15
        for ms in make_box(mario.pos.x, by, mario.pos.z, 35, 30, 60, mc): rlist.append(('m', ms))
        for ms in make_box(mario.pos.x, by, mario.pos.z + 35, 25, 25, 25, skin): rlist.append(('m', ms))
    elif is_crouch:
        bh = 25
        for ms in make_box(mario.pos.x, mario.pos.y + bh, mario.pos.z, 38*sq, bh*2*sq, 38, mc): rlist.append(('m', ms))
        hy = mario.pos.y + bh * 2 + 5
        for mh in make_box(mario.pos.x, hy, mario.pos.z, 28, 28, 28, skin): rlist.append(('m', mh))
        for hs in make_box(mario.pos.x, hy + 12, mario.pos.z, 32, 8, 32, hat_c): rlist.append(('m', hs))
    else:
        bh = 55 * sq
        bob_y = math.sin(mario.bob_phase) * 2 if mario.action == ACT_WALKING else 0
        # Legs (blue overalls)
        for ms in make_box(mario.pos.x-10, mario.pos.y + 20 + bob_y, mario.pos.z, 14, 40, 14, blue): rlist.append(('m', ms))
        for ms in make_box(mario.pos.x+10, mario.pos.y + 20 + bob_y, mario.pos.z, 14, 40, 14, blue): rlist.append(('m', ms))
        # Body (red shirt)
        for ms in make_box(mario.pos.x, mario.pos.y + 55 + bob_y, mario.pos.z, 36*sq, 40*sq, 30, mc): rlist.append(('m', ms))
        # Arms
        arm_ext = 12
        if mario.action in (ACT_PUNCHING, ACT_PUNCH2, ACT_KICK):
            arm_ext = 25 if mario.atimer < 8 else 12
        for ms in make_box(mario.pos.x - 25, mario.pos.y + 60 + bob_y, mario.pos.z + arm_ext, 10, 10, 18, mc): rlist.append(('m', ms))
        for ms in make_box(mario.pos.x + 25, mario.pos.y + 60 + bob_y, mario.pos.z + arm_ext, 10, 10, 18, mc): rlist.append(('m', ms))
        # Hands (white gloves)
        for ms in make_box(mario.pos.x - 25, mario.pos.y + 60 + bob_y, mario.pos.z + arm_ext + 12, 8, 8, 8, (255,255,255)): rlist.append(('m', ms))
        for ms in make_box(mario.pos.x + 25, mario.pos.y + 60 + bob_y, mario.pos.z + arm_ext + 12, 8, 8, 8, (255,255,255)): rlist.append(('m', ms))
        # Head
        hy = mario.pos.y + 82 + bob_y
        for mh in make_box(mario.pos.x, hy, mario.pos.z, 28, 28, 28, skin): rlist.append(('m', mh))
        # Hat
        for hs in make_box(mario.pos.x, hy + 14, mario.pos.z, 32, 8, 32, hat_c): rlist.append(('m', hs))
        # Hat brim
        for hb in make_box(mario.pos.x, hy + 2, mario.pos.z + 16, 30, 4, 10, hat_c): rlist.append(('m', hb))
        # Mustache (dark)
        for mu in make_box(mario.pos.x, hy - 5, mario.pos.z + 14, 16, 4, 4, (60,30,10)): rlist.append(('m', mu))
        # Nose
        for no in make_box(mario.pos.x, hy - 1, mario.pos.z + 16, 8, 6, 6, (240,180,140)): rlist.append(('m', no))

    # Shadow
    if mario.floor:
        sh_scale = max(0.3, 1.0 - (mario.pos.y - mario.floor_y) / 500)
        sz = int(30 * sh_scale)
        for ss in make_box(mario.pos.x, mario.floor_y + 2, mario.pos.z, sz, 2, sz, (10,10,10)):
            rlist.append(('s', ss))

    # Particles
    for p in ptcl.ps:
        for ps in make_box(p.pos.x, p.pos.y, p.pos.z, p.size, p.size, p.size, p.color):
            rlist.append(('p', ps))

    # Project and sort
    polys = []
    for rt, sf in rlist:
        pv = []; az = 0; visible = False
        for v in sf.verts:
            rx, ry, rz = rot_pt(v, cam.pos.x, cam.pos.y, cam.pos.z, -cam.yaw)
            if rz > NEAR_CLIP:
                visible = True; sc = FOV / rz
                pv.append((WIDTH/2 + rx * sc, HEIGHT/2 - ry * sc))
                az += rz
        if visible and len(pv) >= 3:
            az /= len(sf.verts)
            if az > FAR_CLIP: continue
            col = sf.color if rt != 's' else (10, 10, 10)
            # Distance fog
            f = clamp(az / FAR_CLIP, 0, 1)
            f = f * f  # Quadratic falloff for more natural fog
            fc = (int(col[0]*(1-f) + sky[0]*f),
                  int(col[1]*(1-f) + sky[1]*f),
                  int(col[2]*(1-f) + sky[2]*f))
            polys.append((az, fc, pv, rt))

    polys.sort(key=lambda x: x[0], reverse=True)
    for z, col, pts, rt in polys:
        col = _cc(col)
        pygame.draw.polygon(screen, col, pts)
        # Wireframe for nearby geometry
        if z < 2500 and rt not in ('s', 'p'):
            ec = _cc((col[0]*0.6, col[1]*0.6, col[2]*0.6))
            pygame.draw.polygon(screen, ec, pts, 1)

# ============================================================================
#  HUD — Authentic SM64 Style
# ============================================================================
def draw_hud(screen, mario, fonts, frame):
    ft, fu, fs = fonts

    # === SM64 Power Meter (Health) ===
    hx, hy, hr = 68, HEIGHT - 68, 40
    # Outer ring
    pygame.draw.circle(screen, (20, 20, 20), (hx, hy), hr + 4)
    pygame.draw.circle(screen, (40, 40, 60), (hx, hy), hr + 2)
    w = mario.wedges()
    for i in range(8):
        a1 = math.radians(90 - i * 45)
        a2 = math.radians(90 - (i + 1) * 45)
        if i < w:
            if w > 4: c = (80, 210, 80)
            elif w > 2: c = (220, 220, 50)
            else: c = (220, 60, 60)
            pts = [(hx, hy)]
            steps = 4
            for s in range(steps + 1):
                a = a1 + (a2 - a1) * s / steps
                pts.append((hx + hr * math.cos(a), hy - hr * math.sin(a)))
            pygame.draw.polygon(screen, c, pts)
    pygame.draw.circle(screen, (255, 255, 255), (hx, hy), hr, 3)
    pygame.draw.circle(screen, (200, 200, 200), (hx, hy), hr - 2, 1)

    # === Star Counter (top-left, like SM64) ===
    star_surf = fu.render("\u2605", True, (255, 255, 50))
    screen.blit(star_surf, (20, 15))
    star_x = fu.render(f"x {mario.stars}", True, (255, 255, 255))
    screen.blit(star_x, (48, 17))

    # === Coin Counter (top-left, under stars) ===
    coin_icon = fu.render("\u25CF", True, (255, 215, 0))
    screen.blit(coin_icon, (20, 48))
    coin_txt = fu.render(f"x {mario.coins}", True, (255, 255, 255))
    screen.blit(coin_txt, (42, 50))

    # === Lives (top-right area like SM64) ===
    lives_txt = fu.render(f"MARIO  x {mario.lives}", True, (255, 255, 255))
    screen.blit(lives_txt, (WIDTH - lives_txt.get_width() - 20, 15))

    # === Level Name (top-center) ===
    lt = fu.render(cur_name, True, (255, 255, 220))
    lts = fu.render(cur_name, True, (40, 40, 40))
    screen.blit(lts, (WIDTH // 2 - lt.get_width() // 2 + 2, 17))
    screen.blit(lt, (WIDTH // 2 - lt.get_width() // 2, 15))

    # === Action/Speed Debug (bottom-left, SM64 decomp style) ===
    act_names = {
        ACT_IDLE: "IDLE", ACT_WALKING: "WALK", ACT_DECELERATING: "DECEL",
        ACT_CROUCH_IDLE: "CROUCH",
        ACT_PUNCHING: "PUNCH1", ACT_PUNCH2: "PUNCH2", ACT_KICK: "KICK",
        ACT_JUMP: "JUMP", ACT_DOUBLE_JUMP: "DBL_JUMP", ACT_TRIPLE_JUMP: "TRIPLE",
        ACT_BACKFLIP: "BACKFLIP", ACT_LONG_JUMP: "LONG_JUMP", ACT_WALL_KICK: "WALL_KICK",
        ACT_SIDE_FLIP: "SIDE_FLIP", ACT_FREEFALL: "FREEFALL",
        ACT_DIVE: "DIVE", ACT_BELLY_SLIDE: "BELLY_SLIDE",
        ACT_SLIDE_KICK: "SLIDE_KICK", ACT_SLIDE_KICK_SL: "SK_SLIDE",
        ACT_GROUND_POUND: "GP", ACT_GP_LAND: "GP_LAND",
        ACT_KNOCKBACK: "KNOCKBACK", ACT_LAVA_BOOST: "LAVA_BOOST",
        ACT_STAR_DANCE: "STAR_GET", ACT_DEATH: "DEAD"
    }
    aname = act_names.get(mario.action, hex(mario.action))
    dbg = fs.render(f"{aname}  SPD:{mario.fvel:.0f}  Y:{mario.pos.y:.0f}  HP:{mario.wedges()}/8", True, (200, 200, 200))
    dbg_bg = pygame.Surface((dbg.get_width() + 10, dbg.get_height() + 4), pygame.SRCALPHA)
    dbg_bg.fill((0, 0, 0, 100))
    screen.blit(dbg_bg, (15, HEIGHT - 28))
    screen.blit(dbg, (20, HEIGHT - 26))

# ============================================================================
#  TITLE SCREEN — SM64 Authentic
# ============================================================================
def draw_title(screen, fonts, frame):
    ft, fu, fs = fonts
    # Sky gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(20 + t * 40); g = int(10 + t * 30); b = int(60 + t * 140)
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

    # Clouds
    for i in range(5):
        cx = (frame * 0.3 + i * 200) % (WIDTH + 200) - 100
        cy = 80 + i * 40 + math.sin(frame * 0.01 + i) * 10
        pygame.draw.ellipse(screen, (60, 60, 120), (cx, cy, 120, 40))
        pygame.draw.ellipse(screen, (70, 70, 130), (cx + 20, cy - 10, 80, 30))

    # Title text with shadow
    off = math.sin(frame * 0.04) * 12
    title = "SUPER MARIO 64"
    t = ft.render(title, True, (255, 215, 0))
    ts = ft.render(title, True, (80, 60, 0))
    tx = WIDTH // 2 - t.get_width() // 2
    screen.blit(ts, (tx + 4, 80 + off + 4))
    screen.blit(t, (tx, 80 + off))

    # Subtitle
    sub = fu.render("Cat's PC Port — Python Edition v5.0", True, (200, 200, 255))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 155 + off))

    # Mario face (improved)
    cx, cy = WIDTH // 2, 310
    # Face
    pygame.draw.circle(screen, (255, 200, 170), (cx, cy), 60)
    # Hat
    pygame.draw.rect(screen, (255, 0, 0), (cx - 65, cy - 80, 130, 50), border_radius=8)
    pygame.draw.rect(screen, (255, 0, 0), (cx + 5, cy - 30, 65, 20), border_radius=4)
    # Hat "M" circle
    pygame.draw.circle(screen, (255, 255, 255), (cx, cy - 60), 22)
    mf = pygame.font.SysFont('Arial Black', 26)
    m_txt = mf.render("M", True, (255, 0, 0))
    screen.blit(m_txt, (cx - m_txt.get_width() // 2, cy - 73))
    # Eyes
    pygame.draw.ellipse(screen, (255, 255, 255), (cx - 28, cy - 22, 20, 22))
    pygame.draw.ellipse(screen, (255, 255, 255), (cx + 8, cy - 22, 20, 22))
    pygame.draw.ellipse(screen, (0, 80, 180), (cx - 23, cy - 18, 12, 16))
    pygame.draw.ellipse(screen, (0, 80, 180), (cx + 13, cy - 18, 12, 16))
    pygame.draw.ellipse(screen, (0, 0, 0), (cx - 20, cy - 15, 6, 10))
    pygame.draw.ellipse(screen, (0, 0, 0), (cx + 16, cy - 15, 6, 10))
    # Nose
    pygame.draw.ellipse(screen, (200, 140, 110), (cx - 12, cy + 2, 24, 18))
    # Mustache
    pygame.draw.ellipse(screen, (60, 30, 10), (cx - 30, cy + 12, 60, 22))
    # Ears
    pygame.draw.circle(screen, (255, 190, 160), (cx - 55, cy - 5), 15)
    pygame.draw.circle(screen, (255, 190, 160), (cx + 55, cy - 5), 15)

    # Press Start blink
    if (frame // 30) % 2 == 0:
        ps = fu.render("PRESS ENTER", True, (255, 255, 255))
        pss = fu.render("PRESS ENTER", True, (60, 60, 60))
        screen.blit(pss, (WIDTH // 2 - ps.get_width() // 2 + 2, 472))
        screen.blit(ps, (WIDTH // 2 - ps.get_width() // 2, 470))

    # Footer
    screen.blit(fs.render("v5.0 — All 27 Levels — 60fps — Procedural Audio — PC Port Physics", True, (120, 120, 160)),
                (WIDTH // 2 - 230, HEIGHT - 30))

    # Controls hint
    ctrl_txt = fs.render("WASD/Arrows=Move  Space=Jump  X=Punch  Z=Crouch  Q/E=Camera", True, (100, 100, 140))
    screen.blit(ctrl_txt, (WIDTH // 2 - ctrl_txt.get_width() // 2, HEIGHT - 55))

# ============================================================================
#  LEVEL SELECT — SM64 Style
# ============================================================================
def draw_select(screen, fonts, lflat, sel, mario, scr):
    ft, fu, fs = fonts
    screen.fill((15, 10, 35))

    # Title
    tt = ft.render("SELECT COURSE", True, (255, 215, 0))
    tts = ft.render("SELECT COURSE", True, (80, 60, 0))
    screen.blit(tts, (WIDTH // 2 - tt.get_width() // 2 + 2, 17))
    screen.blit(tt, (WIDTH // 2 - tt.get_width() // 2, 15))

    # Star count
    screen.blit(fu.render(f"\u2605 x {mario.stars}", True, (255, 255, 100)), (WIDTH - 160, 20))

    yp = 75 - scr; idx = 0
    for cn, lids in CATS:
        if -30 < yp < HEIGHT - 40:
            ct = fs.render(cn, True, (150, 150, 200))
            screen.blit(ct, (30, yp))
        yp += 30
        for lid in lids:
            if -30 < yp < HEIGHT - 40:
                info = LI[lid]; sel_ = idx == sel
                nc = len(mario.lvl_stars.get(lid, set())); ns = info.nstars
                ss = f"[{'★' * nc}{'☆' * max(0, ns - nc)}]" if ns > 0 else ""
                col = (255, 215, 0) if sel_ else (180, 180, 180)
                pre = "▶ " if sel_ else "   "
                if sel_:
                    pygame.draw.rect(screen, (40, 30, 70), (50, yp - 2, WIDTH - 100, 26), border_radius=3)
                txt = fu.render(f"{pre}{info.name}  {ss}", True, col)
                screen.blit(txt, (55, yp))
            yp += 30; idx += 1
        yp += 12

    # Footer
    fc = fs.render("↑↓ Navigate   ENTER Select   ESC Back", True, (100, 100, 130))
    screen.blit(fc, (WIDTH // 2 - fc.get_width() // 2, HEIGHT - 30))

# ============================================================================
#  PAUSE / DEATH SCREENS
# ============================================================================
def draw_pause(screen, fonts, mario):
    ft, fu, fs = fonts
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 160))
    screen.blit(ov, (0, 0))

    pt = ft.render("PAUSE", True, (255, 255, 255))
    pts = ft.render("PAUSE", True, (60, 60, 60))
    screen.blit(pts, (WIDTH // 2 - pt.get_width() // 2 + 3, 143))
    screen.blit(pt, (WIDTH // 2 - pt.get_width() // 2, 140))

    stats = [f"Stars: {mario.stars}", f"Coins: {mario.coins}",
             f"Lives: {mario.lives}", f"Level: {cur_name}"]
    for i, s in enumerate(stats):
        st = fu.render(s, True, (220, 220, 220))
        screen.blit(st, (WIDTH // 2 - 70, 240 + i * 40))

    ft2 = fs.render("ESC Resume    Q Exit to Select", True, (150, 150, 150))
    screen.blit(ft2, (WIDTH // 2 - ft2.get_width() // 2, 440))

def draw_death(screen, fonts, mario, t):
    ft, fu, fs = fonts
    screen.fill((0, 0, 0))
    if t > 30:
        go = ft.render("GAME OVER", True, (255, 50, 50))
        gos = ft.render("GAME OVER", True, (80, 15, 15))
        screen.blit(gos, (WIDTH // 2 - go.get_width() // 2 + 3, 203))
        screen.blit(go, (WIDTH // 2 - go.get_width() // 2, 200))
    if t > 60:
        lt = fu.render(f"Lives: {mario.lives}", True, (200, 200, 200))
        screen.blit(lt, (WIDTH // 2 - lt.get_width() // 2, 300))
    if t > 90:
        pt = fu.render("Press ENTER", True, (150, 150, 150))
        if (t // 20) % 2 == 0:
            screen.blit(pt, (WIDTH // 2 - pt.get_width() // 2, 400))

# ============================================================================
#  MAIN LOOP — SM64 PC Port Style
# ============================================================================
def main():
    global ctrl
    pygame.init()
    init_audio()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cat's SM64 PC Port v5.0 — Python Edition")
    clock = pygame.time.Clock()

    ft = pygame.font.SysFont('Arial Black', 48)
    fu = pygame.font.SysFont('Arial', 24)
    fs = pygame.font.SysFont('Arial', 18)
    fonts = (ft, fu, fs)

    state = GameState.TITLE
    frame = 0; lacc = 0
    mario = MarioState(); ctrl = Controller()
    cam = LakituCam()

    lflat = []
    for _, lids in CATS: lflat.extend(lids)
    sel = 0; scr = 0; dtimer = 0

    running = True
    while running:
        frame += 1; clock.tick(FPS)
        kp = set()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            if ev.type == pygame.KEYDOWN:
                kp.add(ev.key)
                if state == GameState.TITLE:
                    if ev.key == pygame.K_RETURN: state = GameState.LEVEL_SELECT
                elif state == GameState.LEVEL_SELECT:
                    if ev.key == pygame.K_UP:
                        sel = (sel - 1) % len(lflat); scr = max(0, sel * 30 - 250)
                    elif ev.key == pygame.K_DOWN:
                        sel = (sel + 1) % len(lflat); scr = max(0, sel * 30 - 250)
                    elif ev.key == pygame.K_RETURN:
                        lid = lflat[sel]; info = LI[lid]; load_level(lid)
                        mario.pos = info.start.copy(); mario.vel.set(0, 0, 0); mario.fvel = 0
                        mario.action = ACT_FREEFALL; mario.health = 0x880; mario.coins = 0
                        mario.punch_state = 0
                        cam = LakituCam()
                        cam.pos = Vec3f(mario.pos.x, mario.pos.y + 300, mario.pos.z + 800)
                        cam.focus = mario.pos.copy()
                        state = GameState.GAMEPLAY
                    elif ev.key == pygame.K_ESCAPE: state = GameState.TITLE
                elif state == GameState.GAMEPLAY:
                    if ev.key == pygame.K_ESCAPE: state = GameState.PAUSE
                elif state == GameState.PAUSE:
                    if ev.key == pygame.K_ESCAPE: state = GameState.GAMEPLAY
                    elif ev.key == pygame.K_q: state = GameState.LEVEL_SELECT
                elif state == GameState.DEATH:
                    if ev.key == pygame.K_RETURN and dtimer > 90:
                        if mario.lives > 0: state = GameState.LEVEL_SELECT
                        else: mario = MarioState(); state = GameState.TITLE

        keys = pygame.key.get_pressed()
        lacc += 1; do_logic = (lacc >= FRAME_SKIP)
        if do_logic: lacc = 0

        if state == GameState.GAMEPLAY and do_logic:
            ctrl.pressed = 0; ctrl.down = 0
            if keys[pygame.K_SPACE] or pygame.K_SPACE in kp: ctrl.pressed |= IN_A
            if keys[pygame.K_SPACE]: ctrl.down |= IN_A_D
            if keys[pygame.K_x] or pygame.K_x in kp: ctrl.pressed |= IN_B
            if keys[pygame.K_z] or pygame.K_z in kp: ctrl.pressed |= IN_Z
            if keys[pygame.K_z]: ctrl.down |= IN_Z_D

            dx = dz = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
            if keys[pygame.K_UP] or keys[pygame.K_w]: dz += 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dz -= 1
            if dx or dz:
                ctrl.stick_mag = 1.0
                mario.iyaw = math.degrees(math.atan2(dx, dz)) + cam.yaw
                mario.imag = MAX_WALK
            else:
                ctrl.stick_mag = 0; mario.imag = 0

            fn = ACT_MAP.get(mario.action, a_idle)
            fn(mario, ctrl)

            if mario.inv > 0: mario.inv -= 1
            if mario.hurt > 0: mario.hurt -= 1

            # Squish animation
            if mario.squish < 1.0:
                mario.squish += mario.squish_vel
                mario.squish_vel *= 0.85
                if mario.squish > 1.0: mario.squish = 1.0
                if abs(mario.squish - 1.0) < 0.01: mario.squish = 1.0

            # Floor surface effects
            if mario.floor:
                if mario.floor.stype == SURF_LAVA and mario.action not in (ACT_LAVA_BOOST, ACT_KNOCKBACK):
                    mario.set_act(ACT_LAVA_BOOST)
                elif mario.floor.stype == SURF_DEATH:
                    mario.pos.set(0, 200, 0); mario.vel.set(0, 0, 0)

            update_objs(mario, frame); ptcl.update()
            wr = interact_objs(mario)
            if wr and wr[0] == 'warp':
                lid = wr[1]; info = LI[lid]; load_level(lid)
                mario.pos = info.start.copy(); mario.vel.set(0, 0, 0); mario.fvel = 0
                mario.action = ACT_FREEFALL; mario.health = 0x880; mario.coins = 0
                mario.punch_state = 0
                cam = LakituCam()
                cam.pos = Vec3f(mario.pos.x, mario.pos.y + 300, mario.pos.z + 800)
                cam.focus = mario.pos.copy()

            if mario.health <= 0:
                mario.lives -= 1; dtimer = 0; state = GameState.DEATH

            if mario.pos.y < -3000:
                mario.pos = LI.get(cur_lvl, LI[0]).start.copy()
                mario.vel.set(0, 0, 0); mario.fvel = 0
                mario.action = ACT_FREEFALL; mario.take_dmg(0x100)

            # Lakitu camera update
            cam.update(mario, keys)

        if state == GameState.DEATH and do_logic: dtimer += 1

        # === RENDER ===
        if state == GameState.TITLE:
            draw_title(screen, fonts, frame)
        elif state == GameState.LEVEL_SELECT:
            draw_select(screen, fonts, lflat, sel, mario, scr)
        elif state == GameState.GAMEPLAY:
            render(screen, mario, cam, frame)
            draw_hud(screen, mario, fonts, frame)
        elif state == GameState.PAUSE:
            render(screen, mario, cam, frame)
            draw_hud(screen, mario, fonts, frame)
            draw_pause(screen, fonts, mario)
        elif state == GameState.DEATH:
            draw_death(screen, fonts, mario, dtimer)

        # FPS counter
        fps_txt = fs.render(f"FPS: {clock.get_fps():.0f}", True, (100, 100, 100))
        screen.blit(fps_txt, (WIDTH - 80, HEIGHT - 25))

        pygame.display.flip()

    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()
