import argparse
import asyncio
from utils import Status, Command, RpcReceiver


def run():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        'host', metavar='H', type=str, nargs='1', help='ip address to server')
    parser.add_argument(
        'port', metavar='P', type=int, nargs='1', help='a network port')

    args = parser.parse_args()

    url_listen = args.host + ":" + args.port + "/commands"
    url_send = args.host + ":" + args.port + "/notifications"

    try:
        print("Starting client ...")
        rpc = RpcReceiver(url_listen, url_send)
        asyncio.get_event_loop().run_until_complete(rpc.run())
        print("Finished client ...")

    except:
        pass


if __name__ == "__main__":
    run()
