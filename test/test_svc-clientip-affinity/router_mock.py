#!/usr/bin/python3
import socket
import select
import threading
import time
import random
import sys

tcp_port = 179
udp_port = 2055

remote_ip=sys.argv[1]
local_ip=sys.argv[2]

print(f"Connecting to '{remote_ip}' using src_ip: '{local_ip}'")

#Create the fake BGP session
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.bind((local_ip, 0))
tcp.connect((remote_ip, tcp_port))

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind((local_ip, 0))
while True:
    sleep_time = random.uniform(1, 10)

    udp.sendto("HELLO".encode(), (remote_ip, udp_port))
    time.sleep(sleep_time)
