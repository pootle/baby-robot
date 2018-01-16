#!/usr/bin/python3

usepigpio=True
import http.server
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from socketserver import ThreadingMixIn
import phatpigpio as ph

class camhandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        pr = urlparse(self.path)
        pf = pr.path.split('/')
        print('split url',pf)
        if pf[-1] == '' or pf[-1] == 'index.html':
            sfp = Path('indexuv4l.html')
            pstr = self.headers['Host'].split(':')
            pstr[-1] = '8080'
            with sfp.open('r') as sfile:
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                sparms={'srvr':':'.join(pstr)}
                print(sparms)
                xs=sfile.read()
                xf=xs.format(**sparms)
                xe=xf.encode('utf-8')
                self.wfile.write(xe)
        elif pf[-1] == 'setspeedturn2':
            qu = parse_qs(pr.query) if pr.query else ()
            print(qu,'for setspeedturn2')
            if qu and 'speed' in qu and 'turn' in qu:
                speed=int(qu['speed'][0])
                turn=int(qu['turn'][0])
                print("touch with speed", speed, 'and turn', turn)
                mdrive.setspeeddir(speedf=speed, dirf=turn)
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'boo')
        elif pf[-1]=='cputemp':
            with open('/sys/class/thermal/thermal_zone0/temp') as cput:
                tstr='%3.1f' % (int(cput.readline().strip())/1000)
            print('read temp %s' % tstr)
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(tstr.encode('utf-8'))
        else:
            print('do not understand', pf[-1])
            self.send_error(404,"I think there may be an error - I only do jpegs (%s)" % pf[-1])
            return

    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

DEFWEBPORT = 8088

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( "-w", "--webport", type=int
        , help="port used for the webserver, default %d" % DEFWEBPORT)
#    parser.add_argument( "-d", "--basedir"
#        , help="base directory for web server, default %s" % DEFBASEDIR)
#    parser.add_argument("-s", "--stereo", action="store_true"
#        , help="expect left / right stereo images in cl / cr directories")

    args = parser.parse_args()
    webport = args.webport if args.webport else DEFWEBPORT
    mdrive=ph.phatpair()
    try:
        print("server starting on port %d" % webport)
        server = ThreadedHTTPServer(('',webport),camhandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()
    
    mdrive.stop()
    mdrive.close()