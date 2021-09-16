import math
import os
import random
import socket
import time
import pickle
import commonnetwork
import copy

#handles all complexity of communcation with server. Getting messages etc
#this thing knows about frames!
class ClientController:
    recv_data =b'' # required as network could chop up messages
    newest_frame_msg = 0
    s = None
    user_name = ""
    game_name = ""
    session_id = 0
    is_joined = False
    ordered_msg = [] # largest frame number to smallest
    invalidate_frame = -1
    
    def ResetInvalidFrame(self):
        self.invalidate_frame = 9999999
    
    def GatherRecentFrames(self):
        rollback_inclusive =  self.invalidate_frame
        self.ResetInvalidFrame()
        return self.ordered_msg , rollback_inclusive

    def InsertMessageSorted(self, msg):
        #print( "insert msg " + msg.debug_msg + str(msg.frame_id) )
        if(msg.frame_id == -1):
            return# this is an init style messages
        
        # insertion sort
        was_added = False
        for i in range(len(self.ordered_msg)):
            if self.ordered_msg[i].frame_id <= msg.frame_id:
                self.ordered_msg.insert(i,msg)
                was_added = True
                break;
        
        if(not was_added):
            self.ordered_msg.append(msg)
            
        self.invalidate_frame = min(self.invalidate_frame, msg.frame_id)
    
    def SetupConnection(self, name_game, name_user, id_session, host_ip):
        self.user_name = name_user
        self.game_name = name_game
        self.session_id = id_session
        # Create a socket connection.
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(host_ip)
        self.s.connect((host_ip, commonnetwork.PORT))
        self.s.setblocking(False)
        init_msg = commonnetwork.NetworkMessage()
        # we dont know what frame we are on 
        init_msg.frame_id = -1
        init_msg.debug_msg = "init tracker with server"
        self.SendMsg(init_msg)
        # join and get all our previous messages
        # after joined we will consider messages user_name as echos and throw away
        got_data_about_self = True
        while got_data_about_self:
            got_data_about_self = False
            print("syncing...")
            for i in range(0, 100):
                got_data_about_self = self.Sync() or got_data_about_self
                time.sleep(0.01)
       
            
        self.is_joined = True;
        # run deterministic sim from start 
        invalidate_frame = 0;
    
    def SendMsg(self, msg):
        # fill in origin creation vars
        local_msg = copy.deepcopy(msg)
        local_msg.game_name = self.game_name
        local_msg.user_id = self.user_name
        local_msg.session_id = self.session_id
        self.s.sendall( commonnetwork.FromMessageToBytes(local_msg))
        self.InsertMessageSorted(local_msg)

    
    def AddRecvMessage(self, msg):
        #dont add echo messages
        if(msg.user_id == self.user_name and self.is_joined):
            #print("skip echo")
            return False
        else:
            self.InsertMessageSorted(msg)
        
        return msg.user_id == self.user_name
    
    def Sync(self):
        new_data = False
        while True:
            try:
                temp_data = self.s.recv(4096*64)  # Should be ready to read
                if temp_data:
                    if len(temp_data) == 0:
                        return new_data 
                    
                    self.recv_data += temp_data
                else:
                    return new_data
            except BlockingIOError:
                temp_data = None
                return new_data
            
            while True:
                consumed_bytes, msg = commonnetwork.FromBytesToMessage(self.recv_data);
                if consumed_bytes:
                    self.recv_data = self.recv_data[consumed_bytes:]
                    new_data = self.AddRecvMessage(msg) or new_data
                else:
                    # get some more data
                    break
