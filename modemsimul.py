#!/usr/bin/env python3

import os
import sys
import time
import math
import serial
import random
import socket
import select
import errno

from codenerix_lib.debugger import Debugger

__version__ = "1.0"


class Modem(Debugger):
    def __init__(self, tcpport, serialargs):

        # Debug
        self.set_debug()
        self.set_name("Modem Simulator")

        # Initialize variables
        self.__echo = False
        self.__pin = True
        self.__socket = None
        self.__cfun = 1
        self.__servers = {}
        self.__clients = {}
        self.__client_selected = None
        self.__clients_id = 0

        # Default config
        self.__serial_bytesize = 8
        self.__serial_parity = "N"
        self.__serial_stopbit = 1

        # Check TCP Port
        try:
            self.__tcpport = int(tcpport)
        except Exception:
            msg = "TCP port '{}' it nos a number".format(tcpport)
            self.error(msg)
            raise IOError(msg)

        # Serial port
        if len(serialargs) >= 1:
            if os.path.exists(serialargs[0]):
                self.__serial_port = serialargs[0]
            else:
                msg = "Serial port not found at '{}'".format(serialargs[0])
                self.error(msg)
                raise IOError(msg)

        # Serial speed
        if len(serialargs) >= 2:
            try:
                self.__serial_speed = int(serialargs[1])
                if self.__serial_speed not in serial.Serial.BAUDRATES:
                    raise IOError
            except Exception:
                msg = "Wrong speed selected '{}', valid speeds are {}".format(
                    serialargs[1], ",".join(serial.Serial.BAUDRATES)
                )
                self.error(msg)
                raise IOError(msg)
        else:
            self.__serial_speed = 9600

        # Serial configuration
        if len(serialargs) == 3:
            serial_config = serialargs[2]
            if len(serial_config) == 3:

                # Get serial byte size
                try:
                    self.__serial_bytesize = int(serial_config[0])
                    if self.__serial_bytesize not in serial.Serial.BYTESIZES:
                        raise IOError
                except Exception:
                    msg = "Wrong bytesize selected '{}', valid speeds are {}".format(
                        serial_config[0], ",".join(serial.Serial.BYTESIZES)
                    )
                    self.error(msg)
                    raise IOError(msg)

                # Get serial parity
                try:
                    self.__serial_parity = serial_config[1]
                    if self.__serial_parity not in serial.Serial.PARITIES:
                        raise IOError
                except Exception:
                    msg = "Wrong parity selected '{}', valid speeds are {}".format(
                        serial_config[1], ",".join(serial.Serial.PARITIES)
                    )
                    self.error(msg)
                    raise IOError(msg)

                # Get stop bit
                try:
                    self.__serial_stopbit = int(serial_config[2])
                    if self.__serial_stopbit not in serial.Serial.STOPBITS:
                        raise IOError
                except Exception:
                    msg = "Wrong stopbit selected '{}', valid speeds are {}".format(
                        serial_config[2], ",".join(serial.Serial.STOPBITS)
                    )
                    self.error(msg)
                    raise IOError(msg)

            else:
                # Wrong configuration
                msg = "Serial data is wrong, expected <number><letter><number> (Ex: 8N1) and got {}".format(
                    serialargs[3]
                )
                self.error(msg)
                raise IOError(msg)

        elif len(serialargs) > 3:
            # Too many arguments
            msg = "Serial data is wrong, too many parameters, do not understand: {}".format(
                ",".join(serialargs[3:])
            )
            self.error(msg)
            raise IOError(msg)

    def connect(self):
        # Connect to the bus
        self.socket = serial.Serial(
            port=self.__serial_port,
            baudrate=self.__serial_speed,
            parity=self.__serial_parity,
            stopbits=self.__serial_stopbit,
            bytesize=self.__serial_bytesize,
        )
        self.debug("CONNECTED ", head=False, tail=False, color="white")

    def disconnect(self):
        self.socket.close()
        self.debug("DISCONNECTED ", head=False, tail=False, color="white")

    def reconnect(self):
        self.debug("Reconnecting serial port: ", tail=False, color="purple")
        self.disconnect()
        self.connect()
        self.debug("DONE", head=False, color="green")

    def send(self, data):
        self.socket.write(data)
        # block = 50
        # start = 0
        # end = min(block, len(data))
        # while (start < len(data)):
        #     print(start, end)
        #     self.socket.write(data[start:end])
        #     start = end
        #     end = min(start + block, len(data))

    def recv(self, decode=True):

        # Give to to send
        time.sleep(0.1)

        # There is data
        data = True
        buf = b""
        while data:

            # Get data from the bus
            data = self.socket.read_all()

            # Do not process
            if data:
                buf += data
                time.sleep(0.1)

        # Try to decode string if not there is noisy in the bus
        if decode:
            try:
                buf = buf.decode()
            except Exception:
                self.warning("The bus is noisy...dropping data! {}".format(data))
                buf = None

        # Return buffer if any
        return buf

    def start_server(self, act):

        # Split request
        (port, zero) = act.split(",")

        # Try converting port
        try:
            port = int(port)
        except Exception:
            port = None

        # Check if we got a valid port
        if port:

            # Make sure the server is not already started
            if str(port) not in self.__servers:

                # Listen on desired port
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("", port))
                server.listen(5)
                self.__servers[str(port)] = server
                self.debug("Listening on port {}".format(port), color="cyan")
            else:
                self.debug("Already listening on port {}".format(port), color="cyan")

            # We are ready
            answer = "\r\nOK"

        else:

            # There was an error
            answer = "\r\nERROR"

        return answer

    def listen_chttpact(self, act):

        # Split request
        (host, port) = act.split(",")

        # Clean host
        host = host[1:-1]

        # Check port
        try:
            port = int(port)
        except Exception:
            port = None

        # Prepare answer
        answer = None

        # Check data
        if host and port:
            done = -1
            buf = ""
            while done < 0:
                data = self.recv()
                if data:
                    buf += data
                    done = buf.find("")

            # Cut the non processable string
            httprequest = buf[:done].encode()

            # Send request to server
            s = socket.socket()
            s.connect((host, port))
            s.sendall(httprequest)
            data = s.recv(65535)
            httpanswer = data.decode()

            # Prepare answer from the remote server
            answer = "\r\nOK{}".format(httpanswer)

        elif not host and not port:
            answer = "\r\n+CHTTPACT ERROR: incorrect host({}) and port({})".format(
                host, port
            )

        elif not host:
            answer = "\r\n+CHTTPACT ERROR: incorrect host({})".format(host)

        elif not port:
            answer = "\r\n+CHTTPACT ERROR: incorrect port({})".format(port)

        return answer

    def tcp_remote_connection_closed(self, sock):
        """
        Returns True if the remote side did close the connection
        This detects if the remote side closed the connection, without actually consuming the data
        """
        try:
            buf = sock.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
            if buf == b"":
                return True
        except socket.timeout:
            pass
        except BlockingIOError as exc:
            if exc.errno != errno.EAGAIN:
                # Raise on unknown exception
                raise
        return False

    def listen_client(self, cliid=None):

        # Select this client
        if cliid:
            # Get given client
            self.__client_selected = cliid
        else:
            # Use selected client
            cliid = self.__client_selected

        # Check if client exists
        if cliid in self.__clients:

            # Get client details
            (cliaddr, cliport, clisocket) = self.__clients[cliid]

            # Show header
            self.debug(
                "Client {} - Listening to client from {}:{}".format(
                    cliid, cliaddr, cliport
                ),
                color="cyan",
            )

            # Show header
            answer = "\r\nCONNECT {}\r\n".format(self.__serial_speed)
            self.debug("SENT {} bytes".format(len(answer), color="simplegreen"))
            self.send(answer.encode())

            # If the client keeps being online
            online = True
            request_standby = False
            while online:

                # Read serial
                serial_buf = self.recv(decode=False)
                if serial_buf:
                    serial_sp = serial_buf.split(b"+++")
                    if len(serial_sp) > 1:
                        request_standby = True
                        serial_buf = serial_sp[0]

                # Read from tcp
                try:
                    tcp_buf = clisocket.recv(65535)
                except socket.timeout:
                    tcp_buf = None

                # Dump to serial
                if tcp_buf:
                    self.debug(
                        "GPRS->SERIAL: {} bytes".format(len(tcp_buf)), color="white"
                    )
                    self.debug(
                        "SENT {} bytes".format(len(tcp_buf), color="simplegreen")
                    )
                    self.send(tcp_buf)

                # Dump to tcp
                if serial_buf:
                    self.debug(
                        "SERIAL->GPRS: {} bytes".format(len(serial_buf)), color="white"
                    )
                    clisocket.sendall(serial_buf)

                # Request exit
                if request_standby:
                    answer = "\r\nOK"
                    break

                # Check if client didn't close the connection
                online = not self.tcp_remote_connection_closed(clisocket)
                if not online:
                    answer = "\r\nCLOSED"
                    break

            # Remove client from list of connection if not online
            if not online:
                # Remove this client
                self.__clients.pop(cliid)
                clisocket.close()
                # If there are clients, select the last one
                if self.__clients:
                    self.__client_selected = self.__clients.keys()[-1]
                else:
                    # No more clients
                    self.__client_selected = None

            # Show info
            if request_standby:
                self.debug("Client {} - Stand by".format(cliid), color="cyan")
            elif not online:
                self.debug("Client {} - Closed connection".format(cliid), color="cyan")
            else:
                self.error("Client {} - Out from bucle with no reason".format(cliid))

        elif cliid is not None:
            answer = "\r\nSERVERSTART ERROR: client id {} not found".format(cliid)

        else:
            answer = "\r\nSERVERSTART ERROR: no clients connected"

        # If there is some answer, send it!
        if answer:
            self.debug("SENT {} bytes".format(len(answer), color="simplegreen"))
            self.send(answer.encode())

    def execute_cmd(self, buf):
        delay = 0

        # Remove tail if exists
        if buf[-1] == "\n":
            buf = buf[:-1]

        # Prepare for multicmds
        if buf.find("\n"):
            cmds = buf.split("\n")
        else:
            cmds = [buf]

        # For each cmd
        for cmd in cmds:

            # Clean cmd
            if cmd[-1] == "\r":
                cmd = cmd[:-1]

            # Process the CMD
            self.debug("CMD({}): {}".format(len(cmd), cmd), color="blue")

            if cmd == "+++":
                answer = None

            elif cmd == "":
                answer = None

            elif cmd == "AT":
                answer = "\r\nOK"

            elif cmd == "ATZ":
                answer = "\r\nOK"
                for cliid in self.__clients:
                    (cliaddr, cliport, clisocket) = self.__clients[cliid]
                    self.warning("Dropping client {}:{}".format(cliaddr, cliport))
                    clisocket.close()
                for port in self.__servers:
                    server = self.__servers[port]
                    self.warning("Closing server at port {}".format(port))
                    server.close()
                # Reconnect serial port
                self.reconnect()
                # Reset values
                self.__clients_id = 0
                self.__client_selected = None
                self.__clients = {}
                self.__servers = {}

            elif cmd == "ATI":
                answer = "\r\nModem Simul v{}".format(__version__)

            elif cmd == "ATE0":
                answer = "\r\nOK"
                self.__echo = False

            elif cmd == "ATO":
                self.listen_client()
                answer = None

            elif cmd == "AT+CFUN=1":
                answer = "\r\nOK"
                if self.__cfun != 1:
                    self.__cfun = 1
                    delay = 10

            elif cmd == "AT+CFUN=6":
                answer = "\r\nOK"
                if self.__cfun != 6:
                    self.__cfun = 6
                    delay = 8

            elif cmd == "AT+CPIN?":
                if self.__pin:
                    answer = "\r\n+CPIN: READY"
                else:
                    answer = "\r\n+CPIN: SIM PIN"

            elif cmd[:8] == "AT+CPIN=":
                pin = cmd[8:]
                self.debug("Got pin '{}'".format(pin), color="green")
                self.__pin = True
                answer = "\r\n+CPIN: READY\r\n\r\nSMS DONE\r\n\r\nPB DONE"

            elif cmd == "AT+CIPMODE=1":
                answer = "\r\nOK"

            elif cmd == "AT+NETOPEN":
                answer = "\r\nOK"
                delay = 6

            elif cmd == "AT+IPADDR":
                answer = "\r\n+IPADDR: 127.127.127.127"

            elif cmd[:12] == "AT+CHTTPACT=":

                # Send answer
                answer = "\r\n+CHTTPACT: REQUEST"
                self.debug("SENT {} bytes".format(len(answer), color="simplegreen"))
                self.send(answer.encode())

                # Start listening for user request
                answer = self.listen_chttpact(cmd[12:])

            elif cmd[:15] == "AT+SERVERSTART=":

                # Start listening for user request
                answer = self.start_server(cmd[15:])

            else:
                self.warning("Unknown CMD: {}".format(cmd))
                answer = "ERROR"

            # Send echo
            if self.__echo:
                cmd += "\r\n"
                self.debug("SENT {} bytes".format(len(cmd), color="simplegreen"))
                self.send(cmd.encode())

            # Send answer
            if answer:
                self.debug("SENT {} bytes".format(len(answer), color="simplegreen"))
                self.send(answer.encode())

            # Do delay
            if delay:
                self.debug("Sleeping {} seconds".format(delay), color="white")
                time.sleep(delay)

    def simul(self):

        # Say we are starting
        self.debug(
            "Starting at {}@{}:{}{}{} and TCP port {}".format(
                self.__serial_port,
                self.__serial_speed,
                self.__serial_bytesize,
                self.__serial_parity,
                self.__serial_stopbit,
                self.__tcpport,
            ),
            color="cyan",
        )

        self.debug("Connecting serial port: ", tail=False, color="purple")
        self.connect()
        self.debug("DONE", head=False, color="green")

        # For ever
        while True:

            # Read buffer
            buf = self.recv()

            # We got all the data from the buffer
            if buf:
                self.execute_cmd(buf)
            else:

                # Build the list of servers
                servers = []
                for port in self.__servers:
                    servers.append(self.__servers[port])

                # Check available ports
                (readable, writeable, errored) = select.select(servers, [], [], 0)
                for server in readable:

                    # New client
                    cliid = str(self.__clients_id)
                    self.__clients_id += 1

                    # Process new client each time
                    (clisocket, client) = server.accept()
                    clisocket.settimeout(1)
                    (cliaddr, cliport) = client
                    self.debug(
                        "New client connected from {}:{}, id={}".format(
                            cliaddr, cliport, cliid
                        ),
                        color="cyan",
                    )
                    # Answer on the bus that a new client got connected
                    msg = "\r\n+CLIENT: {},0,{}:{}".format(cliid, cliaddr, cliport)
                    self.__clients[cliid] = (cliaddr, cliport, clisocket)

                    # Listen client
                    self.listen_client(cliid)

                time.sleep(0.1)


# Start software
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        m = Modem(sys.argv[1], sys.argv[2:])
        try:
            m.simul()
        except KeyboardInterrupt:
            m.debug("User requested to close!", color="green")

    else:
        print(
            "Usage: {} <tcp port> <serial port> [serial speed [serial config]]".format(
                sys.argv[0]
            )
        )
        print("    > Example: {} 2222 /dev/ttyUSB0 115200")
        print("    > Default serial speed will be: 9600")
        print("    > Default serial config will be: 8N1")
