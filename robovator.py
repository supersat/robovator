#!/usr/bin/python
# Robovator
# An HTTPS interface to the MCE IMC-SCR elevator controller

import BaseHTTPServer, SimpleHTTPServer
import ssl
import serial

#httpd = BaseHTTPServer.HTTPServer(('localhost', 4443), SimpleHTTPServer.SimpleHTTPRequestHandler)
#httpd.socket = ssl.wrap_socket (httpd.socket, certfile='path/to/localhost.pem', server_side=True)
#httpd.serve_forever()

class robovator:
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyS0', 19200, xonxoff=1, rtscts=0, timeout=None);
        self.floor_selected = 0;

    def loop(self):
        while True:
            if self.ser.read() == '\x1b':
                if self.ser.read() == ' ':
                    print 'Got terminal type request';
                    break;

if __name__ == "__main__":
    r = robovator();
    r.loop()
