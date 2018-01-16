"""
Main file
"""

import argparse
import asyncio
import sys
import os
import logging

from utils import RpcReceiver


def generate_uri(host, port, path):
    """
    Generates URI string for connection.

    Arguments
    ---------
        host: Host string
        port: Port string/number
        path: Path string without a starting '/'

    Returns
    -------
        A valid URI string.

    """
    return "ws://{host}:{port}/{path}".format(
        host=host,
        port=port,
        path=path,
    )


def main():
    """
    Main function which will called if this is the main script.
    """
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        'host',
        metavar='HOST',
        type=str,
        help='ip address to server',
    )
    parser.add_argument(
        'port',
        metavar='PORT',
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

    print("Starting client.")

    if os.name == 'nt':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    rpc = RpcReceiver(url_listen, url_send)
    loop.run_until_complete(rpc.run())
    print("Exit client ...")


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[CLIENT] [%(asctime)s]: %(message)s",
        datefmt='%M:%S',
    )
    ch.setFormatter(formatter)
    root.addHandler(ch)

    main()
