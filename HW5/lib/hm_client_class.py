import zmq


class HoldingsClient:
    'Holdings manager client class'

    default_host = 'localhost'
    default_port = 6020

    def __init__(self, host=None, port=None):
        if host is None or host == HoldingsClient.default_host:
            self.host = HoldingsClient.default_host
        else:
            print("Overriding default host name to", host)
            self.host = host
        if port is None or port == HoldingsClient.default_port:
            self.port = HoldingsClient.default_port
        else:
            print("Overriding default port number to", str(port))
            self.port = port
        # Using "zmq.PAIR" means there is exactly one server for each client
        # and vice-versa.
        self.socket = zmq.Context().socket(zmq.PAIR)
        print("Connecting to server...")
        self.socket.connect('tcp://' + self.host + ':' + str(self.port))

    def send_command(self, cmd):
        self.socket.send_string(cmd)
        message = self.socket.recv()
        result = message.decode("utf-8")
        return result
