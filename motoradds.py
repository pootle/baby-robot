#!/usr/bin/python3

import motorset
class tester(motorset.motorset):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mlist=[mname for mname in self.motors.keys()]
        usespeed=True
        for mname in mlist:
            if self.motors[mname].speedLimits() is None:
                usespeed=False
        if usespeed:
            self.mcontrols={
                'smode': 'speed',
                'motors': {
                     mname: {
                        'sfunc': self.motors[mname].speed,
                        'smap' : self.motors[mname].speedLimits()} 
                            for mname in mlist}}
        else:
            self.mcontrols={
                'smode':'DC',
                'motors': {
                    mname: {
                        'sfunc': self.motors[mname].DC, 
                        'smax': self.motors[mname].maxDC()} 
                            for mname in mlist}}
        self.mcontrols['nullspeed']=150
        self.mcontrols['nullturn']=150

    def setspeeddir(self, speedf, dirf):
        """
        takes speed and turn values and sets the individual speeds of the 'left' and 'right' motors
        
        speedf: from -1000 to +1000 representing full speed backwards to full speed forwards
        
        dirf  : from -1000 to + 1000 representing fastest possible turn left, through straight to fastest possible turn right
        """
#        print("request speed", speedf, '(', type(speedf).__name__, ') ','dir', dirf, '(', type(dirf).__name__, ')')
        nullspeed=self.mcontrols['nullspeed']
        speedl=0 if abs(speedf) < nullspeed else (abs(speedf)-nullspeed)/(1000-nullspeed)
        if abs(speedf) < 0:
            speedl=-speedl
        speedr=speedl
        # speedr/l now in range -1 to +1
#        print('normed speed: %3.2f' % speedl)
        nullturn=self.mcontrols['nullturn']
        if abs(dirf) > nullturn:
            spad=(abs(dirf)-nullturn)/(1000-nullturn)
            if dirf < 0:
                spad=-spad
            # spad now in range -1 to +1
            speedl+=spad
            speedr-=spad
            combo=abs(speedf)+abs(dirf)
            if combo > 1000:
                scale=1000/combo
                speedl*=scale
                speedr*=scale
        print('abstract speeds: %3.2f   /   %3.2f' % (speedl, speedr))
        smode = self.mcontrols['smode']
        if smode=='DC':
            lval=speedl*self.mcontrols['motors']['left']['smax']
            rval=speedr*self.mcontrols['motors']['right']['smax']
            print('DC mode settings left: %3d, right: %3d' % (lval,rval))
            self.mcontrols['motors']['left']['sfunc'](lval)
            self.mcontrols['motors']['right']['sfunc'](rval)
        elif smode=='speed':
            lpars=self.mcontrols['motors']['left']['smap']
            rpars=self.mcontrols['motors']['right']['smap']
            if -.001 < speedl < .001:
                lval=0
            elif speedl < 0:
                lval=lpars[1]-(lpars[0]-lpars[1])*speedl
            else:
                lval=lpars[2]+(lpars[3]-lpars[2])*speedl
            if -.001 < speedr < .001:
                rval=0
            elif speedr < 0:
                rval=rpars[1]-(rpars[0]-rpars[1])*speedr
            else:
                rval=rpars[2]+(rpars[3]-rpars[2])*speedr
            print('speed mode settings left: %3d, right: %3d' % (lval,rval))
            self.mcontrols['motors']['left']['sfunc'](lval)
            self.mcontrols['motors']['right']['sfunc'](rval)
        else:
            print('no code for smode %s' % smode)
#        speedl=int(speedl/4)
#        speedr=int(speedr/4)
##        if speedf > -50:
#            speedl, speedr = speedr, speedl
#        print("request speed", speedf, '(', type(speedf).__name__, ') ','dir', dirf, '(', type(dirf).__name__, ')', '=> (%d, %d)' % (speedl,speedr))
#        self.motors['left'].DC(speedl)
#        self.motors['right'].DC(speedr)

import asprocess

class tstub(asprocess.runAsProcess):
    def __init__(self, **kwargs):
        super().__init__('motoradds.tester', ticktime=.1, procName='motorprocess', kwacktimeout=3, timeoutfunction='stopMotor', **kwargs)

    def setspeeddir(self, speedf, dirf):
        self.runOnProc('setspeeddir', 'a', speedf=speedf, dirf=dirf)

    def close(self):
        self.runOnProc('close','e')
        self.stubend()
