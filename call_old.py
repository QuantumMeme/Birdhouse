'''
Each circle represents an unused pin.
Each other symbol represents a used one and what it's used by

Use this as a reference: https://pinout.xyz/

> - a green LED as an indicator light.
< - a blue LED as an indicator light
X - PT-1000 Temperature Sensor
    TX -> RXD
    RX -> TXD
    VCC -> 5V
    GND -> GND
Z - VEML7700 Lux Sensor
    VID -> 3V3
    3o3 -> nothing
    GND -> GND
    SDA -> SDA
    SCL -> SCL

3V3 power       ZX    5V power
SDA             ZO
SCL             ZO
                OX    TXD
GND             ZX    RXD
                OO
                OX    GND
                OO
                OO
                O<    GND
                OO
                OO
                OO
                OO
                OO
                OO
                OO
                OO
GPIO 26         >O
GND             ><    GPIO 21


'''




#communication
from json import load
import serial
from serial import SerialException
import board
import adafruit_veml7700

#import string
import sys, os
import time
from datetime import datetime, timedelta
import atexit

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import RPi.GPIO as GPIO



#global flags
veml = False
pt1000 = False
birdhouseID = "bh1" #change for different point on influx


def clean(): # this is defined for atExit.
    GPIO.cleanup()
    print("GPIO unallocated")

# following functions are taken straight from AtlasScientific's github repo. Same for their UART implementation
# https://github.com/AtlasScientific/Raspberry-Pi-sample-code 
def send_cmd(cmd, ser):
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
def read_line(ser):
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
def read_lines(pt1000):
	"""
	also taken from ftdi lib to work with modified readline function
	"""
	lines = []
	try:
		while True:
			line = read_line(pt1000)
			if not line:
				break
				ser.flush_input()
			lines.append(line)
		return lines
	
	except SerialException as e:
		print( "Error, ", e)
		return None	


# You can change the GPIO pins if you want for the LEDs
# https://pinout.xyz/ to help you out there.
def flash_green(stayOn = 0): 
    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.1)
    if stayOn == 0:
        GPIO.output(26, GPIO.LOW)
        time.sleep(0.1)
def flash_red(stayOn = 0):
    GPIO.output(21, GPIO.HIGH)
    time.sleep(0.1)
    if stayOn == 0:
        GPIO.output(21, GPIO.LOW)
        time.sleep(0.1)

#InfluxDB definitions

token = "nyAWc7MpHrEuB0cKpUdG5aY6DEvJgiVYcQakKGsq-UNavSiv_krD1NvYik9rH0LFsYC6uz1FBwWQoiyn-us0ag=="
org = "david.pesin@gmail.com"
bucket = "david.pesin's Bucket"

def sendLux(influx_client, value): # Sending lux 
    point = Point("birdhouse") \
        .tag("bhID", birdhouseID) \
        .field("lux", value) \
        .time(datetime.utcnow(), WritePrecision.NS)
    try: 
        influx_client.write(bucket, org, point)
    except Exception as e:
        print(e)
        for i in range(4):
            flash_red()
    else:
        flash_green()
        print(value)

def sendTemp(influx_client, valueBytes): #Sending first 7 digits (including the period) of the bytes received.

    val = float(valueBytes[0][:6].decode('utf-8'))

    point = Point("birdhouse") \
            .tag("bhID", birdhouseID) \
            .field("tmp", val)\
            .time(datetime.utcnow(), WritePrecision.NS)
    try:
        influx_client.write(bucket, org, point)
    except Exception as e:
        print(e)
        for i in range(4):
            flash_red()
    else:
        flash_green()
        #print(val)

# Hardware setup functions

def loadVEML(): # returning the veml object to be able to get data from it later
    global veml
    try:
        i2c = board.I2C()  # uses board.SCL and board.SDA -- This won't throw any error, it's just using constants 'board' has stored
        obj = adafruit_veml7700.VEML7700(i2c)
    except RuntimeError:
        print("Unable to enable VEML7700")
    except Exception as e: # This is SUPER bad practice, just to catch stuff during testing to find out what exceptions can be thrown
        print("Unknown Error, \n", e)
    else:
        veml = True
        print("done!")
        return obj

def loadPT1000(uart_addr = '/dev/ttyS0'): # returning the serial object of the temperature probe. Defaulting to the tx/rx pins, can change according to your needs though
    global pt1000
    try:
        ser = serial.Serial(uart_addr, 9600, timeout=0)
    except serial.SerialException as e:
        print( "Error, \n", e)
    else:
        pt1000 = True
        send_cmd("C,0", ser) #Turn off cont mode
        time.sleep(1)
        ser.flush() # Clear prior data
        print("done!")
        return ser

def main():
    global veml, pt1000
    #when the program terminates we will clean up GPIO stuff.
    atexit.register(clean)

    #GPIO setup
    GPIO.setwarnings(False)
    GPIO.setup(26, GPIO.OUT, initial = GPIO.LOW)
    GPIO.setup(21, GPIO.OUT, initial = GPIO.LOW)

    #variables will change depending on if the device is on

    print("setting up VEML7700 lux sensor...")

    veml7700 = loadVEML()

    '''
    Setting up the Atlas PT-1000 thermometer through UART.
    TX/RX is '/dev/ttyS0' and it will be defined as such
    '''

    print("Connecting AtlasScientific PT-1000...")

    #Try to connect to the serial port. This shouldn't fail and if it does, check your physical connections
    ser = loadPT1000()

    # We continue if at least one sensor is working, otherwise what's the point?    
    if veml and pt1000:
        print("all connected!")
        for i in range(3):
            flash_green()
    elif veml and not pt1000:
        print("Temperature not connected")
        flash_red()
        flash_red()
        flash_green()
    elif not veml and pt1000:
        print("lux not connected")
        flash_green()
        flash_green()
        flash_red()
    elif not veml and not pt1000:
        print("No devices connected. No point in running this.")
        flash_red(1)
        sys.exit()
    
    '''
    InfluxDB setup
    '''
    while True: # keep trying to connect, no point otherwise
        try:
            dbclient = InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token, org=org)
            write_api = dbclient.write_api(write_options=SYNCHRONOUS)
        except Exception as e:
            print(e)
            for i in range(3):
                flash_red()
        else:
            for i in range(3):
                flash_green()
            break
    
    
    try:
        while True:
            '''lux'''
            # Try to get data, if fails change "veml" variable
            try:
                val = veml7700.light #easier lux value
            except Exception as e:
                print("failed val assignment:\n ", e)
                veml = False
            
            #if it disconnects midway then we can try to do it again?
            if not veml:
                veml7700 = loadVEML()

            # we're just gonna send lux before trying to do anything temp related.
            if veml:
                sendLux(write_api, val)
            else: #lux sensor isn't working, we aren't sending anything
                flash_red()


            '''temp'''

            # Send "read" command to the pt-1000
            
            if not pt1000: #This will usually not fix it, if it's a serial issue there's something wrong with the RPi's setup
                ser = loadPT1000()            
            try:
                send_cmd("R", ser) #send commands
                lines = read_lines(ser) #read results
            except Exception as e: # probably SerialException but unsure if that's the only one. Need to keep testing
                print(e)
                pt1000 = False 

            #Checking results and sending temp
            if pt1000:
                try:
                    print(lines[0].decode("utf-8"))
                except IndexError: #Nothing was sent
                    print("nothing sent; Not sending temp")
                    flash_red()
                except UnicodeDecodeError: #What was sent isn't decodable
                    print("cannot decode data; Not sending temp")
                    flash_red()
                else:
                    try:
                        lines[0].decode("utf-8")
                    except UnicodeDecodeError:
                        print("garbage was sent and cannot be decoded!")
                    if not str(lines[0][0]).isdigit(): #What was sent isn't a number.
                        print("expected float but got string; Not sending temp")
                        flash_red()
                    else:
                        if lines[0][0] == b'*'[0]: #Checking for status messages, sometimes the first message is going to be one.
                            print("status message, skipping")
                            flash_red()
                        elif float(lines[0][:6].decode("utf-8")) < -1000 or float(lines[0][:6].decode("utf-8")) > 100: #Checking for erroneous response. throws -1023 degrees or obscenely hot temps if not connected properly
                            print("the thermometer is disconnected, or connected improperly")
                            flash_red()
                        else:
                            sendTemp(write_api, lines)

            else: # try to connect to the thermometer again
                ser = loadPT1000()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nExiting loop and clearing data")
        ser.flush()
        sys.exit()


if __name__ == "__main__":
    main()