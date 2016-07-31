import asyncore
import socket
import struct
from markovobfuscate.obfuscation import MarkovKeyState
import logging
import threading
import zlib

BUFFER_SIZE = 4096


class LocalProxy(asyncore.dispatcher):
    """Listens for new client connections and creates new ToClient
    objects for each one."""

    def __init__(self, markov, localHost, localPort, mtunnelHost, mtunnelPort):
        """Creates the socket, binds to clientPort"""
        asyncore.dispatcher.__init__(self)
        self.markov = markov
        self.clientPort = localPort
        self.host = localHost
        self.mtunnel_host = mtunnelHost
        self.mtunnel_port = mtunnelPort
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((self.host, self.clientPort))
        self.listen(5)

    def handle_accept(self):
        """Handles new client connections"""
        conn, addr = self.accept()
        logging.info("{0} connected".format(addr))
        return LocalProxy.SendToClient(self.markov, conn, self.mtunnel_host, self.mtunnel_port)

    def handle_close(self):
        self.close()
        logging.info("Local socket closed")

    def run(self):
        logging.info("Local server running...")
        self.listen(5)

    def die(self, error):
        logging.info("Death....")
        logging.info("Error: %s" % error)
        self.handle_close()

    class SendToClient(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, remote_server, remote_port):
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, sock)
            msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            msock.connect((remote_server, remote_port))
            self.msock = LocalProxy.ToMTunnelServer(markov, self, msock)

        def handle_read(self):
            data = self.recv(BUFFER_SIZE)
            logging.info("Recv'd {0} bytes from the client".format(len(data)))
            data = self.markov.obfuscate_string(zlib.compress(data, 9)) + "\n"
            logging.info("Obfuscated into {0} bytes and sending to other side of the tunnel".format(len(data)))
            self.msock.send(data)

        def handle_close(self):
            logging.info("Closing client socket...")
            self.close()

    class ToMTunnelServer(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, oSock):
            self.read_buffer = ''
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, oSock)
            self.client = sock

        def handle_read(self):
            data = self.recv(BUFFER_SIZE)
            logging.info("Recv'd {0} bytes from the other side of the tunnel".format(len(data)))
            self.read_buffer += data
            while "\n" in self.read_buffer:
                data, self.read_buffer = self.read_buffer.split("\n", 1)
                logging.info("Recv'd obfuscated {0} bytes from the other side of the tunnel".format(len(data)))
                if len(data) > 0:
                    data = zlib.decompress(self.markov.deobfuscate_string(data))
                    logging.info("Deobfuscated {0} bytes from the other side of the tunnel".format(len(data)))
                    self.client.send(data)

        def handle_close(self):
            logging.info("Closing MTunnel socket...")
            self.close()


class MTunnelServer(asyncore.dispatcher):
    """Listens for new client connections and creates new ToClient
    objects for each one."""

    def __init__(self, markov, localHost, localPort):
        """Creates the socket, binds to clientPort"""
        self.markov = markov
        asyncore.dispatcher.__init__(self)
        self.clientPort = localPort
        self.host = localHost
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((self.host, self.clientPort))
        self.listen(5)

    def handle_accept(self):
        """Handles new client connections"""
        conn, addr = self.accept()
        logging.info("{0} connected.".format(addr))
        return MTunnelServer.MSendToClient(self.markov, conn)

    def handle_close(self):
        self.close()
        logging.info("Obfuscated SOCKS server socket closed")

    def run(self):
        logging.info("Obfuscated SOCKS server running...")
        self.listen(5)

    def die(self, error):
        logging.info("Death....")
        logging.info("Error: %s" % error)
        self.handle_close()

    class MSendToClient(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock):
            self.read_buffer = ''
            self.markov = markov
            #self.msock = MTunnelServer.ToRemoteServer(markov, self, msock)
            self.msock = None
            self.state = 0
            asyncore.dispatcher_with_send.__init__(self, sock)
            self.state_lock = threading.RLock()

        def handle_read(self):
            data = self.recv(BUFFER_SIZE)
            logging.info("Recv'd {0} bytes from the other side of the tunnel".format(len(data)))
            self.read_buffer += data
            while "\n" in self.read_buffer:
                data, self.read_buffer = self.read_buffer.split("\n", 1)
                logging.info("Recv'd obfuscated {0} bytes from the other side of the tunnel".format(len(data)))
                if len(data) > 0:
                    data = zlib.decompress(self.markov.deobfuscate_string(data))
                    logging.info("Deobfuscated {0} bytes from the other side of the tunnel".format(len(data)))
                    with self.state_lock:
                        if self.state == 0:
                            if len(data) > 2:
                                # All socks4 initial packets start with 4 and end with 0
                                if data[0] == "\x04" and data[-1] == "\x00":
                                    # Socks4/4a
                                    if len(data) >= 9:  # minimum for socks4
                                        if data[1] == "\x01":
                                            # Let's only support stream connections...
                                            port = struct.unpack("!H", data[2:4])[0]
                                            ip = data[4:8]

                                            # Get user string
                                            user = ""
                                            index = 8
                                            while data[index] != "\x00":
                                                user += data[index]
                                                index += 1

                                            if ip[0:3] == "\x00\x00\x00" and ip[3] != "\x00":
                                                # socks4a
                                                index += 1
                                                domain = ""

                                                while data[index] != "\x00":
                                                    domain += data[index]
                                                    index += 1

                                                try:
                                                    ip = socket.gethostbyname(domain)
                                                    msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                                    msock.connect((ip, port))
                                                    self.msock = MTunnelServer.ToRemoteServer(self.markov, self, msock)
                                                    self.send(self.markov.obfuscate_string(zlib.compress("\x00\x5a" + struct.pack("!H", port) + socket.inet_aton(ip))) + "\n")
                                                    self.state = 0x10
                                                    logging.info("Connected to remote server {2} - {0}:{1}".format(ip, port, domain))
                                                except socket.error:
                                                    logging.info("Error connecting to remote server {0}:{1}".format(ip, port))
                                                    self.send(self.markov.obfuscate_string(zlib.compress("\x00\x5b" + struct.pack("!H", port) + socket.inet_aton(ip))) + "\n")
                                                    self.handle_close()
                                            else:
                                                # socks4
                                                try:
                                                    ip = socket.inet_ntoa(ip)
                                                    msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                                    msock.connect((ip, port))
                                                    self.msock = MTunnelServer.ToRemoteServer(self.markov, self, msock)
                                                    self.send(self.markov.obfuscate_string(zlib.compress("\x00\x5a" + struct.pack("!H", port) + socket.inet_aton(ip))) + "\n")
                                                    self.state = 0x10
                                                    logging.info("Connected to remote server {0}:{1}".format(ip, port))
                                                except socket.error:
                                                    logging.info("Error connecting to remote server {0}:{1}".format(ip, port))
                                                    self.send(self.markov.obfuscate_string(zlib.compress("\x00\x5b" + struct.pack("!H", port) + socket.inet_aton(ip))) + "\n")
                                                    self.handle_close()

                                    pass
                                elif data[0] == 0x5:
                                    # Socks5
                                    pass
                            pass
                        elif self.state == 0x10:
                            logging.info("Sending {0} bytes to other side of tunnel".format(len(data)))
                            self.msock.send(data)

        def handle_close(self):
            logging.info("Closing client socket...")
            self.close()

    class ToRemoteServer(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, oSock):
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, oSock)
            self.client = sock

        def handle_read(self):
            data = self.recv(BUFFER_SIZE)
            logging.info("Recv'd {0} bytes from remote server".format(len(data)))
            data = self.markov.obfuscate_string(zlib.compress(data, 9)) + "\n"
            logging.info("Obfuscated into {0} bytes and sending to other side of the tunnel".format(len(data)))
            self.client.send(data)

        def handle_close(self):
            logging.info("Closing remote server socket...")
            self.close()


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog=__file__,
        description="Acts as both ends of a Markov model obfuscated TCP tunnel",
        version="%(prog)s v0.1 by Brian Wallace (@botnet_hunter)",
        epilog="%(prog)s v0.1 by Brian Wallace (@botnet_hunter)"
    )

    parser.add_argument('-s', '--server', default=False, required=False, action='store_true', help="Run as end server")
    parser.add_argument('-r', '--remote', default=None, type=str, action='append', help='Remote server to tunnel to')
    parser.add_argument('-p', '--port', default=9050, type=int, help='Port to listen on')
    parser.add_argument('-P', '--remoteport', default=9999, type=int, help='Port for remote server')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    # Regular expression to split our training files on
    split_regex = r'\.'

    # File/book to read for training the Markov model (will be read into memory)
    training_file = "datasets/98.txt"

    # Obfuscating Markov engine
    m = MarkovKeyState()

    # Read the shared key into memory
    logging.info("Reading {0}".format(training_file))
    with open(training_file, "r") as f:
        text = f.read()

    import re
    # Split learning data into sentences, in this case, based on periods.
    logging.info("Teaching the Markov model")
    map(m.learn_sentence, re.split(split_regex, text))

    if args.server:
        # We are the terminating server
        host = "0.0.0.0"
        port = int(args.remoteport)
        logging.info("Running as server on {0}:{1}".format(host, port))
        server = MTunnelServer(m, host, port)
        asyncore.loop()
    else:
        # We are the local server
        logging.info("Running as local SOCKS proxy on {0}:{1} connecting to {2}:{3}".format(
            'localhost', args.port, args.remote[0], int(args.remoteport)))
        server = LocalProxy(m, 'localhost', args.port, args.remote[0], int(args.remoteport))
        asyncore.loop()
