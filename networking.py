#!/usr/bin/env python

# Discovery rondezvous port
r_port = 25233 #...Random?

delim = '--(~!**_DELIMITER_**!~)--' # String we'll use as a delimiter... If it appears in the data we're boned.

client_msg = {'discovery_request':'1','new_data':'2'}
server_msg = {'discovery_reply':'01','interval_change':'02','refresh':'03','exit':'04'}
interface = ''

# From https://stackoverflow.com/a/24196955
def get_ip_address(ifname):
    import socket
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

# From https://stackoverflow.com/a/936469
def get_netmask(ifname):
    import socket
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x891b, struct.pack('256s',ifname))[20:24])

def get_broadcast(ifname):
    ip = get_ip_address(ifname)
    subnet = get_netmask(ifname)
    
    ip = ip.split('.')
    subnet = subnet.split('.')
    
    # The function for broadcast address is:
    # IP of interface AND'ed with subnet = network, 
    # network OR'ed with bit flipped subnet = broadcast address    
    network = [0,0,0,0]
    broadcast = [0,0,0,0]
    for i in xrange(0,4):
        ip[i] = int(ip[i])
        subnet[i] = int(subnet[i])
               
        network[i] = ip[i] & subnet[i]
        
        subnet[i] = subnet[i] ^ 255 # Bit flip the subnet
        broadcast[i] = network[i] | subnet[i]

    return str(broadcast[0]) + '.' + str(broadcast[1]) + '.' + str(broadcast[2]) + '.' + str(broadcast[3])   
        
    
    
    
def split_msg(msg):
    msg = msg.split(delim)
    return msg

def make_message(type,msg_tuple):
    
    #### CLIENT MESSAGES
    
    if type == client_msg['discovery_request']:
        ip = str(msg_tuple[0])
        port = str(msg_tuple[1])
        return client_msg['discovery_request']+delim+ip+delim+port
    
    elif type == client_msg['new_data']:
        data = msg_tuple[0]
        return client_msg['new_data']+delim+data
    
    #### SERVER MESSAGES
    
    elif type == server_msg['discovery_reply']:
        ip = str(msg_tuple[0])
        port = str(msg_tuple[1])
        interval = str(msg_tuple[2])
        return server_msg['discovery_reply']+delim+ip+delim+port+delim+interval
    
    elif type == server_msg['interval_change']:
        return server_msg['interval_change']+str(msg_tuple[1])
    
    elif type == server_msg['refresh']:
        return server_msg['refresh']    

    elif type == server_msg['exit']:
        return server_msg['exit']  
    
    else:
        return ''

#### CLIENT MESSAGES
def is_client_discovery_request(msg):
    msg = split_msg(msg)
    if msg[0] == client_msg['discovery_request']:
        return True
    else:
        return False
    
def is_client_new_data(msg):
    msg = split_msg(msg)
    if msg[0] == client_msg['new_data']:
        return True
    else:
        return False


#### SERVER MESSAGES

def is_server_discovery_reply(msg):
    msg = split_msg(msg)
    if msg[0] == server_msg['discovery_reply']:
        return True
    else:
        return False
    
def is_server_interval_change(msg):
    msg = split_msg(msg)
    if msg[0] == server_msg['interval_change']:
        return True
    else:
        return False

def is_server_refresh(msg):
    msg = split_msg(msg)
    if msg[0] == server_msg['refresh']:
        return True
    else:
        return False
    
def is_server_exit(msg):
    msg = split_msg(msg)
    if msg[0] == server_msg['exit']:
        return True
    else:
        return False

    
# Client and server message parsing
def known_msg_parse(msg):
    msg=split_msg(msg)
    msg_type = msg[0]
    
    #### CLIENT MESSAGES
    
    if is_client_discovery_request(msg_type):
        return (msg[1], msg[2]) # IP, Port
    
    elif is_client_new_data(msg_type):
        return msg[1] # Data
    
    #### SERVER MESSAGES
        
    elif is_server_discovery_reply(msg_type):
        return (msg[1], msg[2], msg[3]) # IP, Port, interval
    
    elif is_server_interval_change(msg_type):
        return msg[1] # Interval time

    elif is_server_refresh(msg_type):
        return # Nothing to return... Shouldn't get called for this message type
    
    elif is_server_exit(msg_type):
        return # Nothing to return... Shouldn't get called for this message type
    
    elif False :
        pass
    elif False :
        pass
    return

            