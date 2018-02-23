from argparse import ArgumentParser
from sys import stdin, stdout
from socket import socket, AF_INET, SOCK_STREAM
from os import getpid, linesep

parser = ArgumentParser()
parser.add_argument('--port', type=int, help='port where the log is send to')
args = parser.parse_args()

SOCKET = socket(AF_INET, SOCK_STREAM)
SOCKET.connect(('localhost', args.port))
SOCKET.send((str(getpid()) + linesep).encode())
SOCKET.setblocking(0)

buffer = stdin.buffer.read(1)
while buffer != b'':
    stdout.buffer.write(buffer)
    stdout.buffer.flush()
    SOCKET.send(buffer)
    buffer = stdin.buffer.read(1)
SOCKET.close()
