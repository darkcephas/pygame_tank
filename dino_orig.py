import math
import os
import pygame
import pygame.ftfont
import random
import socket
import time
import pickle
import commonnetwork


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

GROUND_SPEED = 3
SKY_SPEED = GROUND_SPEED // 2

# reduce latency with smaller buffer
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

pygame.init()

pygame.mouse.set_visible(False)

#LOOP = pygame.mixer.Sound(PREFIX + "POL-follow-me-short.wav")
LOOP = pygame.mixer.Sound(PREFIX + "music.wav")

# Set up the drawing window
screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT],
                                 pygame.DOUBLEBUF)

# print(pygame.display.get_driver())
# print(pygame.display.Info())

SPRITE_SHEET = pygame.image.load(PREFIX +
                                 "100-offline-sprite.png").convert_alpha()
# Initialize the joysticks
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

score = 0
hi_score = 0

CRASH = pygame.mixer.Sound(PREFIX + "stop.wav")

class Fireworks(pygame.sprite.Sprite):
    IMAGES = []
    sheet = pygame.image.load(PREFIX + "Firework128.png").convert_alpha()
    for row in range(0, 5):
        for col in range(0, 6):
            next_frame = pygame.Surface((128, 128)).convert_alpha()
            next_frame.fill((255, 255, 255, 0))
            next_frame.blit(sheet, (0, 0), (col * 128, row * 128, 128, 128))
            IMAGES.append(next_frame)
    del sheet

    def __init__(self):
        super().__init__()

        self.index = 0
        self.image = Fireworks.IMAGES[self.index]
        self.rect = pygame.Rect(
            random.randint(64, 256), random.randint(32, 64), 128, 128)

    def update(self):
        self.index = (self.index + 1) % (len(Fireworks.IMAGES) * 2)
        self.image = Fireworks.IMAGES[self.index // 2]

        if self.index == 0:
            self.kill()

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
        self.rect.centerx = cx
        self.rect.centery = cy

    def update(self):
        self.index = (self.index + 1) % (len(self.IMAGES) * 2)
        self.image = self.IMAGES[self.index // 2]
        if self.index == 0:
            self.kill()


class Fuchsia(pygame.sprite.Sprite):
    IMAGES = []
    for i in range(36):
        IMAGES.append(pygame.image.load(
            PREFIX + "fuchsia-logo-" + str(i) + ".png").convert_alpha())

    def __init__(self):
        super().__init__()

        self.index = 0
        self.image = Fuchsia.IMAGES[self.index]
        self.rect = self.image.get_rect()
        self.rect.y = 20

        choice = random.randint(0,1)
        if choice == 0:
           self.dx = - GROUND_SPEED // 2
           r = random.randint(-100, 100)
           if r < 0:
              self.rect.left = SCREEN_WIDTH + r
              self.rect.top = 20
           else:
              self.rect.left = SCREEN_WIDTH
              self.rect.top = 20 + r
        elif choice == 1:
           self.dx = GROUND_SPEED // 2
           r = random.randint(-100, 100)
           if r > 0:
              self.rect.right = r
              self.rect.top = 20
           else:
              self.rect.right = 0
              self.rect.top = 20 - r

    def update(self):
        self.index = (self.index + 1) % (len(Fuchsia.IMAGES) * 2)
        self.image = Fuchsia.IMAGES[self.index // 2]

        left = self.rect.left
        bottom = self.rect.bottom

        self.rect = self.image.get_rect()
        self.rect.left = left + self.dx
        self.rect.bottom = bottom + GROUND_SPEED // 2

        if self.rect.bottom > SCREEN_HEIGHT:
            global score
            score += 10
            self.kill()


# 22 frame jump curve
JUMP_Y = (8, 16, 24, 32, 36, 40, 44, 48, 50, 52, 54, 56, 58, 59, 60, 61, 62,
          62, 63, 63, 63, 63)


class Edge(pygame.sprite.Sprite):
    IMAGES = []
    MASKS = []
    for i in range(36):
        IMAGES.append(pygame.image.load(
            PREFIX + "edge-logo-" + str(i) + ".png").convert_alpha())
        MASKS.append(pygame.mask.from_surface(IMAGES[-1]))

    def __init__(self):
        super().__init__()

        self.index = random.randint(0, len(Edge.IMAGES)-1)
        self.image = Edge.IMAGES[self.index]
        self.mask = Edge.MASKS[self.index]
        self.rect = self.image.get_rect()
        self.rect.left = SCREEN_WIDTH
        self.rect.bottom = 187
        self.jump_count = random.randint(0, 22)

    def update(self):
        self.index = (self.index + 1) % (len(Edge.IMAGES) * 2)
        self.image = Edge.IMAGES[self.index // 2]
        self.mask = Edge.MASKS[self.index // 2]

        left = self.rect.left
        self.rect.left = left - GROUND_SPEED - 1

        if self.jump_count == 44:
            self.rect.bottom = 187
        elif self.jump_count >= 22:
            self.rect.bottom = 187 - JUMP_Y[44 - self.jump_count - 1]
        else:
            self.rect.bottom = 187 - JUMP_Y[self.jump_count]

        self.jump_count += 1
        if self.jump_count > 44:
            self.jump_count = 0

        if self.rect.right < 0:
            global score
            score += 10
            self.kill()


class IE6(pygame.sprite.Sprite):
    IMAGES = []
    MASKS = []
    for i in range(36):
        IMAGES.append(pygame.image.load(
            PREFIX + "IE6-logo-" + str(i) + ".png").convert_alpha())
        MASKS.append(pygame.mask.from_surface(IMAGES[-1]))

    def __init__(self, move_left):
        super().__init__()

        self.move_left = move_left

        self.index = random.randint(0, len(IE6.IMAGES)-1)
        self.image = IE6.IMAGES[self.index]
        self.mask = IE6.MASKS[self.index]

        self.rect = self.image.get_rect()
        self.rect.left = SCREEN_WIDTH
        self.rect.bottom = 195

    def update(self):
        if self.move_left:
            self.index = (self.index + 1) % (len(IE6.IMAGES) * 3)
            self.image = IE6.IMAGES[self.index // 3]
            self.mask = IE6.MASKS[self.index // 3]
        else:
            self.index = (self.index - 1) % (len(IE6.IMAGES) * 6)
            self.image = IE6.IMAGES[self.index // 6]
            self.mask = IE6.MASKS[self.index // 6]

        centerx = self.rect.centerx
        centery = self.rect.centery

        self.rect = self.image.get_rect()

        if self.move_left:
            self.rect.centerx = centerx - GROUND_SPEED - 1
        else:
            self.rect.centerx = centerx - GROUND_SPEED

        self.rect.centery = centery

        if self.rect.right < 0:
            global score
            score += 10
            self.kill()


class Beetle(pygame.sprite.Sprite):
    IMAGES = []
    MASKS = []
    for i in range(2):
        IMAGES.append(pygame.image.load(
            PREFIX + "beetle-" + str(i) + ".png").convert_alpha())
        MASKS.append(pygame.mask.from_surface(IMAGES[-1]))

    def __init__(self, move_left):
        super().__init__()

        self.move_left = move_left
        if self.move_left:
            self.image = Beetle.IMAGES[0]
            self.mask = Beetle.MASKS[0]
        else:
            self.image = Beetle.IMAGES[1]
            self.mask = Beetle.MASKS[1]

        self.rect = self.image.get_rect()
        if self.move_left:
            self.rect.left = 360
        else:
            self.rect.right = 335

        self.rect.bottom = 190

    def update(self):
        if self.move_left:
            self.rect.x -= GROUND_SPEED + 1
        else:
            self.rect.x -= GROUND_SPEED

        if self.rect.right < 0:
            self.kill()


class Cloud(pygame.sprite.Sprite):
    IMAGE = pygame.Surface((45, 15))
    IMAGE.fill((255, 255, 255))
    IMAGE.blit(SPRITE_SHEET, (0, 0), (83, 0, 45, 15))

    def __init__(self):
        super().__init__()

        self.image = Cloud.IMAGE
        self.rect = pygame.Rect(SCREEN_WIDTH, random.randint(0, 120), 45, 15)

    def update(self):
        self.rect.x -= SKY_SPEED
        if self.rect.right < 0:
            self.kill()


class Dino(pygame.sprite.Sprite):
    DINO_MAP = {
        "WAITING_1": {
            "x": 44,
            "w": 44,
            "h": 47
        },
        "WAITING_2": {
            "x": 0,
            "w": 44,
            "h": 47
        },
        "RUNNING_1": {
            "x": 88,
            "w": 44,
            "h": 47
        },
        "RUNNING_2": {
            "x": 132,
            "w": 44,
            "h": 47
        },
        "JUMPING": {
            "x": 0,
            "w": 44,
            "h": 47
        },
        "CRASHED": {
            "x": 220,
            "w": 44,
            "h": 47
        },
        "DUCK_1": {
            "x": 264,
            "w": 59,
            "h": 47
        },
        "DUCK_2": {
            "x": 323,
            "w": 59,
            "h": 47
        },
    }

    BLIP = pygame.mixer.Sound(PREFIX + "blip.wav")

    def __init__(self):
        super().__init__()
        self.images = {}
        self.masks = {}
        for key, value in self.DINO_MAP.items():
            image = pygame.Surface((value["w"], value["h"])).convert_alpha()
            image.fill((255, 255, 255, 0))
            image.blit(SPRITE_SHEET, (0, 0),
                       (value["x"] + 848, 0, value["w"], 48))
            self.images[key] = image
            self.masks[key] = pygame.mask.from_surface(image)

        self.jumping = False
        self.jump_count = 0

        self.frames = 0

        self.x = 30
        self.y = 145

        self.state = "WAITING_2"
        self.update_helper()

    def update_helper(self):
        state = self.state

        if self.state in ["RUNNING_1", "DUCK_1"]:
            step = int(self.frames // 5) % 2

            if step == 1:
                state = self.state.replace("1", "2")

        self.image = self.images[state]
        self.mask = self.masks[state]
        self.rect = pygame.Rect(self.x, self.y, self.DINO_MAP[state]["w"],
                                self.DINO_MAP[state]["h"])

    def update(self):
        y_axis = joystick.get_axis(1)

        pressed = False
        for button in [BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y]:
            if joystick.get_button(button):
                pressed = True

        if pressed and not self.jumping and y_axis <= 0:
            self.state = "JUMPING"
            self.jumping = True
            self.jump_count = 0
            Dino.BLIP.play()

        self.frames += 1

        # Move back and forth a bit
        x_axis = joystick.get_axis(0)
        if x_axis < 0:
            dx = -GROUND_SPEED
            if not self.jumping:
                if self.x + dx > 30:
                    self.state = "WAITING_2"
                else:
                    self.state = "RUNNING_1"
        elif x_axis > 0:
            dx = SKY_SPEED
            if not self.jumping:
                self.state = "RUNNING_1"
        else:
            dx = 0
            if not self.jumping:
                self.state = "RUNNING_1"

        self.x += dx

        # Clamp it
        self.x = max(30, min(self.x, SCREEN_HEIGHT))

        if self.jumping:
            if y_axis > 0:
                if self.jump_count <= 22:
                    self.jump_count = 44 - self.jump_count

            if self.jump_count >= 44:
                self.jumping = False
                self.y = 145
            else:
                if self.jump_count >= 22:
                    self.y = 145 - JUMP_Y[44 - self.jump_count - 1]
                else:
                    self.y = 145 - JUMP_Y[self.jump_count]

                if y_axis > 0:
                    self.jump_count += 2
                else:
                    self.jump_count += 1
        else:
            if y_axis > 0:
                self.state = "DUCK_1"

        self.update_helper()


class Cactus(pygame.sprite.Sprite):
    WIDTH = 17
    HEIGHT = 35

    def __init__(self, x=SCREEN_WIDTH):
        super().__init__()
        image = pygame.Surface((self.WIDTH, self.HEIGHT)).convert_alpha()
        image.fill((255, 255, 255, 0))
        image.blit(
            SPRITE_SHEET, (0, 0),
            (229 + (random.randint(0, 5) * self.WIDTH), 2, self.WIDTH, self.HEIGHT))
        self.image = image
        @self.image = pygame.transform.rotate(self.image, 60)
        self.mask = pygame.mask.from_surface(image)
        self.rect = pygame.Rect(x, 155, self.WIDTH, self.HEIGHT)

    def update(self):
        self.rect.x -= GROUND_SPEED
  
        if self.rect.right < 0:
            global score
            score += 5
            self.kill()


class TallCactus(pygame.sprite.Sprite):
    WIDTH = 49
    HEIGHT = 53

    def __init__(self, x=SCREEN_WIDTH):
        super().__init__()
        image = pygame.Surface((self.WIDTH, self.HEIGHT)).convert_alpha()
        image.fill((255, 255, 255, 0))
        image.blit(
            SPRITE_SHEET, (0, 0),
            (332 + (random.randint(0, 2) * self.WIDTH), 2, self.WIDTH, self.HEIGHT))
        self.image = image
        self.mask = pygame.mask.from_surface(image)
        self.rect = pygame.Rect(x, 143, self.WIDTH, self.HEIGHT)

    def update(self):
        self.rect.x -= GROUND_SPEED

        if self.rect.right < 0:
            global score
            score += 10
            self.kill()


class Pterosaur(pygame.sprite.Sprite):
    WIDTH = 46
    HEIGHT = 40
    IMAGES = []
    MASKS = []
    V_POS = [100, 120, 140]
    for col in range(2):
        next_frame = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
        next_frame.fill((255, 255, 255, 0))
        next_frame.blit(SPRITE_SHEET, (0, 0),
                        (134 + (col * WIDTH), 2, WIDTH, HEIGHT))
        IMAGES.append(next_frame)
        MASKS.append(pygame.mask.from_surface(next_frame))

    def __init__(self, x=SCREEN_WIDTH):
        super().__init__()

        self.index = 0
        self.image = Pterosaur.IMAGES[self.index]
        self.mask = Pterosaur.MASKS[self.index]
        y = self.V_POS[random.randint(0, 2)]
        self.rect = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)

    def update(self):
        UPDATES_PER_FRAME = 10
        self.index = (self.index + 1) % (len(Pterosaur.IMAGES)
                                         * UPDATES_PER_FRAME)
        self.image = Pterosaur.IMAGES[self.index // UPDATES_PER_FRAME]
        self.mask = Pterosaur.MASKS[self.index // UPDATES_PER_FRAME]

        # just a little faster
        self.rect.x -= (GROUND_SPEED+1)

        if self.rect.right < 0:
            global score
            score += 10
            self.kill()


# Used to manage how fast the screen updates.
clock = pygame.time.Clock()

# creating a group with our sprite
all = pygame.sprite.LayeredUpdates()
obstacles = pygame.sprite.Group()
explosions = pygame.sprite.Group()

dino = Dino()
all.add(dino, layer=3)

# Run until the user asks to quit
running = True

random.seed()

pygame.ftfont.init()
font = pygame.ftfont.Font(None, 24)
large_font = pygame.ftfont.Font(None, 36)

HEART = pygame.image.load(PREFIX + "heart.png").convert_alpha()

def reset():
    global starting_count
    starting_count = 60 * 3

    global obstacle_counter
    obstacle_counter = SCREEN_WIDTH // 2

    global obstacle_spacing
    obstacle_spacing = SCREEN_WIDTH // 2

    global obstacles
    for obstacle in obstacles:
        obstacle.kill()

    global score
    score = 0

    global hearts
    hearts = 3

    global no_damage_counter
    no_damage_counter = 0

    LOOP.play(loops=-1)
reset()

def Scroll(move_ground):
    if random.randint(1, 75) == 25:
        all.add(Cloud(), layer=0)

    if move_ground:
        try:
            Scroll.x_scroll += GROUND_SPEED
        except AttributeError:
            Scroll.x_scroll = 0

    X_MAX = 1200
    if (Scroll.x_scroll >= X_MAX):
        Scroll.x_scroll = 0

    # draw the ground
    if (Scroll.x_scroll + SCREEN_WIDTH < X_MAX):
        pygame.Surface.blit(screen, SPRITE_SHEET, (0, 180),
                            (Scroll.x_scroll, 52, SCREEN_WIDTH, 14))
    else:
        pygame.Surface.blit(screen, SPRITE_SHEET, (0, 180),
                            (Scroll.x_scroll, 52, X_MAX - Scroll.x_scroll, 14))
        pygame.Surface.blit(screen, SPRITE_SHEET, (X_MAX - Scroll.x_scroll, 180),
                            (0, 52, SCREEN_WIDTH, 14))

def DrawStatus():
    # Score rendering
    text = font.render("Score: " + str(score), True,
                       (128, 128, 128, 255))
    temp_rect = text.get_rect()
    temp_rect.right = 310
    temp_rect.top = 10
    screen.blit(text, (temp_rect.x, temp_rect.y))

    global hi_score
    if hi_score < score:
        hi_score = score
    text = font.render("Score: " + str(hi_score), True,
                       (128, 128, 128, 255))
    temp_rect = text.get_rect()
    temp_rect.left = 10
    temp_rect.top = 10
    screen.blit(text, (temp_rect.x, temp_rect.y))

    for i in range(hearts):
        screen.blit(HEART, (178 - (i*18), 10))


# TITLE SCREEN
title_text = large_font.render("chrome://dino uneditted", True,
                               (128, 128, 128, 255))
d_pad_text = font.render("D-pad to left, right, drop, crouch", True,
                         (128, 128, 128, 255))
button_text = font.render("A,B,X,Y to jump", True,
                          (128, 128, 128, 255))
start_text = font.render("Press START to play", True,
                         (128, 128, 128, 255))

while not joystick.get_button(BUTTON_START):
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        exit()
    screen.fill((255, 255, 255, 255))

    Scroll(True)

    # move the sprites
    all.update()

    # draw the sprites
    all.draw(screen)

    # Score rendering
    temp_rect = title_text.get_rect()
    temp_rect.centerx = 160
    temp_rect.top = 40
    screen.blit(title_text, temp_rect.topleft)

    temp_rect = d_pad_text.get_rect()
    temp_rect.left = 20
    temp_rect.top = 80
    screen.blit(d_pad_text, temp_rect.topleft)

    temp_rect = button_text.get_rect()
    temp_rect.left = 20
    temp_rect.top = 100
    screen.blit(button_text, temp_rect.topleft)

    temp_rect = start_text.get_rect()
    temp_rect.left = 20
    temp_rect.top = 200
    screen.blit(start_text, temp_rect.topleft)

    pygame.display.flip()

while running:
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        running = False
    # Condition becomes true when keyboard is pressed
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_q:
            running = False
    if joystick.get_button(BUTTON_SELECT):
        running = False

    screen.fill((255, 255, 255, 255))

#  if random.randint(1, 150) == 25:
#    all.add(Fireworks(), layer = 1)

#  if random.randint(1, 100) < 5:
#    all.add(Fuchsia(), layer = 1)

    def AddCacti(use_tall, num_cacti):
        i = 0
        width = 0
        while i < num_cacti:
            if (not use_tall) or random.randint(1, 2) == 1:
                cactus = Cactus(SCREEN_WIDTH + width)
                i += 1
            else:
                cactus = TallCactus(SCREEN_WIDTH + width)
                i += 2
            all.add(cactus, layer=2)
            obstacles.add(cactus)
            width += cactus.rect.width
        return width

    if starting_count > 0:
        starting_count -= 1
    else:
        obstacle_counter += GROUND_SPEED
        if obstacle_counter > obstacle_spacing:
            obstacle_spacing = random.randint(140, 200)
            obstacle_counter = 0
            if score < 50: 
                width = AddCacti(False, random.randint(1, 2))
                obstacle_spacing += width
            elif score < 100:
                width = AddCacti(True, random.randint(1, 2))
                obstacle_spacing += width
            elif score < 200:
                pterosaur = Pterosaur()
                all.add(pterosaur, layer=2)
                obstacles.add(pterosaur)
                obstacle_spacing += pterosaur.rect.width
            elif score < 350:
                move_left = (random.randint(1, 2) == 1)
                poop = IE6(move_left)
                obstacle_spacing += poop.rect.width
                all.add(poop, layer=2)
                obstacles.add(poop)
                beetle = Beetle(move_left)
                obstacle_spacing += beetle.rect.width
                all.add(beetle, layer=2)
                obstacles.add(beetle)
            elif score < 500:
                edge = Edge()
                obstacle_spacing += edge.rect.width
                all.add(edge, layer=2)
                obstacles.add(edge)
            else:
                fuchsia = Fuchsia()
                obstacle_spacing += fuchsia.rect.width
                all.add(fuchsia, layer=2)
                obstacles.add(fuchsia)

    Scroll(True)

    # move the sprites
    all.update()

    # draw the sprites
    all.draw(screen)

    # Start sequence rendering
    text = None
    delta = None
    if starting_count > 120:
        # varies from 0..1
        delta = (180 - starting_count)/60.0
        text = "Ready..."
    elif starting_count > 60:
        delta = (120 - starting_count)/60.0
        text = "Set..."
    elif starting_count > 0:
        delta = (60 - starting_count)/60.0
        text = "GO!"
    if text:
        text = font.render(text, True, (128, 128, 128, 255-int(delta*255)))
        zoom = delta * 1.5 + 1
        text = pygame.transform.smoothscale(
            text, (int(text.get_rect().width*zoom), int(text.get_rect().height*zoom)))
        temp_rect = text.get_rect()
        temp_rect.centerx = 160
        temp_rect.centery = 120
        screen.blit(text, (temp_rect.x, temp_rect.y))

    DrawStatus()

    if no_damage_counter > 0:
        no_damage_counter -= 1

    collisions = pygame.sprite.spritecollide(dino, obstacles, False,
                                             pygame.sprite.collide_mask)
    if collisions:
        for sprite in collisions:
            (x, y) = pygame.sprite.collide_mask(dino, sprite)
            explosion = Explosion(dino.rect.x + x, dino.rect.y + y)
            all.add(explosion, layer=4)
            explosions.add(explosion)
            sprite.kill()
        CRASH.play()

        if no_damage_counter == 0:
           hearts -= 1
           no_damage_counter = 20

        if hearts < 0:
            LOOP.stop()
            pygame.display.flip()
            clock.tick(60)

            while len(explosions) > 0:
                screen.fill((255, 255, 255, 255))
                Scroll(False)
                all.draw(screen)
                explosions.update()
                DrawStatus()

                text = large_font.render("GAME OVER", True, (128, 128, 128, 255))
                temp_rect = text.get_rect()
                temp_rect.centerx = 160
                temp_rect.centery = 90
                screen.blit(text, (temp_rect.x, temp_rect.y))

                text = font.render("Press START to play again",
                                   True, (128, 128, 128, 255))
                temp_rect = text.get_rect()
                temp_rect.centerx = 160
                temp_rect.centery = 120
                screen.blit(text, (temp_rect.x, temp_rect.y))

                pygame.display.flip()
                clock.tick(60)

            waiting = True
            while waiting:
                event = pygame.event.poll()
                if event.type == pygame.QUIT:
                    running = False
                    waiting = False
                if joystick.get_button(BUTTON_START):
                    waiting = False
                time.sleep(0.1)
            reset()
    else:
        # present the draw
        pygame.display.flip()

    # Try to hit 60 fps
    clock.tick(60)

# Done! Time to quit.
pygame.quit()
