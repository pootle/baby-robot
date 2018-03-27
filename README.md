# baby-robot
A Collection of the files needed to make a very simple web browser controlled robot based on a Raspberry Pi.

I lead a small group at my local U3A using Raspberry Pi's to play with computers and learn programming.

This is info on a project we have just started to work on a small simple robot.

It is a simple motorised chassis that can be remotely controlled and streams video from an on-board 
camera to a web page. The web page can also control the motors.

It uses various bits of existing software and some extra parts I have written.

* camservermotorsu4vl.py  This can be run direct from the command line. It runs a basic python webserver which displays a live video stream (we are using UV4L) and allows the robot to be controlled from the web page.
* index.html The web page (that has some parameterised edits applied) that camservermotorsuv4l.py serves up
* motoradds.py very simple extension classes to a motorset (from pimotors) to provide simple steering control
* devastator_config.py The configuration info needed to run 2 motors with steering through an adafruit DC and stepper motor HAT

Note there are a couple of other files in this repo that are historical and will be removed shortly.

In particular most of the functionality from phatpigpio has now been moved to the pimotors repo.

##setup
* clone the repository pimotors to your Raspberry Pi
* clone this repository to your Raspberry PI
* clone the adafruit DC & stepper Hat repository if you are using that hat
* from the baby-robot repository, copy robot.service to /etc/systemd/system
* create a folder 'robotrun' directly under pi's home folder. This will hold the robot config and log files. You can use a different folder, robot.service will need to be updated
* copy and edit an appropriate config file from pimotors to ~/robotrun
* sudo systemctl daemon-reload # to pick up the new service file
* sudo service robot start
* sudo service robot status
* on any local machine, use a web browser to open <pi's IP address':8088
