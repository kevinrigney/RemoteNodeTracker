#!/usr/bin/env python

'''

Machine tracker client. Connects to server and sends
coordinates


'''

import networking as nt

import socket
import threading
import time
import logging

def get_new_data():
    
    return nt.get_ip_address(nt.interface) + ' time is ' + str(time.time())

def discover_server(client_port, got_server_event, end_event, normal_search_time=1,found_search_time=15):
    logger = logging.getLogger(__name__)   
        
    # Open discovery socket
    disc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    disc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Get broadcast address    
    bcast_addr = nt.get_broadcast(nt.interface)
    my_ip = nt.get_ip_address(nt.interface)
        
    # Bind to rondevous port
    #disc_socket.bind((bcast_addr,nt.r_port))
    #ip,port = disc_socket.getsockname()

    message = nt.make_message(nt.client_msg['discovery_request'],(my_ip,client_port))
    logger.info('Starting server discover')
    while not end_event.isSet():
        disc_socket.sendto(message,(bcast_addr,nt.r_port))
        logger.debug("Sent discovery request to "+ bcast_addr + ' ' + str(nt.r_port))
        if got_server_event.isSet() == False:
            # "Flood" broadcast if we haven't found a server yet
            time.sleep(normal_search_time)
        else:
            # Sleep longer if we already have made a handshake
            time.sleep(found_search_time)
    
    return

class main_state_machine():
        
    def search_for_server(self):
        self.logger.debug('Search state')
        # timeout should be the search time on the discover
        self.rx_socket.settimeout(self.search_time)
        while not self.end_event.isSet():
            try:
                data = self.rx_socket.recv(1500)
            except socket.timeout:
                # Try again
                continue
            # timeout didn't occurr
            if nt.is_server_discovery_reply(data):      
                self.got_reply_event.set()
                self.server_ip, self.server_port, self.interval = nt.known_msg_parse(data)
                return 'connect'
    
    def connect_to_server(self):
        self.logger.debug('Connect State')
        # Close it if it's open
        if type(self.tx_socket) != type(None):
            self.tx_socket.close()
        # Open the socket
        self.tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       
        
        return 'change'
    
    def send_data(self):
        self.logger.debug('Send State')
        
        msg = nt.make_message(nt.client_msg['new_data'],(get_new_data(),))
        self.tx_socket.sendto(msg,(self.server_ip,int(self.server_port)))
        
        return 'wait'
    
    def wait_for_interval(self):
        self.logger.debug('Wait State')
        try:
            data = self.rx_socket.recv(1500)
        except socket.timeout:
            return 'send'
        
        # We got data
        if nt.is_server_discovery_reply(data):
            self.server_ip, self.server_port, self.interval = nt.known_msg_parse(data)
            return 'connect'
        elif nt.is_server_interval_change(data):
            self.interval = nt.known_msg_parse(data)
            return 'change'
        elif nt.is_server_refresh(data):
            return 'send'
        elif nt.is_server_exit(data):
            return 'exit'
        else:
            return 'wait'
    
    def change_interval(self):
        self.logger.debug('Interval change state')
        self.rx_socket.settimeout(int(self.interval))        
        return 'wait'
    
    def exit(self):
        self.logger.debug('Exit state')
        self.end_event.set()
        return
    
    def machine(self,initial_state):
        self.logger.info('Starting state machine')
        # Initial state is search
        next_state = initial_state
        
        while not self.end_event.isSet():
            next_state = self.state[next_state](self)  
            
        self.logger.debug('State machine exiting')
        return 
        
    
    
    def __init__(self,search_time,slow_search_time,end_event):
        self.logger = logging.getLogger(__name__)
        self.logger.debug('Main Init')
        # Open recieve socket
        self.rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        self.rx_socket.bind((nt.get_ip_address(nt.interface),0))
        self.rx_port = self.rx_socket.getsockname()[1]
        
        # Set empty TX socket
        self.tx_socket = None
        
        self.got_reply_event = threading.Event()
        self.end_event = end_event
        
        self.search_time = search_time
        self.slow_search_time = slow_search_time
        
        search_thread_args = (self.rx_port,self.got_reply_event,self.end_event,)
        serach_thread_kwargs = {'normal_search_time':search_time,'found_search_time':slow_search_time}
        
        # Start search
        self.search_thread = threading.Thread(target=discover_server,args=search_thread_args,kwargs=serach_thread_kwargs)
        self.search_thread.start()
        
        self.machine('search')
        return

    state = {'search':search_for_server,
             'connect':connect_to_server,
             'send':send_data,
             'wait':wait_for_interval,
             'change':change_interval,
             'exit':exit}



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(filename)s:%(lineno)s\t%(levelname)s: %(message)s',level=logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.warning('test')
    
    # Figure out what interface to use - from the user
    nt.interface = 'eth0'    
    end_event = threading.Event()
    try:
        main_state_machine(1,15,end_event)
        print('Clean exit... Please wait.')
    except Exception as e:
        logger.error(str(e))
        logger.error('Got kill... Please wait 15 seconds.')
        end_event.set()
