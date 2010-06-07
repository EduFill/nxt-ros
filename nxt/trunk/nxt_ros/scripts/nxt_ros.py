#!/usr/bin/env python

import roslib; roslib.load_manifest('nxt_ros')  
import nxt.locator
import rospy
import math
from nxt.motor import PORT_A, PORT_B, PORT_C
from nxt.sensor import PORT_1, PORT_2, PORT_3, PORT_4
import nxt.sensor 
import nxt.motor 
import thread
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool
from nxt_msgs.msg import Range, Contact, JointCommand, Color

POWER_TO_NM = 1.0

global my_lock
my_lock = thread.allocate_lock()

def check_params(ns, params):
    for p in params:
        if not rospy.get_param(ns+'/'+p):
            return False
    return True


class Motor:
    def __init__(self, params, comm):
        # create motor
        self.name = params['name']
        self.motor = nxt.motor.Motor(comm, eval(params['port']))

        # create publisher
        self.pub = rospy.Publisher('joint_state', JointState)
        self.last_js = None
        
        # create subscriber
        self.sub = rospy.Subscriber('joint_command', JointCommand, self.cmd_cb, None, 1)


    def cmd_cb(self, msg):
        if msg.name == self.name:
            my_lock.acquire()
            self.motor.run(int(msg.effort * POWER_TO_NM), 0)
            my_lock.release()


    def trigger(self):
        js = JointState()
        js.header.stamp = rospy.Time.now()
        state = self.motor.get_output_state()
        js.name.append(self.name)
        js.position.append(state[9] * math.pi / 180.0)
        js.effort.append(state[1] * POWER_TO_NM)
        vel = 0
        if self.last_js:
            vel = (js.position[0]-self.last_js.position[0])/(js.header.stamp-self.last_js.header.stamp).to_sec()
            js.velocity.append(vel)
        self.pub.publish(js)
        self.last_js = js




class TouchSensor:
    def __init__(self, params, comm):
        # create touch sensor
        self.touch = nxt.sensor.TouchSensor(comm, eval(params['port']))
        self.frame_id = params['frame_id']

        # create publisher
        self.pub = rospy.Publisher(params['name'], Contact)
        
    def trigger(self):
        ct = Contact()
        ct.contact = self.touch.get_sample()
        ct.header.frame_id = self.frame_id
        ct.header.stamp = rospy.Time.now()
        self.pub.publish(ct)



class UltraSonicSensor:
    def __init__(self, params, comm):
        # create ultrasonic sensor
        self.ultrasonic = nxt.sensor.UltrasonicSensor(comm, eval(params['port']))
        self.frame_id = params['frame_id']

        # create publisher
        self.pub = rospy.Publisher(params['name'], Range)
        
    def trigger(self):
        ds = Range()
        ds.header.frame_id = self.frame_id
        ds.header.stamp = rospy.Time.now()
        ds.range = self.ultrasonic.get_sample()/100.0
        ds.spread_angle = 0.05
        ds.range_min = 0.0
        ds.range_max = 2.54
        self.pub.publish(ds)


class ColorSensor:
    def __init__(self, params, comm):
        # create color sensor
        self.color = nxt.sensor.ColorSensor(comm, eval(params['port']))
        self.frame_id = params['frame_id']

        # create publisher
        self.pub = rospy.Publisher(params['name'], Color)
        
    def trigger(self):
        co = Color()
        co.header.frame_id = self.frame_id
        co.header.stamp = rospy.Time.now()
        color = self.color.get_color()
        if color == 1:  # black
            co.r = 0.0
            co.g = 0.0
            co.b = 0.0
        elif color == 2: # blue
            co.r = 0.0
            co.g = 0.0
            co.b = 1.0
        elif color == 3: # green
            co.r = 0.0
            co.g = 1.0
            co.b = 0.0
        elif color == 4: # yellow
            co.r = 1.0
            co.g = 1.0
            co.b = 0.0
        elif color == 5: # red
            co.r = 1.0
            co.g = 0.0
            co.b = 1.0
        elif color == 6: # white
            co.r = 1.0
            co.g = 1.0
            co.b = 1.0
        else:
            rospy.logerr('Undefined color of color sensor')
        self.pub.publish(co)




def main():
    sock = nxt.locator.find_one_brick()
    b = sock.connect()

    ns = 'nxt_ros'
    rospy.init_node(ns)
    config = rospy.get_param(ns)
    components = []
    for c in config:
        print c
        if c['type'] == 'motor':
            components.append(Motor(c, b))
        if c['type'] == 'touch':
            components.append(TouchSensor(c, b))
        if c['type'] == 'ultrasonic':
            components.append(UltraSonicSensor(c, b))
        if c['type'] == 'color':
            components.append(ColorSensor(c, b))


    rate = rospy.Rate(50)
    while not rospy.is_shutdown():
        my_lock.acquire()
        for c in components:
            c.trigger()
        my_lock.release()
        rospy.sleep(0.01)



if __name__ == '__main__':
    main()