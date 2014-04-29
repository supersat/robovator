#!/usr/bin/python
# Robovator
# An HTTPS interface to the MCE IMC-SCR elevator controller

import BaseHTTPServer
import ssl
import serial
import sys
import threading

class RobovatorRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_head()
        self.wfile.write('OK')
        if self.path.startswith('/move/'):
            self.server.cmd_queue.put(self.path[6])

    def do_HEAD(self):
        self.send_head()

    def send_head(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', 2)
        self.end_headers()

class Robovator:
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

class ServerThread(threading.Thread):
    def run():
        self.httpd.serve_forever

if __name__ == "__main__":
    r = Robovator()

    httpd = BaseHTTPServer.HTTPServer(('172.28.7.241', 4443), RobovatorRequestHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile='robovator.crt', keyfile='robovator.key', server_side=True)
    httpd.cmd_queue = r.cmd_queue

    server_thread = ServerThread()
    server_thread.httpd = httpd
    server_thread.start()

    r.loop()

