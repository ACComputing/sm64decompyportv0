import pygame
import math
import sys

# --- Constants & Configuration ---
WIDTH, HEIGHT = 800, 600
FPS = 60
FOV = 400  # Field of view scaler
VIEW_DISTANCE = 4000
BG_COLOR = (135, 206, 235)  # Sky blue
GROUND_COLOR = (34, 139, 34)  # Forest green
PLATFORM_COLOR = (139, 69, 19)  # Saddle brown
PLAYER_COLOR = (255, 0, 0)  # Mario Red
CASTLE_COLOR = (200, 200, 200)

# Physics - SM64-ish Feel
GRAVITY = 0.8
JUMP_FORCE = -16
ACCELERATION = 0.6
FRICTION = 0.85  # Slippery-ish but controlled
MAX_SPEED = 12
ROTATION_SPEED = 0.08
CAM_DISTANCE = 400
CAM_HEIGHT = 200

# --- 3D Math Engine ---

class Vector3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def add(self, v):
        return Vector3(self.x + v.x, self.y + v.y, self.z + v.z)

    def sub(self, v):
        return Vector3(self.x - v.x, self.y - v.y, self.z - v.z)

    def rotate_y(self, angle, center):
        # Rotate around a center point on the Y axis
        dx = self.x - center.x
        dz = self.z - center.z
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        nx = dx * cos_a - dz * sin_a
        nz = dx * sin_a + dz * cos_a
        return Vector3(nx + center.x, self.y, self.z + center.z) 

def rotate_point_y(x, z, cx, cz, angle):
    dx = x - cx
    dz = z - cz
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    nx = dx * cos_a - dz * sin_a
    nz = dx * sin_a + dz * cos_a
    return nx + cx, nz + cz

class Face:
    def __init__(self, vertices, color):
        self.vertices = vertices # List of Vector3
        self.color = color
        self.avg_z = 0

    def calculate_depth(self, camera):
        # simple depth sort based on average distance to camera
        dist_sum = 0
        for v in self.vertices:
            dx = v.x - camera.x
            dy = v.y - camera.y
            dz = v.z - camera.z
            dist_sum += math.sqrt(dx*dx + dy*dy + dz*dz)
        self.avg_z = dist_sum / len(self.vertices)

class Object3D:
    def __init__(self, x, y, z, color=None):
        self.x, self.y, self.z = x, y, z
        self.faces = [] # List of Face objects
        self.color = color if color else (255, 255, 255)

    def add_cube(self, w, h, d, color=None):
        c = color if color else self.color
        # 8 vertices relative to center
        hw, hh, hd = w/2, h/2, d/2
        # Base format: (x, y, z)
        # Front face
        v1 = Vector3(-hw, -hh, -hd)
        v2 = Vector3(hw, -hh, -hd)
        v3 = Vector3(hw, hh, -hd)
        v4 = Vector3(-hw, hh, -hd)
        # Back face
        v5 = Vector3(-hw, -hh, hd)
        v6 = Vector3(hw, -hh, hd)
        v7 = Vector3(hw, hh, hd)
        v8 = Vector3(-hw, hh, hd)
        
        verts = [v1, v2, v3, v4, v5, v6, v7, v8]
        
        # Add faces (indices)
        # Front, Back, Left, Right, Top, Bottom
        indices = [
            [0, 1, 2, 3], [5, 4, 7, 6], # Front, Back
            [4, 0, 3, 7], [1, 5, 6, 2], # Left, Right
            [3, 2, 6, 7], [4, 5, 1, 0]  # Top, Bottom
        ]
        
        for idx_list in indices:
            face_verts = [verts[i] for i in idx_list]
            self.faces.append(Face(face_verts, c))

class Player(Object3D):
    def __init__(self, x, y, z):
        super().__init__(x, y, z, PLAYER_COLOR)
        self.width = 40
        self.height = 60 # Taller like Mario
        self.depth = 40
        
        # Physics State
        self.vel_x = 0
        self.vel_y = 0
        self.vel_z = 0
        self.on_ground = False
        self.facing_angle = 0
        
        # Build Model (Simple Red Box - No Cat Ears)
        self.add_cube(40, 60, 40, PLAYER_COLOR)
        # Added a blue bottom to signify overalls
        self.add_cube(42, 20, 42, (0, 0, 255)) 

    def update(self, keys, map_objects):
        # --- Rotation ---
        turn = 0
        if keys[pygame.K_LEFT]:
            turn = -1
        if keys[pygame.K_RIGHT]:
            turn = 1
        
        self.facing_angle += turn * ROTATION_SPEED
            
        # --- Movement (Momentum Based) ---
        forward = 0
        if keys[pygame.K_UP]:
            forward = 1
        if keys[pygame.K_DOWN]:
            forward = -1
            
        # Acceleration
        if forward != 0:
            ax = math.sin(self.facing_angle) * forward * ACCELERATION
            az = math.cos(self.facing_angle) * forward * ACCELERATION
            self.vel_x += ax
            self.vel_z += az
        else:
            # Friction
            self.vel_x *= FRICTION
            self.vel_z *= FRICTION
            
        # Cap Speed
        current_speed = math.sqrt(self.vel_x**2 + self.vel_z**2)
        if current_speed > MAX_SPEED:
            scale = MAX_SPEED / current_speed
            self.vel_x *= scale
            self.vel_z *= scale
            
        # Stop completely if crawling
        if current_speed < 0.1:
            self.vel_x = 0
            self.vel_z = 0
            
        # Apply Horizontal Velocity
        self.x += self.vel_x
        self.z += self.vel_z
        
        # --- Jump ---
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False
            
        # --- Gravity ---
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # --- Collision (Simplified AABB) ---
        ground_level = 0
        hit_platform = False
        
        for obj in map_objects:
            # Check horizontal overlap
            if abs(self.x - obj.x) < (obj.width/2 + self.width/2) and \
               abs(self.z - obj.z) < (obj.depth/2 + self.depth/2):
                   
                   top_surface = obj.y - obj.height/2
                   
                   # Landing logic
                   # Must be falling (vel_y > 0) and close to top surface
                   if self.y + self.height/2 >= top_surface and \
                      self.y + self.height/2 <= top_surface + 30 and \
                      self.vel_y >= 0:
                       ground_level = top_surface - self.height/2
                       hit_platform = True

        if not hit_platform and self.y > 0: # 0 is absolute floor
             ground_level = 0
        elif not hit_platform and self.y > 500: # Fall off map reset
            self.x, self.y, self.z = 0, -100, 0
            self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
            ground_level = 0
            
        if self.y >= ground_level:
            self.y = ground_level
            self.vel_y = 0
            self.on_ground = True

class LevelBlock(Object3D):
    def __init__(self, x, y, z, w, h, d, color):
        super().__init__(x, y, z, color)
        self.width, self.height, self.depth = w, h, d
        self.add_cube(w, h, d, color)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cat's SM64") # Title updated
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 18)

    # Create World
    player = Player(0, 0, 0)
    
    map_objects = []
    
    # Map Generation 
    
    # 1. The Bridge
    map_objects.append(LevelBlock(0, 0, 0, 200, 20, 200, (100, 100, 100))) # Start pad
    
    # 2. Steps
    for i in range(1, 6):
        map_objects.append(LevelBlock(0, -i*20, i*100 + 100, 100, 20, 100, PLATFORM_COLOR))
        
    # 3. Castle Area
    castle_z = 800
    map_objects.append(LevelBlock(0, -100, castle_z, 600, 20, 400, GROUND_COLOR)) # Courtyard
    map_objects.append(LevelBlock(-200, -150, castle_z, 50, 100, 50, CASTLE_COLOR)) # Tower L
    map_objects.append(LevelBlock(200, -150, castle_z, 50, 100, 50, CASTLE_COLOR)) # Tower R
    map_objects.append(LevelBlock(0, -150, castle_z + 100, 300, 100, 100, CASTLE_COLOR)) # Keep
    
    # 4. Floating platforms
    map_objects.append(LevelBlock(300, -50, 300, 80, 20, 80, (200, 100, 100)))
    map_objects.append(LevelBlock(400, -100, 400, 80, 20, 80, (200, 100, 100)))
    map_objects.append(LevelBlock(300, -150, 500, 80, 20, 80, (200, 100, 100)))

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()
        player.update(keys, map_objects)

        # 2. Camera Logic (Follow Player with simple lag/smoothing)
        # Desired Camera Position
        target_cam_x = player.x - math.sin(player.facing_angle) * CAM_DISTANCE
        target_cam_z = player.z - math.cos(player.facing_angle) * CAM_DISTANCE
        target_cam_y = player.y - CAM_HEIGHT
        
        # Current camera pos (direct assignment for stability in this simple engine)
        camera_pos = Vector3(target_cam_x, target_cam_y, target_cam_z)
        
        cam_yaw = -player.facing_angle

        # 3. Rendering
        screen.fill(BG_COLOR)
        
        # Collect all faces to render
        render_list = []
        
        # Add Player Faces
        for face in player.faces:
            world_verts = []
            for v in face.vertices:
                # Local Rotation (Model space)
                rx, rz = rotate_point_y(v.x, v.z, 0, 0, player.facing_angle)
                # World Translation
                wx = rx + player.x
                wy = v.y + player.y
                wz = rz + player.z
                world_verts.append(Vector3(wx, wy, wz))
            render_list.append(Face(world_verts, face.color))
            
        # Add Map Faces
        for obj in map_objects:
            for face in obj.faces:
                world_verts = []
                for v in face.vertices:
                    wx = v.x + obj.x
                    wy = v.y + obj.y
                    wz = v.z + obj.z
                    world_verts.append(Vector3(wx, wy, wz))
                render_list.append(Face(world_verts, face.color))

        # Add floor
        floor_color = (100, 200, 100)
        floor_y = 0
        render_list.append(Face([
            Vector3(-2000, floor_y, -2000),
            Vector3(2000, floor_y, -2000),
            Vector3(2000, floor_y, 2000),
            Vector3(-2000, floor_y, 2000)
        ], floor_color))

        # Project and Sort
        screen_faces = []
        
        for face in render_list:
            cam_verts = []
            in_front = True
            
            for v in face.vertices:
                x = v.x - camera_pos.x
                y = v.y - camera_pos.y
                z = v.z - camera_pos.z
                
                rx, rz = rotate_point_y(x, z, 0, 0, cam_yaw)
                ry = y 
                
                if rz <= 1: 
                    in_front = False
                    break
                    
                scale = FOV / rz
                sx = int(rx * scale + WIDTH / 2)
                sy = int(ry * scale + HEIGHT / 2)
                
                cam_verts.append((sx, sy, rz))
            
            if in_front:
                avg_z = sum(v[2] for v in cam_verts) / len(cam_verts)
                screen_points = [(v[0], v[1]) for v in cam_verts]
                screen_faces.append((avg_z, face.color, screen_points))

        screen_faces.sort(key=lambda x: x[0], reverse=True)

        for _, color, points in screen_faces:
            if len(points) > 2:
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (0, 0, 0), points, 1)

        # HUD - Updated Title
        text = font.render(f"Cat's SM64 | FPS: {int(clock.get_fps())}", True, (0, 0, 0))
        screen.blit(text, (10, 10))
        text2 = font.render("Arrows: Move | Space: Jump", True, (0, 0, 0))
        screen.blit(text2, (10, 30))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
