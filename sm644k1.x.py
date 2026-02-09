import pygame
import math
import sys
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Set, Optional, Dict

# ============================================================================
#  Cat's SM64 Py Port 3.0 (Python 3.14 Edition)
#  Architecture: Action State Machine, Quarter-Step Physics, Graph Nodes
#  Content: Main Menu, Castle Hub, Multiple Courses
# ============================================================================

# --- Constants & Configuration ---
WIDTH, HEIGHT = 800, 600
FPS = 30  # SM64 runs at 30 logic frames
FOV = 450
BG_COLOR = (135, 206, 235)

# --- Math Macros & Types ---
S16_MAX = 32767
S16_MIN = -32768

@dataclass
class Vec3f:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def set(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def copy(self):
        return Vec3f(self.x, self.y, self.z)

    def dist_to(self, other):
        dx, dy, dz = self.x - other.x, self.y - other.y, self.z - other.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)

@dataclass
class Vec3s:
    x: int = 0
    y: int = 0
    z: int = 0

# --- Game States ---
class GameState(Enum):
    TITLE = auto()
    LEVEL_SELECT = auto()
    GAMEPLAY = auto()
    PAUSE = auto()

# --- SM64 Action Defines ---
ACT_IDLE            = 0x001
ACT_WALKING         = 0x004
ACT_BRAKING_STOP    = 0x00D
ACT_JUMP            = 0x010
ACT_DOUBLE_JUMP     = 0x011
ACT_TRIPLE_JUMP     = 0x012
ACT_LONG_JUMP       = 0x014
ACT_FREEFALL        = 0x018
ACT_BUTT_SLIDE      = 0x020
ACT_GROUND_POUND    = 0x025
ACT_WALL_KICK_AIR   = 0x030

# Physics Constants
GRAVITY          = -4.0
MAX_FALL_SPEED   = -75.0
MAX_WALK_SPEED   = 32.0
FRICTION_FLOOR   = 0.8
FRICTION_AIR     = 0.95

# Input Flags
INPUT_A_PRESSED = 0x0001
INPUT_Z_PRESSED = 0x0002
INPUT_NONZERO_ANALOG = 0x0010

# --- Controller Struct ---
@dataclass
class Controller:
    stick_x: float = 0
    stick_y: float = 0
    stick_mag: float = 0
    button_pressed: int = 0
    button_down: int = 0
    camera_x: int = 0  # C-buttons

# --- Surface/Geometry Types ---
SURFACE_DEFAULT = 0
SURFACE_BURNING = 1
SURFACE_SLIPPERY = 2 # Ice
SURFACE_DEATH_PLANE = 3
SURFACE_WATER = 4
SURFACE_LAVA = 5

@dataclass
class Surface:
    vertices: List[Vec3f]
    normal: Vec3f
    type: int = SURFACE_DEFAULT
    color: Tuple[int, int, int] = (255, 255, 255)
    lower_y: float = -10000 
    upper_y: float = 10000

# ============================================================================
#  ENGINE CORE: MARIO STATE
# ============================================================================

@dataclass
class MarioState:
    # Position & Velocity
    pos: Vec3f = field(default_factory=Vec3f)
    vel: Vec3f = field(default_factory=Vec3f)
    forward_vel: float = 0.0
    
    # Rotation
    face_angle: Vec3s = field(default_factory=Vec3s)
    angle_vel: Vec3s = field(default_factory=Vec3s)
    
    # State
    action: int = ACT_IDLE
    prev_action: int = ACT_IDLE
    action_state: int = 0
    action_timer: int = 0
    action_arg: int = 0
    
    # Status
    health: int = 0x880
    num_coins: int = 0
    num_stars: int = 0
    num_lives: int = 4
    
    # Environment
    floor: Optional[Surface] = None
    floor_height: float = -10000.0
    
    # Buffers
    intended_mag: float = 0.0
    intended_yaw: int = 0
    
    def set_action(self, new_action, arg=0):
        self.prev_action = self.action
        self.action = new_action
        self.action_arg = arg
        self.action_state = 0
        self.action_timer = 0

# ============================================================================
#  COLLISION SYSTEM (Simplified)
# ============================================================================

def find_floor(x, y, z, surfaces: List[Surface]) -> Tuple[float, Optional[Surface]]:
    height = -11000.0
    floor = None
    
    # Optimization: Only check surfaces roughly near x,z could go here
    
    for surf in surfaces:
        # Simple AABB check
        min_x = min(v.x for v in surf.vertices) - 10
        max_x = max(v.x for v in surf.vertices) + 10
        min_z = min(v.z for v in surf.vertices) - 10
        max_z = max(v.z for v in surf.vertices) + 10
        
        if x < min_x or x > max_x or z < min_z or z > max_z:
            continue
            
        p1 = surf.vertices[0]
        nx, ny, nz = surf.normal.x, surf.normal.y, surf.normal.z
        
        # Wall check
        if abs(ny) < 0.1: continue
        
        # Plane math
        # ny * y = -nx(x-x1) - nz(z-z1) + ny*y1
        dist = -(x*nx + z*nz - (nx*p1.x + ny*p1.y + nz*p1.z))
        if ny == 0: continue
        surf_y = dist / ny
        
        if height < surf_y <= y + 150:
            height = surf_y
            floor = surf
            
    return height, floor

# ============================================================================
#  ACTION IMPLEMENTATIONS
# ============================================================================

def update_air_without_turn(m: MarioState):
    drag = FRICTION_AIR
    m.forward_vel *= drag
    m.vel.x = m.forward_vel * math.sin(math.radians(m.face_angle.y))
    m.vel.z = m.forward_vel * math.cos(math.radians(m.face_angle.y))
    m.vel.y += GRAVITY
    if m.vel.y < MAX_FALL_SPEED: m.vel.y = MAX_FALL_SPEED

def mario_set_forward_vel(m: MarioState, speed):
    m.forward_vel = speed
    m.vel.x = m.forward_vel * math.sin(math.radians(m.face_angle.y))
    m.vel.z = m.forward_vel * math.cos(math.radians(m.face_angle.y))

def perform_ground_step(m: MarioState):
    m.pos.x += m.vel.x
    m.pos.z += m.vel.z
    floor_y, floor = find_floor(m.pos.x, m.pos.y + 100, m.pos.z, current_scene_surfaces)
    m.floor = floor
    m.floor_height = floor_y
    
    if m.pos.y > floor_y + 10: return 'air'
    m.pos.y = floor_y
    return 'ground'

def perform_air_step(m: MarioState):
    m.pos.x += m.vel.x
    m.pos.z += m.vel.z
    m.pos.y += m.vel.y
    floor_y, floor = find_floor(m.pos.x, m.pos.y, m.pos.z, current_scene_surfaces)
    m.floor = floor
    m.floor_height = floor_y
    
    if m.pos.y <= floor_y:
        m.pos.y = floor_y
        return 'land'
    return 'air'

def approach_angle(current, target, inc):
    diff = (target - current + 180) % 360 - 180
    if diff > inc: return current + inc
    if diff < -inc: return current - inc
    return target

# --- Actions ---

def act_idle(m: MarioState, c: Controller):
    if c.button_pressed & INPUT_A_PRESSED: return m.set_action(ACT_JUMP)
    if c.button_pressed & INPUT_Z_PRESSED: return m.set_action(ACT_BRAKING_STOP)
    if c.stick_mag > 0: return m.set_action(ACT_WALKING)
    m.forward_vel = 0; m.vel.x = 0; m.vel.z = 0
    perform_ground_step(m)

def act_walking(m: MarioState, c: Controller):
    if c.button_pressed & INPUT_A_PRESSED:
        if m.forward_vel > 10.0 and (c.button_down & INPUT_Z_PRESSED): return m.set_action(ACT_LONG_JUMP)
        return m.set_action(ACT_JUMP)
    if c.stick_mag == 0: return m.set_action(ACT_IDLE)
    
    m.face_angle.y = approach_angle(m.face_angle.y, m.intended_yaw, 10.0)
    target_speed = c.stick_mag * MAX_WALK_SPEED
    if m.forward_vel < target_speed: m.forward_vel += 1.1
    else: m.forward_vel -= 1.0
    mario_set_forward_vel(m, m.forward_vel)
    
    if perform_ground_step(m) == 'air': m.set_action(ACT_FREEFALL)

def act_jump(m: MarioState, c: Controller):
    if m.action_timer == 0: m.vel.y = 42.0 + m.forward_vel * 0.25
    if c.button_pressed & INPUT_Z_PRESSED: return m.set_action(ACT_GROUND_POUND)
    update_air_without_turn(m)
    if perform_air_step(m) == 'land':
        m.set_action(ACT_WALKING if c.stick_mag > 0 else ACT_IDLE)
    m.action_timer += 1

def act_long_jump(m: MarioState, c: Controller):
    if m.action_timer == 0:
        m.vel.y = 30.0; m.forward_vel *= 1.5
    update_air_without_turn(m)
    if perform_air_step(m) == 'land':
        m.forward_vel = 0; m.set_action(ACT_IDLE)
    m.action_timer += 1

def act_ground_pound(m: MarioState, c: Controller):
    if m.action_state == 0:
        m.forward_vel = 0; m.vel.x=0; m.vel.z=0; m.vel.y=0
        m.action_timer += 1
        if m.action_timer > 10: m.action_state = 1; m.vel.y = -50.0
    else:
        if perform_air_step(m) == 'land': m.set_action(ACT_IDLE)

# ============================================================================
#  LEVEL GENERATION
# ============================================================================

current_scene_surfaces: List[Surface] = []
current_level_name = "Castle Grounds"

def make_box(x, y, z, w, h, d, color) -> List[Surface]:
    hw, hh, hd = w/2, h/2, d/2
    surfs = []
    # Normals: Top(0,1,0), Front(0,0,1), Back(0,0,-1), Left(-1,0,0), Right(1,0,0)
    # Top
    surfs.append(Surface([Vec3f(x-hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z+hd)], Vec3f(0,1,0), color=tuple(min(255, c*1.2) for c in color)))
    # Sides
    surfs.append(Surface([Vec3f(x-hw,y-hh,z+hd), Vec3f(x+hw,y-hh,z+hd), Vec3f(x+hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z+hd)], Vec3f(0,0,1), color=color)) # Front
    surfs.append(Surface([Vec3f(x+hw,y-hh,z-hd), Vec3f(x-hw,y-hh,z-hd), Vec3f(x-hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z-hd)], Vec3f(0,0,-1), color=color)) # Back
    surfs.append(Surface([Vec3f(x-hw,y-hh,z-hd), Vec3f(x-hw,y-hh,z+hd), Vec3f(x-hw,y+hh,z+hd), Vec3f(x-hw,y+hh,z-hd)], Vec3f(-1,0,0), color=tuple(max(0, c*0.8) for c in color))) # Left
    surfs.append(Surface([Vec3f(x+hw,y-hh,z+hd), Vec3f(x+hw,y-hh,z-hd), Vec3f(x+hw,y+hh,z-hd), Vec3f(x+hw,y+hh,z+hd)], Vec3f(1,0,0), color=tuple(max(0, c*0.8) for c in color))) # Right
    return surfs

def make_quad(p1, p2, p3, p4, color, type=SURFACE_DEFAULT):
    # Compute normal manually
    ux, uy, uz = p2.x - p1.x, p2.y - p1.y, p2.z - p1.z
    vx, vy, vz = p3.x - p1.x, p3.y - p1.y, p3.z - p1.z
    nx = uy*vz - uz*vy
    ny = uz*vx - ux*vz
    nz = ux*vy - uy*vx
    mag = math.sqrt(nx*nx + ny*ny + nz*nz)
    if mag == 0: mag = 1
    return Surface([p1, p2, p3, p4], Vec3f(nx/mag, ny/mag, nz/mag), type=type, color=color)

def load_level(level_id):
    global current_scene_surfaces, current_level_name
    current_scene_surfaces = []
    
    if level_id == 0: # CASTLE GROUNDS
        current_level_name = "Peach's Castle Grounds"
        # Green Lawn
        current_scene_surfaces.append(make_quad(Vec3f(-2000, 0, -2000), Vec3f(2000, 0, -2000), Vec3f(2000, 0, 2000), Vec3f(-2000, 0, 2000), (34, 180, 34)))
        # Moat (Water)
        current_scene_surfaces.extend(make_box(0, -100, -500, 1000, 100, 300, (64, 120, 220)))
        # Bridge
        current_scene_surfaces.extend(make_box(0, 10, -500, 200, 20, 400, (139, 90, 43)))
        # Castle Walls
        current_scene_surfaces.extend(make_box(0, 200, -1000, 800, 400, 200, (220, 210, 190)))
        # Side Towers
        current_scene_surfaces.extend(make_box(-500, 200, -900, 200, 400, 200, (200, 190, 170)))
        current_scene_surfaces.extend(make_box(500, 200, -900, 200, 400, 200, (200, 190, 170)))
        
    elif level_id == 1: # BOB-OMB BATTLEFIELD
        current_level_name = "Bob-omb Battlefield"
        # Base
        current_scene_surfaces.append(make_quad(Vec3f(-2000, 0, -2000), Vec3f(2000, 0, -2000), Vec3f(2000, 0, 2000), Vec3f(-2000, 0, 2000), (100, 160, 60)))
        # The Summit (Pyramid-ish)
        for i in range(5):
            w = 800 - i*150
            current_scene_surfaces.extend(make_box(0, 100 + i*100, -1000, w, 100, w, (139, 100, 50)))
        # Bridge to Mountain
        current_scene_surfaces.extend(make_box(0, 50, -200, 100, 10, 400, (160, 120, 80)))
        # Chain Chomp Gate
        current_scene_surfaces.extend(make_box(-500, 100, 0, 20, 200, 20, (50,50,50)))
        current_scene_surfaces.extend(make_box(-300, 100, 0, 20, 200, 20, (50,50,50)))
        current_scene_surfaces.extend(make_box(-400, 200, 0, 220, 20, 20, (50,50,50)))

    elif level_id == 2: # WHOMP'S FORTRESS
        current_level_name = "Whomp's Fortress"
        # Stone Base
        current_scene_surfaces.append(make_quad(Vec3f(-2000, 0, -2000), Vec3f(2000, 0, -2000), Vec3f(2000, 0, 2000), Vec3f(-2000, 0, 2000), (150, 150, 150)))
        # Main Fortress
        current_scene_surfaces.extend(make_box(0, 100, -500, 800, 200, 600, (180, 180, 180)))
        # Steps
        for i in range(5):
            current_scene_surfaces.extend(make_box(-600 + i*100, i*40, 200, 100, 40, 200, (200, 200, 200)))
        # Floating Islands
        current_scene_surfaces.extend(make_box(600, 300, 0, 200, 20, 200, (160, 160, 180)))
        current_scene_surfaces.extend(make_box(800, 400, 200, 150, 20, 150, (160, 160, 180)))

    elif level_id == 3: # COOL COOL MOUNTAIN
        current_level_name = "Cool, Cool Mountain"
        # Snow Base
        current_scene_surfaces.append(make_quad(Vec3f(-2000, 0, -2000), Vec3f(2000, 0, -2000), Vec3f(2000, 0, 2000), Vec3f(-2000, 0, 2000), (240, 245, 255)))
        # Big Slope
        p1, p2 = Vec3f(-1000, 1000, -1000), Vec3f(1000, 1000, -1000)
        p3, p4 = Vec3f(1000, 0, 1000), Vec3f(-1000, 0, 1000)
        current_scene_surfaces.append(make_quad(p1, p2, p3, p4, (220, 230, 255), type=SURFACE_SLIPPERY))
        # Cabin
        current_scene_surfaces.extend(make_box(0, 1050, -1200, 300, 200, 300, (100, 60, 30)))
        # Snowman Head
        current_scene_surfaces.extend(make_box(0, 100, 500, 200, 200, 200, (255, 255, 255)))

    elif level_id == 4: # LETHAL LAVA LAND
        current_level_name = "Lethal Lava Land"
        # Lava Ocean
        current_scene_surfaces.append(make_quad(Vec3f(-2000, -50, -2000), Vec3f(2000, -50, -2000), Vec3f(2000, -50, 2000), Vec3f(-2000, -50, 2000), (200, 40, 0), type=SURFACE_LAVA))
        # Central Platform
        current_scene_surfaces.extend(make_box(0, 0, 0, 400, 50, 400, (80, 80, 80)))
        # Volcano
        current_scene_surfaces.extend(make_box(0, 100, -800, 600, 200, 600, (100, 50, 50)))
        # Steps
        current_scene_surfaces.extend(make_box(-500, 20, 0, 100, 20, 100, (60, 60, 60)))
        current_scene_surfaces.extend(make_box(-650, 20, 0, 100, 20, 100, (60, 60, 60)))

# ============================================================================
#  RENDERER
# ============================================================================

def rotate_point(v: Vec3f, cx, cy, cz, ang_x, ang_y):
    x, y, z = v.x - cx, v.y - cy, v.z - cz
    rad_y = math.radians(ang_y)
    cos_y, sin_y = math.cos(rad_y), math.sin(rad_y)
    rx = x * cos_y - z * sin_y
    rz = x * sin_y + z * cos_y
    ry = y 
    return rx, ry, rz

def render_frame(screen, mario: MarioState, cam_pos: Vec3f, cam_yaw: float):
    screen.fill(BG_COLOR)
    render_list = []
    
    # Environment
    for surf in current_scene_surfaces:
        render_list.append(('surf', surf))
        
    # Mario (Red Box)
    mario_surfs = make_box(mario.pos.x, mario.pos.y + 60, mario.pos.z, 50, 120, 50, (255, 20, 20))
    for s in mario_surfs: render_list.append(('mario', s))

    # Shadow
    if mario.floor:
        shadow_y = mario.floor_height + 2
        shadow_surfs = make_box(mario.pos.x, shadow_y, mario.pos.z, 40, 0, 40, (0, 0, 0))
        for s in shadow_surfs: render_list.append(('shadow', s))

    polys_to_draw = []
    
    for r_type, surf in render_list:
        proj_verts = []
        avg_z = 0
        in_front = False
        
        for v in surf.vertices:
            rx, ry, rz = rotate_point(v, cam_pos.x, cam_pos.y, cam_pos.z, 0, -cam_yaw)
            if rz > 10:
                in_front = True
                scale = FOV / rz
                sx = WIDTH/2 + rx * scale
                sy = HEIGHT/2 - ry * scale
                proj_verts.append((sx, sy))
                avg_z += rz
                
        if in_front and len(proj_verts) > 2:
            avg_z /= len(surf.vertices)
            col = surf.color
            if r_type == 'shadow': col = (0,0,0)
            # Distance fog
            fog_factor = min(1.0, avg_z / 3000.0)
            final_col = (
                col[0] * (1-fog_factor) + BG_COLOR[0]*fog_factor,
                col[1] * (1-fog_factor) + BG_COLOR[1]*fog_factor,
                col[2] * (1-fog_factor) + BG_COLOR[2]*fog_factor
            )
            polys_to_draw.append((avg_z, final_col, proj_verts))
            
    polys_to_draw.sort(key=lambda x: x[0], reverse=True)
    
    for z, col, pts in polys_to_draw:
        pygame.draw.polygon(screen, col, pts)
        if z < 1500: pygame.draw.polygon(screen, (0,0,0), pts, 1)

def draw_title_screen(screen, font_title, font_sub, frame):
    # SM64 Gradient Background
    for y in range(HEIGHT):
        r = int(30 + (y/HEIGHT)*50)
        g = int(30 + (y/HEIGHT)*80)
        b = int(100 + (y/HEIGHT)*155)
        pygame.draw.line(screen, (r,g,b), (0,y), (WIDTH,y))
        
    # Title
    offset = math.sin(frame * 0.05) * 10
    title = font_title.render("Cat's SM64", True, (255, 215, 0))
    title_shadow = font_title.render("Cat's SM64", True, (50, 50, 50))
    screen.blit(title_shadow, (WIDTH//2 - title.get_width()//2 + 5, 100 + offset + 5))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100 + offset))
    
    sub = font_sub.render("PC Port Edition - Python 3.14", True, (200, 200, 255))
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 180 + offset))
    
    # Mario Head (Pixel Art Approximation)
    cx, cy = WIDTH//2, 350
    pygame.draw.circle(screen, (255, 200, 180), (cx, cy), 60) # Face
    pygame.draw.rect(screen, (255, 0, 0), (cx-65, cy-80, 130, 50)) # Hat
    pygame.draw.rect(screen, (255, 0, 0), (cx+10, cy-30, 70, 20)) # Brim
    pygame.draw.rect(screen, (0,0,0), (cx+10, cy-10, 40, 10)) # Mustache
    pygame.draw.circle(screen, (255, 200, 180), (cx+20, cy-20), 10) # Nose

    if (frame // 30) % 2 == 0:
        msg = font_sub.render("PRESS START", True, (255, 255, 255))
        screen.blit(msg, (WIDTH//2 - msg.get_width()//2, 500))

def draw_level_select(screen, font, levels, selected):
    screen.fill((20, 20, 40))
    title = font.render("SELECT MAP", True, (255, 255, 255))
    screen.blit(title, (50, 50))
    
    for i, name in enumerate(levels):
        col = (255, 215, 0) if i == selected else (100, 100, 100)
        txt = font.render(f"> {name}" if i == selected else f"  {name}", True, col)
        screen.blit(txt, (80, 120 + i * 40))

# ============================================================================
#  MAIN LOOP
# ============================================================================

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cat's SM64 - PC Port")
    clock = pygame.time.Clock()
    
    font_title = pygame.font.SysFont('Arial Black', 60)
    font_ui = pygame.font.SysFont('Arial', 24)
    
    # Init Game
    state = GameState.TITLE
    frame = 0
    mario = MarioState()
    controller = Controller()
    
    # Level Data
    levels = ["Peach's Castle", "Bob-omb Battlefield", "Whomp's Fortress", "Cool Cool Mountain", "Lethal Lava Land"]
    selected_level = 0
    
    # Camera
    cam_pos = Vec3f(0, 500, -800)
    cam_yaw = 0.0
    
    running = True
    while running:
        frame += 1
        
        # --- INPUT ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.KEYDOWN:
                if state == GameState.TITLE:
                    if event.key == pygame.K_RETURN: state = GameState.LEVEL_SELECT
                    
                elif state == GameState.LEVEL_SELECT:
                    if event.key == pygame.K_UP: selected_level = (selected_level - 1) % len(levels)
                    if event.key == pygame.K_DOWN: selected_level = (selected_level + 1) % len(levels)
                    if event.key == pygame.K_RETURN:
                        load_level(selected_level)
                        mario.pos.set(0, 200, 0)
                        mario.vel.set(0,0,0)
                        mario.action = ACT_IDLE
                        cam_yaw = 0
                        state = GameState.GAMEPLAY
                        
                elif state == GameState.GAMEPLAY:
                    if event.key == pygame.K_ESCAPE: state = GameState.LEVEL_SELECT
                    
        keys = pygame.key.get_pressed()
        
        # --- LOGIC ---
        if state == GameState.GAMEPLAY:
            # Controller
            controller.button_pressed = 0
            if keys[pygame.K_SPACE]: controller.button_pressed |= INPUT_A_PRESSED
            if keys[pygame.K_z]: controller.button_pressed |= INPUT_Z_PRESSED
            
            dx, dz = 0, 0
            if keys[pygame.K_LEFT]: dx -= 1
            if keys[pygame.K_RIGHT]: dx += 1
            if keys[pygame.K_UP]: dz += 1
            if keys[pygame.K_DOWN]: dz -= 1
            
            if dx != 0 or dz != 0:
                controller.stick_mag = 1.0
                stick_angle = math.degrees(math.atan2(dx, dz))
                mario.intended_yaw = stick_angle + cam_yaw
                mario.intended_mag = 32.0
            else:
                controller.stick_mag = 0
                mario.intended_mag = 0
                
            # Mario State Machine
            match mario.action:
                case 0x001: act_idle(mario, controller)
                case 0x004: act_walking(mario, controller)
                case 0x010 | 0x011 | 0x012: act_jump(mario, controller)
                case 0x014: act_long_jump(mario, controller)
                case 0x018:
                    update_air_without_turn(mario)
                    if perform_air_step(mario) == 'land': mario.set_action(ACT_IDLE)
                case 0x025: act_ground_pound(mario, controller)
                case _: act_idle(mario, controller)
                
            # Lakitu Camera
            target_cam_dist = 800
            if keys[pygame.K_q]: cam_yaw -= 3
            if keys[pygame.K_e]: cam_yaw += 3
            
            want_x = mario.pos.x - math.sin(math.radians(cam_yaw)) * target_cam_dist
            want_z = mario.pos.z - math.cos(math.radians(cam_yaw)) * target_cam_dist
            
            cam_pos.x += (want_x - cam_pos.x) * 0.1
            cam_pos.z += (want_z - cam_pos.z) * 0.1
            cam_pos.y += ((mario.pos.y + 300) - cam_pos.y) * 0.1
            
            if mario.pos.y < -2000: # Respawn
                mario.pos.set(0, 200, 0)
                mario.vel.set(0,0,0)

        # --- RENDER ---
        if state == GameState.TITLE:
            draw_title_screen(screen, font_title, font_ui, frame)
        elif state == GameState.LEVEL_SELECT:
            draw_level_select(screen, font_title, levels, selected_level)
        elif state == GameState.GAMEPLAY:
            render_frame(screen, mario, cam_pos, cam_yaw)
            
            # HUD
            hud_txt = font_ui.render(f"STAR x {mario.num_stars}   {current_level_name}", True, (255, 255, 200))
            screen.blit(hud_txt, (20, 20))
            debug_txt = font_ui.render(f"ACT: {hex(mario.action)}", True, (200, 200, 200))
            screen.blit(debug_txt, (20, 50))
            
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
