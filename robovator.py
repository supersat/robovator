#!/usr/bin/python
# Robovator
# An HTTPS interface to the MCE IMC-SCR elevator controller

import BaseHTTPServer, SimpleHTTPServer
import ssl
import serial
import sys

#httpd = BaseHTTPServer.HTTPServer(('localhost', 4443), SimpleHTTPServer.SimpleHTTPRequestHandler)
#httpd.socket = ssl.wrap_socket (httpd.socket, certfile='path/to/localhost.pem', server_side=True)
#httpd.serve_forever()

class robovator:
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyS0', 19200, xonxoff=1, rtscts=0, timeout=None);
        self.floor_selected = 0;
        self.cmd_queue = Queue(2)

    def read(self):
        c = self.ser.read()
        sys.stdout.write(c)
        return c

    def wait_for_enq(self):
        while True:
            if self.read() == '\x05':
                self.ser.write('\x06');
                break

    def go_to_floor(self, floor):
        if floor < self.floor_selected:
            self.ser.write('\x0a' * (self.floor_selected - floor))
        elif floor > self.floor_selected:
            self.ser.write('\x0b' * (floor - self.floor_selected))
        self.ser.write('\x0d')
        self.floor_selected = floor

    def loop(self):
        # Wait for terminal type request
        while True:
            if self.read() == '\x1b':
                if self.read() == ' ':
                    print 'Got terminal type request';
                    break;

        self.wait_for_enq()
        self.ser.write(' ') # "Press any key"
        self.wait_for_enq()
        self.ser.write('\x01B\r') # F3
        self.wait_for_enq()

        while True:
            c = self.read()
            if c == '\x05':
                self.ser.write('\x06')
            if not self.cmd_queue.empty():
                self.go_to_floor(self.cmd_queue.get())

if __name__ == "__main__":
    r = robovator()
    r.loop()
