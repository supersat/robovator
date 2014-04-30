#!/usr/bin/python
# Robovator
# An HTTPS interface to the MCE IMC-SCR elevator controller

import BaseHTTPServer
import ssl
import serial
import sys
import time
import threading
from Queue import *

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

        self.mode = 'XX'
        self.RD = False
        self.PR = False
        self.R5 = False
        self.R4 = False
        self.R3 = False
        self.R2 = False
        self.R1 = False
        self.R0 = False
        self.last_floor = 1

    def read(self):
        c = self.ser.read()
        if c != '\x05':
            sys.stdout.write(c)
            sys.stdout.flush()
        return c

    def wait_for_enq(self):
        while True:
            if self.read() == '\x05':
                self.ser.write('\x06');
                break

    def wait_for_term_req(self):
        while True:
            c = self.ser.read()
            if c == '\x1b':
                if self.read() == ' ':
                    self.ser.write('60\r')
                    sys.stderr.write('Got terminal type request\n')
                    break
            elif c == '\x05':
                self.ser.write('\x06')

    def go_to_floor(self, floor):
        floor = int(floor)
        sys.stderr.write('Going to floor %s\n' % (floor))
        if floor < self.floor_selected:
            while self.mode == 'UP':
                self.update_status()
            for x in range(0, (self.floor_selected - floor)):
                self.ser.write('\x0a')
                time.sleep(0.05)
        elif floor > self.floor_selected:
            while self.mode == 'DN':
                self.update_status()
            for x in range(0, (floor - self.floor_selected)):
                self.ser.write('\x0b')
                time.sleep(0.05)
        self.ser.write('\x0d')
        self.floor_selected = floor
        while self.last_floor != self.floor_selected:
            self.update_status()
        sys.stderr.write('Done issuing command\n')

    def update_status(self):
        c = self.read()
        if c == '\x05':
            self.ser.write('\x06')
        elif c == '\x1b':
            c = self.read()
            if c == '\x3b':
                y = self.read()
                x = self.read()
                if (y == '\x29') and (x == '\x4a'):
                    self.mode = self.read() + self.read()
                elif (y == '\x28'):
                    if (x == '\x22'):
                        self.RD = (self.read() == '\x1b')
                    elif (x == '\x25'):
                        self.PR = (self.read() == '\x1b')
                    elif (x == '\x2a'):
                        self.R5 = (self.read() == '\x1b')
                    elif (x == '\x2d'):
                        self.R4 = (self.read() == '\x1b')
                    elif (x == '\x30'):
                        self.R3 = (self.read() == '\x1b')
                    elif (x == '\x33'):
                        self.R2 = (self.read() == '\x1b')
                    elif (x == '\x36'):
                        self.R1 = (self.read() == '\x1b')
                    elif (x == '\x39'):
                        self.R0 = (self.read() == '\x1b')
                if self.RD:
                    self.last_floor = \
                        (32 if self.R5 else 0) + \
                        (16 if self.R5 else 0) + \
                        (8 if self.R5 else 0) + \
                        (4 if self.R5 else 0) + \
                        (2 if self.R5 else 0) + \
                        (1 if self.R5 else 0) - 1                        

    def loop(self):
        self.wait_for_term_req()
        self.wait_for_term_req()

        self.wait_for_enq()
        sys.stderr.write('Got logo\n')
        self.ser.write(' ') # "Press any key"
        self.wait_for_enq()
        sys.stderr.write('Got main menu\n')
        self.ser.write('\x01B\r') # F3
        self.wait_for_enq()
        sys.stderr.write('Got hoistway view\n')

        while True:
            self.update_status()
            if not self.cmd_queue.empty():
                sys.stderr.write('Got a command\n')
                self.go_to_floor(self.cmd_queue.get())

class ServerThread(threading.Thread):
    def run(self):
        self.httpd.serve_forever()

if __name__ == "__main__":
    r = Robovator()

    httpd = BaseHTTPServer.HTTPServer(('172.28.7.241', 4443), RobovatorRequestHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile='robovator.crt', keyfile='robovator.key', server_side=True)
    httpd.cmd_queue = r.cmd_queue

    server_thread = ServerThread()
    server_thread.httpd = httpd
    t = server_thread.start()
    
    r.loop()
