"""
Main file
"""

import argparse
import asyncio
import os

from utils import RpcReceiver
from .logger import LOGGER


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

    url = generate_uri(
        args.host,
        args.port,
        "commands",
    )

    LOGGER.url = generate_uri(
        args.host,
        args.port,
        "logs",
    )
    LOGGER.enable()

    print("Starting client.")
    if os.name == 'nt':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    rpc = RpcReceiver(url)
    loop.run_until_complete(rpc.run())
    print("Exit client ...")


if __name__ == "__main__":
    main()
