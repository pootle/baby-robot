#!/usr/bin/python3
"""
A module to provide simple in-line control of multiple pwm devices (typically dc motors via an h-bridge) using pigpio.

Originally implemented to control motors through a pimoroni explorer phat (https://shop.pimoroni.com/products/explorer-phat).

This method using pigpio has a constant cpu load of ~10% on a raspberry pi Zero, as compared to the pimoroni module which has
a constant cpu load of ~20%.
"""
import pigpio
import atexit

dlookup={
    0: 'stopped',
    1: 'forward',
    2: 'backward',
}
"""
The speed table maps from speeds (in the range 0-srange) to pwm frequencies and dutycycles
at any given speed, 1 or 2 entries are used; if the requested speed equals entry[0], then that entry
defines the frequency (entry[1]) and duty cycle (entry[2]), otherwise the pair of entries where
the requested speed lies between the entrya[0] and entryb[0] are used as follows:

The duty cycle used will be the linear interpolation between entrya[2] and entryb[2] and the frequency will be
that defined in entrya[1].
"""
defaultspeedtable1000=(
    (0,10,0),
    (21,10,0),
    (22,   10, 40),
    (45,   10, 60),
    (79,   10, 80),
    (100,  10, 90),
    (127,  10, 100),
    (148,  10, 110),
    (190,  10, 120),
    (264,  20, 125),
    (345,  20, 130),
    (426,  20, 140),
    (430,  40, 140),
    (447,  40, 145),
    (476,  40, 155),
    (563,  40, 175),
    (591,  40, 195),
    (651,  40, 220),
    (702,  40, 240),
    (760,  40, 280),
    (813,  40, 325),
    (844,  40, 350),
    (942,  40, 500),
    (985,  40, 600),
    (1000, 40, 700),
)

class motor():
    """
    A class to provide simple pwm control - typically of a motor - via a pair of pins to an H bridge such as
    DRV8833PWP as found on a pimoroni explorer HAT.
    
    """
    def __init__(self, name, pinf, pinb, frequency, range=255, speedtable=None, piggy=None, loglevel=0, **kwargs):
        """
        Initialises a single PWM motor using pigpio controlling an H bridge 

        The forward and backward pins are set up for pwm with a 0% (stopped, no power) duty cycle and
        the frequency is initialised
        
        pinf      : the gpio pin for 'forwards'
        pinb      : the gpio pin for 'backwards'
        frequency : the frequency in Hz used to drive the motor 
                    (see http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_frequency)
        range     : the (integer) range of values used for (approximately) the %age on time
                    -range will drive the motor full speed in reverse, +(range/2) will drive it at
                    50% duty cycle forwards
        speedtable: a table that maps requested speed to pwm values to enable an approximately linear response
        piggy     : an instance of pigpio.pi (or None in which case a new instance of pigpio is started)
        loglevel  : allows simple logging of what goes on via print statements
        **kwargs  : allows other arbitrary keyword parameters to be ignored
        """
        if isinstance(range, int) and 10<=range<=10000:
            self.piggy=pigpio.pi() if piggy is None else piggy
            self.mf=pinf
            self.mb=pinb
            self.Hz = None
            self.range=range
            self.lastdc=None
            self.loglevel=loglevel
            self.name=name
            self.setFrequency(frequency)
            self.piggy.set_PWM_range(self.mf,range)
            self.piggy.set_PWM_range(self.mb, range)
            self.stop()
            self.speedtab=defaultspeedtable1000 if speedtable is None else speedtable
        else:
            raise ValueError('%s is not valid - should be integer in range (10..10000)',str(range))

    def stop(self):
        """
        stops (removes power) from the motor by setting the dutycycle to 0 on both pins.
        """
        self.setDC(0)

    def setDC(self, dutycycle):
        """
        The mpost basic way to drive the motor. Sets the motor's duty cycle to the given value.
        
        The rpm resulting from different values of duty cycle will follow an approximately asymptotic curve after some 
        wibbly bits at low values.
        
        First checks the new value is different to the last value, and the value is valid.
        """
        if dutycycle == self.lastdc:
            return
        if -self.range<=dutycycle<=self.range:
            if dutycycle >=0:
                self.piggy.set_PWM_dutycycle(self.mb,0)
                self.piggy.set_PWM_dutycycle(self.mf,int(dutycycle))
            else:
                self.piggy.set_PWM_dutycycle(self.mf,0)
                self.piggy.set_PWM_dutycycle(self.mb,int(-dutycycle))
            if self.loglevel & 4 == 4:
                if self.lastdc is None:
                    print('motor %s: motor speed initially set to %d' % (str(self.name), dutycycle))
                else:
                    print('motor %s: motor speed changed from %d to %d' % (str(self.name), self.lastdc, dutycycle))
            elif self.loglevel & 2 == 2:
                newm=0 if dutycycle is 0 else 1 if dutycycle > 0 else 2
                oldm=0 if self.lastdc is 0 or self.lastdc is None else 1 if self.lastdc > 0 else 2
                if oldm != newm:
                    print('motor %s: now %s, was %s' % (str(self.name), dlookup[newm], dlookup[oldm]))
            self.lastdc=dutycycle
        else:
            self.stop()
            raise ValueError('motor %s: %s is not valid - should be in range (-255, +255)' % (
                str(self.name), str(dutycycle)))

    def setFrequency(self, frequency):
        """
        changes the frequency to be used for this motor. For low revs, low frequencies work better than higher
        frequencies, albeit this can make the motion a bit jerky.
        
        See http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_frequency for further details
        """
        if isinstance(frequency, int):
            if frequency == self.Hz:
                return
            self.Hz=frequency
            self.piggy.set_PWM_frequency(self.mb, self.Hz)
            newf = self.piggy.set_PWM_frequency(self.mf, self.Hz)
            if self.loglevel & 2 == 2:
                print('motor %s: frequency now %d, requested %d' % (str(self.name), newf, self.Hz))
        else:
            raise ValueError('motor %s: setFrequency - frequency must be an int, not %s' % (
                    str(self.name), type(frequency).__name__))

    def speed(self, speed):
        """
        Provides an approximately linear way to drive the motor, i.e. the motor rpm should be a simple ratio of the speed
        parameter to this call. This uses the lookup table in self.speedtab. Se defaultspeedtable1000 for an explanation.
        """
        aspeed = abs(speed)
        i=0
        while i < len(self.speedtab) and self.speedtab[i][0] < aspeed:
            i+=1
        if i>=len(self.speedtab):
            enta=None
            entb=self.speedtab[-1]
        elif i==0 or self.speedtab[i][0]==aspeed:
            enta=None
            entb=self.speedtab[i]
        else:
            enta=self.speedtab[i-1]
            entb=self.speedtab[i]
        if enta is None:
            fr=entb[1]
            dc=entb[2]
        else:
            fr=enta[1]
            deltas=(aspeed-enta[0]) / (entb[0]-enta[0])
            dc=int(round(enta[2]+(entb[2]-enta[2]) * deltas))
        if self.loglevel & 8==8:
            print('motor %s: dc %d and frequency %d derived from speed %d and entries %s, %s' % (
                    str(self.name), dc, fr, speed, str(enta), str(entb)))
        self.setFrequency(fr)
        self.setDC(-dc if speed < 0 else dc)

defaultsallmotors= {'range':1000, 'frequency':100, 'loglevel':6}

defaultmotorparams=(
    {'name': 'left',  'pinf':26, 'pinb':21, 'loglevel':10},
    {'name': 'right', 'pinf':20, 'pinb':19, 'loglevel':10},
)

class phatpair():
    """
    provides control of a pair of motors that provide drive and steering - typically a trike style with 1 free wheel and 
    2 driven wheels each with its own motor.
    """
    def __init__(self, motors=None, motordefaults=None, piggy=None):
        self.piggy=pigpio.pi() if piggy is None else piggy
        self.motors={}
        for i in range(max(len(defaultmotorparams), 0 if motors is None else len(motors))):
            mp=defaultsallmotors.copy()
            if not motordefaults is None:
                mp.update(motordefaults)
            if i < len(defaultmotorparams):
                mp.update(defaultmotorparams[i])
            if not motors is None and i < len(motors):
                mp.update(motors[i])
            self.motors[mp['name']]=motor(piggy=self.piggy, **mp)
        atexit.register(self.close)
        print('phatpair set up motors %s' % ','.join(self.motors.keys()))

    def setMotorFrequency(self, f, mlist=None):
        """
        sets the frequency used for the dutycycle (see class help for mlist param)
        
        see the motor class for details of the frequency param.
        """
        for u in self._delist(mlist):
            u.setFrequency(f)

    def setMotorDC(self, dutycycle, mlist=None):
        """
        directly sets the duty cycle of the given set of motors (see class help for mlist param)
        
        See the motor class for details of the dutycycle param.
        """
        for u in self._delist(mlist):
            u.setDC(dutycycle)

    def setMotorSpeed(self, speed, mlist=None):
        """
        Sets the speed of the given set of motors (see class help for mlist param)
        
        See the motor class for details of the speed param.
        """
        for u in self._delist(mlist):
            u.speed(speed)

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
        self.motors['left'].speed(speedl)
        self.motors['right'].speed(speedr)

    def stopMotor(self, mlist=None):
        """
        stops specified motors (see class help for mlist param)
        """
        for u in self._delist(mlist):
            u.stop()

    def close(self):
        """
        completely shuts down this instance and deletes all internal knowledge of motors
        """
        if not self.piggy is None:
            self.stopMotor()
            self.piggy.stop()
            self.piggy=None
        print("phatpair closing down")
        self.motors={}

    def _delist(self, units):
        """
        converts / validates units param to list of motors
        """ 
        if units is None:
            return tuple(self.motors.values())
        elif isinstance(units,str):
            if units in self.motors:
                return (self.motors[units],)
            else:
                raise ValueError('%s is not a known motor name' % units)
        else:
            for u in units:
                if not u in self.motors:
                    self.stopMotor()
                    raise ValueError('%s is not a known motor name' % str(u))
            return [self.motors[m] for m in units]