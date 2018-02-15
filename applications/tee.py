from argparse import ArgumentParser
from sys import stdin, stdout

parser = ArgumentParser()
parser.add_argument('--path', type=str, help='path to logfile')
parser.add_argument('--max-size', type=int, default=1048576,help='max size of the logfile in bytes')
parser.add_argument('--chunk-size', type=int, default=1024,help='max size of a chunk in bytes')
args = parser.parse_args()

with open(args.path, mode='wb+') as logfile:
    while True:
        buffer = stdin.buffer.read(1)
        if buffer.decode() is '':
            break
        elif logfile.tell() >= args.max_size:
            logfile.seek(args.chunk_size)
            tmp = logfile.read()
            logfile.seek(0)
            logfile.write(tmp)

        logfile.write(buffer)
        logfile.flush()
        stdout.buffer.write(buffer)
        stdout.buffer.flush()
