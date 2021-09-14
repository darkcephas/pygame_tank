import math
import os
import random
import socket
import time
import pickle

PORT = 25565
SIZE_OF_INT=4

class NetworkMessage:
    game_name = ""
    session_id = 0
    user_id = ""
    game_action = 0
    event_id = 0
    frame_id = 0
    debug_msg = ""

def FromBytesToMessage(data_bytes):
    if len(data_bytes) < SIZE_OF_INT:
        return None, None
    as_byte_array = bytearray(data_bytes)
    int_byte_array = as_byte_array[0:SIZE_OF_INT];
    num_bytes = int.from_bytes(bytes(int_byte_array),  byteorder='big')
    if len(data_bytes) < (num_bytes + SIZE_OF_INT):
        return None, None
    del as_byte_array[0:SIZE_OF_INT]
    return (num_bytes + SIZE_OF_INT), pickle.loads(bytes(as_byte_array))
    
# returns packed bytes for object
def FromMessageToBytes(message_net):
    as_bytes = pickle.dumps(message_net);
    #prepend the size of the pickle
    return len(as_bytes).to_bytes(4,  byteorder='big') + as_bytes


#test
def Test():
    msg_data = NetworkMessage()
    msg_data.game_name = "test"
    msg_data.frame_id = 777
    print( msg_data.game_name  + str(msg_data.frame_id))
    some_data = FromMessageToBytes(msg_data)
    msg_data.game_name = "other"
    msg_data.frame_id = 888
    print( msg_data.game_name  + str(msg_data.frame_id))
    total_bytes , msg_data = FromBytesToMessage(some_data)
    print( msg_data.game_name  + str(msg_data.frame_id))
    print( str(total_bytes))
    