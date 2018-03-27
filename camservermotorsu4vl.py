#!/usr/bin/python3

import http.server
import argparse
import importlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from socketserver import ThreadingMixIn
import json

indexbase={'ok':'index.html','off':'index_off.html','na':'index_nocam.html'}

class camhandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        pr = urlparse(self.path)
        pf = pr.path.split('/')
        if pf[-1] == '' or pf[-1] == 'index.html':
            sfp=Path(indexfiles[camstate])
            pstr = self.headers['Host'].split(':')
            pstr[-1] = '8080'
            with sfp.open('r') as sfile:
                sparms={'srvr':':'.join(pstr)}
                xs=sfile.read()
                self.simpleSend(xs.format(**sparms))
        elif pf[-1] == 'setspeedturn2':
            qu = parse_qs(pr.query) if pr.query else ()
            if qu and 'speed' in qu and 'turn' in qu:
                speed=int(qu['speed'][0])
                turn=int(qu['turn'][0])
                if not mdrive is None:
                    mdrive.setspeeddir(speedf=speed, dirf=turn)
            self.simpleSend('boo')
        elif pf[-1]=='cputemp':
            with open('/sys/class/thermal/thermal_zone0/temp') as cput:
                tstr='%3.1f' % (int(cput.readline().strip())/1000)
            self.simpleSend(tstr)
            if not mdrive is None:
                mdrive.sendkwac()
        elif pf[-1]=='sensors':
            if usens is None:
                self.send_response(404)
            else:
                lastreadings=usens.getlastgood()
                datats=json.dumps(lastreadings)
                self.simpleSend(datats)
            if not mdrive is None:
                mdrive.sendkwac()
        elif pf[1]=='shutdown':
            server.shutdown()
            self.simpleSend('wibble')
        else:
            print('do not understand', pf[-1])
            self.send_error(404,"I think there may be an error - I only do jpegs (%s)" % pf[-1])
            return

    def simpleSend(self, thcontent):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(thcontent.encode('utf-8'))

    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

def findMyIp():
    """
    A noddy function to find local machines' IP address for simple cases....
    based on info from https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    
    returns an array of IP addresses (in simple cases there will only be one entry)
    """
    import socket
    return([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or 
            [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]
          )
DEFWEBPORT      = 8088
DEFPIMOTORLIB   = "/home/pi/gitbits/pimotors"

if __name__ == '__main__':
    import sys, os, pathlib
    global indexfiles
    clparse = argparse.ArgumentParser(description='runs a simple webserver to control motors specified in the configuration file. '
            'The configuration file must be in the current working directory or a directory in $PYTHONPATH')
    clparse.add_argument( "-w", "--webport", type=int, default=DEFWEBPORT,
        help="port used for the webserver, default %d" % DEFWEBPORT)
    clparse.add_argument( "-a", "--async",  action="store_true", help='run motor control in separate thread')
    clparse.add_argument( "-p", "--pimotorlib", default=DEFPIMOTORLIB,
        help="pimotors library, default %s" % DEFPIMOTORLIB)
    clparse.add_argument( "-i", "--htmlfolder", default='',
        help="folder contaning html files, default is folder this module loads from")
    clparse.add_argument('config', help='configuration file to use')
    args=clparse.parse_args()
    sys.path.insert(1, args.pimotorlib)
    sys.path.insert(1, os.getcwd())
    pimfold=pathlib.Path(sys.path[0] if args.htmlfolder=='' else args.htmlfolder)
    indexfiles={k:pimfold/v for k,v in indexbase.items()}
    conf=importlib.import_module(args.config)
    webport = args.webport
    if hasattr(conf,'motordef'):
        import motoradds
        if args.async:
            mdrive=motoradds.tstub(motordefs=conf.motordef)
            minf='motors in new process from config file %s' % args.config
        else:
            mdrive=motoradds.tester(motordefs=conf.motordef)
            minf='motors in process from config file %s' % args.config
    else:
       mdrive=None
       minf='no motors found'
    usens=None
    usinf='no sensors running'
    server = ThreadedHTTPServer(('',webport),camhandler)
    import pistatus
    camon=pistatus.get_state('camera_on')
    if camon:
        camstate='ok'
    else:
        camenabled=pistatus.get_state('camera_enabled')
        if camenabled:
            camstate='off'
        else:
            camstate='na'
    ips=findMyIp()
    if len(ips)==0:
        print('starting webserver on internal IP only (no external IP addresses found), port %d, %s, %s' % (webport, minf, usinf))
    elif len(ips)==1:
        print('Starting webserver on %s:%d, %s, %s' % (ips[0],webport, minf, usinf))
    else:
        print('Starting webserver on multiple ip addresses (%s), port:%d, %s, %s' % (str(ips),webport, minf, usinf))
    try:
        server.serve_forever()
        print('webserver shut down')
    except KeyboardInterrupt:
        server.socket.close()
    if not mdrive is None:
        if args.async:
            pstats=mdrive.getProcessStats()
            idlep=pstats['idletime']/pstats['elapsed']*100
            cpup=pstats['cputime']/pstats['elapsed']*100
            m,s = divmod(pstats['elapsed'],60)
            h,m = divmod(m,60)
            print('elapsed: %02d:%02d:%4.2f, idle%%: %4.2f, cpu%%: %3.2f with %d ticks.' % (int(h), int(m),s,idlep, cpup, pstats['ticks']))
        mdrive.close()
