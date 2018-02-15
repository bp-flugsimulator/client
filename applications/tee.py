from argparse import ArgumentParser
from sys import stdin, stdout

parser = ArgumentParser()
parser.add_argument('--path', type=str, help='path to logfile')
args = parser.parse_args()

with open(args.path, mode='w') as logfile:

    buffer = stdin.read(1)
    while buffer is not '':
        logfile.write(buffer)
        logfile.flush()
        stdout.write(buffer)
        stdout.flush()
        buffer = stdin.read(1)
