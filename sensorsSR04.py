#!/usr/bin/python3

"""
A basic module supporting accurate readings from HC-SR04 sensors connected directly to a Raspbery pi.

The module uses pigpio and DMA to drive the trigger pulses, and pigpio callbacks to time the echo pin pulse edges so
the timings should be accurate to a few microseconds. This corresponds to a distance of around 1mm, so the measurement accuracy
is basically the same as the sensor itself.

The primary code never uses time.sleep or other functions that hang up the thread of execution.

Once initialised (i.e once the constructors have completed), all the code runs within the callback functions called from pigpio, 
so the execution thread used to initialise is free to do anything else.
"""

import pigpio
from pigpio import pulse as pgpulse

class simpleHC_SR04():
    """
    The class for a single sensor. After initialisation, it merely tracks edges on the sense pin via the pigpio callbacks and
    takes appropriate action.
    """
    def __init__(self, trigger, sense, bounds, name, parent, **ignore):
        """
        An individual sensor object merely looks after gpio pin connected to the sense output of an HC-SR04. Initiasing it, 
        responding to edge detection callbacks and closing down tidily.
        
        Note that the trigger pin is set up and driven from main class that looks after a bunch of sensors as they are all driven
        
        trigger:    The gpio pin used to trigger the unit to make a measurement. Note this is initialised by the main class, although it is 
                    reset here on closedown
        sense:      The gpio pin used for the sense signal from the unit
        bounds:     A 2-tuple with the minimum and maximum values allowed (outside this range a bad reading is reported)
        name:       The name of the unit used for log and reporting (and to identify the unit in the main class
        parent:     The parent class that supports a number of units. This 'owns' the pigpio interface and provides the log and reporting functions
        **ignore:   Allows other parameters for a unit to be used by the main class, but ignored here.
        
        ***** other unit level parameters supported by the module, but not used in this class.
        trigoffset: Defines the offset with the overall cycle time for this sensor. This allows sensor pulses to be timed so that they do not
                    trigger other nearby sensors.
        """
        assert bounds[1] > bounds[0], 'simpleHC-SR04 bounds parameter problem'
        assert isinstance(trigger, int) and isinstance(sense,int) and 0<trigger<32 and 0<sense<32, 'problem with sense or trigger pin number'
        self.parent=parent
        self.trigp=trigger
        self.sensp=sense
        self.lowerbound, self.upperbound = bounds
        self.name=name
        self.parent.pgp.set_mode(self.sensp, pigpio.INPUT)
        self.lastval=-1
        self.lastgood=-1
        self.parent.pgp.callback(self.sensp, pigpio.EITHER_EDGE, self.echo)
        self.measurestart=None
        self.state='idle'
        self.notmsg= {
            'sensor':self.name,
            'cmdist': 0,
            'tstamp': 0,
            'good'  : False,
        }
        self.logmsg(1, None, 'HC-SR04 %s initialised. Pin %d to trigger, pin %d for echo sense time' % (self.name, self.trigp, self.sensp))

    def stop(self):
        """
        simple method that reports closedown and resets the trigger pin to input mode
        """
        self.parent.pgp.set_mode(self.trigp, pigpio.INPUT)
        self.logmsg(1, None, 'HC-SR04 %s closed' % self.name)

    def logmsg(self, level, tstamp, msg):
        """
        housekeeping / convenience method for logging from this sensor - calls the main class' log method after adding the sensor name.
        Note actual output of log messages is managed in the main class.
        """
        self.parent.logmsg(level=level, tstamp=tstamp, msg=msg, sname=self.name)

    def set_state(self, tstamp, newstate, msg, level):
        """
        single place to update the state and log the change.
        """
        self.logmsg(level, tstamp, 'state %10s->%10s, %s.' % (self.state, newstate, msg))
        self.state=newstate

    def echo(self, pinno, level, tick):
        """
        callback from pigpio whenever the echo sense pin changes state. This is where everything happens after initialisation.
        
        This is called from pigpio.
        
        pinno:  The gpio pin that triggered this call - we don't used this 'cos we only monitor 1 pin.
        level:  indicated whether rising or falling edge. 
                    Rising edge merely records the time and sets the state to measure.
                    Falling edge checks that we are in state measure and if so:
                        calculates time and distance
                        checks within bounds
                        calls the tell method with a dict with appropriate info.
                    if not in state measure, just sets state to error.
        
        This calls the tell method each time a successful measure is made:
        """
        if level==1:
            if self.state=='idle' or self.state=='error':
                self.measurestart=tick
                self.set_state(tick, 'measure', 'rising edge on sense pin', 2)
            else:
                self.set_state(tick, 'error', 'rising edge on sense pin unexpected', 4)
        else:
            if self.state=='measure':
                lastmtime=pigpio.tickDiff(self.measurestart, tick)
                tstamp=tick
                dist=lastmtime * 0.017015   # distance in cm
                mst=lastmtime/1000          # time in milliseconds is a bit friendlier to read
                goodmeasure = self.lowerbound < dist < self.upperbound
                if goodmeasure:
                    msg='good measure: %4.1fcm, %3.1fms' % (dist, mst)
                    self.lastgood=tick
                    self.lastval=dist
                else:
                    msg='bad  measure: %4.1fcm, %3.1fms' % (dist, mst)
                self.set_state(tstamp, 'idle', msg, 8)
                self.tell(dist, tstamp, goodmeasure)
            else:
                self.set_state(tick, 'error', 'unexpected falling edge', 4)

    def tell(self, cmdist, tstamp, isOK):
        """
        Standard method (override as appropriate) to process a successful measure.
            cmdist: distance in cm (assuming you use the default scale value)
            tstamp: timestamp (in microseconds since system boot so all sensors report against the same same clock)
            isOK  : True if the reading is OK, False if out of bounds or any other error. In this latter case the timestamp and
                    distance are the last know good values (if any)

        Calls the main class' tell method with details of the measure made. 
        """
        self.notmsg['cmdist'] = cmdist
        self.notmsg['tstamp'] = tstamp
        self.notmsg['good']   = isOK
        self.parent.tell(self.notmsg)        

class averageHC_SR04(simpleHC_SR04):
    """
    Version of sensor which averages the previous n readings
    """
    def __init__(self, avover=4, **params):
        self.avover=avover
        self.av=None
        self.badcount=0
        super().__init__(**params)

    def tell(self, cmdist, tstamp, isOK):
        if isOK:
            fdist=cmdist   
        else:
            if cmdist <= self.lowerbound:
                fdist=self.lowerbound
            elif cmdist >= self.upperbound:
                fdist=self.upperbound
            else:
                x=17/0
        if self.av is None:
            self.av=fdist
        else:
            self.av=(self.av*(self.avover-1)+fdist)/self.avover
        self.badcount=0
        self.notmsg['cmdist'] = self.av
        self.notmsg['tstamp'] = tstamp
        self.notmsg['good']   = isOK
        self.parent.tell(self.notmsg)     

defprintformat='{sensor}, {good:d}, {M:02d}:{S:02.2f},      {cmdist:5.2f}cm'
deflogformat=defprintformat+'/n'

class usSensors():
    """
    A very simple class to support multiple HC-SR04 connected (nearly) directly to a raspberry pi
    
    The sensors are defined by a list of dicts, each dict with the parameters for a single sensor:
        class:      The class to use for this sensor
        name:       name of the sensor (anything which can be used as a dict key, but typically a string
        
        other parameters depend on the class used for the sensor - see the sensor class for details        
    """
    def __init__(self, sensors, pgp=None, defaults={'bounds':(.5, 150)}, log=3, period=.5, logfile=None, printlog=None,
                logformat=deflogformat, printformat=defprintformat):
        """
        Sets up a sensor controller for multiple HC-SR04 sensors.
        
        Once setup the sensors are identified by the 'name' parameter in the dict
        
        sensors:    a list of dicts, each dict defines a single sensor, the list declares the sensors in turn
        pgp    :    an instance of pigpio to use to interface with the sensors, if None a new instance of pigpio is created
        defaults:   dict ofdefault values for any parameters required by the individual sensor classes - ensures consistency for
                    a group of sensors. Any value will be overridden by values in the individual entries in the sensors param
        log:        log level to be recorded, bit significant - see below
        period:     interval between measurements in seconds
        logfile:    filename for log file
        printlog:   if True log calls are also 'print'ed
        logformat:  format string used for log file lines - uses deflogformat if None
        printformat:format string used for print calls - uses defprintformat if None
        
        log params bits:
            1:      setup and closedown
            2:      record sense pin rising edges
            4:      error / unexpected conditions
            8:      measures
        """
        self.log=log
        self.pgp=pigpio.pi() if pgp is None else pgp
        self.printlog=printlog if not printlog is None else True if logfile is None else False
        self.printformat=printformat
        self.logformat=logformat
        self.logfile=None if logfile is None else open(logfile, mode='w')
        self.sensors={}
        for s in sensors:
            sx=defaults.copy()
            sx.update(s)
            sx['parent']=self
            self.sensors[sx['name']]=sx['class'](**sx)
        self.running=True
        self.setupTriggers(period, [(s['trigger'], s['trigoffset']) for s in sensors if 'trigoffset' in s])   # use the list param so we process in the order declared
        self.logmsg(1, None, None, '%d sensors started' % len(sensors))

    def logmsg(self, level, tstamp, sname, msg):
        """
        logging function used by this class and by sensors
        """
        if level & self.log != 0:
            ts = self.pgp.get_current_tick() if tstamp is None else tstamp
            nm = 'master' if sname is None else sname
            fmsg='%10d (%6s): %s' % (ts, nm, msg)
            if self.printlog:
                print(fmsg)
            if not self.logfile is None:
                self.logfile.write('#', fmsg, '\n')

    def setupTriggers(self, period, pinlist):
        """
        For now, a simple setup to use pigpio waves to send out regular triggers pulses
        """
        self.pgp.wave_clear()
        usperiod=1000000*period
        for p,o in pinlist:
            self.pgp.set_mode(p, pigpio.OUTPUT)
            self.pgp.write(p, 0)
            pchain=[
                pgpulse(0, 0, int(10+o)),
                pgpulse(1<<p, 0, 10),
                pgpulse(0, 1<<p, int(usperiod-20-o))
            ]
            self.pgp.wave_add_generic(pchain)
        wavetime=self.pgp.wave_get_micros()
        self.waveid = self.pgp.wave_create() # create and save id
        self.pgp.wave_send_repeat(self.waveid)
        self.logmsg(1, None, None, 'wave created (%d), time:%3.3f ms' % (self.waveid, wavetime))

    def getlastgood(self):
        """
        returns the last good readings from all the sensors. A polling type of access
        """
        return {sk: (-1 if sv.lastgood==-1 else sv.lastval) for sk, sv in self.sensors.items()}

    def tell(self, msg):
        if not self.logformat is None:
            m, s = divmod(msg['tstamp']/1000000,60)
            h, m = divmod(m,60)
            msg['H']=int(h)
            msg['M']=int(m)
            msg['S']=s
            if not self.printformat is None:
                print(self.printformat.format(**msg))
            if not self.logfile is None:
                self.logfile.write(self.logformat.format(**msg))

    def stop(self):
        self.running=False
        self.pgp.wave_tx_stop()
        for s in self.sensors.values():
            s.stop()
        if not self.logfile is None:
            self.logfile.close()
            self.logfile=None
        self.sensors={}

s1={'class': simpleHC_SR04, 'name': 'left ', 'trigger':6 , 'sense':23, 'trigoffset': 120}
s2={'class': simpleHC_SR04, 'name': 'right', 'trigger':12, 'sense':22, 'trigoffset': 20}
s1a={'class': averageHC_SR04, 'name': 'left ', 'trigger':6 , 'sense':23, 'trigoffset': 120}
s2a={'class': averageHC_SR04, 'name': 'right', 'trigger':12, 'sense':22, 'trigoffset': 20}

if __name__ == '__main__':
    import time
    pgp=pigpio.pi()
    sens1=usSensors(sensors=(s1,), pgp=pgp, log=1, printlog=False)
    running=True
    while running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            running=False
    sens1.stop()
    time.sleep(1)
    pgp.stop()
