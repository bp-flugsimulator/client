"""
Main file
"""

import argparse
import asyncio
import sys, os

from utils import Status, Command, RpcReceiver


def generate_uri(host, port, path):
    """
    Generates URI string for connection.
    """
    return "ws://{host}:{port}/{path}".format(
        host=host,
        port=port,
        path=path,
    )


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

    url_listen = generate_uri(
        args.host,
        args.port,
        "commands",
    )

    url_send = generate_uri(
        args.host,
        args.port,
        "notifications",
    )

    print(os.listdir("/usr/bin/"))

    print("Starting client.")
    rpc = RpcReceiver(url_listen, url_send)
    asyncio.get_event_loop().run_until_complete(rpc.run())
    print("Exit client ...")


if __name__ == "__main__":
    run()
