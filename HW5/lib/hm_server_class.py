import zmq
import sys
import threading
from decimal import Decimal, DecimalException
from time import sleep, strftime
from collections import namedtuple


class HoldingsServer:
    'Holdings manager server class'

    default_port = 6020
    penny = Decimal('0.01')  # For rounding off all cash amounts.
    # To represent an individual buy or sell:
    Transaction = namedtuple('Transaction', 'quantity price')

    @staticmethod
    def parse_positive_decimal(s):
        try:
            d = Decimal(s)
        except DecimalException:
            return (None, "[ERROR] Price must be a number")
        if d <= 0:
            return (None, "[ERROR] Price must be positive")
        return (d.quantize(HoldingsServer.penny), "")

    @staticmethod
    def parse_positive_int(s):
        try:
            i = int(s)
        except ValueError:
            return (None, "[ERROR] Quantity must be a number")
        if i <= 0:
            return (None, "[ERROR] Quantity must be positive")
        return (i, "")

    def __init__(self, port=None, verbose=False):
        # The number of shares we currently hold, and the amount
        # of cash we currently hold:
        self.share_balance = 0
        self.cash_balance = Decimal('0')
        # A history of the buys and sells respectively:
        self.buy_history = []
        self.sell_history = []
        # A lock to control access to the histories:
        self.history_lock = threading.Lock()
        # We create our VWAP calculator thread as a "daemon thread",
        # which means we won't need to explicitly shut it down in order
        # to shut down the server.
        self.vwap_thread = threading.Thread(target=self.vwap_calculator,
                                            daemon=True)
        # This server supports the following commands:
        # - buy <# shares> <price per share>
        # - sell <# shares> <price per share>
        # - deposit_cash <amount>
        # - get_share_balance
        # - get_cash_balance
        # - shutdown_server
        # - help
        self.request_handlers = {
                'buy':               self.buy_handler,
                'sell':              self.sell_handler,
                'deposit_cash':      self.deposit_cash_handler,
                'get_share_balance': self.share_balance_handler,
                'get_cash_balance':  self.cash_balance_handler,
                # 'shutdown_server': # Requires special treatment
                'help':              self.help_handler}
        if port is None or port == HoldingsServer.default_port:
            self.port = HoldingsServer.default_port
        else:
            print("Overriding default port to", str(port))
            self.port = port
        self.verbose = verbose
        # Using "zmq.PAIR" means there is exactly one server for each client
        # and vice-versa.
        self.socket = zmq.Context().socket(zmq.PAIR)
        self.socket.bind("tcp://*:" + str(self.port))
        if self.verbose:
            print("I am the server, now listening on port", str(self.port))

    def run(self):
        self.vwap_thread.start()
        while True:
            message = self.socket.recv()
            decoded = message.decode("utf-8")
            tokens = decoded.split()
            if len(tokens) == 0:
                continue
            cmd = tokens[0]
            if cmd == "shutdown_server":
                self.socket.send_string("[OK] Server shutting down")
                sys.exit()
            else:
                handler = self.request_handlers.get(cmd,
                                                    self.invalid_cmd_handler)
                options = tokens[1:]
                response = handler(options)
                self.socket.send_string(response)

    # The method which calculates and publishes VWAPs indefinitely.
    def vwap_calculator(self):
        while True:
            with self.history_lock:
                buy_vwap = (sum([buy.quantity * buy.price
                                 for buy in self.buy_history]) /
                            sum([buy.quantity for buy in self.buy_history])
                            if len(self.buy_history) > 0 else None)
                sell_vwap = (sum([sale.quantity * sale.price
                                  for sale in self.sell_history]) /
                             sum([sale.quantity for sale in self.sell_history])
                             if len(self.sell_history) > 0 else None)
            # Here, "publishing" is just printing to the console. There are
            # many other possibilities.
            print(strftime("[%H:%M:%S] "), "Buy VWAP = ", buy_vwap,
                  ", sell VWAP = ", sell_vwap, sep='')
            sleep(15)

    def buy_handler(self, options):
        if len(options) != 2:
            return "[ERROR] Must supply quantity and price per share"
        qty, err_str1 = HoldingsServer.parse_positive_int(options[0])
        if err_str1 != "":
            return err_str1
        price, err_str2 = HoldingsServer.parse_positive_decimal(options[1])
        if err_str2 != "":
            return err_str2
        purchase_amount = qty * price
        if purchase_amount > self.cash_balance:
            return "[ERROR] Not enough cash on hand"
        self.share_balance += qty
        self.cash_balance -= purchase_amount
        with self.history_lock:
            self.buy_history.append(HoldingsServer.Transaction(qty, price))
        return "[OK] Purchased"

    def sell_handler(self, options):
        if len(options) != 2:
            return "[ERROR] Must supply quantity and price per share"
        qty, err_str1 = HoldingsServer.parse_positive_int(options[0])
        if err_str1 != "":
            return err_str1
        price, err_str2 = HoldingsServer.parse_positive_decimal(options[1])
        if err_str2 != "":
            return err_str2
        if qty > self.share_balance:
            return "[ERROR] Not enough shares on hand"
        self.share_balance -= qty
        self.cash_balance += qty * price
        with self.history_lock:
            self.sell_history.append(HoldingsServer.Transaction(qty, price))
        return "[OK] Sold"

    def deposit_cash_handler(self, options):
        if len(options) != 1:
            return "[ERROR] Must supply deposit amount"
        dep_amt, err_str = HoldingsServer.parse_positive_decimal(options[0])
        if err_str != "":
            return err_str
        self.cash_balance += dep_amt
        return "[OK] Deposited"

    def share_balance_handler(self, options):
        return "[OK] " + str(self.share_balance)

    def cash_balance_handler(self, options):
        return "[OK] " + f'{self.cash_balance:.28}'

    def help_handler(self, options):
        supported_cmds = list(self.request_handlers.keys())
        supported_cmds.extend(['shutdown_server', 'exit', 'quit'])
        return "[OK] Supported commands: " + ", ".join(sorted(supported_cmds))

    def invalid_cmd_handler(self, options):
        return "[ERROR] Unknown command"
