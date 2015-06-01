#!/usr/bin/env python

'''

Machine tracker server. Waits for connections. Once connected
it will save the updates to locations.


'''

import networking as nt
import socket
import threading 


def discovery_thread(client_list_lock, client_list,end_event):
    ''' 
    This thread runs forever. It waits for a client discovery
    request. If it recieves one it initiates a new client
    class, if the client doesn't already exist.
    '''
        
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set sock opt so we can recv broadcast
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    broadcast_addr = nt.get_broadcast(nt.interface)
    s.bind((broadcast_addr,nt.r_port))
    #ip,port = s.getsockname()
    s.settimeout(2)

    while not end_event.isSet():

        # Recieve the discovery requests
        try:
            data = s.recv(1500)
        except socket.timeout:
            data = ''
        #print nt.split_msg(data)
        if nt.is_client_discovery_request(data):
            client_ip,client_port = nt.known_msg_parse(data)
            # The dictionary is passed to the class
            client_dict = {'ip':client_ip, 'port':client_port}
            
            with client_list_lock:
                # Check if the host exists already
                for client in client_list:
                    if client.ip() == client_ip:
                        # TODO check port as well. If a client died it has a differnt port
                        if client.port() != client_port:
                            print "Client " + client_ip + " has a new port. Ending the old thread and starting a new one."
                            client.end()
                            print('Old client manager thread joined.')
                            client_list.remove(client)
                            continue
                        else:
                            print 'Client ' + client_ip + ' already in list.'
                            break               
                else: # Only happens if the for didn't break
                    print 'Appending ' + client_ip + ' to client list'
                    new_client = client_manager(client_dict)
                    client_list.append(new_client)
    return

class client_manager():
    
    def ip(self):
        return self.client_ip
    
    def port(self):
        return self.client_port
    
    def get_data(self):
        with self.data_lock:
            data = self.client_data[0]
            self.client_data.pop()
        return data
    
   
    def end(self):
        
        msg = nt.make_message(nt.server_msg['exit'],())
        self.tx_socket.sendto(msg,self.tx_tuple)    
       
        self.end_event.set()
        self.tx_thread.join()
        self.rx_thread.join()
        self.tx_socket.close()
        self.rx_socket.close()
        return
    
    def client_tx_thread(self):
        print('Tx thread started, sending to port ' + str(self.client_port))
        
        msg = nt.make_message(nt.server_msg['discovery_reply'],(nt.get_ip_address(nt.interface),self.rx_port,self.client_interval))
        self.tx_socket.sendto(msg,self.tx_tuple)        
        self.end_event.wait()
        print('Tx thread ending')
        return
        
    def client_rx_thread(self):
        print('Rx thread started, listening on IP ' + self.rx_ip + ' ' + str(self.rx_port))
        
        while self.end_event.isSet() == False:
            self.rx_socket.settimeout(self.client_interval+1)            
            try:
                data = self.rx_socket.recv(1500)                           
                print data
                with self.data_lock:
                    self.client_data.append(data)
            except socket.timeout:
                print('RX timeout') 
        
        self.end_event.wait()
        print('Rx thread ending')
        return
    
     
    def __init__(self,client_dict):
    
        # Client manager thread

        self.client_interval = 1
        self.end_event = threading.Event()

        self.client_ip = client_dict['ip']
        self.client_port = client_dict['port']
        
        self.data_lock = threading.RLock()
        self.client_data = []
    
        # Open new UDP socket to client UDP RX
        self.tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)            
        self.tx_tuple = (self.client_ip,int(self.client_port))    
        
        # Open new UDP socket on random UDP port. This socket talks to the client
        self.rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_socket.bind((nt.get_ip_address(nt.interface),0))
        self.rx_ip, self.rx_port = self.rx_socket.getsockname()
                  
    
        self.tx_thread = threading.Thread(target=self.client_tx_thread)
        self.rx_thread = threading.Thread(target=self.client_rx_thread)
        
        self.rx_thread.start()
        self.tx_thread.start()
        
    
        print("Client " + self.client_ip + " created.")

        # Send IP, socket to client UDP RX
        # Send info interval to client UDP RX           
        
        return

def main():
    
    # Figure out what interface to use - from the user
    client_list = []
    client_list_lock = threading.RLock()
    end_event = threading.Event()
    d_thread = threading.Thread(target=discovery_thread, args=(client_list_lock,client_list,end_event))
    d_thread.start()
    raw_input('Press Enter to quit')
    end_event.set()
    with client_list_lock:
        for client in client_list:
            client.end() 
    

if __name__ == "__main__":
    
    debug=False
    nt.interface = 'eth0'
    main()

