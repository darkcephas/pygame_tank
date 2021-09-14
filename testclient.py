import math
import os
import random
import socket
import time
import pickle
import commonnetwork
import selectors
import clientmulti

#data = conn.recv(4096)
#data_variable = pickle.loads(data)
#https://stackoverflow.com/questions/47391774/python-send-and-receive-objects-through-sockets/47396267
#https://realpython.com/python-sockets/

client_control = clientmulti.ClientController()
client_control.SetupConnection( input("gamename:") ,  input("userid:") , 2)
# Create an instance of ProcessData() to send to server.
# Pickle the object and send it to the server
test_msg = commonnetwork.NetworkMessage()
test_integer = 3;
while True:
    test_msg.debug_msg =  input(">_")
    test_msg.frame_id = test_integer
    test_integer +=1
    client_control.SendMsg(test_msg)
    time.sleep(1)
    client_control.Sync()
