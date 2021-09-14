import math
import os
import pygame
import pygame.ftfont
import random
import socket
import time

# Useful if you want to develop on laptop. You can have different
# paths for laptop and GPi
if "backer" in socket.gethostname():
    PREFIX = "/home/backer/game/"
else:
    PREFIX = "/home/pi/game/"

BUTTON_A = 0
BUTTON_B = 1
BUTTON_X = 2
BUTTON_Y = 3
BUTTON_START = 7
BUTTON_SELECT = 8

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Maybe helps reduce latency with smaller buffer.
# Must be called before pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

pygame.init()

# Hide the mouse before creating the screen so you never see it.
pygame.mouse.set_visible(False)

# Set up the drawing window
screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT],
                                 pygame.DOUBLEBUF)

# Initialize the joysticks
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

# Everything that should be displayed. Layered means we can assign
# a draw order (layers) to a sprite.
all = pygame.sprite.LayeredUpdates()

# Considered for collision
obstacles = pygame.sprite.Group()

CRASH = pygame.mixer.Sound(PREFIX + "stop.wav")


def rot_center(image, rect, angle):
    """rotate an image while keeping its center"""
    rot_image = pygame.transform.rotate(image, angle)
    # rot_rect = rot_image.get_rect(center=rect.center)
    return rot_image#,rot_rect

ROT_SPEED = 5
SPEED = 2

COLOURS = ["green", "red"]

class Tank(pygame.sprite.Sprite):
    IMAGES = {}

    for col in COLOURS:
        righttank = pygame.image.load("tank-{}.png".format(col)).convert_alpha()
        IMAGES[col] = [righttank]
        for i in range(1, 36):
            IMAGES[col].append(rot_center(righttank, righttank.get_bounding_rect(), i * 10))

    def __init__(self, colour):
        super().__init__()

        self.colour = colour
        self.rot = 0 # in degrees
        self.index = 0
        self.image = Tank.IMAGES[self.colour][self.index]
        self.x = 50
        self.y = 30
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

    def update(self):
        if COLOURS[px] != self.colour:
            return

        x_axis = joystick.get_axis(0)
        if x_axis < 0:
            self.rot = (self.rot + ROT_SPEED + 360) % 360
        if x_axis > 0:
            self.rot = (self.rot - ROT_SPEED + 360) % 360

        self.index = self.rot // 10
        # print(len(Tank.IMAGES))
        # print(self.rot, self.index)

        # self.index = (self.index + 1) % (len(Fuchsia.IMAGES) * 2)
        self.image = Tank.IMAGES[self.colour][self.index]
        self.rect = self.image.get_rect()

        y_axis = joystick.get_axis(1)
        dir = 0
        if y_axis < 0:
            dir = 1
        if y_axis > 0:
            dir = -1

        if dir != 0:
            self.x += dir * SPEED * math.sin((self.rot + 90) * math.pi / 180)
            self.y += dir * SPEED * math.cos((self.rot + 90) * math.pi / 180)
        self.rect.center = (self.x, self.y)

class Box(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        # Need alpha for mask collision
        self.image = pygame.Surface((50, 50)).convert_alpha()
        self.image.fill((0, 255, 0, 255))

        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # Used for collision detection
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect.x += 5
        if self.rect.left > SCREEN_WIDTH:
            self.rect.right = 0


class Explosion(pygame.sprite.Sprite):
    IMAGES = []
    sheet = pygame.image.load(PREFIX + "exp2_0.png").convert_alpha()
    for row in range(4):
        for col in range(4):
            next_frame = pygame.Surface((64, 64)).convert_alpha()
            next_frame.fill((255, 255, 255, 0))
            next_frame.blit(sheet, (0, 0), (col * 64, row * 64, 64, 64))
            IMAGES.append(next_frame)
    del sheet

    def __init__(self, cx, cy):
        super().__init__()

        self.index = 0
        self.image = Explosion.IMAGES[self.index]
        self.rect = pygame.Rect(0, 0, 64, 64)
        self.rect.center = (cx, cy)

    def update(self):
        self.index = (self.index + 1) % (len(self.IMAGES) * 2)
        self.image = self.IMAGES[self.index // 2]

        if self.index == 0:
            self.kill()


class Edge(pygame.sprite.Sprite):
    IMAGES = []
    MASKS = []
    for i in range(36):
        IMAGES.append(pygame.image.load(
            PREFIX + "edge-logo-" + str(i) + ".png").convert_alpha())
        MASKS.append(pygame.mask.from_surface(IMAGES[-1]))
    BLIP = pygame.mixer.Sound(PREFIX + "blip.wav")

    def __init__(self):
        super().__init__()

        self.index = 0
        self.image = Edge.IMAGES[self.index]
        self.mask = Edge.MASKS[self.index]
        self.rect = self.image.get_rect()

        self.rect.center = (random.randint(0, SCREEN_WIDTH),
                            random.randint(0, SCREEN_HEIGHT))

    def update(self):
        x_axis = joystick.get_axis(0)
        if x_axis < 0:
            self.rect.x -= 2
        elif x_axis > 0:
            self.rect.x += 2

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(SCREEN_WIDTH, self.rect.right)

        y_axis = joystick.get_axis(1)
        if y_axis < 0:
            self.rect.y -= 2
        elif y_axis > 0:
            self.rect.y += 2

        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(SCREEN_HEIGHT, self.rect.bottom)

        pressed = False
        for button in [BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y]:
            if joystick.get_button(button):
                pressed = True

        if pressed:
            CRASH.play()
            explosion = Explosion(self.rect.centerx, self.rect.centery)
            all.add(explosion, layer=3)

        # Rotate
        self.index = (self.index + 1) % (len(self.IMAGES) * 5)
        self.image = self.IMAGES[self.index // 5]
        self.mask = self.MASKS[self.index // 5]

        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center


# Used to manage how fast the screen updates.
clock = pygame.time.Clock()

nplayers = len(COLOURS)
players = []
for col in COLOURS:
    p = Tank(col)
    players.append(p)
    all.add(p, layer=2)
px = 0 # current player

box = Box()
all.add(box, layer=1)
obstacles.add(box)

# Run until the user asks to quit
running = True

random.seed()

pygame.ftfont.init()
large_font = pygame.ftfont.Font(None, 36)

text = large_font.render("Hello world!", True, (128, 128, 128, 255))

prev = {
    BUTTON_A: False,
    BUTTON_B: False,
    BUTTON_X: False,
    BUTTON_Y: False,
    BUTTON_SELECT: False,
    BUTTON_START: False
}

while running:

    # To respond to Ctrl-C from terminal need to propage SIGINT
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        exit()

    screen.fill((255, 255, 255, 255))

    curr = {}
    for butt in [BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y, BUTTON_SELECT, BUTTON_START]:
        curr[butt] = joystick.get_button(butt)
    if curr[BUTTON_X] and not prev[BUTTON_X]:
        px = (px + 1) % nplayers
    elif curr[BUTTON_Y] and not prev[BUTTON_Y]:
        px = (px - 1) % nplayers

    # move the sprites
    all.update()

    # draw the sprites
    all.draw(screen)

    # text blitting
    temp_rect = text.get_rect()
    temp_rect.centerx = SCREEN_WIDTH // 2
    temp_rect.top = 40
    screen.blit(text, temp_rect.topleft)

    if joystick.get_button(BUTTON_SELECT):
        running = False

    collisions = pygame.sprite.spritecollide(players[px], obstacles, False,
                                             pygame.sprite.collide_mask)
    if collisions:
        for sprite in collisions:
            (x, y) = pygame.sprite.collide_mask(players[px], sprite)
            explosion = Explosion(players[px].rect.x + x, players[px].rect.y + y)
            all.add(explosion, layer=3)
            sprite.kill()
        CRASH.play()

    # present the draw
    pygame.display.flip()

    prev = curr

    # Try to hit 60 fps
    clock.tick(60)

# Done! Time to quit.
pygame.quit()
