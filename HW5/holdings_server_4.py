import argparse
from lib.hm_server_class import HoldingsServer


parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int)
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()

server = HoldingsServer(port=args.port, verbose=args.verbose)

server.run()
