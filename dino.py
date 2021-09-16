import math
import os
import pygame
import pygame.ftfont
import random
import socket
import time
import pickle
import commonnetwork
import clientmulti
import enum
import copy
import sys
import random
import math
import uuid
from enum import IntEnum


is_raspberry = "raspberry" in socket.gethostname()
HOST = "97.108.128.161"

has_extra_arg = False
if len(sys.argv) > 1:
    has_extra_arg = True
    
g_user_id = str(uuid.getnode())
if has_extra_arg:
    g_user_id += "XX"

print("user_id:" + str(g_user_id))
client_control = clientmulti.ClientController()

client_control.SetupConnection( "tank" ,  g_user_id , 0, HOST)



#for rollback
saved_sim = []

class MsgEnum(IntEnum):
    GAME_POST_FRAME = 2
    ACTION_RIGHT = 3
    ACTION_LEFT = 4
    ACTION_UP = 5
    ACTION_DOWN = 6
    ACTION_SHIELD = 7
    ACTION_FIRE = 8
    GAME_PLAYER_TEAM = 9


PREFIX = "/home/pi/game/"

#running from dir
if(not is_raspberry):
    PREFIX = ""

BUTTON_A = 0
BUTTON_B = 1
BUTTON_X = 2
BUTTON_Y = 3
BUTTON_START = 7
BUTTON_SELECT = 8

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

RED_COLOR = (255,0, 0, 255)
GREEN_COLOR = (0,255, 0, 255)
BLUE_COLOR = (0,0, 255, 255)
YELLO_COLOR = (255,255, 0, 255)

SHIELD_TIME = 30 * 2
SHIELD_COOLOFF = 30 * 7
EXPLOSION_RAD = 60
# reduce latency with smaller buffer
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

pygame.init()

pygame.mouse.set_visible(False)

#LOOP = pygame.mixer.Sound(PREFIX + "POL-follow-me-short.wav")

# Set up the drawing window
screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT],
                                 pygame.DOUBLEBUF)

# print(pygame.display.get_driver())
# print(pygame.display.Info())

# Initialize the joysticks
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)
joystick.init()

score = 0
hi_score = 0
g_holding_down_fire = 0
player_name_images = {}


COLOURS = ["green", "red", "white"]
WORLD_GRID = 100
BULLET_FLIGHT_TIME = 30 * 2
BULLET_COOLDOWN_TIME = 2 * 30# after bullet has exploded
BULLET_EXPLODING_TIME = 30
HEALTH_MAX = 100
g_map_image = pygame.image.load(PREFIX + "tank_map.png")


class PlayerState:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.posx = 133 * WORLD_GRID
        self.posy = 100 * WORLD_GRID
        self.colour = "white"
        self.rot_index = 0 # rotation 0-35 aka 360 degrees
        self.shield_active_frame = -10000 #
        self.health = HEALTH_MAX
        self.bullet_explode_frame = -1000
        self.bullet_x_start = 0
        self.bullet_y_start = 0
        self.bullet_x_end = 0
        self.bullet_y_end = 0
        self.explosion_radius = 0
    
    def ToNormalPosition(self):
        global g_map_image
        posx_int = min(max( int(self.posx//WORLD_GRID),0) , g_map_image.get_width()-1)
        posy_int = min(max( int(self.posy//WORLD_GRID),0) , g_map_image.get_height()-1)
        return (posx_int,posy_int)

class SimState:
    def __init__(self):
        self.next_frame = 0
        self.players = {} # user, PlayerState()
    
simstate = SimState()


def rot_center(image, rect, angle):
    """rotate an image while keeping its center"""
    rot_image = pygame.transform.rotate(image, angle)
    # rot_rect = rot_image.get_rect(center=rect.center)
    return rot_image#,rot_rect

ROT_SPEED = 5
SPEED = 2


sin_rot = []
cos_rot = []
for i in range(0, 36):
    sin_rot.append( math.sin( math.radians(i * 10.0)))
    cos_rot.append( -math.cos( math.radians(i * 10.0)))

g_tank_images = {}

for col in COLOURS:
    righttank = pygame.image.load(PREFIX + "tank-{}.png".format(col))
    g_tank_images[col] = []
    for i in range(0, 36):
        g_tank_images[col].append(rot_center(righttank, righttank.get_bounding_rect(), i * 10.0))
        g_tank_images[col][i].convert_alpha()


# Used to manage how fast the screen updates.
clock = pygame.time.Clock()

# creating a group with our sprite
all = pygame.sprite.LayeredUpdates()
obstacles = pygame.sprite.Group()
explosions = pygame.sprite.Group()

# Run until the user asks to quit
running = True

random.seed()

pygame.ftfont.init()
font = pygame.ftfont.Font(None, 24)
large_font = pygame.ftfont.Font(None, 36)
HEART = pygame.image.load(PREFIX + "heart.png").convert_alpha()
g_cam_loc = (0,0)
g_cam_vel = (0,0)
CAM_DIR_MULT = 80

def BlitScreenCenter(local_image, center_image):
    screen.blit(local_image, center_image)

def DrawSimulationState():
    global simstate
    global g_tank_images
    global g_user_id
    global g_cam_loc
    global g_cam_vel
    global g_holding_down_fire
    # update camera
    player_own = simstate.players[g_user_id]
    screen_pos_user = (player_own.posx//WORLD_GRID, player_own.posy//WORLD_GRID) 
    cam_target_loc = (screen_pos_user[0]-SCREEN_WIDTH//2,  screen_pos_user[1] -SCREEN_HEIGHT//2)
    g_cam_vel = (cos_rot[player_own.rot_index] * 0.1 + 0.9 * g_cam_vel[0] ,sin_rot[player_own.rot_index] * 0.1 + 0.9 * g_cam_vel[1])
    g_cam_loc = (cam_target_loc[0] - g_cam_vel[0] * CAM_DIR_MULT, cam_target_loc[1] - g_cam_vel[1] *CAM_DIR_MULT)
    
    
    BlitScreenCenter(g_map_image, (-g_cam_loc[0], -g_cam_loc[1]))
    if g_holding_down_fire > 0:
        screen_pos_cam =  (screen_pos_user[0] - g_cam_loc[0], screen_pos_user[1] -g_cam_loc[1])
        screen_bomb_cam = (screen_pos_cam[0] - cos_rot[player_own.rot_index] * g_holding_down_fire, screen_pos_cam[1] - sin_rot[player_own.rot_index] * g_holding_down_fire)
        screen_bomb_cam = (int(screen_bomb_cam[0]), int(screen_bomb_cam[1]))
        pygame.draw.line(screen, (128,128,128,128), screen_pos_cam, screen_bomb_cam)
        pygame.draw.circle(screen, (128,128,128,128), screen_bomb_cam, 13, 1)
    
    for key, player in simstate.players.items():
        temp_image = g_tank_images[player.colour][player.rot_index]
        trect = temp_image.get_rect()
        screen_pos = (player.posx//WORLD_GRID, player.posy//WORLD_GRID) 
        screen_pos = (screen_pos[0] - g_cam_loc[0], screen_pos[1] -g_cam_loc[1])
        screen_pos = (int(screen_pos[0]), int(screen_pos[1]))
        temp_center = (screen_pos[0]- trect.centerx , screen_pos[1] - trect.centery)
        BlitScreenCenter(temp_image, temp_center)
        side = 30
        is_tank_in_full_view = screen_pos[0] > side and screen_pos[1] > side and (screen_pos[0] + side  < SCREEN_WIDTH)  and (screen_pos[1] + side  < SCREEN_HEIGHT )
        if key != g_user_id and is_tank_in_full_view: # dont draw self name
            screen.blit(player_name_images[key], (screen_pos[0] + 16, screen_pos[1] -16))
        
        # shield when active
        if(is_tank_in_full_view and player.shield_active_frame + SHIELD_TIME >= g_frame_idx):
            pygame.draw.circle(screen, (50,50,255,40), screen_pos, 27, 4)
        
        # rotated health bar
        if is_tank_in_full_view and player.health > 0:
            arc_radius = 20
            arc_rect = pygame.Rect(screen_pos[0] - arc_radius, screen_pos[1] - arc_radius, arc_radius * 2,  arc_radius * 2)
            arc_stop_angle =  ((3.14159 * player.health) / HEALTH_MAX) * 2.0
            pygame.draw.arc(screen, (255,10,255,40), arc_rect, 0.0, arc_stop_angle, 1)
        
        # bomb is flying
        if g_frame_idx <= player.bullet_explode_frame:
            bomb_lerp = float(player.bullet_explode_frame - g_frame_idx) / BULLET_FLIGHT_TIME
            bomb_lerp_m1 = 1.0 - bomb_lerp
            bombx = int( (player.bullet_x_start * bomb_lerp + player.bullet_x_end * bomb_lerp_m1)// WORLD_GRID - g_cam_loc[0])
            bomby = int( (player.bullet_y_start * bomb_lerp + player.bullet_y_end * bomb_lerp_m1)// WORLD_GRID - g_cam_loc[1])
            pygame.draw.circle(screen, (0,0,0,255), (bombx,bomby), 7, 7)
            
        if player.explosion_radius > 0.0:
            explodex = int( player.bullet_x_end// WORLD_GRID - g_cam_loc[0])
            explodey = int( player.bullet_y_end// WORLD_GRID - g_cam_loc[1])
            rad_exp = int( player.explosion_radius// WORLD_GRID)
            pygame.draw.circle(screen, (0,0,0,255), (explodex,explodey), rad_exp, 1)
            pygame.draw.circle(screen, YELLO_COLOR, (explodex,explodey), rad_exp+ 2, 2)
            pygame.draw.circle(screen, (0,0,0,255), (explodex,explodey), rad_exp+3, 1)
    
def CreateNewPlayer(user_id):
    global simstate
    simstate.players[user_id] = PlayerState()
    name_text = font.render(user_id, True, (128, 128, 128, 70))
    player_name_images[user_id] = name_text;
    return simstate.players[user_id]

def CreateUserMessages(action_frame_next):
    global g_holding_down_fire
    x_axis = joystick.get_axis(0)
    y_axis = joystick.get_axis(1)
    action_to_take = None
    if x_axis > 0.5:
        action_to_take = MsgEnum.ACTION_RIGHT

    if x_axis < -0.5:
        action_to_take = MsgEnum.ACTION_LEFT
        
        
    if y_axis > 0.5:
        action_to_take = MsgEnum.ACTION_DOWN

    if y_axis < -0.5:
        action_to_take = MsgEnum.ACTION_UP
        
    if action_to_take:
        test_msg = commonnetwork.NetworkMessage()
        test_msg.frame_id = action_frame_next
        test_msg.game_action = int(action_to_take)
        client_control.SendMsg(test_msg)
     
    if joystick.get_button(BUTTON_A):
        g_holding_down_fire +=4
    elif g_holding_down_fire > 1:
        test_msg = commonnetwork.NetworkMessage()
        test_msg.frame_id = action_frame_next
        test_msg.game_action = int(MsgEnum.ACTION_FIRE)
        test_msg.event_id = int(g_holding_down_fire)
        client_control.SendMsg(test_msg)
        g_holding_down_fire = 0
        
    if joystick.get_button(BUTTON_B):
        test_msg = commonnetwork.NetworkMessage()
        test_msg.frame_id = action_frame_next
        test_msg.game_action = int(MsgEnum.ACTION_SHIELD)
        client_control.SendMsg(test_msg)
        
    # tell everyone that im going to work on this frame next
    test_msg = commonnetwork.NetworkMessage()
    test_msg.frame_id = action_frame_next
    test_msg.game_action = int(MsgEnum.GAME_POST_FRAME)
    client_control.SendMsg(test_msg)

def UpdateSimulationOnAction( action_msg):
    global simstate
    if action_msg.user_id in simstate.players:
        curr_player = simstate.players[action_msg.user_id]
    else:
        curr_player = CreateNewPlayer(action_msg.user_id)

    if(action_msg.game_action == MsgEnum.GAME_PLAYER_TEAM):
        if action_msg.event_id == 0:
            curr_player.colour = "red"
            curr_player.posx = 183 * WORLD_GRID
            curr_player.posy = 400 * WORLD_GRID
        else:
            curr_player.colour = "green"
            curr_player.posx = 1350 * WORLD_GRID
            curr_player.posy = 380 * WORLD_GRID
            curr_player.rot_index = 18 # turn 180 degrees

    if(action_msg.game_action == MsgEnum.ACTION_RIGHT):
        curr_player.x =-1
        
    if(action_msg.game_action == MsgEnum.ACTION_LEFT):
        curr_player.x =1
    
    if(action_msg.game_action == MsgEnum.ACTION_UP):
        curr_player.y +=4
        
        
    if(action_msg.game_action == MsgEnum.ACTION_DOWN):
        curr_player.y -=10
    
    #clamp speed
    curr_player.y = max(0,min(curr_player.y,200))
    player_alive = curr_player.colour != "white"
    if(player_alive and action_msg.game_action == MsgEnum.ACTION_FIRE and action_msg.frame_id -  curr_player.bullet_explode_frame > BULLET_COOLDOWN_TIME):
        held_down_time = action_msg.event_id
        curr_player.bullet_explode_frame = BULLET_FLIGHT_TIME + action_msg.frame_id
        curr_player.bullet_x_start = curr_player.posx
        curr_player.bullet_y_start = curr_player.posy
        curr_player.bullet_x_end = curr_player.posx - cos_rot[curr_player.rot_index] * held_down_time * WORLD_GRID
        curr_player.bullet_y_end = curr_player.posy - sin_rot[curr_player.rot_index]* held_down_time * WORLD_GRID
    
    if(action_msg.game_action == MsgEnum.ACTION_SHIELD):
        if(action_msg.frame_id -  curr_player.shield_active_frame > SHIELD_COOLOFF):
            curr_player.shield_active_frame = action_msg.frame_id;

g_winning_team = ""

def UpdateSimulationState(iter_frame):
    global g_winning_team
    found_red = False
    found_green = False
    for key, player in simstate.players.items():
        if player.health <= 0:
            player.colour = "white"

        if player.colour == "red":
            found_red = True
        elif player.colour == "green":
            found_green = True

        player.posy = player.posy - sin_rot[player.rot_index] * player.y;
        player.posx = player.posx - cos_rot[player.rot_index] * player.y;
        player.rot_index = (player.x + 36 + player.rot_index ) % 36
        #print(player.rot_index)
        player.x = 0
        is_burning_ground = False
        map_below_col = g_map_image.get_at(player.ToNormalPosition())
        if RED_COLOR == map_below_col and player.colour == "green":
            is_burning_ground = True
        elif GREEN_COLOR == map_below_col and player.colour == "red":
            is_burning_ground = True
        elif YELLO_COLOR == map_below_col:
            is_burning_ground = True
        
        is_shield_active = player.shield_active_frame + SHIELD_TIME >= iter_frame
        if(is_burning_ground and not is_shield_active):
            player.health -= 2
        
        # n^2 bomb check
        for key2 , player_other in  simstate.players.items():
            if( iter_frame >= player_other.bullet_explode_frame  and player_other.bullet_explode_frame + BULLET_EXPLODING_TIME >= iter_frame ):
                lerp_explosion = (iter_frame-player_other.bullet_explode_frame) / BULLET_EXPLODING_TIME
                player_other.explosion_radius = int(float(EXPLOSION_RAD * WORLD_GRID) * lerp_explosion)
                dist_x = player_other.bullet_x_end - player.posx
                dist_y = player_other.bullet_y_end - player.posy
                dist_sq = dist_x * dist_x  + dist_y * dist_y
                
                if dist_sq <= (player_other.explosion_radius* player_other.explosion_radius) and not is_shield_active:
                    player.health-=3
            else:
                player_other.explosion_radius = -1
    
    
    if found_green and not found_red:
        g_winning_team = "green"
    elif found_red and not found_green:
        g_winning_team = "red"
    elif found_green and found_red:
        g_winning_team = "" # clear if new joining
    
    InsertSimStateAtIndex(iter_frame, simstate)
    

def UpdateSimulation(msg_list, rollback_frame, curr_frame):
    #rollback frame is inclusive !!!
    global simstate
    global saved_sim

    #find first real frame
    rollback_frame = max(min(rollback_frame, len(saved_sim)-1), 1)
    while not saved_sim[rollback_frame-1]:
        rollback_frame-=1

    # print("rollback:" + str(curr_frame) + " " +  str(rollback_frame))

    simstate = copy.deepcopy(saved_sim[rollback_frame-1])
    
    start_from = len(msg_list)
    for idx, msg in enumerate(msg_list):
        if msg.frame_id < rollback_frame:
            start_from = idx
            break
    
    iter_frame = rollback_frame
    no_future = True
    for msg in reversed(msg_list[0:start_from]):
        if iter_frame != msg.frame_id:
            UpdateSimulationState(iter_frame)
            iter_frame = msg.frame_id
            
        if msg.frame_id > curr_frame:
            print("messages from the future. Accounted for!")
            no_future = False
            if  msg.game_action == MsgEnum.GAME_POST_FRAME:
                print("Why didnt we update to this frame?")
        
        if msg.frame_id >= rollback_frame:
            # delta update for this one message
            UpdateSimulationOnAction( msg)

    #handle last frame update
    if no_future:
        UpdateSimulationState(curr_frame)
            

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

    #LOOP.play(loops=-1)
reset()

g_user_color = None

while True:
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        exit()
    if joystick.get_button(BUTTON_A):
        g_user_color = RED_COLOR
        break

    if joystick.get_button(BUTTON_B):
        g_user_color = GREEN_COLOR
        break;

    text = font.render(" Press - A for team red. B for team green." , True,
                       (128, 128, 128, 255))
    temp_rect = text.get_rect()
    temp_rect.right = 320
    temp_rect.top = 100
    screen.blit(text, (temp_rect.x, temp_rect.y))
    
    pygame.display.flip()

while not joystick.get_button(BUTTON_START):
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        exit()
    screen.fill(g_user_color)
    text = font.render("Wait for players then press start ..." , True,
                       (128, 128, 128, 255))
    temp_rect = text.get_rect()
    temp_rect.right = 300
    temp_rect.top = 100
    screen.blit(text, (temp_rect.x, temp_rect.y))
    # move the sprites
    all.update()

    # draw the sprites
    all.draw(screen)

    # Score rendering
    pygame.display.flip()

g_frame_idx = 0

def LatestPostFrame(ordered_msg):
    global g_frame_idx
    for msg in ordered_msg:
        if(msg.game_action == MsgEnum.GAME_POST_FRAME):
            g_frame_idx = msg.frame_id
            break
            
def InsertSimStateAtIndex(at_index,  simstate):
    global saved_sim
    while len(saved_sim) < at_index:
        saved_sim.insert(len(saved_sim) , None)
    
    saved_sim.insert(at_index, copy.deepcopy(simstate))

# 0 frame is original data
InsertSimStateAtIndex(g_frame_idx, simstate)

while client_control.Sync():
    print("syncing...")

ordered_msg, rollback_inclusive = client_control.GatherRecentFrames()
client_control.ResetInvalidFrame()
# ok run everything forward now
LatestPostFrame(ordered_msg)
if g_frame_idx <= 0:
    g_frame_idx = 1

#checks to see if this player already exists 
is_rejoin = False
for msg in ordered_msg:
    if(msg.game_action == MsgEnum.GAME_POST_FRAME  and msg.user_id == g_user_id):
        is_rejoin = True
        break

if not is_rejoin:
    # used to propagate team decision
    print("creating new player on team")
    player_team_msg = commonnetwork.NetworkMessage()
    player_team_msg.frame_id = g_frame_idx
    player_team_msg.game_action = int(MsgEnum.GAME_PLAYER_TEAM)
    if g_user_color == RED_COLOR:
        player_team_msg.event_id = 0
    else:
        player_team_msg.event_id = 1 # green team
    client_control.SendMsg(player_team_msg)

print( "join at frame"  + str(g_frame_idx))
CreateUserMessages(g_frame_idx)


while running:
    #print( "frame counter " + str(g_frame_idx))
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        running = False
    # Condition becomes true when keyboard is pressed
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_q:
            running = False
    if joystick.get_button(BUTTON_SELECT):
        running = False

    screen.fill((255, 255 , 255, 255))

    # if random.randint(1, 150) == 25:
    #   all.add(Fireworks(), layer = 1)
    
    #simulate flaky network
    if random.random() >= 0.05:
        client_control.Sync()
#  if random.randint(1, 100) < 5:
#    all.add(Fuchsia(), layer = 1)
    ordered_msg, rollback_inclusive = client_control.GatherRecentFrames()
    #client_control.ResetInvalidFrame()
    LatestPostFrame(ordered_msg) # updates our frame counter
    UpdateSimulation(ordered_msg, rollback_inclusive,g_frame_idx )
    # move the sprites
    all.update()

    # draw the sprites
    all.draw(screen)
    DrawSimulationState()
    # Start sequence rendering

    CreateUserMessages(g_frame_idx+1)
    InsertSimStateAtIndex(g_frame_idx, simstate)

    # win condition
    if g_winning_team != "":
        text = font.render("Team " + g_winning_team + " has Won!" , True,
                           (128, 128, 128, 255))
        temp_rect = text.get_rect()
        temp_rect.right = 300
        temp_rect.top = 100
        screen.blit(text, (temp_rect.x, temp_rect.y))

    # present the draw
    pygame.display.flip()

    # Try to hit 60 fps
    if has_extra_arg:
        clock.tick(25)
    else:
        clock.tick(30)

# Done! Time to quit.
pygame.quit()
