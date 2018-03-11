#!/usr/bin/python3
#def dc hat 2 motors on an adafruit dc and stepper motor hat
#no feedback

motordef=(
    {'direct_h':{'pinf':26, 'pinb': 21, 'invert': True},
     'senseparams': {'pinss': ((17, 27)), 'edges': 'both', 'pulsesperrev':3},
     'analysemotor':{'name':'left'},},
    {'direct_h':{'pinf':20, 'pinb':19},
     'senseparams': {'pinss': ((9, 10)), 'edges': 'both', 'pulsesperrev':3},
     'analysemotor':{'name':'right'},},
)
