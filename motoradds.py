#!/usr/bin/python3

import motorset
class tester(motorset.motorset):
    def setspeeddir(self, speedf, dirf):
        """
        takes speed and turn values and sets the individual speeds of the 'left' and 'right' motors
        """
        print("request speed", speedf, '(', type(speedf).__name__, ') ','dir', dirf, '(', type(dirf).__name__, ')')
        speedl=speedr=0 if abs(speedf) < 50 else speedf
        if abs(dirf) > 25:
            spad=dirf/2
            speedl+=spad
            speedr-=spad
            speedl=1000 if speedl>1000 else -1000 if speedl<-1000 else speedl
            speedr=1000 if speedr>1000 else -1000 if speedr<-1000 else speedr
        speedl=int(speedl/4)
        speedr=int(speedr/4)
        if speedf > -50:
            speedl, speedr = speedr, speedl
        print("request speed", speedf, '(', type(speedf).__name__, ') ','dir', dirf, '(', type(dirf).__name__, ')', '=> (%d, %d)' % (speedl,speedr))
        self.motors['left'].DC(speedl)
        self.motors['right'].DC(speedr)

import asprocess

class tstub(asprocess.runAsProcess):
    def __init__(self, **kwargs):
        super().__init__('motoradds', 'tester', ticktime=.3, procName='motorprocess', kwargs=kwargs)

    def setspeeddir(self, speedf, dirf):
        self.runOnProc('setspeeddir', 'a', speedf=speedf, dirf=dirf)

    def close(self):
        self.runOnProc('close','e')
        self.stubend()
