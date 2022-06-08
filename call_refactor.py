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

# communication
from json import load
import serial
from serial import SerialException
import board
import adafruit_veml7700

# import string
import sys, os
import time
from datetime import datetime, timedelta
import atexit

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import RPi.GPIO as GPIO

# global flags
#lux_sensor_bool = False
#temp_sensor_bool = False
birdhouseID = "bh1"  # change for different point on influx


def clean():  # this is defined for atExit.
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
    buf = cmd + "\r"  # add carriage return
    try:
        ser.write(buf.encode('utf-8'))
        return True
    except SerialException as e:
        print("Error, ", e)
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
        print("Error, ", e)
        return None


# You can change the GPIO pins if you want for the LEDs
# https://pinout.xyz/ to help you out there.
def flash_green(stayOn=0):
    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.1)
    if stayOn > 0:
        GPIO.output(26, GPIO.LOW)
        time.sleep(0.1)


def flash_red(stayOn=0):
    GPIO.output(21, GPIO.HIGH)
    time.sleep(0.1)
    if stayOn > 0:
        GPIO.output(21, GPIO.LOW)
        time.sleep(0.1)


# InfluxDB definitions

token = "nyAWc7MpHrEuB0cKpUdG5aY6DEvJgiVYcQakKGsq-UNavSiv_krD1NvYik9rH0LFsYC6uz1FBwWQoiyn-us0ag=="
org = "david.pesin@gmail.com"
bucket = "david.pesin's Bucket"


def send_lux(influx_client, value):  # Sending lux
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


def send_temp(influx_client, valueBytes):  # Sending first 7 digits (including the period) of the bytes received.

    val = float(valueBytes[0][:6].decode('utf-8'))

    point = Point("birdhouse") \
        .tag("bhID", birdhouseID) \
        .field("tmp", val) \
        .time(datetime.utcnow(), WritePrecision.NS)
    try:
        influx_client.write(bucket, org, point)
    except Exception as e:
        print(e)
        for i in range(4):
            flash_red()
    else:
        flash_green()
        print(val)


# Hardware setup functions

def load_lux_sensor(lux_sensor_bool):
    # returning the veml object to be able to get data from it later

    try:
        # uses board.SCL and board.SDA -- This won't throw any error, it's just using constants 'board' has stored
        i2c = board.I2C()
        lux_sensor = adafruit_veml7700.VEML7700(i2c)
    except RuntimeError:
        print("Unable to enable VEML7700 lux sensor")
    # This is SUPER bad practice, just to catch stuff during testing to find out what exceptions can be thrown
    except Exception as e:
        print("Unknown Error, \n", e)
    else:
        lux_sensor_bool = True
        print("done!")
        return lux_sensor, lux_sensor_bool


def load_temp_sensor(temp_sensor_bool, uart_address='/dev/ttyS0'):
    # returning the serial object of the temperature probe.
    # Defaulting to the tx/rx pins, can change according to your needs

    try:
        temp_sensor_serial = serial.Serial(uart_address, 9600, timeout=0)
    except serial.SerialException as e:
        print("Error, check physical connections \n", e)
    else:
        temp_sensor_bool = True
        send_cmd("C,0", temp_sensor_serial)  # Turn off cont mode
        time.sleep(1)
        temp_sensor_serial.flush()  # Clear prior data
        print("done!")
        return temp_sensor_serial, temp_sensor_bool


def connect_influxdb():
    num_led_flash = 3
    while True:  # continuously try to connect
        # TODO: if the network is disconnected, will the script get stuck here?
        # TODO: if so, might be better to set a flag and store locally, maybe after some number of tries?
        write_api = None
        connection_bool = False
        try:
            dbclient = InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token, org=org)
            write_api = dbclient.write_api(write_options=SYNCHRONOUS)
        except Exception as e:
            print(e)
            for i in range(num_led_flash):
                flash_red()
        else:
            for i in range(num_led_flash):
                flash_green()
                connection_bool = True
            return write_api, connection_bool


def collect_lux_data(lux_sensor, write_api, lux_sensor_bool):
    # Try to get data, if fails change "lux_sensor_bool" variable
    # Initialize value for error checking
    lux_value = None
    lux_sent_bool = False

    # If sensor disconnects midway try again
    if not lux_sensor_bool:
        lux_sensor = load_lux_sensor(lux_sensor_bool)

    try:
        lux_value = lux_sensor.light  # easier lux value
    except Exception as e:
        print("failed val assignment:\n ", e)
        lux_sensor_bool = False

    # send lux data before attempting temperature data
    if lux_sensor_bool and lux_value:
        # TODO: any error checking on value?
        send_lux(write_api, lux_value)
        lux_sent_bool = True
    else:  # lux sensor isn't working, nothing is being sent
        # TODO: if saving values locally, do that here
        flash_red()

    return lux_sent_bool, lux_sensor_bool, lux_sensor


def collect_temp_data(temp_sensor_serial, write_api, temp_sensor_bool):
    temp_sent_bool = False
    lines = 'not set'
    # This will usually not fix it, if it's a serial issue there's something wrong with the RPi's setup
    if not temp_sensor_bool:
        temp_sensor_serial = load_temp_sensor(temp_sensor_bool)
    try:
        send_cmd("R", temp_sensor_serial)  # send commands
        lines = read_lines(temp_sensor_serial)  # read results
    except Exception as e:  # probably SerialException but unsure if that's the only one. Need to keep testing
        print(e)
        temp_sensor_bool = False

        # Checking results and sending temp
    if temp_sensor_bool:
        try:
            lines[0].decode("utf-8")
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
                    send_temp(write_api, lines)

    else:  # try to connect to the thermometer again
        temp_sensor_serial = load_temp_sensor(temp_sensor_bool)

    time.sleep(1)

    return temp_sent_bool, temp_sensor_bool, temp_sensor_serial


def main():
    lux_sensor_bool = False
    temp_sensor_bool = False
    # when the program terminates we will clean up GPIO information
    atexit.register(clean)

    # GPIO setup
    GPIO.setwarnings(False)
    GPIO.setup(26, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(21, GPIO.OUT, initial=GPIO.LOW)

    # TODO: elaborate on what this comment means
    # variables will change depending on if the device is on

    print("setting up VEML7700 lux sensor...")

    lux_sensor, lux_sensor_bool = load_lux_sensor(lux_sensor_bool)

    '''
    Setting up the Atlas PT-1000 thermometer through UART.
    TX/RX is '/dev/ttyS0' and it will be defined as such
    '''

    print("Connecting AtlasScientific PT-1000 temperature sensor...")

    # Try to connect to the serial port. This shouldn't fail and if it does, check your physical connections
    temp_sensor_serial, temp_sensor_bool = load_temp_sensor(temp_sensor_bool)

    # We continue if at least one sensor is working
    if lux_sensor_bool and temp_sensor_bool:
        print("all connected!")
        for i in range(3):
            flash_green()
    elif lux_sensor_bool and not temp_sensor_bool:
        print("Temperature not connected")
        flash_red()
        flash_red()
        flash_green()
    elif not lux_sensor_bool and temp_sensor_bool:
        print("lux not connected")
        flash_green()
        flash_green()
        flash_red()
    elif not lux_sensor_bool and not temp_sensor_bool:
        print("No devices connected. No point in running this.")
        flash_red(1)
        sys.exit()

    '''
    InfluxDB setup
    '''
    write_api, connection_bool = connect_influxdb()

    try:
        while True:
            '''lux'''
            # get data from lux sensor and send to influxDB
            lux_sent_bool, lux_sensor_bool, lux_sensor = collect_lux_data(lux_sensor, write_api, lux_sensor_bool)

            '''temperature'''
            # get data from pt-1000 temperature sensor and send to influxDB
            temp_sent_bool, temp_sensor_bool, temp_sensor_serial = \
                collect_temp_data(temp_sensor_serial, write_api, temp_sensor_bool)

    except KeyboardInterrupt:
        print("\n\nExiting loop and clearing data")
        temp_sensor_serial.flush()
        sys.exit()


if __name__ == "__main__":
    main()