import os
import pygame


class Ball(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((100,100))
        pygame.draw.circle(self.image, (0, 0, 255), (50, 50), 50)

os.environ["SDL_VIDEODRIVER"] = "wayland"
# reduce latency with smaller buffer
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

pygame.init()


# Set up the drawing window
print(pygame.display.list_modes())

screen = pygame.display.set_mode([640,480], pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)


car_img = pygame.image.load("car.png").convert_alpha()
image_w, image_h = car_img.get_size()
scale = 100/image_w

car_rot = []
for rot in range(0, 360, 2):
  car_rot.append(pygame.transform.rotozoom(car_img, rot, scale))

# Used to manage how fast the screen updates.
clock = pygame.time.Clock()

pygame.mouse.set_visible(False)

# Initialize the joysticks
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

blip_sound = pygame.mixer.Sound("blip.wav")

# Run until the user asks to quit
running = True

x = 250
y = 250
dx = 0
dy = 0
color = (0, 0, 255)
rot = 0

def blip():
    pygame.mixer.Sound.play(blip_sound)
    pygame.mixer.music.stop()

while running:
    # Did the user click the window close button?
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN:
            if joystick.get_button(7):  # start
                running = False
            if joystick.get_button(0):
                color = (255, 0, 0)
            if joystick.get_button(1):
                color = (0, 255, 0)
            if joystick.get_button(2):
                color = (0, 0, 255)
            if joystick.get_button(3):
                color = (127, 127, 127)

        elif event.type == pygame.JOYBUTTONUP:
            print("Joystick button released.")

    x_axis = joystick.get_axis(0)
    if x_axis < 0:
        dx = -5
    elif x_axis > 0:
        dx = 5

    y_axis = joystick.get_axis(1)
    if y_axis < 0:
        dy = -5
    elif y_axis > 0:
        dy = 5

    x += dx
    y += dy

    # Clamp
    if x < 100:
        x = 100
        dx = 0
        blip()
    if x > 550:
        x = 550
        dx = 0
        blip()

    if y < 100:
        y = 100
        dy = 0
        blip()
    if y > 400:
        y = 400
        dy = 0
        blip()

    # Fill the background with white
    screen.fill((255, 255, 255))

    rot = (rot + 1) % 180
    pygame.Surface.blit(screen, car_rot[rot], (0,0))
    
    # Draw a solid blue circle in the center
    pygame.draw.circle(screen, color, (x, y), 75)

    # Flip the display
    pygame.display.flip()

    # Limit to 30 fps
    clock.tick(30)

# Done! Time to quit.
pygame.quit()
