"""
Main file
"""

import argparse
import asyncio
import sys

from utils import Status, Command, RpcReceiver


def run():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        'host',
        metavar='H',
        type=str,
        help='ip address to server',
    )
    parser.add_argument(
        'port',
        metavar='P',
        type=int,
        help='a network port',
    )

    args = parser.parse_args()

    url_listen = args.host + ":" + str(args.port) + "/commands"
    url_send = args.host + ":" + str(args.port) + "/notifications"

    try:
        print("Starting client ...")
        rpc = RpcReceiver(url_listen, url_send)
        asyncio.get_event_loop().run_until_complete(rpc.run())
        print("Finished client ...")
    except:
        pass


if __name__ == "__main__":
    run()
