'''
Each circle represents an unused pin.
Each other symbol represents a used one and what it's used by

> - a green LED as an indicator light.
X - PT-1000 Temperature Sensor
Z - VEM17700 Lux Sensor

3V3 power       ZX    5V power
SDA             ZO
SCL             ZO
                OX    TXD
GND             ZX    RXD
                OO
                OX    GND
                OO
                OO
                OO
                OO
                OO
                OO
                OO
                OO
                OO
                OO
                OO
GPIO 26         >O
GND             >O
'''




#communication
import smbus
import serial
from serial import SerialException
import board
import adafruit_veml7700

import sys, os
import time
from datetime import datetime, timedelta
import atexit

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import socket

import RPi.GPIO as GPIO
def clean():
    print("gpio cleaned")
    GPIO.cleanup()

# following functions are taken straight from AtlasScientific's github repo. Same for their UART implementation
# https://github.com/AtlasScientific/Raspberry-Pi-sample-code 
def send_cmd(cmd):
	"""
	Send command to the Atlas Sensor.
	Before sending, add Carriage Return at the end of the command.
	:param cmd:
	:return:
	"""
	buf = cmd + "\r"     	# add carriage return
	try:
		ser.write(buf.encode('utf-8'))
		return True
	except SerialException as e:
		print ("Error, ", e)
		return None
def read_line():
	"""
	taken from the ftdi library and modified to 
	use the ezo line separator "\r"
	"""
	lsl = len(b'\r')
	line_buffer = []
	while True:
		next_char = ser.read(1)
		if next_char == b'':
			break
		line_buffer.append(next_char)
		if (len(line_buffer) >= lsl and
				line_buffer[-lsl:] == [b'\r']):
			break
	return b''.join(line_buffer)
def read_lines():
	"""
	also taken from ftdi lib to work with modified readline function
	"""
	lines = []
	try:
		while True:
			line = read_line()
			if not line:
				break
				ser.flush_input()
			lines.append(line)
		return lines
	
	except SerialException as e:
		print( "Error, ", e)
		return None	


#The following functions are all for MQTT.

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("\nConnected with result code "+str(rc))
    
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    print("Subscribing to topic \"sensors/birdhouse1\"")
    client.subscribe("sensors/birdhouse1")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, message):
    # most will not have messages this is just for testing
    print("\nMessage received")
    print("topic =", message.topic)
    m_decode=message.payload.decode("utf-8","ignore")
    #print("data Received",m_decode)
    
    print("Converting from Json to Object")
    m_in=json.loads(m_decode)

    print(m_in)

#publish one
def publish_one(dict, client):
    data_out = json.dumps(dict)
    #QOS defines the guarantee of a message being sent. 0 - At most once, 1 - At least once, 2 - Exactly once. The higher the number, the slower the protocol.
    client.publish("sensors/birdhouse1", data_out, qos=1)
    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(26, GPIO.LOW)

if __name__ == "__main__":

    #when the program terminates we will clean up GPIO stuff.
    atexit.register(clean)


    '''
    GPIO Setup
    '''


    GPIO.setwarnings(False)
    GPIO.setup(26, GPIO.OUT, initial = GPIO.LOW)




    '''
    Direct way of setting up the VEML7700 lux sensor.
    Information gleaned from https://www.vishay.com/docs/84323/designingveml7700.pdf

    This is all through I2C
    '''
    print("setting up VEML7700 lux sensor...")
    
    '''
    bus = smbus.SMBus(1)

    addr = 0x10

    #Write registers
    als_conf_0 = 0x00
    als_WH = 0x01
    als_WL = 0x02
    pow_sav = 0x03

    #Read registers
    als = 0x04
    white = 0x05
    interrupt = 0x06


    # These settings will provide the max range for the sensor (0-120Klx)
    # but at the lowest precision:
    #              LSB   MSB
    confValues = [0x00, 0x13] # 1/8 gain, 25ms IT (Integration Time)
    #Reference data sheet Table 1 for configuration settings

    interrupt_high = [0x00, 0x00] # Clear values
    #Reference data sheet Table 2 for High Threshold

    interrupt_low = [0x00, 0x00] # Clear values
    #Reference data sheet Table 3 for Low Threshold

    power_save_mode = [0x00, 0x00] # Clear values
    #Reference data sheet Table 4 for Power Saving Modes

    bus.write_i2c_block_data(addr, als_conf_0, confValues)
    bus.write_i2c_block_data(addr, als_WH, interrupt_high)
    bus.write_i2c_block_data(addr, als_WL, interrupt_low)
    bus.write_i2c_block_data(addr, pow_sav, power_save_mode)
    '''

    # Turns out there's a much easier way to do this with a premade package lol
    i2c = board.I2C()  # uses board.SCL and board.SDA
    veml7700 = adafruit_veml7700.VEML7700(i2c)
    print("done!")

    '''
    Setting up the Atlas PT-1000 thermometer through UART.
    TX/RX is '/dev/ttyS0' and it will be defined as such
    '''

    print("Connecting AtlasScientific PT-1000...")

    uart_addr = '/dev/ttyS0'

    #Try to connect to the serial port. This shouldn't fail and if it does it's a hardware issue at this point.
    try:
        ser = serial.Serial(uart_addr, 9600, timeout=0)
    except serial.SerialException as e:
        print( "Error, ", e)
        sys.exit(0)
    send_cmd("C,0") #Turn off cont mode
    time.sleep(1)
    ser.flush() # Clear prior data

    print("done!")


    '''
    MQTT Setup
    '''
    
    '''
    hn = socket.gethostname()
    port = 1883 #This is an unsecured port with no TLS, but we really don't care

    print("creating new instance of client")
    client = mqtt.Client(client_id="Birdhouse_1")

    client.on_connect = on_connect
    client.on_message = on_message


    while True:
        try:
            client.connect(hn, port)
        except Exception as e:
            print(e)
        else:
            break

    print("Loop start")
    client.loop_start() #creates a thread for mqtt to run off of seperate to the calling thread that the rest of the code is running on.
    '''
    
    '''
    InfluxDB setup
    '''
    
    token = "nyAWc7MpHrEuB0cKpUdG5aY6DEvJgiVYcQakKGsq-UNavSiv_krD1NvYik9rH0LFsYC6uz1FBwWQoiyn-us0ag=="
    org = "david.pesin@gmail.com"
    bucket = "david.pesin's Bucket"
    
    dbclient = InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token, org=org)
    write_api = dbclient.write_api(write_options=SYNCHRONOUS)
    
    
    try:
        while True:
            '''lux'''
            #word = bus.read_word_data(addr,als)
            
            #gain = 1.8432 #Gain for 1/8 gain & 25ms IT
            #Reference www.vishay.com/docs/84323/designingveml7700.pdf
            # 'Calculating the LUX Level'       
            #val = round(word * gain,3) # LUX VALUE

            val = veml7700.light #easier lux value

            '''temp'''
            send_cmd("R") #send commands
            lines = read_lines() #read results
            '''Printing'''


            # we're just gonna send lux before trying to do anything temp related.
            point = Point("birdhouse") \
                .tag("bhID", "bh1") \
                .field("lux", val) \
                .time(datetime.utcnow(), WritePrecision.NS)
            write_api.write(bucket, org, point)

            print(val)

            try:
                print(lines[0].decode("utf-8"))
            except IndexError:
                print("nothing sent! Not sending temp")
            except UnicodeDecodeError:
                print("garbage was sent! Not sending temp")

            else:
                if lines[0][0] == b'*'[0]: #Checking for status messages, sometimes the first message is going to be one.
                    print("status message, skipping")
                elif lines[0][4] == b"-1024": #Checking for erroneous response. throws -1024 degrees whenever disconnected.
                    print("the thermometer is disconnected")
                else:

                    #The MQTT portion will be redone once we have a bunch of sensors, but honestly we probably wont need MQTT
                    #Considering they will independently be sending information
                    '''
                    output_json = {#dictionary for file
                        'utc': str(datetime.utcnow() - timedelta(hours=4)), #getting utc into our timezone 
                        'temp': lines[0][:6].decode('utf-8'), #truncating because it returns '/r' after each reading
                        'lux': str(val),
                        'birdhouse': 1
                    }
                    try:
                        publish_one(output_json)
                    except Exception as e:
                        print(str(e))
                    '''
                    
                    point = Point("birdhouse") \
                            .tag("bhID", "bh1") \
                            .field("tmp", float(lines[0][:6].decode('utf-8')))\
                            .time(datetime.utcnow(), WritePrecision.NS)
                    write_api.write(bucket, org, point)



            GPIO.output(26, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(26, GPIO.LOW)
            time.sleep(0.9)

    except KeyboardInterrupt:
        print("\n\nExiting loop and clearing data")
        ser.flush()
        sys.exit()



