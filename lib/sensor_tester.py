import socket
import sys

# Create a TCP/IP socket
sock = socket.socket()
sock.connect(("192.168.43.1", 3451))

while True:
    h = sock.recv(1)
    l = sock.recv(1)

    json_len = 256 * ord(h) + ord(l)

    json = bytes()
    while len(json) < json_len:
        json += sock.recv(json_len - len(json))

    print(json)

