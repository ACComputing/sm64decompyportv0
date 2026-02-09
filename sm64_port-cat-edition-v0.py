#!/usr/bin/env python3
"""
============================================================================
 Cat's SM64 Py Port 4.0 — Full Course Edition
 All 15 Main Courses + Castle Hub + Bowser Stages + Secret Levels
 60 FPS display / 30 Hz logic (N64-accurate timing)
 Single-File Build — No external assets required
============================================================================
"""
import pygame, math, sys, random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Set

WIDTH, HEIGHT = 800, 600
FPS = 60
LOGIC_HZ = 30
FRAME_SKIP = FPS // LOGIC_HZ
FOV = 450

S16_MAX = 32767

@dataclass
class Vec3f:
    x: float = 0.0; y: float = 0.0; z: float = 0.0
    def set(self, x, y, z): self.x, self.y, self.z = x, y, z
    def copy(self): return Vec3f(self.x, self.y, self.z)
    def dist_to(self, o):
        dx, dy, dz = self.x-o.x, self.y-o.y, self.z-o.z
        return math.sqrt(dx*dx+dy*dy+dz*dz)

@dataclass
class Vec3s:
    x: int = 0; y: int = 0; z: int = 0

def clamp(v, lo, hi): return max(lo, min(hi, v))
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
def _cc(c): return tuple(max(0, min(255, int(v))) for v in c)

class GameState(Enum):
    TITLE=auto(); LEVEL_SELECT=auto(); GAMEPLAY=auto(); PAUSE=auto(); DEATH=auto()

# SM64 Actions
ACT_IDLE=0x001; ACT_WALKING=0x004; ACT_DECEL=0x005; ACT_CROUCH=0x008
ACT_JUMP=0x010; ACT_DBL_JUMP=0x011; ACT_TRIPLE=0x012; ACT_BACKFLIP=0x013
ACT_LONG_JUMP=0x014; ACT_WALLKICK=0x015; ACT_SIDEFLIP=0x016; ACT_FREEFALL=0x018
ACT_DIVE=0x01A; ACT_BELLY_SLIDE=0x01B; ACT_GROUND_POUND=0x025; ACT_GP_LAND=0x026
ACT_KNOCKBACK=0x040; ACT_LAVA_BOOST=0x042; ACT_STAR_DANCE=0x050; ACT_DEATH=0x051

GRAVITY=-4.0; MAX_FALL=-75.0; MAX_WALK=32.0; AIR_DRAG=0.98
IN_A=0x01; IN_B=0x02; IN_Z=0x04; IN_A_D=0x10; IN_Z_D=0x40

@dataclass
class Controller:
    stick_x:float=0; stick_y:float=0; stick_mag:float=0
    pressed:int=0; down:int=0

SURF_DEFAULT=0; SURF_LAVA=1; SURF_SLIP=2; SURF_DEATH=3; SURF_WATER=4; SURF_ICE=5; SURF_SAND=6

@dataclass
class Surface:
    verts: List[Vec3f]; normal: Vec3f; stype:int=0
    color: Tuple[int,int,int]=(200,200,200); warp:int=-1

class ObjType(Enum):
    COIN=auto(); COIN_RED=auto(); COIN_BLUE=auto(); STAR=auto()
    GOOMBA=auto(); BOBOMB=auto(); BULLY=auto(); BOO=auto()
    PIRANHA=auto(); KOOPA=auto(); AMP=auto(); THWOMP=auto()
    CHAIN_CHOMP=auto(); KING_BOB=auto(); BIG_BOO=auto(); BOWSER=auto()
    ONE_UP=auto(); TREE=auto(); PIPE=auto(); BOX=auto()

@dataclass
class Obj:
    type:ObjType; pos:Vec3f; vel:Vec3f=field(default_factory=Vec3f)
    angle:float=0; radius:float=50; height:float=50; hp:int=1
    active:bool=True; timer:int=0; state:int=0; home:Vec3f=field(default_factory=Vec3f)
    color:Tuple[int,int,int]=(255,255,0); collected:bool=False
    irange:float=80; scale:float=1.0; dmg:int=1; coins:int=0; star_id:int=0
    warp:int=-1; spd:float=1.5; pdir:int=1; bob:float=0; flash:int=0

@dataclass
class Particle:
    pos:Vec3f; vel:Vec3f; color:Tuple[int,int,int]; life:int; size:float=3.0

class Particles:
    def __init__(self): self.ps: List[Particle] = []
    def emit(self, p, n, c, s=5.0, l=20, sz=3.0):
        for _ in range(n):
            v = Vec3f(random.uniform(-s,s), random.uniform(0,s*1.5), random.uniform(-s,s))
            self.ps.append(Particle(p.copy(), v, c, l, sz))
    def update(self):
        alive = []
        for p in self.ps:
            p.pos.x+=p.vel.x; p.pos.y+=p.vel.y; p.pos.z+=p.vel.z
            p.vel.y-=0.5; p.life-=1
            if p.life>0: alive.append(p)
        self.ps = alive

@dataclass
class MarioState:
    pos:Vec3f=field(default_factory=Vec3f); vel:Vec3f=field(default_factory=Vec3f)
    fvel:float=0.0; face:Vec3s=field(default_factory=Vec3s)
    action:int=ACT_IDLE; prev_act:int=ACT_IDLE; astate:int=0; atimer:int=0
    health:int=0x880; coins:int=0; stars:int=0; lives:int=4
    floor:Optional[Surface]=None; floor_y:float=-10000
    wall:Optional[Surface]=None; imag:float=0; iyaw:int=0
    peak_y:float=0; jcount:int=0; jtimer:int=0; wktimer:int=0
    hurt:int=0; inv:int=0; lvl_stars:Dict[int,Set[int]]=field(default_factory=dict)

    def set_act(self, a, arg=0):
        self.prev_act=self.action; self.action=a; self.astate=0; self.atimer=0
    def heal(self, amt): self.health=min(0x880, self.health+amt)
    def take_dmg(self, amt):
        if self.inv>0: return
        self.health=max(0, self.health-amt); self.hurt=10; self.inv=60
    def wedges(self): return (self.health>>8)&0xF
    def has_star(self, l, s): return s in self.lvl_stars.get(l, set())
    def get_star(self, l, s):
        if l not in self.lvl_stars: self.lvl_stars[l]=set()
        if s not in self.lvl_stars[l]: self.lvl_stars[l].add(s); self.stars+=1

# Globals
surfs: List[Surface] = []
objs: List[Obj] = []
cur_lvl = 0; cur_name = ""
ptcl = Particles()
ctrl = Controller()

# ============================================================================
#  GEOMETRY
# ============================================================================
def make_box(x,y,z,w,h,d,col,st=SURF_DEFAULT,wp=-1):
    hw,hh,hd=w/2,h/2,d/2; s=[]
    tc=_cc((col[0]*1.15,col[1]*1.15,col[2]*1.15))
    dc=_cc((col[0]*0.75,col[1]*0.75,col[2]*0.75))
    s.append(Surface([Vec3f(x-hw,y+hh,z-hd),Vec3f(x+hw,y+hh,z-hd),Vec3f(x+hw,y+hh,z+hd),Vec3f(x-hw,y+hh,z+hd)],Vec3f(0,1,0),st,tc,wp))
    s.append(Surface([Vec3f(x-hw,y-hh,z+hd),Vec3f(x+hw,y-hh,z+hd),Vec3f(x+hw,y+hh,z+hd),Vec3f(x-hw,y+hh,z+hd)],Vec3f(0,0,1),st,col,wp))
    s.append(Surface([Vec3f(x+hw,y-hh,z-hd),Vec3f(x-hw,y-hh,z-hd),Vec3f(x-hw,y+hh,z-hd),Vec3f(x+hw,y+hh,z-hd)],Vec3f(0,0,-1),st,col,wp))
    s.append(Surface([Vec3f(x-hw,y-hh,z-hd),Vec3f(x-hw,y-hh,z+hd),Vec3f(x-hw,y+hh,z+hd),Vec3f(x-hw,y+hh,z-hd)],Vec3f(-1,0,0),st,dc,wp))
    s.append(Surface([Vec3f(x+hw,y-hh,z+hd),Vec3f(x+hw,y-hh,z-hd),Vec3f(x+hw,y+hh,z-hd),Vec3f(x+hw,y+hh,z+hd)],Vec3f(1,0,0),st,dc,wp))
    return s

def make_quad(p1,p2,p3,p4,col,st=SURF_DEFAULT):
    ux,uy,uz=p2.x-p1.x,p2.y-p1.y,p2.z-p1.z
    vx,vy,vz=p3.x-p1.x,p3.y-p1.y,p3.z-p1.z
    nx=uy*vz-uz*vy; ny=uz*vx-ux*vz; nz=ux*vy-uy*vx
    m=math.sqrt(nx*nx+ny*ny+nz*nz)
    if m<0.0001: m=1
    return Surface([p1,p2,p3,p4],Vec3f(nx/m,ny/m,nz/m),st,col)

def make_ground(x,z,w,d,y,col,st=SURF_DEFAULT):
    hw,hd=w/2,d/2
    return make_quad(Vec3f(x-hw,y,z-hd),Vec3f(x+hw,y,z-hd),Vec3f(x+hw,y,z+hd),Vec3f(x-hw,y,z+hd),col,st)

def make_slope(x1,y1,z1,x2,y2,z2,w,col,st=SURF_DEFAULT):
    hw=w/2
    return make_quad(Vec3f(x1-hw,y1,z1),Vec3f(x1+hw,y1,z1),Vec3f(x2+hw,y2,z2),Vec3f(x2-hw,y2,z2),col,st)

def make_stairs(x,y,z,n,sw,sh,sd,dr,col):
    r=[]
    for i in range(n):
        r.extend(make_box(x+dr[0]*i*sd, y+i*sh+sh/2, z+dr[1]*i*sd, sw,sh,sd,col))
    return r

# ============================================================================
#  SPAWNERS
# ============================================================================
def sp_coin(x,y,z,t=ObjType.COIN):
    cs={ObjType.COIN:(255,215,0),ObjType.COIN_RED:(255,50,50),ObjType.COIN_BLUE:(50,100,255)}
    vs={ObjType.COIN:1,ObjType.COIN_RED:2,ObjType.COIN_BLUE:5}
    o=Obj(t,Vec3f(x,y+30,z),radius=30,height=30,color=cs.get(t,(255,215,0)),irange=60)
    o.coins=vs.get(t,1); o.bob=random.uniform(0,6.28); o.home=Vec3f(x,y+30,z); return o

def sp_star(x,y,z,sid=0):
    o=Obj(ObjType.STAR,Vec3f(x,y+50,z),radius=40,height=40,color=(255,255,100),irange=80,star_id=sid)
    o.bob=random.uniform(0,6.28); o.home=Vec3f(x,y+50,z); return o

def sp_goomba(x,y,z):
    o=Obj(ObjType.GOOMBA,Vec3f(x,y,z),radius=40,height=50,color=(150,80,30),irange=60,dmg=1,spd=1.5)
    o.home=Vec3f(x,y,z); return o

def sp_bobomb(x,y,z):
    o=Obj(ObjType.BOBOMB,Vec3f(x,y,z),radius=35,height=45,color=(20,20,20),irange=60,spd=1.0)
    o.home=Vec3f(x,y,z); return o

def sp_bully(x,y,z):
    o=Obj(ObjType.BULLY,Vec3f(x,y,z),radius=50,height=60,color=(80,80,80),irange=70,dmg=0,hp=3,spd=2.0)
    o.home=Vec3f(x,y,z); return o

def sp_boo(x,y,z):
    o=Obj(ObjType.BOO,Vec3f(x,y+30,z),radius=50,height=60,color=(220,220,255),irange=70,dmg=1)
    o.home=Vec3f(x,y+30,z); return o

def sp_piranha(x,y,z):
    o=Obj(ObjType.PIRANHA,Vec3f(x,y,z),radius=40,height=80,color=(20,140,20),irange=70,dmg=2)
    o.home=Vec3f(x,y,z); return o

def sp_koopa(x,y,z):
    o=Obj(ObjType.KOOPA,Vec3f(x,y,z),radius=40,height=55,color=(50,180,50),irange=60,spd=1.8)
    o.home=Vec3f(x,y,z); return o

def sp_amp(x,y,z,r=200):
    o=Obj(ObjType.AMP,Vec3f(x,y,z),radius=30,height=30,color=(30,30,200),irange=50,dmg=1)
    o.home=Vec3f(x,y,z); o.scale=r; return o

def sp_thwomp(x,y,z):
    o=Obj(ObjType.THWOMP,Vec3f(x,y,z),radius=60,height=100,color=(130,130,150),irange=80,dmg=2)
    o.home=Vec3f(x,y,z); return o

def sp_chomp(x,y,z):
    o=Obj(ObjType.CHAIN_CHOMP,Vec3f(x,y,z),radius=60,height=80,color=(20,20,30),irange=90,dmg=3)
    o.home=Vec3f(x,y,z); return o

def sp_1up(x,y,z):
    o=Obj(ObjType.ONE_UP,Vec3f(x,y+30,z),radius=25,height=25,color=(0,200,0),irange=50)
    o.home=Vec3f(x,y+30,z); o.bob=random.uniform(0,6.28); return o

def sp_tree(x,y,z,h=200):
    return Obj(ObjType.TREE,Vec3f(x,y,z),radius=20,height=h,color=(80,50,20),irange=0)

def sp_pipe(x,y,z,tgt):
    o=Obj(ObjType.PIPE,Vec3f(x,y,z),radius=50,height=80,color=(0,180,0),irange=50)
    o.warp=tgt; return o

def sp_ring(x,y,z,r=200,n=8):
    return [sp_coin(x+r*sins(360/n*i),y,z+r*coss(360/n*i)) for i in range(n)]

def sp_line(x,y,z,dx,dy,dz,n=5):
    return [sp_coin(x+dx*i,y+dy*i,z+dz*i) for i in range(n)]

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
    name:str; sky:Tuple[int,int,int]=(135,206,235); nstars:int=7
    start:Vec3f=field(default_factory=lambda:Vec3f(0,200,0))

LI = {
    LVL_GROUNDS: LvlInfo("Peach's Castle",(135,206,235),0,Vec3f(0,200,600)),
    LVL_INSIDE:  LvlInfo("Castle Interior",(60,60,80),0,Vec3f(0,50,0)),
    LVL_BOB:     LvlInfo("Bob-omb Battlefield",(135,206,235),7,Vec3f(0,200,800)),
    LVL_WF:      LvlInfo("Whomp's Fortress",(150,200,240),7,Vec3f(0,200,800)),
    LVL_JRB:     LvlInfo("Jolly Roger Bay",(80,140,200),7,Vec3f(0,200,800)),
    LVL_CCM:     LvlInfo("Cool, Cool Mountain",(200,220,255),7,Vec3f(0,1200,-1000)),
    LVL_BBH:     LvlInfo("Big Boo's Haunt",(30,20,50),7,Vec3f(0,200,800)),
    LVL_HMC:     LvlInfo("Hazy Maze Cave",(50,40,30),7,Vec3f(0,200,800)),
    LVL_LLL:     LvlInfo("Lethal Lava Land",(80,30,10),7,Vec3f(0,200,0)),
    LVL_SSL:     LvlInfo("Shifting Sand Land",(230,200,140),7,Vec3f(0,200,800)),
    LVL_DDD:     LvlInfo("Dire, Dire Docks",(20,40,100),7,Vec3f(0,200,800)),
    LVL_SL:      LvlInfo("Snowman's Land",(180,200,240),7,Vec3f(0,200,800)),
    LVL_WDW:     LvlInfo("Wet-Dry World",(170,190,220),7,Vec3f(0,1000,800)),
    LVL_TTM:     LvlInfo("Tall, Tall Mountain",(130,190,230),7,Vec3f(0,2000,0)),
    LVL_THI:     LvlInfo("Tiny-Huge Island",(135,206,235),7,Vec3f(0,200,800)),
    LVL_TTC:     LvlInfo("Tick Tock Clock",(40,30,50),7,Vec3f(0,200,0)),
    LVL_RR:      LvlInfo("Rainbow Ride",(100,80,180),7,Vec3f(0,200,0)),
    LVL_B1:      LvlInfo("Bowser Dark World",(10,10,30),1,Vec3f(0,200,800)),
    LVL_B2:      LvlInfo("Bowser Fire Sea",(40,10,10),1,Vec3f(0,200,800)),
    LVL_B3:      LvlInfo("Bowser in the Sky",(50,40,80),1,Vec3f(0,200,800)),
    LVL_SA:      LvlInfo("Secret Aquarium",(20,60,120),1,Vec3f(0,200,0)),
    LVL_PSS:     LvlInfo("Princess's Secret Slide",(80,60,120),2,Vec3f(0,1200,0)),
    LVL_TOTWC:   LvlInfo("Tower of the Wing Cap",(100,160,255),1,Vec3f(0,200,0)),
    LVL_COTMC:   LvlInfo("Cavern of the Metal Cap",(30,60,30),1,Vec3f(0,200,800)),
    LVL_VCUTM:   LvlInfo("Vanish Cap Under Moat",(40,40,80),1,Vec3f(0,200,800)),
    LVL_WMOTR:   LvlInfo("Wing Mario Over Rainbow",(150,100,220),1,Vec3f(0,200,0)),
    LVL_COURT:   LvlInfo("Castle Courtyard",(80,100,80),0,Vec3f(0,50,400)),
}

CATS = [
    ("— Castle —",[LVL_GROUNDS,LVL_INSIDE,LVL_COURT]),
    ("— Courses 1-4 —",[LVL_BOB,LVL_WF,LVL_JRB,LVL_CCM]),
    ("— Courses 5-9 —",[LVL_BBH,LVL_HMC,LVL_LLL,LVL_SSL,LVL_DDD]),
    ("— Courses 10-15 —",[LVL_SL,LVL_WDW,LVL_TTM,LVL_THI,LVL_TTC,LVL_RR]),
    ("— Bowser —",[LVL_B1,LVL_B2,LVL_B3]),
    ("— Secrets —",[LVL_SA,LVL_PSS,LVL_TOTWC,LVL_COTMC,LVL_VCUTM,LVL_WMOTR]),
]

# ============================================================================
#  LEVEL BUILDERS — ALL 27 LEVELS
# ============================================================================
def load_level(lid):
    global surfs, objs, cur_lvl, cur_name
    surfs=[]; objs=[]; cur_lvl=lid
    info=LI.get(lid,LI[0]); cur_name=info.name
    _builders.get(lid, _b_grounds)()

def _b_grounds():
    surfs.append(make_ground(0,0,4000,4000,0,(34,180,34)))
    surfs.append(make_ground(0,-400,-50,1200,400,(40,80,200),SURF_WATER))
    surfs.extend(make_box(0,10,-350,250,20,500,(139,90,43)))
    surfs.extend(make_box(0,250,-900,900,500,300,(225,215,195)))
    surfs.extend(make_box(-550,300,-850,200,600,200,(210,200,180)))
    surfs.extend(make_box(550,300,-850,200,600,200,(210,200,180)))
    surfs.extend(make_box(0,550,-900,250,400,200,(230,220,200)))
    surfs.extend(make_box(-550,630,-850,150,60,150,(180,40,40)))
    surfs.extend(make_box(550,630,-850,150,60,150,(180,40,40)))
    surfs.extend(make_box(0,780,-900,180,60,150,(180,40,40)))
    surfs.extend(make_box(-1200,80,-400,400,160,400,(50,160,50)))
    surfs.extend(make_box(1200,80,-400,400,160,400,(50,160,50)))
    objs.extend(sp_ring(0,20,400,200,8))
    for tx,tz in [(-600,400),(600,400),(-900,-200),(900,-200)]:
        objs.append(sp_tree(tx,0,tz))
    objs.append(sp_pipe(0,10,-600,LVL_INSIDE))
    objs.append(sp_1up(-1200,180,-400))

def _b_inside():
    surfs.append(make_ground(0,0,0,2000,3000,(180,160,130)))
    surfs.extend(make_box(0,300,-1500,2000,600,20,(160,140,110)))
    surfs.extend(make_box(-1000,300,0,20,600,3000,(160,140,110)))
    surfs.extend(make_box(1000,300,0,20,600,3000,(160,140,110)))
    surfs.extend(make_box(0,300,1500,2000,600,20,(160,140,110)))
    surfs.extend(make_box(0,5,0,200,5,2000,(180,30,30)))
    surfs.extend(make_stairs(0,0,-1200,8,400,40,60,(0,-1),(170,150,120)))
    surfs.extend(make_box(0,350,-1300,800,20,200,(190,170,140)))
    pipes=[(-800,-400,LVL_BOB),(-800,-800,LVL_WF),(-800,0,LVL_JRB),(800,-400,LVL_CCM),
           (800,0,LVL_BBH),(0,1200,LVL_HMC),(-400,1200,LVL_LLL),(400,1200,LVL_SSL),
           (-600,1200,LVL_DDD),(-800,-1300,LVL_SL),(-400,-1300,LVL_WDW),(0,-1300,LVL_TTM),
           (400,-1300,LVL_THI),(800,-1300,LVL_TTC),(0,-1400,LVL_RR),
           (-200,-1400,LVL_B1),(200,-1400,LVL_B2),(0,-1500,LVL_B3),
           (600,-1200,LVL_PSS),(-600,-1400,LVL_SA),(0,1400,LVL_GROUNDS)]
    for px,pz,tgt in pipes:
        y=0 if abs(pz)<1250 else 360
        objs.append(sp_pipe(px,y,pz,tgt))
    objs.extend(sp_line(-500,10,-200,100,0,0,6))

def _b_court():
    surfs.append(make_ground(0,0,0,1200,1200,(80,130,80)))
    for w in [(-600,1200,20),(600,1200,20)]:
        surfs.extend(make_box(0,150,w[0] if w[2]==20 else 0,w[0] if w[2]!=20 else 1200,300,w[2] if w[2]==20 else 1200,(120,120,120)))
    surfs.extend(make_box(0,150,-600,1200,300,20,(120,120,120)))
    surfs.extend(make_box(0,150,600,1200,300,20,(120,120,120)))
    surfs.extend(make_box(-600,150,0,20,300,1200,(120,120,120)))
    surfs.extend(make_box(600,150,0,20,300,1200,(120,120,120)))
    for bx,bz in [(-200,-200),(200,-200),(0,200),(-300,100),(300,100)]:
        objs.append(sp_boo(bx,50,bz))
    objs.append(sp_star(0,100,-400,0))
    objs.append(sp_pipe(0,0,550,LVL_INSIDE))

def _b_bob():
    surfs.append(make_ground(0,0,0,4000,4000,(90,160,50)))
    for i in range(8):
        w=1000-i*110
        surfs.extend(make_box(0,50+i*120,-1200,w,120,w,(139-i*5,100-i*3,50)))
    surfs.extend(make_box(0,1050,-1200,250,20,250,(160,120,60)))
    surfs.extend(make_box(0,40,-400,120,10,600,(160,120,80)))
    surfs.extend(make_box(-600,0,400,400,10,400,(70,140,50)))
    surfs.extend(make_box(500,20,0,200,40,800,(120,100,70)))
    surfs.extend(make_box(800,600,-800,300,40,300,(90,160,90)))
    objs.append(sp_goomba(-200,0,300)); objs.append(sp_goomba(200,0,300))
    objs.append(sp_goomba(-100,0,600)); objs.append(sp_bobomb(-400,0,600))
    objs.append(sp_chomp(-600,0,400)); objs.append(sp_koopa(500,60,200))
    king=sp_bobomb(0,1070,-1200); king.type=ObjType.KING_BOB; king.hp=3; king.radius=80
    king.color=(40,40,40); king.scale=2.0; king.irange=100; objs.append(king)
    objs.append(sp_star(0,1120,-1200,0)); objs.append(sp_star(500,80,-200,1))
    objs.append(sp_star(800,660,-800,2)); objs.append(sp_star(-600,50,600,5))
    objs.extend(sp_ring(0,30,200,150,8))
    for rx,rz in [(-300,-300),(300,-300),(-300,600),(300,600),(-700,0),(700,0),(0,-800),(0,800)]:
        objs.append(sp_coin(rx,30,rz,ObjType.COIN_RED))
    objs.append(sp_1up(-1000,30,600))
    for tx,tz in [(-1000,600),(1000,600),(-800,-400),(800,-400)]:
        objs.append(sp_tree(tx,0,tz))

def _b_wf():
    surfs.append(make_ground(0,0,0,3000,3000,(160,160,170)))
    surfs.extend(make_box(0,150,-400,1000,300,800,(185,185,190)))
    surfs.extend(make_box(0,400,-400,700,200,600,(175,175,180)))
    surfs.extend(make_box(0,550,-400,500,20,400,(195,195,200)))
    surfs.extend(make_stairs(-500,0,-200,6,200,50,80,(0,-1),(180,180,185)))
    surfs.extend(make_box(600,300,0,200,20,200,(160,160,180)))
    surfs.extend(make_box(800,400,200,150,20,150,(160,160,180)))
    surfs.extend(make_box(600,500,400,180,20,180,(160,160,180)))
    surfs.extend(make_box(-500,200,-600,250,20,250,(150,150,160)))
    surfs.extend(make_box(0,650,-500,150,200,150,(190,190,195)))
    objs.append(sp_thwomp(0,350,-200)); objs.append(sp_piranha(-500,220,-600))
    objs.append(sp_goomba(300,0,300)); objs.append(sp_goomba(-300,0,500))
    objs.append(sp_star(0,770,-500,0)); objs.append(sp_star(600,540,400,1))
    objs.extend(sp_ring(0,170,-400,200,8))
    for rx,rz in [(-400,300),(400,300),(-200,-800),(200,-800),(-600,-200),(600,-200),(0,600),(0,-600)]:
        objs.append(sp_coin(rx,30,rz,ObjType.COIN_RED))

def _b_jrb():
    surfs.append(make_ground(0,-300,0,4000,4000,(60,100,140),SURF_WATER))
    surfs.append(make_ground(0,0,800,2000,800,(180,170,130)))
    surfs.extend(make_box(-800,100,600,400,200,400,(140,130,100)))
    surfs.extend(make_box(0,-250,-800,600,100,400,(80,100,120)))
    surfs.extend(make_box(0,-100,-400,400,150,150,(100,70,40)))
    surfs.extend(make_box(0,0,-400,300,20,120,(110,80,50)))
    objs.append(sp_goomba(-200,0,900)); objs.append(sp_koopa(0,0,1000))
    objs.append(sp_star(0,50,-400,0)); objs.append(sp_star(0,-230,-800,1))
    objs.append(sp_star(-800,220,600,3))
    objs.extend(sp_ring(0,-250,-600,150,8))

def _b_ccm():
    surfs.append(make_ground(0,0,0,4000,4000,(240,245,255)))
    surfs.append(make_slope(-1000,1200,-1500,1000,0,1500,2000,(225,235,255),SURF_SLIP))
    surfs.extend(make_box(0,1250,-1500,500,100,500,(210,220,240)))
    surfs.extend(make_box(0,1350,-1500,300,200,300,(100,60,30)))
    surfs.extend(make_box(0,50,1200,250,150,200,(90,55,25)))
    surfs.extend(make_box(500,600,0,100,10,800,(200,220,255),SURF_SLIP))
    surfs.extend(make_box(-600,200,500,250,20,250,(235,240,250)))
    surfs.extend(make_box(-600,350,500,200,200,200,(255,255,255)))
    objs.append(sp_goomba(200,1260,-1400)); objs.append(sp_goomba(0,10,600))
    objs.append(sp_star(0,100,1200,0)); objs.append(sp_star(0,1380,-1500,1))
    objs.append(sp_star(-600,540,500,2)); objs.append(sp_star(500,650,400,3))
    objs.extend(sp_ring(0,1270,-1500,200,8))
    for rx,rz in [(-300,-500),(300,-500),(-500,200),(500,200),(-200,800),(200,800),(-600,-200),(600,-200)]:
        objs.append(sp_coin(rx,30,rz,ObjType.COIN_RED))

def _b_bbh():
    surfs.append(make_ground(0,0,0,3000,3000,(50,60,40)))
    surfs.extend(make_box(0,300,-600,1000,600,800,(80,70,90)))
    surfs.extend(make_box(0,650,-600,1100,50,900,(60,50,70)))
    surfs.extend(make_box(0,50,-600,800,100,600,(100,90,80)))
    surfs.extend(make_box(0,300,-600,800,20,600,(95,85,75)))
    surfs.extend(make_box(0,450,-200,500,20,200,(85,75,65)))
    surfs.extend(make_box(500,-80,-800,300,20,300,(75,65,55)))
    for bx,bz in [(-200,200),(200,200),(-300,-300),(300,-300),(0,-400)]:
        objs.append(sp_boo(bx,100,bz))
    bb=sp_boo(0,150,-600); bb.type=ObjType.BIG_BOO; bb.hp=3; bb.radius=100; bb.scale=2.0
    bb.color=(240,240,255); objs.append(bb)
    objs.append(sp_star(0,500,-600,0)); objs.append(sp_star(0,350,-600,1))
    objs.append(sp_star(0,700,-600,2)); objs.append(sp_star(500,-50,-800,4))
    objs.extend(sp_ring(0,60,-400,150,8))

def _b_hmc():
    surfs.append(make_ground(0,0,0,3000,4000,(80,70,55)))
    surfs.extend(make_box(0,600,0,3000,20,4000,(60,50,40)))
    surfs.extend(make_box(0,100,0,600,200,600,(100,90,75)))
    for wx,wz in [(-300,-200),(-300,-600),(0,-400),(300,-200),(300,-600)]:
        surfs.extend(make_box(wx,100,wz,20,200,200,(70,60,50)))
    surfs.append(make_ground(600,-100,800,800,600,(40,60,120),SURF_WATER))
    surfs.extend(make_box(600,-80,800,200,20,200,(100,140,100)))
    surfs.extend(make_box(-800,100,-400,200,400,200,(85,75,60)))
    objs.append(sp_goomba(-200,10,300)); objs.append(sp_goomba(200,10,300))
    objs.append(sp_goomba(0,10,-500))
    objs.append(sp_star(0,200,0,0)); objs.append(sp_star(-800,350,-400,1))
    objs.append(sp_star(600,-50,800,2)); objs.append(sp_star(0,10,-900,3))
    objs.extend(sp_ring(0,120,0,200,8))

def _b_lll():
    surfs.append(make_ground(0,-50,0,4000,4000,(200,40,0),SURF_LAVA))
    surfs.extend(make_box(0,20,0,500,40,500,(80,80,80)))
    for i in range(6):
        w=700-i*100
        surfs.extend(make_box(0,50+i*100,-800,w,100,w,(120-i*8,50-i*3,40-i*3)))
    surfs.extend(make_box(0,700,-800,200,20,200,(100,60,40)))
    for px,pz in [(-300,300),(-500,100),(-700,-100),(-500,-300)]:
        surfs.extend(make_box(px,20,pz,100,20,100,(90,90,90)))
    surfs.extend(make_box(600,30,600,200,20,200,(100,100,100)))
    surfs.extend(make_box(-700,20,-600,400,20,400,(70,70,75)))
    objs.append(sp_bully(-700,40,-600)); objs.append(sp_bully(-600,40,-500))
    bb=sp_bully(-700,40,-700); bb.hp=5; bb.radius=70; bb.scale=1.5; objs.append(bb)
    objs.append(sp_star(0,740,-800,0)); objs.append(sp_star(-700,60,-700,1))
    objs.append(sp_star(600,60,600,3)); objs.append(sp_star(600,60,-500,4))
    objs.extend(sp_ring(0,40,0,180,8))
    for rx,rz in [(-300,300),(-500,100),(-700,-100),(-500,-300),(400,-300),(600,-500),(600,600),(-700,-600)]:
        objs.append(sp_coin(rx,50,rz,ObjType.COIN_RED))

def _b_ssl():
    surfs.append(make_ground(0,0,0,4000,4000,(220,190,130),SURF_SAND))
    for i in range(8):
        w=1200-i*140
        surfs.extend(make_box(0,i*120,-600,w,120,w,(200-i*5,170-i*5,100-i*3)))
    surfs.extend(make_box(0,1020,-600,150,60,150,(210,180,110)))
    surfs.append(make_ground(-800,-30,600,400,400,(40,100,180),SURF_WATER))
    surfs.extend(make_box(-800,0,600,500,10,500,(60,140,60)))
    surfs.append(make_ground(800,-100,-600,600,600,(200,180,100),SURF_DEATH))
    surfs.extend(make_box(-600,300,-200,200,20,200,(180,160,100)))
    objs.append(sp_goomba(-200,10,400)); objs.append(sp_goomba(200,10,400))
    objs.append(sp_star(0,1060,-600,0)); objs.append(sp_star(-800,20,600,1))
    objs.append(sp_star(-600,340,-200,2)); objs.append(sp_star(0,500,-600,3))
    objs.extend(sp_ring(0,30,0,300,8))

def _b_ddd():
    surfs.append(make_ground(0,-400,0,4000,4000,(30,50,100),SURF_WATER))
    surfs.append(make_ground(0,0,800,2000,800,(120,110,100)))
    surfs.extend(make_box(0,-350,-400,300,100,800,(40,60,110)))
    surfs.extend(make_box(-500,-300,-600,400,200,400,(80,80,90)))
    surfs.extend(make_box(500,-200,-400,400,100,300,(90,90,100)))
    surfs.extend(make_box(500,-150,-400,300,80,150,(60,60,70)))
    surfs.extend(make_box(0,-350,-1000,400,20,400,(50,70,120)))
    objs.append(sp_star(500,-120,-400,0)); objs.append(sp_star(0,-330,-1000,1))
    objs.append(sp_star(-500,-200,-600,2)); objs.append(sp_star(0,50,800,4))
    objs.extend(sp_ring(0,-350,-600,150,8))

def _b_sl():
    surfs.append(make_ground(0,0,0,4000,4000,(230,240,255)))
    for i in range(6):
        w=800-i*120
        surfs.extend(make_box(0,i*150,-800,w,150,w,(245,248,255)))
    surfs.extend(make_box(0,1000,-800,300,300,300,(255,255,255)))
    surfs.extend(make_box(-600,50,400,400,100,400,(180,210,255),SURF_ICE))
    surfs.extend(make_box(600,50,400,250,150,250,(220,230,250)))
    surfs.append(make_ground(0,-10,600,500,500,(160,200,255),SURF_ICE))
    surfs.extend(make_box(0,50,-200,100,10,400,(200,200,210)))
    surfs.extend(make_box(-600,80,-400,300,20,300,(210,220,240)))
    objs.append(sp_bully(-600,100,-400)); objs.append(sp_goomba(300,10,300))
    objs.append(sp_star(0,1150,-800,0)); objs.append(sp_star(-600,120,-400,1))
    objs.append(sp_star(-600,170,400,2)); objs.append(sp_star(600,100,400,3))
    objs.extend(sp_ring(0,30,200,200,8))

def _b_wdw():
    surfs.append(make_ground(0,-200,0,3000,3000,(60,100,180),SURF_WATER))
    surfs.extend(make_box(-400,200,-400,300,400,300,(180,180,190)))
    surfs.extend(make_box(400,300,-400,250,600,250,(170,170,185)))
    surfs.extend(make_box(-400,150,400,350,300,350,(175,175,185)))
    surfs.extend(make_box(400,100,400,200,200,200,(185,185,195)))
    surfs.extend(make_box(0,500,0,100,20,100,(200,200,255)))
    surfs.extend(make_box(0,100,0,1500,20,100,(160,160,170)))
    surfs.extend(make_box(0,100,0,100,20,1500,(160,160,170)))
    surfs.extend(make_box(0,-180,-1000,1000,20,500,(140,140,150)))
    objs.append(sp_goomba(-200,210,-300)); objs.append(sp_amp(0,300,-400,150))
    objs.append(sp_star(-400,420,-400,0)); objs.append(sp_star(400,620,-400,1))
    objs.append(sp_star(0,540,0,2)); objs.append(sp_star(0,-160,-1000,3))
    objs.extend(sp_ring(0,120,0,200,8))

def _b_ttm():
    surfs.append(make_ground(0,0,0,3000,3000,(100,140,80)))
    for i in range(10):
        w=1500-i*130
        surfs.extend(make_box(0,i*200,0,w,200,w,(120+i*3,100+i*3,70+i*2)))
    surfs.extend(make_box(0,2050,0,300,50,300,(140,120,90)))
    for mx,my,mz,mr in [(-500,800,400,100),(-700,600,200,80),(-400,400,600,120)]:
        surfs.extend(make_box(mx,my,mz,mr*2,20,mr*2,(200,60,60)))
        surfs.extend(make_box(mx,my-60,mz,30,80,30,(180,170,140)))
    surfs.extend(make_box(400,800,-300,60,1000,60,(80,140,220)))
    objs.append(sp_goomba(-200,10,400)); objs.append(sp_goomba(300,600,200))
    objs.append(sp_koopa(0,2060,0))
    objs.append(sp_star(0,2100,0,0)); objs.append(sp_star(-500,840,400,2))
    objs.append(sp_star(-400,440,600,3)); objs.append(sp_star(400,1350,-300,4))
    objs.extend(sp_ring(0,2070,0,120,8))

def _b_thi():
    surfs.append(make_ground(0,0,0,4000,4000,(90,160,70)))
    surfs.append(make_ground(0,-50,0,800,800,(40,80,180),SURF_WATER))
    surfs.extend(make_box(-600,150,-600,500,300,500,(100,150,70)))
    surfs.extend(make_box(600,100,-600,400,200,400,(105,155,75)))
    surfs.extend(make_box(0,10,800,800,20,400,(200,180,140)))
    surfs.extend(make_box(-800,30,0,100,60,100,(0,180,0)))
    surfs.extend(make_box(800,30,0,100,60,100,(0,180,0)))
    objs.append(sp_piranha(-300,0,300)); objs.append(sp_piranha(300,0,300))
    g=sp_goomba(200,10,600); g.radius=70; g.scale=2.0; objs.append(g)
    objs.append(sp_koopa(600,30,800))
    objs.append(sp_star(-600,320,-600,0)); objs.append(sp_star(600,220,-600,1))
    objs.append(sp_star(0,100,800,2)); objs.append(sp_star(-800,60,0,4))
    objs.extend(sp_ring(0,30,400,200,8))

def _b_ttc():
    plats=[(0,0,0,400),(-200,200,100,200),(200,400,-100,200),(0,600,200,250),
           (-150,800,-200,200),(150,1000,100,200),(0,1200,-100,300),(-200,1400,200,200),
           (200,1600,0,200),(0,1800,-200,250),(-100,2000,100,200),(100,2200,-100,200),(0,2400,0,300)]
    for px,py,pz,pw in plats:
        c=_cc((160+py//20,140+py//30,100+py//25))
        surfs.extend(make_box(px,py,pz,pw,20,pw if pw<300 else 200,c))
    surfs.extend(make_box(0,500,0,300,10,20,(120,120,130)))
    surfs.extend(make_box(0,1100,0,20,10,250,(120,120,130)))
    objs.append(sp_amp(0,400,0,200)); objs.append(sp_amp(0,1000,0,150))
    objs.append(sp_goomba(-200,220,100)); objs.append(sp_thwomp(0,1400,-100))
    objs.append(sp_star(0,2450,0,0)); objs.append(sp_star(-100,2040,100,1))
    objs.append(sp_star(150,1640,0,2)); objs.append(sp_star(-150,840,-200,3))
    for i,(px,py,pz,_) in enumerate(plats):
        if i%2==0: objs.append(sp_coin(px,py+40,pz))
    for rx,ry,rz in [(-200,240,100),(200,440,-100),(0,640,200),(-150,840,-200),
                     (150,1040,100),(0,1240,-100),(-200,1440,200),(200,1640,0)]:
        objs.append(sp_coin(rx,ry,rz,ObjType.COIN_RED))

def _b_rr():
    surfs.extend(make_box(0,0,0,400,20,400,(200,180,220)))
    rc=[(255,80,80),(255,165,80),(255,255,80),(80,255,80),(80,80,255),(180,80,255)]
    for i in range(18):
        a=i*30; d=300+i*100; px=d*sins(a); pz=d*coss(a); py=100+i*80
        surfs.extend(make_box(px,py,pz,150,20,150,rc[i%6]))
    surfs.extend(make_box(800,1200,-800,400,100,200,(120,80,40)))
    surfs.extend(make_box(-600,1000,-400,300,200,300,(200,180,160)))
    surfs.extend(make_box(-600,1130,-400,320,60,320,(180,60,40)))
    for j in range(5):
        surfs.extend(make_box(-300+j*150,600+j*50,400,120,20,120,_cc((180+j*10,160+j*10,200))))
    objs.append(sp_goomba(0,30,200)); objs.append(sp_amp(400,500,0,180))
    objs.append(sp_star(800,1360,-800,0)); objs.append(sp_star(-600,1120,-400,1))
    objs.append(sp_star(0,1600,0,2)); objs.append(sp_star(-300,850,400,3))
    objs.extend(sp_ring(0,40,0,150,8))
    for i in range(8):
        a=i*45; objs.append(sp_coin(300*sins(a),800+i*30,300*coss(a),ObjType.COIN_RED))

def _b_b1():
    surfs.append(make_ground(0,-200,0,4000,4000,(180,30,0),SURF_LAVA))
    path=[(0,0,0),(300,50,300),(600,100,200),(800,150,500),(600,200,800),
          (300,250,900),(0,300,700),(-300,350,500),(-500,400,300),(-300,450,0),
          (0,500,-300),(300,550,-500),(0,600,-700)]
    for px,py,pz in path:
        surfs.extend(make_box(px,py,pz,200,20,200,(70+py//10,50+py//15,90+py//10)))
    surfs.extend(make_box(0,650,-1000,600,20,600,(80,40,40)))
    objs.append(sp_goomba(300,70,300)); objs.append(sp_amp(0,300,700,150))
    bw=Obj(ObjType.BOWSER,Vec3f(0,680,-1000),radius=100,height=150,color=(20,120,20),irange=120,dmg=3,hp=1)
    bw.home=Vec3f(0,680,-1000); bw.spd=2.0; objs.append(bw)
    objs.append(sp_star(0,730,-1000,0))
    for px,py,pz in path[::2]: objs.append(sp_coin(px,py+40,pz))

def _b_b2():
    surfs.append(make_ground(0,-200,0,4000,4000,(200,50,0),SURF_LAVA))
    for i in range(15):
        a=i*25; d=200+i*100; px=d*sins(a); pz=d*coss(a); py=i*60
        surfs.extend(make_box(px,py,pz,180,20,180,(100,60,40)))
    surfs.extend(make_box(0,500,-500,250,20,250,(110,70,50)))
    surfs.extend(make_box(0,900,-1200,600,20,600,(90,50,40)))
    objs.append(sp_goomba(100,80,100)); objs.append(sp_bully(0,520,-500))
    bw=Obj(ObjType.BOWSER,Vec3f(0,930,-1200),radius=100,height=150,color=(20,130,20),irange=120,dmg=3,hp=1)
    bw.home=Vec3f(0,930,-1200); bw.spd=2.0; objs.append(bw)
    objs.append(sp_star(0,980,-1200,0)); objs.extend(sp_ring(0,920,-1200,200,8))

def _b_b3():
    surfs.append(make_ground(0,-500,0,100,100,(0,0,0),SURF_DEATH))
    path=[(0,0,0),(300,100,200),(500,200,500),(300,300,800),(0,400,1000),
          (-300,500,800),(-500,600,500),(-300,700,200),(0,800,0),(300,900,-300),
          (500,1000,-600),(300,1100,-900),(0,1200,-1100),(-200,1300,-1300),(0,1400,-1500)]
    for px,py,pz in path:
        surfs.extend(make_box(px,py,pz,200,20,200,_cc((80+py//20,60+py//25,100+py//15))))
    surfs.extend(make_box(0,1500,-1800,800,30,800,(100,80,120)))
    objs.append(sp_goomba(300,120,200)); objs.append(sp_goomba(-300,520,800))
    objs.append(sp_amp(0,600,500,200)); objs.append(sp_thwomp(0,1000,-600))
    bw=Obj(ObjType.BOWSER,Vec3f(0,1540,-1800),radius=120,height=180,color=(30,150,30),irange=150,dmg=3,hp=3)
    bw.home=Vec3f(0,1540,-1800); bw.spd=2.5; bw.scale=1.5; objs.append(bw)
    objs.append(sp_star(0,1600,-1800,0))
    for px,py,pz in path[::2]: objs.append(sp_coin(px,py+40,pz))

def _b_sa():
    surfs.append(make_ground(0,-400,0,1500,1500,(30,60,130),SURF_WATER))
    surfs.extend(make_box(0,0,0,600,20,600,(100,130,160)))
    objs.append(sp_star(0,50,0,0))
    for _ in range(20):
        objs.append(sp_coin(random.randint(-500,500),random.randint(-300,-50),random.randint(-500,500)))

def _b_pss():
    pts=[(0,1200,0),(200,1000,200),(0,800,400),(-200,600,200),(0,400,0),(200,200,-200),(0,0,-400)]
    for i in range(len(pts)-1):
        p1,p2=pts[i],pts[i+1]
        surfs.append(make_slope(p1[0],p1[1],p1[2],p2[0],p2[1],p2[2],200,(140,100,180),SURF_SLIP))
    surfs.extend(make_box(0,1220,0,300,40,300,(150,110,190)))
    surfs.extend(make_box(0,10,-400,300,20,300,(160,120,200)))
    objs.append(sp_star(0,50,-400,0)); objs.append(sp_star(0,50,-300,1))
    for p in pts: objs.append(sp_coin(p[0],p[1]+30,p[2]))

def _b_totwc():
    surfs.extend(make_box(0,0,0,200,20,200,(200,180,220)))
    for i in range(8):
        a=i*45; surfs.extend(make_box(500*sins(a),-100,500*coss(a),150,20,150,(180,200,255)))
    for i in range(8):
        a=i*45; objs.append(sp_coin(400*sins(a),50,400*coss(a),ObjType.COIN_RED))
    objs.append(sp_star(0,50,0,0)); objs.extend(sp_ring(0,30,0,200,8))

def _b_cotmc():
    surfs.append(make_ground(0,0,0,2000,3000,(50,70,50)))
    surfs.append(make_ground(0,-30,0,200,3000,(40,80,150),SURF_WATER))
    for i in range(8):
        surfs.extend(make_box(-300,30,-1000+i*300,200,30,100,(60,80,60)))
    surfs.extend(make_box(0,50,-1200,100,50,100,(0,200,0)))
    objs.append(sp_star(0,80,-1200,0)); objs.extend(sp_line(-300,50,-800,0,0,150,6))

def _b_vcutm():
    surfs.append(make_slope(0,400,-500,0,0,500,300,(60,60,100),SURF_SLIP))
    surfs.extend(make_box(0,420,-500,400,40,300,(70,70,110)))
    surfs.extend(make_box(0,10,500,400,20,300,(65,65,105)))
    for i in range(6):
        surfs.extend(make_box(-200+i*80,200-i*30,0,100,20,100,(80,80,120)))
    surfs.extend(make_box(0,50,800,100,50,100,(100,100,200)))
    objs.append(sp_star(0,80,800,0)); objs.extend(sp_ring(0,220,-200,150,8))

def _b_wmotr():
    surfs.extend(make_box(0,0,0,300,20,300,(180,160,220)))
    rc=[(255,80,80),(255,165,80),(255,255,80),(80,255,80),(80,80,255),(180,80,255)]
    for i in range(12):
        a=i*30; d=300+i*80; surfs.extend(make_box(d*sins(a),50+i*60,d*coss(a),120,15,120,rc[i%6]))
    for cx,cy,cz in [(500,400,0),(-400,500,-300),(0,600,-600)]:
        surfs.extend(make_box(cx,cy,cz,200,30,200,(240,240,255)))
    objs.append(sp_star(0,650,-600,0))
    for i in range(8):
        a=i*45; objs.append(sp_coin(350*sins(a),200+i*30,350*coss(a),ObjType.COIN_RED))
    objs.extend(sp_ring(0,40,0,120,8))

_builders={
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
def find_floor(x,y,z):
    h=-11000.0; fl=None
    for s in surfs:
        mnx=min(v.x for v in s.verts)-10; mxx=max(v.x for v in s.verts)+10
        mnz=min(v.z for v in s.verts)-10; mxz=max(v.z for v in s.verts)+10
        if x<mnx or x>mxx or z<mnz or z>mxz: continue
        ny=s.normal.y
        if abs(ny)<0.01: continue
        p1=s.verts[0]; nx,nz=s.normal.x,s.normal.z
        d=-(x*nx+z*nz-(nx*p1.x+ny*p1.y+nz*p1.z))
        sy=d/ny
        if h<sy<=y+150: h=sy; fl=s
    return h,fl

def find_wall(x,y,z,dx,dz):
    tx,tz=x+dx*2,z+dz*2
    for s in surfs:
        ny=s.normal.y
        if abs(ny)>0.7: continue
        mny=min(v.y for v in s.verts)-10; mxy=max(v.y for v in s.verts)+10
        if y<mny or y>mxy: continue
        p1=s.verts[0]; nx,nz=s.normal.x,s.normal.z
        d1=(x-p1.x)*nx+(z-p1.z)*nz
        d2=(tx-p1.x)*nx+(tz-p1.z)*nz
        if d1>0 and d2<=0: return s
    return None

# ============================================================================
#  PHYSICS STEPS
# ============================================================================
def update_air(m):
    m.fvel*=AIR_DRAG
    m.vel.x=m.fvel*sins(m.face.y); m.vel.z=m.fvel*coss(m.face.y)
    m.vel.y+=GRAVITY
    if m.vel.y<MAX_FALL: m.vel.y=MAX_FALL

def set_fvel(m,s):
    m.fvel=s; m.vel.x=s*sins(m.face.y); m.vel.z=s*coss(m.face.y)

def ground_step(m):
    m.pos.x+=m.vel.x; m.pos.z+=m.vel.z
    fy,fl=find_floor(m.pos.x,m.pos.y+100,m.pos.z)
    m.floor=fl; m.floor_y=fy
    if m.pos.y>fy+10: return 'air'
    m.pos.y=fy; return 'ground'

def air_step(m):
    qx,qy,qz=m.vel.x/4,m.vel.y/4,m.vel.z/4
    for _ in range(4):
        m.pos.x+=qx; m.pos.y+=qy; m.pos.z+=qz
        fy,fl=find_floor(m.pos.x,m.pos.y,m.pos.z)
        m.floor=fl; m.floor_y=fy
        if m.pos.y<=fy: m.pos.y=fy; return 'land'
        w=find_wall(m.pos.x,m.pos.y+50,m.pos.z,sins(m.face.y),coss(m.face.y))
        if w: m.wall=w; m.vel.x=0; m.vel.z=0; m.fvel=0; return 'wall'
    return 'air'

# ============================================================================
#  ACTIONS
# ============================================================================
def a_idle(m,c):
    m.fvel=0; m.vel.x=m.vel.z=0
    if c.pressed&IN_A: m.jcount=0; return m.set_act(ACT_JUMP)
    if c.pressed&IN_Z: return m.set_act(ACT_CROUCH)
    if c.pressed&IN_B: return m.set_act(ACT_DIVE)
    if c.stick_mag>0: return m.set_act(ACT_WALKING)
    ground_step(m)

def a_walk(m,c):
    if c.pressed&IN_A:
        if m.fvel>10 and c.down&IN_Z_D: return m.set_act(ACT_LONG_JUMP)
        m.jtimer=5; m.jcount+=1
        if m.jcount>=3 and m.fvel>15: return m.set_act(ACT_TRIPLE)
        elif m.jcount>=2: return m.set_act(ACT_DBL_JUMP)
        return m.set_act(ACT_JUMP)
    if c.pressed&IN_B: return m.set_act(ACT_DIVE)
    if c.stick_mag==0: return m.set_act(ACT_DECEL)
    m.face.y=approach_angle(m.face.y,m.iyaw,11.25)
    tgt=c.stick_mag*MAX_WALK
    m.fvel=min(m.fvel+1.5,tgt) if m.fvel<tgt else max(m.fvel-1.0,tgt)
    set_fvel(m,m.fvel)
    if ground_step(m)=='air': m.set_act(ACT_FREEFALL)
    if m.jtimer>0: m.jtimer-=1
    else: m.jcount=0

def a_decel(m,c):
    if c.pressed&IN_A: return m.set_act(ACT_SIDEFLIP if m.fvel>8 else ACT_JUMP)
    if c.stick_mag>0: return m.set_act(ACT_WALKING)
    m.fvel=approach_f32(m.fvel,0,2.0); set_fvel(m,m.fvel)
    if abs(m.fvel)<0.5: m.set_act(ACT_IDLE)
    ground_step(m)

def a_crouch(m,c):
    m.fvel=0; m.vel.x=m.vel.z=0
    if not(c.down&IN_Z_D): return m.set_act(ACT_IDLE)
    if c.pressed&IN_A: return m.set_act(ACT_BACKFLIP)
    ground_step(m)

def a_jump(m,c):
    if m.atimer==0: m.vel.y=42.0+abs(m.fvel)*0.25; m.peak_y=m.pos.y
    if c.pressed&IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed&IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_WALKING if c.stick_mag>0 else ACT_IDLE)
    elif r=='wall': m.wktimer=5; m.set_act(ACT_FREEFALL)
    m.atimer+=1

def a_dbl(m,c):
    if m.atimer==0: m.vel.y=52.0+abs(m.fvel)*0.2; m.peak_y=m.pos.y
    if c.pressed&IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed&IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_WALKING if c.stick_mag>0 else ACT_IDLE)
    elif r=='wall': m.wktimer=5; m.set_act(ACT_FREEFALL)
    m.atimer+=1

def a_triple(m,c):
    if m.atimer==0: m.vel.y=69.0; m.peak_y=m.pos.y
    if c.pressed&IN_Z: return m.set_act(ACT_GROUND_POUND)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_WALKING if c.stick_mag>0 else ACT_IDLE)
    m.atimer+=1

def a_backflip(m,c):
    if m.atimer==0: m.vel.y=62.0; m.fvel=-10.0; set_fvel(m,m.fvel)
    update_air(m); r=air_step(m)
    if r=='land': m.fvel=0; m.set_act(ACT_IDLE)
    m.atimer+=1

def a_sideflip(m,c):
    if m.atimer==0: m.vel.y=62.0; m.face.y=(m.face.y+180)%360; m.fvel=8.0; set_fvel(m,m.fvel)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_IDLE)
    m.atimer+=1

def a_longjump(m,c):
    if m.atimer==0: m.vel.y=30.0; m.fvel=min(m.fvel*1.5,48.0); set_fvel(m,m.fvel)
    update_air(m); r=air_step(m)
    if r=='land': m.fvel=0; m.set_act(ACT_IDLE)
    m.atimer+=1

def a_freefall(m,c):
    if c.pressed&IN_A and m.wktimer>0:
        m.face.y=(m.face.y+180)%360; m.fvel=24.0; set_fvel(m,m.fvel)
        return m.set_act(ACT_WALLKICK)
    if c.pressed&IN_Z: return m.set_act(ACT_GROUND_POUND)
    if c.pressed&IN_B: return m.set_act(ACT_DIVE)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_WALKING if c.stick_mag>0 else ACT_IDLE)
    elif r=='wall': m.wktimer=5
    if m.wktimer>0: m.wktimer-=1
    m.atimer+=1

def a_wallkick(m,c):
    if m.atimer==0: m.vel.y=52.0
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_WALKING if c.stick_mag>0 else ACT_IDLE)
    m.atimer+=1

def a_dive(m,c):
    if m.atimer==0: m.vel.y=10.0; m.fvel=max(m.fvel,32.0); set_fvel(m,m.fvel)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_BELLY_SLIDE)
    m.atimer+=1

def a_belly(m,c):
    if c.pressed&IN_A: return m.set_act(ACT_JUMP)
    m.fvel=approach_f32(m.fvel,0,1.0); set_fvel(m,m.fvel)
    if abs(m.fvel)<1.0: m.set_act(ACT_IDLE)
    ground_step(m)

def a_gp(m,c):
    if m.astate==0:
        m.fvel=0; m.vel.x=m.vel.z=0; m.vel.y=0; m.atimer+=1
        if m.atimer>10: m.astate=1; m.vel.y=-60.0
    else:
        r=air_step(m)
        if r=='land': m.set_act(ACT_GP_LAND)

def a_gpl(m,c):
    m.atimer+=1
    if m.atimer>5:
        if c.pressed&IN_A: m.set_act(ACT_JUMP)
        elif c.stick_mag>0: m.set_act(ACT_WALKING)
        elif m.atimer>15: m.set_act(ACT_IDLE)

def a_knock(m,c):
    if m.atimer==0: m.vel.y=30.0; m.fvel=-20.0; set_fvel(m,m.fvel)
    update_air(m); r=air_step(m)
    if r=='land': m.fvel=0; m.set_act(ACT_IDLE)
    m.atimer+=1

def a_lava(m,c):
    if m.atimer==0: m.vel.y=60.0; m.fvel=0; m.vel.x=m.vel.z=0; m.take_dmg(0x100)
    update_air(m); r=air_step(m)
    if r=='land': m.set_act(ACT_IDLE)
    m.atimer+=1

def a_star(m,c):
    m.fvel=0; m.vel.x=m.vel.y=m.vel.z=0; m.atimer+=1
    if m.atimer>90: m.set_act(ACT_IDLE)

def a_death(m,c):
    m.fvel=0; m.vel.x=m.vel.z=0; m.vel.y=max(m.vel.y+GRAVITY,MAX_FALL); m.pos.y+=m.vel.y

ACT_MAP={
    ACT_IDLE:a_idle, ACT_WALKING:a_walk, ACT_DECEL:a_decel, ACT_CROUCH:a_crouch,
    ACT_JUMP:a_jump, ACT_DBL_JUMP:a_dbl, ACT_TRIPLE:a_triple, ACT_BACKFLIP:a_backflip,
    ACT_SIDEFLIP:a_sideflip, ACT_LONG_JUMP:a_longjump, ACT_WALLKICK:a_wallkick,
    ACT_FREEFALL:a_freefall, ACT_DIVE:a_dive, ACT_BELLY_SLIDE:a_belly,
    ACT_GROUND_POUND:a_gp, ACT_GP_LAND:a_gpl, ACT_KNOCKBACK:a_knock,
    ACT_LAVA_BOOST:a_lava, ACT_STAR_DANCE:a_star, ACT_DEATH:a_death,
}

# ============================================================================
#  OBJECT AI
# ============================================================================
def update_objs(mario,frame):
    for o in objs:
        if not o.active: continue
        if o.type in(ObjType.COIN,ObjType.COIN_RED,ObjType.COIN_BLUE):
            o.pos.y=o.home.y+30+math.sin(frame*0.08+o.bob)*10; o.angle=(o.angle+6)%360
        elif o.type==ObjType.STAR:
            o.pos.y=o.home.y+50+math.sin(frame*0.06+o.bob)*15; o.angle=(o.angle+3)%360
        elif o.type==ObjType.ONE_UP:
            o.pos.y=o.home.y+30+math.sin(frame*0.07+o.bob)*8
        elif o.type in(ObjType.GOOMBA,ObjType.BOBOMB,ObjType.KOOPA):
            dx=mario.pos.x-o.pos.x; dz=mario.pos.z-o.pos.z
            d=math.sqrt(dx*dx+dz*dz)
            if d<400 and d>0:
                o.pos.x+=(dx/d)*o.spd; o.pos.z+=(dz/d)*o.spd; o.angle=math.degrees(math.atan2(dx,dz))
            else:
                o.timer+=1
                if o.timer%120<60: o.pos.x+=o.spd*o.pdir
                else: o.pos.x-=o.spd*o.pdir
        elif o.type==ObjType.BULLY:
            dx=mario.pos.x-o.pos.x; dz=mario.pos.z-o.pos.z; d=math.sqrt(dx*dx+dz*dz)
            if d<200 and d>0:
                o.pos.x+=(dx/d)*o.spd*1.5; o.pos.z+=(dz/d)*o.spd*1.5
        elif o.type in(ObjType.BOO,ObjType.BIG_BOO):
            dx=mario.pos.x-o.pos.x; dz=mario.pos.z-o.pos.z; d=math.sqrt(dx*dx+dz*dz)
            facing=abs(math.degrees(math.atan2(dx,dz))-mario.face.y)<90
            if not facing and d<400 and d>0:
                o.pos.x+=(dx/d)*1.5; o.pos.z+=(dz/d)*1.5
            o.pos.y=o.home.y+math.sin(frame*0.04)*20
        elif o.type==ObjType.AMP:
            o.timer+=1; r=o.scale
            o.pos.x=o.home.x+r*sins(o.timer*3); o.pos.z=o.home.z+r*coss(o.timer*3)
        elif o.type==ObjType.THWOMP:
            dx=abs(mario.pos.x-o.pos.x); dz=abs(mario.pos.z-o.pos.z)
            if o.state==0:
                if dx<100 and dz<100: o.state=1; o.timer=0
            elif o.state==1:
                o.pos.y=approach_f32(o.pos.y,o.home.y-200,15)
                if o.pos.y<=o.home.y-195: o.state=2; o.timer=0
            elif o.state==2:
                o.timer+=1
                if o.timer>30: o.state=3
            elif o.state==3:
                o.pos.y=approach_f32(o.pos.y,o.home.y,3)
                if o.pos.y>=o.home.y-1: o.state=0
        elif o.type==ObjType.CHAIN_CHOMP:
            o.timer+=1
            if o.timer%90<20:
                dx=mario.pos.x-o.home.x; dz=mario.pos.z-o.home.z; d=math.sqrt(dx*dx+dz*dz)
                if d<300 and d>0:
                    o.pos.x=o.home.x+(dx/d)*100*(o.timer%90)/20
                    o.pos.z=o.home.z+(dz/d)*100*(o.timer%90)/20
            else:
                o.pos.x=approach_f32(o.pos.x,o.home.x,3)
                o.pos.z=approach_f32(o.pos.z,o.home.z,3)
        elif o.type==ObjType.PIRANHA:
            o.timer+=1; cy=o.timer%120
            if cy<30: o.pos.y=approach_f32(o.pos.y,o.home.y+60,3)
            elif cy>90: o.pos.y=approach_f32(o.pos.y,o.home.y-20,3)
        elif o.type in(ObjType.KING_BOB,ObjType.BOWSER):
            dx=mario.pos.x-o.pos.x; dz=mario.pos.z-o.pos.z; d=math.sqrt(dx*dx+dz*dz)
            if d<500 and d>0:
                o.angle=math.degrees(math.atan2(dx,dz))
                if d>100: o.pos.x+=(dx/d)*o.spd; o.pos.z+=(dz/d)*o.spd
        if o.flash>0: o.flash-=1

def interact_objs(mario):
    for o in objs:
        if not o.active or o.collected: continue
        dx=mario.pos.x-o.pos.x; dy=mario.pos.y-o.pos.y; dz=mario.pos.z-o.pos.z
        d=math.sqrt(dx*dx+dy*dy+dz*dz)
        if d>o.irange+30: continue
        if o.type in(ObjType.COIN,ObjType.COIN_RED,ObjType.COIN_BLUE):
            o.collected=True; o.active=False; mario.coins+=o.coins; mario.heal(0x40*o.coins)
            ptcl.emit(o.pos,8,o.color,4.0,15)
        elif o.type==ObjType.STAR:
            if not mario.has_star(cur_lvl,o.star_id):
                o.collected=True; o.active=False; mario.get_star(cur_lvl,o.star_id)
                mario.set_act(ACT_STAR_DANCE); ptcl.emit(o.pos,20,(255,255,100),6.0,30)
        elif o.type==ObjType.ONE_UP:
            o.collected=True; o.active=False; mario.lives+=1; ptcl.emit(o.pos,10,(0,255,0),3.0,15)
        elif o.type==ObjType.PIPE:
            if ctrl.pressed&IN_A: return ('warp',o.warp)
        elif o.type in(ObjType.GOOMBA,ObjType.BOBOMB,ObjType.KOOPA,ObjType.PIRANHA):
            if mario.vel.y<-5 and mario.pos.y>o.pos.y+20:
                o.active=False; mario.vel.y=30.0; mario.coins+=1; ptcl.emit(o.pos,10,o.color,4.0,15)
            elif mario.action in(ACT_DIVE,ACT_GP_LAND):
                o.active=False; mario.coins+=1; ptcl.emit(o.pos,10,o.color,4.0,15)
            else: mario.take_dmg(0x100*o.dmg); mario.set_act(ACT_KNOCKBACK); ptcl.emit(mario.pos,5,(255,50,50),3.0,10)
        elif o.type==ObjType.BULLY:
            if d<o.irange:
                px=dx/max(d,1)*20; pz=dz/max(d,1)*20; mario.pos.x+=px; mario.pos.z+=pz; mario.fvel=15
        elif o.type in(ObjType.BOO,ObjType.BIG_BOO):
            fb=abs(math.degrees(math.atan2(o.pos.x-mario.pos.x,o.pos.z-mario.pos.z))-mario.face.y)>90
            if fb and mario.action in(ACT_GROUND_POUND,ACT_GP_LAND):
                o.hp-=1; o.flash=10
                if o.hp<=0: o.active=False; ptcl.emit(o.pos,15,(220,220,255),5.0,20)
            elif not fb and d<o.irange: mario.take_dmg(0x100); mario.set_act(ACT_KNOCKBACK)
        elif o.type==ObjType.AMP:
            mario.take_dmg(0x100); mario.set_act(ACT_KNOCKBACK)
        elif o.type==ObjType.THWOMP:
            if o.state==1 and d<o.irange: mario.take_dmg(0x200); mario.set_act(ACT_KNOCKBACK)
        elif o.type==ObjType.CHAIN_CHOMP:
            mario.take_dmg(0x300); mario.set_act(ACT_KNOCKBACK); ptcl.emit(mario.pos,8,(255,50,50),4.0,12)
        elif o.type in(ObjType.KING_BOB,ObjType.BOWSER):
            if mario.vel.y<-5 and mario.pos.y>o.pos.y+30:
                o.hp-=1; o.flash=15; mario.vel.y=40.0
                if o.hp<=0: o.active=False; ptcl.emit(o.pos,25,o.color,8.0,30)
            else: mario.take_dmg(0x200); mario.set_act(ACT_KNOCKBACK)
    return None

# ============================================================================
#  RENDERER
# ============================================================================
def rot_pt(v,cx,cy,cz,ay):
    x,y,z=v.x-cx,v.y-cy,v.z-cz
    r=math.radians(ay); c,s=math.cos(r),math.sin(r)
    return x*c-z*s, y, x*s+z*c

def render(screen,mario,cam,cyaw,frame):
    info=LI.get(cur_lvl,LI[0]); sky=info.sky; screen.fill(sky)
    rlist=[]
    for s in surfs: rlist.append(('e',s))
    for o in objs:
        if not o.active: continue
        if o.type==ObjType.TREE:
            for ts in make_box(o.pos.x,o.pos.y+o.height/2,o.pos.z,20,o.height,20,(80,50,20)): rlist.append(('o',ts))
            for cs in make_box(o.pos.x,o.pos.y+o.height+40,o.pos.z,80,80,80,(30,130,30)): rlist.append(('o',cs))
        elif o.type==ObjType.PIPE:
            for ps in make_box(o.pos.x,o.pos.y+40,o.pos.z,60,80,60,o.color): rlist.append(('o',ps))
        else:
            sz=o.radius*o.scale; col=(255,255,255) if o.flash>0 and o.flash%2==0 else o.color
            for os in make_box(o.pos.x,o.pos.y+o.height*o.scale/2,o.pos.z,sz,o.height*o.scale,sz,col): rlist.append(('o',os))
    mc=(255,20,20)
    if mario.hurt>0: mc=(255,150,150) if frame%4<2 else (255,20,20)
    elif mario.inv>0 and mario.inv%4<2: mc=(255,200,200)
    bh=60 if mario.action not in(ACT_CROUCH,ACT_BELLY_SLIDE) else 30
    for ms in make_box(mario.pos.x,mario.pos.y+bh,mario.pos.z,40,bh*2,40,mc): rlist.append(('m',ms))
    hy=mario.pos.y+bh*2+15
    for mh in make_box(mario.pos.x,hy,mario.pos.z,30,30,30,(255,200,170)): rlist.append(('m',mh))
    for hs in make_box(mario.pos.x,hy+15,mario.pos.z,35,10,35,mc): rlist.append(('m',hs))
    if mario.floor:
        for ss in make_box(mario.pos.x,mario.floor_y+2,mario.pos.z,35,2,35,(10,10,10)): rlist.append(('s',ss))
    for p in ptcl.ps:
        for ps in make_box(p.pos.x,p.pos.y,p.pos.z,p.size,p.size,p.size,p.color): rlist.append(('p',ps))
    polys=[]
    for rt,sf in rlist:
        pv=[]; az=0; inf=False
        for v in sf.verts:
            rx,ry,rz=rot_pt(v,cam.x,cam.y,cam.z,-cyaw)
            if rz>10:
                inf=True; sc=FOV/rz; pv.append((WIDTH/2+rx*sc,HEIGHT/2-ry*sc)); az+=rz
        if inf and len(pv)>=3:
            az/=len(sf.verts); col=sf.color if rt!='s' else (10,10,10)
            f=min(1.0,az/4000.0)
            fc=(int(col[0]*(1-f)+sky[0]*f),int(col[1]*(1-f)+sky[1]*f),int(col[2]*(1-f)+sky[2]*f))
            polys.append((az,fc,pv,rt))
    polys.sort(key=lambda x:x[0],reverse=True)
    for z,col,pts,rt in polys:
        col=_cc(col); pygame.draw.polygon(screen,col,pts)
        if z<2000 and rt!='s': pygame.draw.polygon(screen,(0,0,0),pts,1)

def draw_hud(screen,mario,font,fsm,frame):
    w=mario.wedges(); hx,hy,hr=60,HEIGHT-60,35
    pygame.draw.circle(screen,(40,40,40),(hx,hy),hr+3)
    for i in range(8):
        a1=math.radians(90-i*45); a2=math.radians(90-(i+1)*45)
        if i<w:
            c=(80,200,80) if w>2 else (200,80,80)
            pts=[(hx,hy)]
            for a in[a1,(a1+a2)/2,a2]: pts.append((hx+hr*math.cos(a),hy-hr*math.sin(a)))
            pygame.draw.polygon(screen,c,pts)
    pygame.draw.circle(screen,(255,255,255),(hx,hy),hr,2)
    screen.blit(font.render(f"\u2605 x {mario.stars}",True,(255,255,100)),(WIDTH-180,15))
    screen.blit(font.render(f"COINS: {mario.coins}",True,(255,215,0)),(WIDTH-180,50))
    screen.blit(fsm.render(f"LIVES x {mario.lives}",True,(255,255,255)),(20,15))
    lt=fsm.render(cur_name,True,(255,255,200)); screen.blit(lt,(WIDTH//2-lt.get_width()//2,15))
    an={ACT_IDLE:"IDLE",ACT_WALKING:"WALK",ACT_DECEL:"DECEL",ACT_CROUCH:"CROUCH",
        ACT_JUMP:"JUMP",ACT_DBL_JUMP:"DBL",ACT_TRIPLE:"TRIPLE",ACT_BACKFLIP:"BFLIP",
        ACT_SIDEFLIP:"SFLIP",ACT_LONG_JUMP:"LONG",ACT_WALLKICK:"WKICK",ACT_FREEFALL:"FALL",
        ACT_DIVE:"DIVE",ACT_BELLY_SLIDE:"BELLY",ACT_GROUND_POUND:"GP",ACT_GP_LAND:"GP.L",
        ACT_KNOCKBACK:"OUCH",ACT_LAVA_BOOST:"LAVA",ACT_STAR_DANCE:"\u2605GET",ACT_DEATH:"DEAD"}
    screen.blit(fsm.render(f"{an.get(mario.action,hex(mario.action))} SPD:{mario.fvel:.0f} Y:{mario.pos.y:.0f}",True,(180,180,180)),(20,HEIGHT-25))

def draw_title(screen,ft,fs,frame):
    for y in range(HEIGHT):
        r=int(20+(y/HEIGHT)*40); g=int(10+(y/HEIGHT)*30); b=int(60+(y/HEIGHT)*140)
        pygame.draw.line(screen,(r,g,b),(0,y),(WIDTH,y))
    off=math.sin(frame*0.04)*12
    t=ft.render("SUPER MARIO 64",True,(255,215,0)); ts=ft.render("SUPER MARIO 64",True,(80,60,0))
    screen.blit(ts,(WIDTH//2-t.get_width()//2+4,90+off+4)); screen.blit(t,(WIDTH//2-t.get_width()//2,90+off))
    sub=fs.render("Cat's PC Port \u2014 Python Edition",True,(200,200,255))
    screen.blit(sub,(WIDTH//2-sub.get_width()//2,170+off))
    cx,cy=WIDTH//2,320
    pygame.draw.circle(screen,(255,200,170),(cx,cy),55)
    pygame.draw.rect(screen,(255,0,0),(cx-60,cy-75,120,45))
    pygame.draw.rect(screen,(255,0,0),(cx+5,cy-30,60,18))
    pygame.draw.ellipse(screen,(0,0,0),(cx-25,cy-20,14,14))
    pygame.draw.ellipse(screen,(0,0,0),(cx+12,cy-20,14,14))
    pygame.draw.ellipse(screen,(0,0,0),(cx-20,cy+5,50,18))
    pygame.draw.circle(screen,(255,190,160),(cx+5,cy),12)
    mf=pygame.font.SysFont('Arial Black',28)
    screen.blit(mf.render("M",True,(255,255,255)),(cx-12,cy-68))
    if(frame//30)%2==0:
        screen.blit(fs.render("PRESS ENTER",True,(255,255,255)),(WIDTH//2-60,480))
    screen.blit(fs.render("v4.0 \u2014 All 27 Levels \u2014 60fps",True,(120,120,160)),(WIDTH//2-110,550))

def draw_select(screen,ft,fs,lflat,sel,mario,scr):
    screen.fill((15,10,35))
    tt=ft.render("SELECT COURSE",True,(255,215,0)); screen.blit(tt,(WIDTH//2-tt.get_width()//2,15))
    screen.blit(fs.render(f"\u2605 x {mario.stars}",True,(255,255,100)),(WIDTH-150,20))
    yp=70-scr; idx=0
    for cn,lids in CATS:
        if -30<yp<HEIGHT: screen.blit(fs.render(cn,True,(150,150,200)),(30,yp))
        yp+=30
        for lid in lids:
            if -30<yp<HEIGHT:
                info=LI[lid]; sel_=idx==sel
                nc=len(mario.lvl_stars.get(lid,set())); ns=info.nstars
                ss=f"[{'★'*nc}{'☆'*max(0,ns-nc)}]" if ns>0 else ""
                col=(255,215,0) if sel_ else (160,160,160)
                pre="▶ " if sel_ else "  "
                txt=fs.render(f"{pre}{info.name}  {ss}",True,col)
                if sel_: pygame.draw.rect(screen,(40,30,70),(50,yp-2,WIDTH-100,24))
                screen.blit(txt,(60,yp))
            yp+=28; idx+=1
        yp+=10
    screen.blit(fs.render("↑↓ Navigate  ENTER Select  ESC Back",True,(100,100,130)),(WIDTH//2-160,HEIGHT-30))

def draw_pause(screen,ft,fs,mario):
    ov=pygame.Surface((WIDTH,HEIGHT)); ov.set_alpha(160); ov.fill((0,0,0)); screen.blit(ov,(0,0))
    screen.blit(ft.render("PAUSE",True,(255,255,255)),(WIDTH//2-60,150))
    for i,s in enumerate([f"Stars: {mario.stars}",f"Coins: {mario.coins}",f"Lives: {mario.lives}",f"Level: {cur_name}"]):
        screen.blit(fs.render(s,True,(200,200,200)),(WIDTH//2-60,250+i*35))
    screen.blit(fs.render("ESC Resume   Q Exit",True,(150,150,150)),(WIDTH//2-80,450))

def draw_death(screen,ft,fs,mario,t):
    screen.fill((0,0,0))
    if t>30: screen.blit(ft.render("GAME OVER",True,(255,50,50)),(WIDTH//2-100,200))
    if t>30: screen.blit(fs.render(f"Lives: {mario.lives}",True,(200,200,200)),(WIDTH//2-40,300))
    if t>90: screen.blit(fs.render("Press ENTER",True,(150,150,150)),(WIDTH//2-50,400))

# ============================================================================
#  MAIN LOOP
# ============================================================================
def main():
    global ctrl
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    pygame.display.set_caption("Cat's SM64 PC Port — Full Edition")
    clock=pygame.time.Clock()
    ft=pygame.font.SysFont('Arial Black',48); fu=pygame.font.SysFont('Arial',22); fs=pygame.font.SysFont('Arial',18)
    state=GameState.TITLE; frame=0; lacc=0
    mario=MarioState(); ctrl=Controller()
    lflat=[]
    for _,lids in CATS: lflat.extend(lids)
    sel=0; scr=0; dtimer=0
    cam=Vec3f(0,500,800); cyaw=0.0
    running=True
    while running:
        frame+=1; clock.tick(FPS)
        kp=set()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                kp.add(ev.key)
                if state==GameState.TITLE:
                    if ev.key==pygame.K_RETURN: state=GameState.LEVEL_SELECT
                elif state==GameState.LEVEL_SELECT:
                    if ev.key==pygame.K_UP: sel=(sel-1)%len(lflat); scr=max(0,sel*28-200)
                    elif ev.key==pygame.K_DOWN: sel=(sel+1)%len(lflat); scr=max(0,sel*28-200)
                    elif ev.key==pygame.K_RETURN:
                        lid=lflat[sel]; info=LI[lid]; load_level(lid)
                        mario.pos=info.start.copy(); mario.vel.set(0,0,0); mario.fvel=0
                        mario.action=ACT_FREEFALL; mario.health=0x880; mario.coins=0
                        cyaw=0; cam=Vec3f(mario.pos.x,mario.pos.y+300,mario.pos.z+800)
                        state=GameState.GAMEPLAY
                    elif ev.key==pygame.K_ESCAPE: state=GameState.TITLE
                elif state==GameState.GAMEPLAY:
                    if ev.key==pygame.K_ESCAPE: state=GameState.PAUSE
                elif state==GameState.PAUSE:
                    if ev.key==pygame.K_ESCAPE: state=GameState.GAMEPLAY
                    elif ev.key==pygame.K_q: state=GameState.LEVEL_SELECT
                elif state==GameState.DEATH:
                    if ev.key==pygame.K_RETURN and dtimer>90:
                        if mario.lives>0: state=GameState.LEVEL_SELECT
                        else: mario=MarioState(); state=GameState.TITLE
        keys=pygame.key.get_pressed()
        lacc+=1; do_logic=(lacc>=FRAME_SKIP)
        if do_logic: lacc=0
        if state==GameState.GAMEPLAY and do_logic:
            ctrl.pressed=0; ctrl.down=0
            if keys[pygame.K_SPACE] or pygame.K_SPACE in kp: ctrl.pressed|=IN_A
            if keys[pygame.K_SPACE]: ctrl.down|=IN_A_D
            if keys[pygame.K_x] or pygame.K_x in kp: ctrl.pressed|=IN_B
            if keys[pygame.K_z] or pygame.K_z in kp: ctrl.pressed|=IN_Z
            if keys[pygame.K_z]: ctrl.down|=IN_Z_D
            dx=dz=0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx-=1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx+=1
            if keys[pygame.K_UP] or keys[pygame.K_w]: dz+=1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dz-=1
            if dx or dz:
                ctrl.stick_mag=1.0; mario.iyaw=math.degrees(math.atan2(dx,dz))+cyaw; mario.imag=MAX_WALK
            else: ctrl.stick_mag=0; mario.imag=0
            fn=ACT_MAP.get(mario.action,a_idle); fn(mario,ctrl)
            if mario.inv>0: mario.inv-=1
            if mario.hurt>0: mario.hurt-=1
            # Floor surface effects
            if mario.floor:
                if mario.floor.stype==SURF_LAVA and mario.action not in(ACT_LAVA_BOOST,ACT_KNOCKBACK):
                    mario.set_act(ACT_LAVA_BOOST)
                elif mario.floor.stype==SURF_DEATH: mario.pos.set(0,200,0); mario.vel.set(0,0,0)
            update_objs(mario,frame); ptcl.update()
            wr=interact_objs(mario)
            if wr and wr[0]=='warp':
                lid=wr[1]; info=LI[lid]; load_level(lid)
                mario.pos=info.start.copy(); mario.vel.set(0,0,0); mario.fvel=0
                mario.action=ACT_FREEFALL; mario.health=0x880; mario.coins=0
                cyaw=0; cam=Vec3f(mario.pos.x,mario.pos.y+300,mario.pos.z+800)
            if mario.health<=0:
                mario.lives-=1; dtimer=0; state=GameState.DEATH
            if mario.pos.y<-3000:
                mario.pos=LI.get(cur_lvl,LI[0]).start.copy(); mario.vel.set(0,0,0); mario.fvel=0
                mario.action=ACT_FREEFALL; mario.take_dmg(0x100)
            # Camera
            if keys[pygame.K_q]: cyaw-=3
            if keys[pygame.K_e]: cyaw+=3
            wx=mario.pos.x-sins(cyaw)*800; wz=mario.pos.z-coss(cyaw)*800
            cam.x+=(wx-cam.x)*0.1; cam.z+=(wz-cam.z)*0.1; cam.y+=((mario.pos.y+300)-cam.y)*0.1
        if state==GameState.DEATH and do_logic: dtimer+=1
        # RENDER
        if state==GameState.TITLE: draw_title(screen,ft,fs,frame)
        elif state==GameState.LEVEL_SELECT: draw_select(screen,ft,fs,lflat,sel,mario,scr)
        elif state==GameState.GAMEPLAY:
            render(screen,mario,cam,cyaw,frame); draw_hud(screen,mario,fu,fs,frame)
        elif state==GameState.PAUSE:
            render(screen,mario,cam,cyaw,frame); draw_hud(screen,mario,fu,fs,frame)
            draw_pause(screen,ft,fs,mario)
        elif state==GameState.DEATH: draw_death(screen,ft,fs,mario,dtimer)
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__=="__main__": main()
