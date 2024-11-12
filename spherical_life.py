import healpy as hp
import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from dataclasses import dataclass

@dataclass
class GameRules:
    loneliness: int = 2      # Die if fewer than this many neighbors
    overpopulation: int = 3  # Die if more than this many neighbors
    reproduction_min: int = 3 # Born if at least this many neighbors
    reproduction_max: int = 3 # Born if no more than this many neighbors

@dataclass
class Button:
    x: int
    y: int
    width: int
    height: int
    text: str
    
    def is_clicked(self, pos):
        return (self.x <= pos[0] <= self.x + self.width and 
                self.y <= pos[1] <= self.y + self.height)

wide = 1600
high = 900
point_size = 4

nside = 8*4
npix = hp.nside2npix(nside)
vecs = hp.pix2vec(nside, range(npix))

def initialize_random_state():
    return np.random.choice([0, 1], size=npix)

state = initialize_random_state()

def get_neighbors(idx):
    return hp.get_all_neighbours(nside, idx)

def update_state(state, rules):
    new_state = state.copy()
    for i in range(npix):
        neighbors = get_neighbors(i)
        alive_neighbors = sum(state[neighbors] == 1)
        if state[i] == 1:
            if alive_neighbors < rules.loneliness:  # loneliness rule
                new_state[i] = 0
            elif alive_neighbors > rules.overpopulation:  # overpopulation rule
                new_state[i] = 0
        else:
            if (alive_neighbors >= rules.reproduction_min and 
                alive_neighbors <= rules.reproduction_max):  # reproduction rule
                new_state[i] = 1
    return new_state

def draw_slider(x, y, width, value, min_val, max_val, label):
    # Draw slider background
    glColor4f(0.2, 0.2, 0.2, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + 20)
    glVertex2f(x, y + 20)
    glEnd()
    
    # Draw slider position
    pos = x + (value - min_val) / (max_val - min_val) * width
    glColor4f(0.4, 0.6, 0.8, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(pos - 5, y - 5)
    glVertex2f(pos + 5, y - 5)
    glVertex2f(pos + 5, y + 25)
    glVertex2f(pos - 5, y + 25)
    glEnd()
    
    # Draw label and value
    glColor4f(1.0, 1.0, 1.0, 0.9)
    render_text(f"{label}: {value}", x, y - 35, size=16, alpha=0.5, color=(255, 255, 255), font_name='Helvetica Neue')

def render_text(text, x, y, size=20, alpha=1.0, color=(255, 255, 255), font_name=None):
    """
    Render text in OpenGL with customizable font size, alpha, color and font.
    
    Args:
        text (str): Text to render
        x (float): X position
        y (float): Y position
        size (int): Font size in pixels (default: 20)
        alpha (float): Opacity from 0.0 to 1.0 (default: 1.0)
        color (tuple): RGB color tuple (default: white)
        font_name (str): Font name (default: None, uses pygame default font)
    """
    # Create font and render text surface
    if font_name:
        font = pygame.font.SysFont(font_name, size)
    else:
        font = pygame.font.Font(None, size)
    
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    
    # Create OpenGL texture
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(), 
                 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    
    # Enable texture mapping
    glEnable(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    # Draw textured quad with alpha
    glColor4f(1.0, 1.0, 1.0, alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1); glVertex2f(x, y)  # Bottom-left
    glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y)  # Bottom-right
    glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())  # Top-right
    glTexCoord2f(0, 0); glVertex2f(x, y + text_surface.get_height())  # Top-left
    glEnd()
    
    # Clean up
    glDisable(GL_TEXTURE_2D)
    glDeleteTextures([texture])

def render_ui(alive_percentage, generation, rules, buttons):
    glPushMatrix()
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, wide, high, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    glDisable(GL_DEPTH_TEST)
    
    # Draw stats panel
    x, y = 15, 15
    width, height = 200, 80
    
    glColor4f(0.0, 0.0, 0.0, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()
    
    # Draw health bar
    bar_width = 200
    bar_height = 15
    x = 15
    y = 15

    # Border
    glColor4f(0.3, 0.3, 0.3, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + bar_width, y)
    glVertex2f(x + bar_width, y + bar_height)
    glVertex2f(x, y + bar_height)
    glEnd()

    # Health bar
    health_width = int(alive_percentage/100 * bar_width)

    # Calculate distance from optimal 30%
    distance_from_optimal = abs(alive_percentage - 30) / 100
    # Normalize to [0,1] range considering max possible distance (70%)
    normalized_distance = min(1.0, distance_from_optimal / 0.7)

    # Calculate red and green components
    # At optimal (30%), red=0, green=1
    # At extremes (0% or 100%), red=1, green=0
    red = normalized_distance
    green = 1.0 - normalized_distance

    glColor4f(red, green, 0.0, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + health_width, y)
    glVertex2f(x + health_width, y + bar_height)
    glVertex2f(x, y + bar_height)
    glEnd()
    
    # Stats text
    glColor4f(1.0, 1.0, 1.0, 0.9)
    render_text(f"Live Cells: {alive_percentage:.1f}%", x + 10, y + 30, size=16, alpha=0.5, color=(255, 255, 255), font_name='Helvetica Neue')
    render_text(f"Generation: {generation}", x + 10, y + 50, size=16, alpha=0.5, color=(255, 255, 255), font_name='Helvetica Neue')
    
    # Draw rules panel
    rules_x = wide - 280
    rules_y = 15
    rules_width = 260
    rules_height = 280
    
    # Panel background
    glColor4f(0.0, 0.0, 0.0, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(rules_x, rules_y)
    glVertex2f(rules_x + rules_width, rules_y)
    glVertex2f(rules_x + rules_width, rules_y + rules_height)
    glVertex2f(rules_x, rules_y + rules_height)
    glEnd()
    
    # Draw sliders
    slider_x = rules_x + 20
    slider_width = rules_width - 40
    
    draw_slider(slider_x, rules_y + 60, slider_width, 
                rules.loneliness, 1, 8, "Loneliness Threshold")
    draw_slider(slider_x, rules_y + 120, slider_width, 
                rules.overpopulation, 1, 8, "Overpopulation Threshold")
    draw_slider(slider_x, rules_y + 180, slider_width, 
                rules.reproduction_min, 1, 8, "Reproduction Min")
    draw_slider(slider_x, rules_y + 240, slider_width, 
                rules.reproduction_max, 1, 8, "Reproduction Max")
    
    # Draw buttons
    for button in buttons:
        # Button background
        glColor4f(0.2, 0.2, 0.2, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(button.x, button.y)
        glVertex2f(button.x + button.width, button.y)
        glVertex2f(button.x + button.width, button.y + button.height)
        glVertex2f(button.x, button.y + button.height)
        glEnd()
        
        # Button text
        glColor4f(1.0, 1.0, 1.0, 0.9)
        text_width = len(button.text)  # Approximate width of text
        text_x = button.x + (button.width ) / 10
        text_y = button.y + (button.height - 16) / 2 + 16
        render_text(button.text, text_x, text_y-20, size=16, alpha=0.5, color=(255, 255, 255), font_name='Helvetica Neue')
    
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def get_slider_value(mouse_x, slider_x, slider_width, min_val, max_val):
    rel_x = mouse_x - slider_x
    if rel_x < 0:
        return min_val
    if rel_x > slider_width:
        return max_val
    return int(min_val + (rel_x / slider_width) * (max_val - min_val))

def init():
    pygame.init()
    glutInit()
    pygame.display.set_mode((wide, high), DOUBLEBUF | OPENGL)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glPointSize(point_size)
    glClearColor(0.05, 0.06, 0.08, 1.0)

def setup_projection(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(28, width / float(height), 0.01, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def draw_points(state):
    glBegin(GL_POINTS)
    for i, alive in enumerate(state):
        if alive:
            glColor4f(0.6, 0.8, 0.9, 1.0)
        else:
            glColor4f(0.1, 0.1, 0.1, 1.0)
        glVertex3f(vecs[0][i], vecs[1][i], vecs[2][i])
    glEnd()

def draw_sphere(radius=1.0, color=(1.0, 0.0, 0.0), position=(0, 0, 0), slices=32, stacks=32):
    glPushMatrix()
    glTranslatef(*position)
    glColor3f(*color)
    quadric = gluNewQuadric()
    gluSphere(quadric, radius, slices, stacks)
    gluDeleteQuadric(quadric)
    glPopMatrix()

def main(state):
    init()
    setup_projection(wide, high)
    
    rules = GameRules()
    
    buttons = [
        Button(15, high - 55, 120, 40, "Reset"),
        Button(15, high - 105, 120, 40, "Default Rules")
    ]
    
    rotation_x, rotation_y, rotation_z = 0, 0, 0
    distance = 5

    counter = 0
    generation = 0

    mouse_down = False
    last_mouse_x, last_mouse_y = 0, 0
    dragging_slider = None

    random_rotation_speed_x = (np.random.rand() - 0.5) * 0.01
    random_rotation_speed_y = (np.random.rand() - 0.5) * 0.01
    random_rotation_speed_z = (np.random.rand() - 0.5) * 0.01

    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Check buttons
                    for button in buttons:
                        if button.is_clicked(event.pos):
                            if button.text == "Reset":
                                state = initialize_random_state()
                                generation = 0
                            elif button.text == "Default Rules":
                                rules = GameRules()
                            break
                    else:
                        # Check sliders
                        slider_x = wide - 260
                        slider_width = 220
                        if wide - 280 <= event.pos[0] <= wide - 20:
                            if 55 <= event.pos[1] <= 85:
                                dragging_slider = "loneliness"
                            elif 115 <= event.pos[1] <= 145:
                                dragging_slider = "overpopulation"
                            elif 175 <= event.pos[1] <= 205:
                                dragging_slider = "reproduction_min"
                            elif 235 <= event.pos[1] <= 265:
                                dragging_slider = "reproduction_max"
                            else:
                                mouse_down = True
                                last_mouse_x, last_mouse_y = event.pos
                        else:
                            mouse_down = True
                            last_mouse_x, last_mouse_y = event.pos
                elif event.button == 4:
                    distance -= 0.1
                elif event.button == 5:
                    distance += 0.1
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False
                    dragging_slider = None
            elif event.type == MOUSEMOTION:
                if dragging_slider:
                    slider_x = wide - 260
                    slider_width = 220
                    value = get_slider_value(event.pos[0], slider_x, slider_width, 1, 8)
                    setattr(rules, dragging_slider, value)
                elif mouse_down:
                    dx, dy = event.pos[0] - last_mouse_x, event.pos[1] - last_mouse_y
                    rotation_x += dy * 0.1
                    rotation_y += dx * 0.1
                    last_mouse_x, last_mouse_y = event.pos

        counter += 1
        if counter % 20 == 0:
            state = update_state(state,rules)
            generation += 1
            counter = 0

        alive_percentage = (np.sum(state) / npix) * 100

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        rotation_x += random_rotation_speed_x * clock.get_time()
        rotation_y += random_rotation_speed_y * clock.get_time()
        rotation_z += random_rotation_speed_z * clock.get_time()

        glTranslatef(0, 0, -distance)
        glRotatef(rotation_x, 1, 0, 0)
        glRotatef(rotation_y, 0, 1, 0)
        glRotatef(rotation_z, 0, 0, 1)

        draw_sphere(radius=0.95, color=(0.05, 0.06, 0.08), position=(0,0,0))

        draw_points(state)
        
        # Render UI after 3D content
        render_ui(alive_percentage, generation, rules, buttons)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == '__main__':
    main(state)