import serial
from serial import SerialException
import board
import subprocess, os
import socket
#import pandas as pd
#import adafruit_veml7700

import json
import sys
import time
from datetime import datetime
import atexit

from influxdb_client import InfluxDBClient, Point, WritePrecision
#from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from pijuice import PiJuice
import RPi.GPIO as GPIO

#global flags
veml = True
pt1000 = False
connected = False
birdhouseID = "bh0" #change for different point on influx

#influx variables
token = "nyAWc7MpHrEuB0cKpUdG5aY6DEvJgiVYcQakKGsq-UNavSiv_krD1NvYik9rH0LFsYC6uz1FBwWQoiyn-us0ag=="
org = "david.pesin@gmail.com"
bucket = "david.pesin's Bucket"

def clean(): # this is defined for atExit.
    GPIO.cleanup()
    print("GPIO unallocated")

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

#setup and sending is done simultaneously in the C program
def getLux():
    #light = subprocess.run(['sudo', '/home/pi/Desktop/Birdhouse/getlight'], capture_output = True, text = True)
    #print("val: ", light.stdout)
    light = os.popen('/usr/bin/sudo /home/pi/Desktop/Birdhouse/getLight')
    try:
        value = int(light.read()[:4],16)
    except ValueError:
        print("something wrong was sent")
        flash_red()
        raise RuntimeError("Value Error")
    else:
        return value

def disconnect():
    retcode = os.popen('sudo ifconfig wlan0 down')
def reconnect():
    retcode = os.popen('sudo ifconfig wlan0 up')

def influxSetup():
    global connected
    try:
        dbclient = InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token, org=org)
        write_api = dbclient.write_api(write_options=SYNCHRONOUS)
    except Exception as e:
        print(e)
        connected = False
        for i in range(3):
            flash_red()
            return write_api
    else:
        for i in range(3):
            flash_green()
        connected = True
        return write_api

def get_size(fileobject):
    fileobject.seek(0,2) # move the cursor to the end of the file
    size = fileobject.tell()
    return size

def isConnected():
  try:
    # see if we can resolve the host name -- tells us if there is
    # a DNS listening
    host = socket.gethostbyname("1.1.1.1")
    # connect to the host -- tells us if the host is actually reachable
    s = socket.create_connection((host, 80), 2)
    s.close()
    return True
  except Exception:
     pass # we ignore any errors, returning False
  return False

def getBatData(pijuice):
    charge = pijuice.status.GetChargeLevel()["data"]
    temp = pijuice.status.GetBatteryTemperature()["data"]
    voltage = pijuice.status.GetBatteryVoltage()["data"]
    current = pijuice.status.GetBatteryCurrent()["data"]
    return charge, temp, voltage, current

def writeJson(file, fields, values, comma):
    global birdhouseID
    if comma > 0:
        file.write(",\n")
    filedict = {
        "measurement":"birdhouse",
        "tags": {"bhID":birdhouseID},
        "fields":{},
        "time":time.time_ns()
        }
    for i in range(len(fields)):
        filedict["fields"][fields[i]] = values[i]

    tempjson = json.dumps(filedict)
    file.write(tempjson)

def sendJson(file1, file2, file3, write_api):
    reconnect()
    connecttime = time.time()
    while not isConnected():
        if time.time() - connecttime <= 600:
            flash_red()
        else:
            return -1
    flash_green(1)
    time.sleep(10)
    write_api = influxSetup()

    file1.write("]")
    file2.write("]")
    file3.write("]")

    file1.close()
    file2.close()
    file3.close()
    
    with open('/home/pi/Desktop/Birdhouse/data/lux.json', 'r', encoding = "utf-8") as f:
        finallux  = json.load(f)
    with open('/home/pi/Desktop/Birdhouse/data/temp.json', 'r', encoding = "utf-8") as f:
        finaltemp = json.load(f)
    with open('/home/pi/Desktop/Birdhouse/data/bat.json', 'r', encoding = "utf-8") as f:
        finalbat = json.load(f)


    write_api.write(bucket, org, finallux, record_time_key="time")
    flash_green()
    write_api.write(bucket, org, finaltemp, record_time_key="time")
    flash_green()
    write_api.write(bucket, org, finalbat, record_time_key="time")
    flash_green()

    time.sleep(3)
    print("sent!")
    return 0

def main():
    reconnect()
    time.sleep(10)
    global veml, pt1000, connected


    #when the program terminates we will clean up GPIO stuff.
    atexit.register(clean)

    #GPIO setup

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(26, GPIO.OUT, initial = GPIO.LOW)
    GPIO.setup(21, GPIO.OUT, initial = GPIO.LOW)

    pj = PiJuice(1, 0x14) #Instantiate pijuice object

    #variables will change depending on if the device is on

    #print("setting up VEML7700 lux sensor...")

    #veml7700 = loadVEML()

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
    
    time.sleep(3)
    '''
    InfluxDB setup
    '''
    print("connecting to influx")
    write_api = influxSetup()
    print("done!")
    time.sleep(1)

    while True:
        #whether or not to continue writing to the same file
        cont = True
        tempfile = open('/home/pi/Desktop/Birdhouse/data/temp.json', 'w')
        luxfile = open('/home/pi/Desktop/Birdhouse/data/lux.json', 'w')
        batfile = open('/home/pi/Desktop/Birdhouse/data/bat.json', 'w')

        luxfile.write("[")
        tempfile.write("[")
        batfile.write("[")

        luxnum = 0
        batnum = 0
        tempnum = 0

        while cont == True:
            disconnect()
            start_time = time.time()
            
            while (time.time() - start_time) <= 3600:
                try:
                    #val = veml7700.light #easier lux value
                    val = getLux()
                except RuntimeError as e:
                    print("failed val assignment:\n ", e)
                else:
                    writeJson(luxfile,["lux"], [val], luxnum)
                    luxnum += 1

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
                        print(lines[0])
                        float(lines[0].decode("utf-8"))
                    except IndexError: #Nothing was sent
                        print("nothing sent; Not sending temp")
                        flash_red()
                    except UnicodeDecodeError: #What was sent isn't decodable
                        print("cannot decode data; Not sending temp")
                        flash_red()
                    except ValueError: #String was sent instead of float.
                        print("cannot cast data as float; Not sending temp")
                        flash_red()
                    else:
                        try:
                            lines[0].decode("utf-8")
                        except UnicodeDecodeError: # for some reason this isn't caught in the first part sometimes.
                            print("garbage was sent and cannot be decoded!")
                            flash_red()
                        #if not str(lines[0][0]).isdigit() and not str(lines[0][1]).isdigit(): #What was sent isn't a number.
                        #    print("expected float but got string; Not sending temp")
                        #    flash_red()
                        else:
                            if lines[0][0] == b'*'[0]: #Checking for status messages, sometimes the first message is going to be one.
                                print("status message, skipping")
                                flash_red()
                            elif float(lines[0][:6].decode("utf-8")) < -1000 or float(lines[0][:6].decode("utf-8")) > 100: #Checking for erroneous response. throws -1023 degrees or obscenely hot temps if not connected properly
                                print("the thermometer is disconnected, or connected improperly")
                                flash_red()
                            else:
                                writeJson(tempfile, ["tmp"], [float(lines[0][:6].decode("utf-8"))], tempnum)
                                tempnum += 1
                            time.sleep(3)
                else: # try to connect to the thermometer again
                    ser = loadPT1000()

                charge, tmp, voltage, current = getBatData(pj)
                writeJson(batfile, ["batTmp", "batCharge", "batVolt", "batCurrent"], [tmp, charge, voltage, current], batnum)
                batnum += 1
            else:
                retcode = sendJson(luxfile, tempfile, batfile, write_api)
                if retcode == 0:
                    cont = False

if __name__ == "__main__":
    main()
