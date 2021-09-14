import math
import os
import random
import socket
import time
import pickle
import commonnetwork
import selectors
import types

#https://stackoverflow.com/questions/47391774/python-send-and-receive-objects-through-sockets/47396267
#https://realpython.com/python-sockets/

class ClientTracker:
    data_index = 0# read up to and including
    has_init = False
    init_message = commonnetwork.NetworkMessage() #
    
all_msg = []
client_trackers = {}

def add_data_maybe(sock, data):
    tracker = client_trackers[sock];
    while True:
        consumed_bytes, msg = commonnetwork.FromBytesToMessage(data.inb);
        if consumed_bytes:
            data.inb = data.inb[consumed_bytes:]
            if not tracker.has_init:
                tracker.init_message = msg
                tracker.has_init = True
            #either way add to message list total
            all_msg.append(msg)
        else:
            return
        
send_fail_count = 0
def service_existing():
    global send_fail_count
    for sock in client_trackers:
        tracker = client_trackers[sock]
        if not tracker.has_init:
            continue
        full_bytes = bytearray(b'')
        while tracker.data_index < len(all_msg):
            curr_msg = all_msg[tracker.data_index]
            # hacky way of routing messages to only games
            if curr_msg.game_name == tracker.init_message.game_name and curr_msg.session_id == tracker.init_message.session_id:
                #print("sendall:" + tracker.init_message.user_id)
                full_bytes += (commonnetwork.FromMessageToBytes(curr_msg))
            # still need to count this as processed
            tracker.data_index+=1
        sock.setblocking(True)
        try:
            sock.sendall(full_bytes)
        except ConnectionResetError:
            # we probably need to kill the tracker?
            print("connection reset. Keep going?")
        sock.setblocking(False)


def accept_wrapper(sock):
    print("accepting")
    conn, addr = sock.accept()  # Should be ready to read
    client_trackers[conn] = ClientTracker()
    print('accepted connection from', addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
    events = selectors.EVENT_READ
    sel.register(conn, events, data=data)

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(4096)  # Should be ready to read
        except ConnectionResetError:
            recv_data = None
            
        if recv_data:
            data.inb += recv_data
            add_data_maybe(sock, data)
            #can we register socket here and consume data?
        else:
            #unregister sockets here
            if(client_trackers.get(sock)):
                del client_trackers[sock]
            print('closing connection to', data.addr)
            sel.unregister(sock)
            sock.close()


sel = selectors.DefaultSelector()
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind(('', commonnetwork.PORT))
lsock.listen()
print('listening on', ('', commonnetwork.PORT))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            accept_wrapper(key.fileobj)
        else:
            service_connection(key, mask)
            service_existing()