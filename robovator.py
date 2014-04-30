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
        self.wfile.write("%s%s" % (self.server.robovator.last_floor, self.server.robovator.mode))
        if self.path.startswith('/move/'):
            self.server.robovator.cmd_queue.put(self.path[6])

    def do_HEAD(self):
        self.send_head()

    def send_head(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', 3)
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
        self.char_mode = '\x30'

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
            if self.mode == 'UP':
                while self.mode == 'UP':
                    self.update_status()
                time.sleep(0.5)                
            for x in range(0, (self.floor_selected - floor)):
                self.ser.write('\x0a')
                time.sleep(0.1)
        elif floor > self.floor_selected:
            if self.mode == 'DN':
                while self.mode == 'DN':
                    self.update_status()
                time.sleep(0.5)
            for x in range(0, (floor - self.floor_selected)):
                self.ser.write('\x0b')
                time.sleep(0.1)
        self.ser.write('\x0d')
        self.floor_selected = floor
        while (self.last_floor != self.floor_selected) and (self.mode != 'PK'):
            self.update_status()
        sys.stderr.write('Done issuing command\n')

    def is_text_active(self):
        if self.read() == '\x1b':
            if self.read() == '\x47':
                self.char_mode = self.read()            
        return self.char_mode != '\x70'

    def update_status(self):
        c = self.read()
        if c == '\x05':
            self.ser.write('\x06')
        elif c == '\x1b':
            c = self.read()
            if c == '\x47':
                self.char_mode = self.read()
            if c == '\x3d':
                y = self.read()
                x = self.read()
                #sys.stderr.write('Moving cursor to %s, %s\n' % (ord(y), ord(x)))
                if (y == '\x29') and (x == '\x4a'):
                    self.mode = self.read() + self.read()
                elif (y == '\x28'):
                    if (x == '\x22'):
                        self.RD = self.is_text_active()
                    elif (x == '\x25'):
                        self.PR = self.is_text_active()
                    elif (x == '\x2a'):
                        self.R5 = self.is_text_active()
                    elif (x == '\x2d'):
                        self.R4 = self.is_text_active()
                    elif (x == '\x30'):
                        self.R3 = self.is_text_active()
                    elif (x == '\x33'):
                        self.R2 = self.is_text_active()
                    elif (x == '\x36'):
                        self.R1 = self.is_text_active()
                    elif (x == '\x39'):
                        self.R0 = self.is_text_active()
        if self.RD:
            floor = \
                (32 * self.R5) + \
                (16 * self.R4) + \
                (8 * self.R3) + \
                (4 * self.R2) + \
                (2 * self.R1) + \
                (1 * self.R0) - 1
            parity = self.PR + self.R5 + self.R4 + self.R3 + self.R2 + self.R1 + self.R0
            if (parity % 2) == 0 and floor != -1:
                self.last_floor = floor

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
    httpd.robovator = r

    server_thread = ServerThread()
    server_thread.httpd = httpd
    t = server_thread.start()
    
    r.loop()
